from datetime import datetime, timedelta, time
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from django.db.models import Sum
from django.db.utils import IntegrityError
from ..utils import logging, log_tarea_fragmentada, log_timeline_update
import logging

from ..models import (
    ProgramaProduccion,
    TareaFragmentada,
    EjecucionTarea,
    ReporteDiarioPrograma,
    ProgramaOrdenTrabajo,
    ItemRuta,
    HistorialPlanificacion,
    
)

from Operator.models import AsignacionOperador

from ..serializers import (
    TareaFragmentadaSerializer,
    EjecucionTareaSerializer
)
from ..services.time_calculations import TimeCalculator
from ..services.production_scheduler import ProductionScheduler
from ..services.machine_availability import MachineAvailabilityService

# Obtener loggers específicos
logger_tareas = logging.getLogger('tareas')
logger_timeline = logging.getLogger('timeline')

class SupervisorReportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=pk)
            fecha_solicitada = request.GET.get('fecha')
            
            if not fecha_solicitada:
                # Obtener el primer día con tareas fragmentadas
                primera_tarea = TareaFragmentada.objects.filter(
                    programa=programa
                ).order_by('fecha').first()
                
                # Si no hay tareas, usar la primera fecha laboral desde el inicio del programa
                if primera_tarea:
                    fecha_solicitada = primera_tarea.fecha.strftime('%Y-%m-%d')
                else:
                    fecha_inicio = programa.fecha_inicio
                    while fecha_inicio.weekday() >= 5:  # 5=Sábado, 6=Domingo
                        fecha_inicio += timedelta(days=1)
                    fecha_solicitada = fecha_inicio.strftime('%Y-%m-%d')
            
            # Convertir a datetime para mantener consistencia
            fecha = datetime.strptime(fecha_solicitada + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
            print(f"Fecha solicitada (string): {fecha_solicitada}")
            print(f"Fecha parseada (objeto): {fecha}")
            print(f"Fecha.date() usada en filtro: {fecha.date()}")
            
            # Verificar si es día laboral (Lunes-Viernes)
            es_dia_laboral = fecha.weekday() < 5
            
            # Verificar si hay tareas para esta fecha específica
            count_tareas = TareaFragmentada.objects.filter(
                programa=programa,
                fecha=fecha.date()
            ).count()
            print(f"Número de tareas encontradas para {fecha.date()}: {count_tareas}")

            # Buscar también un día después para verificar la teoría
            fecha_siguiente = fecha + timedelta(days=1)
            count_tareas_siguiente = TareaFragmentada.objects.filter(
                programa=programa,
                fecha=fecha_siguiente.date()
            ).count()
            print(f"Número de tareas encontradas para {fecha_siguiente.date()}: {count_tareas_siguiente}")
            
            # Preparar respuesta base
            response_data = {
                'programa': {
                    'id': programa.id,
                    'nombre': programa.nombre,
                    'fecha_inicio': programa.fecha_inicio,
                    'fecha_fin': programa.fecha_fin,
                    'fecha_actual': fecha_solicitada,
                    'es_dia_laboral': es_dia_laboral
                },
                'tareas': []
            }
            
            # Si no es día laboral, retornar respuesta sin tareas
            if not es_dia_laboral:
                return Response(response_data)
            
            # Obtener prioridades actuales de las OTs
            prioridades_ot = {
                pot.orden_trabajo_id: pot.prioridad 
                for pot in ProgramaOrdenTrabajo.objects.filter(programa=programa)
            }
            
            # Obtener las tareas fragmentadas para esta fecha
            tareas_dia = TareaFragmentada.objects.filter(
                programa=programa,
                fecha=fecha.date()
            ).select_related(
                'tarea_original__proceso',
                'tarea_original__maquina',
                'tarea_original__ruta__orden_trabajo',
                'operador'
            )
            
            # Ordenar las tareas según la prioridad actual de sus OTs
            tareas_ordenadas = sorted(
                tareas_dia,
                key=lambda tarea: (
                    prioridades_ot.get(tarea.tarea_original.ruta.orden_trabajo.id, 999),
                    tarea.tarea_original.item  # Mantener el orden de los procesos dentro de la OT
                )
            )

            for tarea in tareas_ordenadas:
                item_ruta = tarea.tarea_original
                if not item_ruta:
                    continue
                    
                orden_trabajo = item_ruta.ruta.orden_trabajo
                
                tarea_data = {
                    'id': tarea.id,
                    'item_ruta_id': item_ruta.id,
                    'orden_trabajo': {
                        'id': orden_trabajo.id,
                        'codigo': orden_trabajo.codigo_ot,
                        'descripcion': orden_trabajo.descripcion_producto_ot
                    },
                    'proceso': {
                        'id': item_ruta.proceso.id,
                        'codigo': item_ruta.proceso.codigo_proceso,
                        'descripcion': item_ruta.proceso.descripcion
                    },
                    'maquina': {
                        'id': item_ruta.maquina.id,
                        'codigo': item_ruta.maquina.codigo_maquina,
                        'descripcion': item_ruta.maquina.descripcion
                    } if item_ruta.maquina else None,
                    'cantidades': {
                        'programada': float(tarea.cantidad_asignada),
                        'pendiente_anterior': float(tarea.cantidad_pendiente_anterior),
                        'total_dia': float(tarea.cantidad_total_dia),
                        'completada': float(tarea.cantidad_completada),
                        'pendiente': float(tarea.cantidad_pendiente)
                    },
                    'kilos': {
                        'fabricados': float(tarea.kilos_fabricados),
                        'programados': float(tarea.cantidad_asignada) * float(orden_trabajo.peso_unitario)
                    },
                    'estado': tarea.estado,
                    'porcentaje_cumplimiento': float(tarea.porcentaje_cumplimiento),
                    'operador': {
                        'id': tarea.operador.id,
                        'nombre': tarea.operador.nombre
                    } if tarea.operador else None,
                    'es_continuacion': tarea.es_continuacion,
                    'observaciones': tarea.observaciones
                }
                print(tarea.cantidad_completada)
                response_data['tareas'].append(tarea_data)
            
            # Para depuración - Imprimir todas las tareas fragmentadas de este programa
            todas_tareas = TareaFragmentada.objects.filter(programa=programa).order_by('fecha')
            print(f"Programa {programa.id} - Tareas fragmentadas existentes:")
            for t in todas_tareas:
                print(f"  Fecha: {t.fecha}, OT: {t.tarea_original.ruta.orden_trabajo.codigo_ot if t.tarea_original else 'N/A'}, Proceso: {t.tarea_original.proceso.descripcion if t.tarea_original else 'N/A'}")
            
            return Response(response_data)
            
        except Exception as e:
            print(f"Error en SupervisorReportView.get: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, pk):
        try:
            tarea_id = request.data.get('tarea_id')
            print(f"[DEBUG] Datos recibidos: {request.data}")
            
            with transaction.atomic():
                if tarea_id:
                    tarea = get_object_or_404(TareaFragmentada, id=tarea_id)
                    print(f"[DEBUG] Tarea encontrada: {tarea.id} - Estado: {tarea.estado}")
                else:
                    tarea = get_object_or_404(TareaFragmentada, id=pk)
                
                # Si se reciben kilos fabricados, calcular unidades
                if 'kilos_fabricados' in request.data:
                    kilos_fabricados = float(request.data.get('kilos_fabricados', 0))
                    tarea.kilos_fabricados = kilos_fabricados
                    
                    # Obtener peso unitario
                    orden_trabajo = tarea.tarea_original.ruta.orden_trabajo
                    peso_unitario = float(orden_trabajo.peso_unitario) if orden_trabajo and orden_trabajo.peso_unitario else None
                    
                    # Si no tiene peso unitario en la orden, intentar obtenerlo del producto
                    if not peso_unitario or peso_unitario <= 0:
                        try:
                            from Product.models import Producto, Pieza
                            codigo_producto = orden_trabajo.codigo_producto_salida
                            if codigo_producto:
                                try:
                                    producto = Producto.objects.get(codigo_producto=codigo_producto)
                                    peso_unitario = float(producto.peso_unitario)
                                except Producto.DoesNotExist:
                                    try:
                                        pieza = Pieza.objects.get(codigo_pieza=codigo_producto)
                                        peso_unitario = float(pieza.peso_unitario)
                                    except Pieza.DoesNotExist:
                                        pass
                        except Exception as e:
                            print(f"Error al buscar peso unitario del producto: {str(e)}")
                    
                    # Calcular unidades si tenemos peso unitario
                    if peso_unitario and peso_unitario > 0:
                        unidades_fabricadas = round(kilos_fabricados / peso_unitario)
                        tarea.unidades_fabricadas = unidades_fabricadas
                        tarea.cantidad_completada = unidades_fabricadas
                        
                # Actualizar otros campos
                if 'observaciones' in request.data:
                    tarea.observaciones = request.data.get('observaciones', '')
                
                if 'estado' in request.data:
                    tarea.estado = request.data.get('estado')
                
                # Antes de crear/actualizar EjecucionTarea
                print(f"[DEBUG] Creando/actualizando ejecución para tarea {tarea.id}")
                print(f"[DEBUG] Fecha de tarea: {tarea.fecha}")
                print(f"[DEBUG] Estado: {tarea.estado}")
                print(f"[DEBUG] Cantidad completada: {tarea.cantidad_completada}")

                now = timezone.now()
                fecha_hora = timezone.datetime.combine(
                    tarea.fecha,
                    now.time(),
                    tzinfo=timezone.get_current_timezone()
                )
                print(f"[DEBUG] Fecha hora calculada: {fecha_hora}")

                ejecucion, created = EjecucionTarea.objects.get_or_create(
                    tarea=tarea,
                    fecha_hora_inicio__date=tarea.fecha,
                    defaults={
                        'fecha_hora_inicio': fecha_hora,
                        'fecha_hora_fin': fecha_hora,
                        'cantidad_producida': tarea.cantidad_completada,
                        'operador': tarea.operador,
                        'estado': tarea.estado
                    }
                )
                print(f"[DEBUG] Ejecución {'creada' if created else 'actualizada'}: {ejecucion.id}")

                if not created:
                    ejecucion.fecha_hora_fin = fecha_hora
                    ejecucion.cantidad_producida = tarea.cantidad_completada
                    ejecucion.estado = tarea.estado
                    ejecucion.save()
                    print(f"[DEBUG] Ejecución actualizada con nueva fecha fin: {ejecucion.fecha_hora_fin}")

                tarea.save()
                
                # Verificar registros después de guardar
                ejecuciones = EjecucionTarea.objects.filter(
                    tarea__programa_id=tarea.programa_id,
                    fecha_hora_inicio__date=tarea.fecha
                )
                print(f"[DEBUG] Total de ejecuciones para el día: {ejecuciones.count()}")
                for e in ejecuciones:
                    print(f"[DEBUG] - Ejecución {e.id}: Tarea {e.tarea_id}, Estado {e.estado}, Cantidad {e.cantidad_producida}")

                return Response({
                    'message': 'Tarea actualizada correctamente',
                    'tarea': TareaFragmentadaSerializer(tarea).data
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TimelineEjecucionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def crear_ejecuciones_por_avance(self, programa, fecha):
        """
        Crea registros de ejecución para todas las tareas que tienen avance pero no tienen registro
        """
        print(f"[DEBUG] Creando ejecuciones por avance para programa {programa.id} fecha {fecha}")
        
        # Buscar todas las tareas que tienen avance
        tareas_con_avance = TareaFragmentada.objects.filter(
            programa=programa,
            fecha=fecha,
            cantidad_completada__gt=0  # Tareas que tienen algún avance
        ).select_related(
            'tarea_original__proceso',
            'tarea_original__maquina',
            'tarea_original__ruta__orden_trabajo',
            'operador'
        ).order_by(
            'tarea_original__ruta__orden_trabajo__codigo_ot',
            'tarea_original__item'
        )
        
        print(f"[DEBUG] Encontradas {tareas_con_avance.count()} tareas con avance")
        ejecuciones_creadas = 0
        
        for tarea in tareas_con_avance:
            # Verificar si ya existe una ejecución para esta tarea en esta fecha
            ejecucion_existente = EjecucionTarea.objects.filter(
                tarea=tarea,
                fecha_hora_inicio__date=fecha
            ).exists()
            
            if not ejecucion_existente:
                # Crear nueva ejecución
                fecha_hora = timezone.datetime.combine(
                    fecha,
                    timezone.now().time(),
                    tzinfo=timezone.get_current_timezone()
                )
                
                EjecucionTarea.objects.create(
                    tarea=tarea,
                    fecha_hora_inicio=fecha_hora,
                    fecha_hora_fin=fecha_hora,
                    cantidad_producida=tarea.cantidad_completada,
                    operador=tarea.operador,
                    estado=tarea.estado
                )
                ejecuciones_creadas += 1
                print(f"[DEBUG] Creada ejecución para tarea {tarea.id} - OT: {tarea.tarea_original.ruta.orden_trabajo.codigo_ot} - Proceso: {tarea.tarea_original.proceso.descripcion}")
        
        print(f"[DEBUG] Total de ejecuciones creadas: {ejecuciones_creadas}")
        return ejecuciones_creadas

    def get(self, request, pk):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=pk)
            fecha_solicitada = request.GET.get('fecha', programa.fecha_inicio.strftime('%Y-%m-%d'))
            fecha = datetime.strptime(fecha_solicitada, '%Y-%m-%d').date()
            
            print(f"[DEBUG] Buscando ejecuciones para programa {pk} en fecha {fecha}")
            
            # Crear ejecuciones para tareas con avance que no tengan registro
            ejecuciones_creadas = self.crear_ejecuciones_por_avance(programa, fecha)
            if ejecuciones_creadas > 0:
                print(f"[DEBUG] Se crearon {ejecuciones_creadas} nuevas ejecuciones")
            
            # NUEVO: Obtener prioridades actuales de las OTs
            prioridades_ot = {
                pot.orden_trabajo_id: pot.prioridad 
                for pot in ProgramaOrdenTrabajo.objects.filter(programa=programa)
            }
            print(f"[DEBUG] Prioridades actuales de OTs: {prioridades_ot}")
            
            # Estructura para guardar las OTs y sus procesos
            ot_grupos = {}
            items = []
            
            # 1. Obtener todas las tareas fragmentadas para esa fecha
            tareas_fragmentadas = TareaFragmentada.objects.filter(
                programa=programa,
                fecha=fecha
            ).select_related(
                'tarea_original__proceso',
                'tarea_original__maquina',
                'tarea_original__ruta__orden_trabajo',
                'operador'
            )
            
            # 2. Agrupar por orden de trabajo
            for tarea in tareas_fragmentadas:
                item_ruta = tarea.tarea_original
                orden_trabajo = item_ruta.ruta.orden_trabajo
                
                # Crear grupo para la OT si no existe
                ot_id = f"ot_{orden_trabajo.id}"
                if ot_id not in ot_grupos:
                    ot_grupos[ot_id] = {
                        'id': ot_id,
                        'orden_trabajo_codigo_ot': orden_trabajo.codigo_ot,
                        'descripcion': orden_trabajo.descripcion_producto_ot,
                        'prioridad': prioridades_ot.get(orden_trabajo.id, 999),  # NUEVO: Guardar la prioridad actual
                        'procesos': []
                    }
                
                # Agregar proceso si no existe
                proceso_id = f"proc_{item_ruta.id}"
                if not any(p['id'] == proceso_id for p in ot_grupos[ot_id]['procesos']):
                    ot_grupos[ot_id]['procesos'].append({
                        'id': proceso_id,
                        'descripcion': item_ruta.proceso.descripcion,
                        'item': item_ruta.item
                    })
                
                # 3. Buscar ejecución existente para esta tarea o crear uno temporal para la visualización
                ejecucion = EjecucionTarea.objects.filter(
                    tarea=tarea,
                    fecha_hora_inicio__date=fecha
                ).first()
                
                if ejecucion:
                    # Usar datos de la ejecución existente
                    items.append({
                        'id': f"item_{ejecucion.id}",
                        'ot_id': ot_id,
                        'proceso_id': proceso_id,
                        'name': item_ruta.proceso.descripcion,
                        'start_time': ejecucion.fecha_hora_inicio.strftime('%Y-%m-%d %H:%M:%S'),
                        'end_time': ejecucion.fecha_hora_fin.strftime('%Y-%m-%d %H:%M:%S'),
                    'estado': ejecucion.estado,
                        'cantidad_intervalo': float(ejecucion.cantidad_producida),
                        'cantidad_total': float(tarea.cantidad_asignada),
                        'porcentaje_avance': float(tarea.porcentaje_cumplimiento)
                    })
                else:
                    # Crear item temporal para visualización
                    # Utilizar fecha planificada inicio y fin si existen
                    fecha_inicio = tarea.fecha_planificada_inicio or datetime.combine(
                        fecha, time(7, 45)
                    )
                    
                    # Si no hay fecha fin planificada, calcular basado en estándar
                    if tarea.fecha_planificada_fin:
                        fecha_fin = tarea.fecha_planificada_fin
                    elif item_ruta.estandar > 0:
                        duracion_horas = float(tarea.cantidad_asignada) / float(item_ruta.estandar)
                        fecha_fin = fecha_inicio + timedelta(hours=duracion_horas)
                    else:
                        fecha_fin = fecha_inicio + timedelta(hours=1)  # 1 hora por defecto
                    
                    items.append({
                        'id': f"temp_item_{tarea.id}",
                        'ot_id': ot_id,
                        'proceso_id': proceso_id,
                        'name': item_ruta.proceso.descripcion,
                        'start_time': fecha_inicio.strftime('%Y-%m-%d %H:%M:%S'),
                        'end_time': fecha_fin.strftime('%Y-%m-%d %H:%M:%S'),
                        'estado': tarea.estado,
                        'cantidad_intervalo': 0,  # No hay avance todavía
                        'cantidad_total': float(tarea.cantidad_asignada),
                        'porcentaje_avance': 0,
                        'es_temporal': True  # Indicador de que es un item temporal
                    })
            
            # NUEVO: Ordenar los grupos por prioridad actual antes de devolverlos
            grupos_ordenados = sorted(
                list(ot_grupos.values()), 
                key=lambda g: g['prioridad']
            )
            
            return Response({
                'programa': {
                    'id': programa.id,
                    'nombre': programa.nombre,
                    'fecha': fecha_solicitada
                },
                'groups': grupos_ordenados,  # MODIFICADO: Ahora devuelve grupos ordenados por prioridad
                'items': items
            })
            
        except Exception as e:
            print(f"Error en TimelineEjecucionView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ReporteSupervisorListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            fecha_inicio = request.GET.get('fecha_inicio')
            fecha_fin = request.GET.get('fecha_fin')
            programa_id = request.GET.get('programa_id')
            
            # Filtrar reportes
            reportes = ReporteDiarioPrograma.objects.all()
            
            if fecha_inicio:
                reportes = reportes.filter(fecha__gte=fecha_inicio)
            if fecha_fin:
                reportes = reportes.filter(fecha__lte=fecha_fin)
            if programa_id:
                reportes = reportes.filter(programa_id=programa_id)
                
            reportes = reportes.select_related('programa')
            
            data = []
            for reporte in reportes:
                data.append({
                    'id': reporte.id,
                    'fecha': reporte.fecha,
                    'programa': {
                        'id': reporte.programa.id,
                        'nombre': reporte.programa.nombre
                    },
                    'total_tareas': reporte.total_tareas,
                    'tareas_completadas': reporte.tareas_completadas,
                    'porcentaje_cumplimiento': float(reporte.porcentaje_cumplimiento),
                    'observaciones': reporte.observaciones
                })
                
            return Response(data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ResumenDiarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, programa_id, fecha):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()

            # Obtener todas las tareas del programa hasta la fecha
            tareas = TareaFragmentada.objects.filter(
                programa=programa,
                fecha__lte=fecha_obj
            ).select_related(
                'tarea_original__ruta__orden_trabajo'
            )

            # Calcular totales
            kilos_totales = 0
            kilos_fabricados = 0

            for tarea in tareas:
                orden_trabajo = tarea.tarea_original.ruta.orden_trabajo
                peso_unitario = float(orden_trabajo.peso_unitario) if orden_trabajo.peso_unitario else 0
                
                # Kilos totales (programados)
                kilos_totales += float(tarea.cantidad_asignada) * peso_unitario
                
                # Kilos fabricados (completados)
                if tarea.estado in ['COMPLETADO', 'CONTINUADO']:
                    kilos_fabricados += float(tarea.kilos_fabricados)

            # Calcular porcentaje de progreso
            porcentaje_progreso = (kilos_fabricados / kilos_totales * 100) if kilos_totales > 0 else 0

            return Response({
                'kilos_totales': round(kilos_totales, 2),
                'kilos_fabricados': round(kilos_fabricados, 2),
                'porcentaje_progreso': round(porcentaje_progreso, 2)
            })
        
        except Exception as e:
            print(f"Error en ResumenDiarioView.get: {str(e)}")  # Para debugging
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FinalizarDiaView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.time_calculator = TimeCalculator()
        self.production_scheduler = ProductionScheduler(self.time_calculator)

    def get(self, request, programa_id, fecha_str):
        """Previsualiza el cierre del día"""
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            try:
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verificar si el día ya está cerrado
            reporte_existente = ReporteDiarioPrograma.objects.filter(
                programa=programa,
                fecha=fecha_obj,
                estado='CERRADO'
            ).first()
            
            if reporte_existente:
                return Response({
                    'error': 'Este día ya está cerrado',
                    'fecha_cierre': reporte_existente.fecha_cierre
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verificar si existe un reporte para este día
            reporte = ReporteDiarioPrograma.objects.filter(
                programa=programa,
                fecha=fecha_obj
            ).first()
            
            if not reporte:
                return Response({
                    'error': 'No existe un reporte para esta fecha'
                }, status=status.HTTP_404_NOT_FOUND)

            # Obtener tareas incompletas
            tareas_incompletas = TareaFragmentada.objects.filter(
                programa=programa,
                fecha=fecha_obj,
                estado__in=['PENDIENTE', 'EN_PROCESO']
            ).select_related(
                'tarea_original__proceso',
                'tarea_original__maquina',
                'tarea_original__ruta__orden_trabajo'
            )

            preview_data = {
                'fecha': fecha_str,
                'siguiente_dia': self.obtener_siguiente_dia_laboral(fecha_obj).strftime('%Y-%m-%d'),
                'tareas_pendientes': []
            }

            for tarea in tareas_incompletas:
                if tarea.cantidad_pendiente > 0:
                    preview_data['tareas_pendientes'].append({
                        'id': tarea.id,
                        'orden_trabajo': tarea.tarea_original.ruta.orden_trabajo.codigo_ot,
                        'proceso': tarea.tarea_original.proceso.descripcion,
                        'cantidad_pendiente': float(tarea.cantidad_pendiente),
                        'porcentaje_completado': float(tarea.porcentaje_cumplimiento)
                    })

            return Response(preview_data)

        except ProgramaProduccion.DoesNotExist:
            return Response({
                'error': 'Programa no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': f'Error al obtener preview: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def post(self, request, programa_id, fecha_str):
        cambios = []
        historial = None
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            fecha_actual = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            
            # 1. Verificaciones iniciales (reporte diario y historial existente)
            reporte_actual = get_object_or_404(
                ReporteDiarioPrograma,
                programa=programa,
                fecha=fecha_actual
            )

            if reporte_actual.estado == 'CERRADO':
                return Response({
                    'error': 'Este día ya está cerrado'
                }, status=status.HTTP_400_BAD_REQUEST)

            historial_existente = HistorialPlanificacion.objects.filter(
                programa=programa,
                fecha_referencia=fecha_actual,
                tipo_reajuste='DIARIO'
            ).exists()

            if historial_existente:
                return Response({
                    'error': 'Ya existe un intento de finalización para este día. Por favor, regenere el programa si necesita volver a intentarlo.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 2. IMPORTANTE: Obtener la timeline base actual ANTES de cualquier modificación
            program_ots = ProgramaOrdenTrabajo.objects.filter(
                programa=programa
            ).select_related(
                'orden_trabajo',
                'orden_trabajo__ruta_ot'
            ).prefetch_related(
                'orden_trabajo__ruta_ot__items',
                'orden_trabajo__ruta_ot__items__proceso',
                'orden_trabajo__ruta_ot__items__maquina'
            ).order_by('prioridad')

            # Usar el mismo método que usa la vista principal para obtener la timeline base
            timeline_base = self.production_scheduler.generate_timeline_data(programa, program_ots)
            siguiente_dia_laboral = self.obtener_siguiente_dia_laboral(fecha_actual)

            # 3. Crear el historial ANTES de realizar modificaciones
            historial = HistorialPlanificacion.objects.create(
                programa=programa,
                fecha_referencia=fecha_actual,
                tipo_reajuste='DIARIO',
                reporte_diario=reporte_actual,
                timeline_data={
                    'grupos': timeline_base.get('groups', []),
                    'items': timeline_base.get('items', []),
                    'metadata': {
                        'fecha_referencia': fecha_actual.isoformat(),
                        'fecha_siguiente': siguiente_dia_laboral.isoformat(),
                        'tareas_totales': 0,  # Se actualizará después
                        'fecha_cierre': timezone.now().isoformat()
                    }
                }
            )

            # 4. Procesar las tareas del día actual
            tareas_dia = TareaFragmentada.objects.filter(
                programa=programa,
                fecha=fecha_actual
            ).select_related(
                'tarea_original__proceso',
                'tarea_original__maquina',
                'tarea_original__ruta__orden_trabajo',
                'operador'
            )

            # 5. Validar cantidades
            for tarea in tareas_dia:
                try:
                    cantidad_asignada = float(tarea.cantidad_asignada)
                    cantidad_completada = float(tarea.cantidad_completada)
                    kilos_fabricados = float(tarea.kilos_fabricados)
                    
                    if cantidad_asignada < 0 or cantidad_completada < 0 or kilos_fabricados < 0:
                        raise ValueError(f"La tarea {tarea.id} tiene cantidades negativas")
                    
                    if cantidad_completada > cantidad_asignada:
                        print(f"Aviso: La tarea {tarea.id} completó más unidades ({cantidad_completada}) que las asignadas ({cantidad_asignada})")
                    
                except (ValueError, TypeError) as e:
                    return Response({
                        'error': f'Error en los datos de la tarea {tarea.id}: {str(e)}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 6. Procesar cada tarea PERO NO actualizar estado aún
            for tarea in tareas_dia:
                estado_original = {
                    'id': tarea.id,
                    'estado': tarea.estado,
                    'cantidad_pendiente': float(tarea.cantidad_pendiente),
                    'cantidad_completada': float(tarea.cantidad_completada)
                }

                if tarea.cantidad_pendiente > 0:
                    # Crear continuación sin cambiar el estado
                    tarea_continuada = self._crear_o_actualizar_continuacion(
                        tarea=tarea,
                        siguiente_dia=siguiente_dia_laboral,
                        cantidad_pendiente=tarea.cantidad_pendiente
                    )
                    
                    cambios.append({
                        'tarea_id': tarea.id,
                        'tipo': 'CONTINUACION',
                        'estado_original': estado_original,
                        'estado_nuevo': {
                            'continuacion_id': tarea_continuada.id,
                            'cantidad_pendiente': float(tarea.cantidad_pendiente),
                            'fecha_continuacion': siguiente_dia_laboral.isoformat()
                        }
                    })
                else:
                    # Marcar como completada inmediatamente
                    tarea.estado = 'COMPLETADO'
                    tarea.save()
                    
                    cambios.append({
                        'tarea_id': tarea.id,
                        'tipo': 'COMPLETADO',
                        'estado_original': estado_original,
                        'estado_nuevo': {
                            'estado': 'COMPLETADO',
                            'cantidad_completada': float(tarea.cantidad_completada)
                        }
                    })

            # 7. Reorganizar la timeline para el siguiente día
            self.reorganizar_timeline(programa, siguiente_dia_laboral)
            
            # 8. Capturar la timeline actualizada DESPUÉS de los cambios
            timeline_actualizada = self.production_scheduler.generate_timeline_data(programa, program_ots)
            
            # 9. Actualizar el historial con todos los datos
            historial.timeline_data = {
                'grupos': [
                    {
                        'id': grupo.get('id'),
                        'codigo_ot': grupo.get('orden_trabajo_codigo_ot'),
                        'descripcion': grupo.get('descripcion'),
                        'procesos': grupo.get('procesos', [])
                    } for grupo in timeline_actualizada.get('groups', [])
                ],
                'items': [
                    {
                        'id': item.get('id'),
                        'grupo_id': item.get('ot_id'),
                        'proceso_id': item.get('proceso_id'),
                        'nombre': item.get('name'),
                        'inicio': item.get('start_time'),
                        'fin': item.get('end_time'),
                        'cantidad_total': float(item.get('cantidad_total', 0)),
                        'cantidad_intervalo': float(item.get('cantidad_intervalo', 0)),
                        'estado': item.get('estado', 'PENDIENTE'),
                        'es_continuacion': item.get('es_continuacion', False),
                        'porcentaje_avance': item.get('porcentaje_avance', 0)
                    } for item in timeline_actualizada.get('items', [])
                ],
                'cambios': cambios,
                    'metadata': {
                        'fecha_referencia': fecha_actual.isoformat(),
                        'fecha_siguiente': siguiente_dia_laboral.isoformat(),
                        'tareas_totales': tareas_dia.count(),
                    'tareas_completadas': len([c for c in cambios if c['tipo'] == 'COMPLETADO']),
                    'tareas_continuadas': len([c for c in cambios if c['tipo'] == 'CONTINUACION']),
                        'fecha_cierre': timezone.now().isoformat()
                    }
                }
            historial.save()

            # 10. AHORA SÍ actualizar los estados de las tareas con continuaciones
            for tarea in tareas_dia:
                if tarea.cantidad_pendiente > 0 and tarea.estado != 'COMPLETADO':
                    tarea.estado = 'CONTINUADO'
                    tarea.save()

            # 11. Actualizar el reporte y crear uno para el siguiente día
            reporte_actual.estado = 'CERRADO'
            reporte_actual.cerrado_por = request.user
            reporte_actual.fecha_cierre = timezone.now()
            reporte_actual.save()

            ReporteDiarioPrograma.objects.get_or_create(
                programa=programa,
                fecha=siguiente_dia_laboral,
                defaults={'estado': 'ABIERTO'}
            )

            return Response({
                'message': 'Día finalizado correctamente',
                'siguiente_dia': siguiente_dia_laboral.strftime('%Y-%m-%d'),
                    'cambios_realizados': len(cambios),
                    'historial_id': historial.id
            })

        except Exception as e:
            print(f"Error en FinalizarDiaView.post: {str(e)}")
            import traceback
            traceback.print_exc()
    
            # Si se creó el historial pero hubo un error, eliminarlo
            if historial:
                historial.delete()
            
            return Response({
                'error': f'Error al finalizar el día: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def obtener_siguiente_dia_laboral(self, fecha):
        """Obtiene el siguiente día laboral (excluye fines de semana)"""
        siguiente_dia = fecha + timedelta(days=1)
        while siguiente_dia.weekday() >= 5:  # 5 = Sábado, 6 = Domingo
            siguiente_dia += timedelta(days=1)
        return siguiente_dia
    
    def reorganizar_timeline(self, programa, fecha):
        """
        Reorganiza la timeline para el día especificado, considerando conflictos de máquina
        """
        try:
            # Obtener todas las tareas del día con las relaciones necesarias
            tareas = TareaFragmentada.objects.filter(
                programa=programa,
                fecha=fecha
            ).select_related(
                'tarea_original__proceso',
                'tarea_original__maquina',
                    'tarea_original__ruta__orden_trabajo',
                    'tarea_original__ruta__orden_trabajo__programaordentrabajo'
            ).order_by(
                    'tarea_original__ruta__orden_trabajo__programaordentrabajo__prioridad',
                'tarea_original__item'
            )
        
            # Agrupar tareas por máquina
            tareas_por_maquina = {}
            for tarea in tareas:
                    maquina_id = tarea.tarea_original.maquina.id
                    if maquina_id not in tareas_por_maquina:
                        tareas_por_maquina[maquina_id] = []
                    tareas_por_maquina[maquina_id].append(tarea)

            # Para cada máquina, reorganizar sus tareas
            for maquina_id, tareas_maquina in tareas_por_maquina.items():
                hora_inicio = datetime.combine(fecha, time(7, 45))  # Hora de inicio del día
                
                for tarea in tareas_maquina:
                    # Establecer hora de inicio y fin
                    tarea.fecha_planificada_inicio = hora_inicio
                    duracion = timedelta(hours=float(tarea.cantidad_asignada) / float(tarea.tarea_original.estandar))
                    tarea.fecha_planificada_fin = hora_inicio + duracion
                    tarea.save()
                    
                    # La próxima tarea comienza después de esta
                    hora_inicio = tarea.fecha_planificada_fin + timedelta(minutes=30)  # 30 minutos de setup
                    
                    # Si pasamos las 17:45, pasar al siguiente día
                    if hora_inicio.time() > time(17, 45):
                        siguiente_dia = self.obtener_siguiente_dia_laboral(fecha)
                        hora_inicio = datetime.combine(siguiente_dia, time(7, 45))

        except Exception as e:
            print(f"Error en reorganizar_timeline: {str(e)}")
            import traceback
            traceback.print_exc()

    def _crear_o_actualizar_continuacion(self, tarea, siguiente_dia, cantidad_pendiente):
        try:
            # Log inicio de operación
            log_tarea_fragmentada(logger_tareas, 'INICIO_CREAR_CONTINUACION', tarea, {
                'siguiente_dia': siguiente_dia,
                'cantidad_pendiente': cantidad_pendiente
            })

            # Buscar continuación existente con una consulta más específica
            tarea_continuada = TareaFragmentada.objects.filter(
                tarea_original=tarea.tarea_original,
                fecha=siguiente_dia,
                programa=tarea.programa  # Añadido para mayor especificidad
            ).order_by('es_continuacion', '-nivel_fragmentacion').first()
            
            # Asegurar que cantidad_pendiente sea float
            cantidad_pendiente = float(cantidad_pendiente)
            
            if tarea_continuada:
                # Actualizar la continuación existente
                tarea_continuada.cantidad_asignada = cantidad_pendiente
                tarea_continuada.cantidad_pendiente_anterior = cantidad_pendiente
                tarea_continuada.estado = 'PENDIENTE'
                tarea_continuada.es_continuacion = True
                tarea_continuada.tarea_padre = tarea
                tarea_continuada.nivel_fragmentacion = tarea.nivel_fragmentacion + 1
                tarea_continuada.operador = tarea.operador
                tarea_continuada.fecha_planificada_inicio = None  # Se recalculará
                tarea_continuada.fecha_planificada_fin = None  # Se recalculará
                tarea_continuada.save()
                
                log_tarea_fragmentada(logger_tareas, 'ACTUALIZACION_CONTINUACION', tarea_continuada)
            else:
                # Crear nueva continuación
                tarea_continuada = TareaFragmentada.objects.create(
                    tarea_original=tarea.tarea_original,
                    tarea_padre=tarea,
                    programa=tarea.programa,
                    fecha=siguiente_dia,
                    cantidad_asignada=cantidad_pendiente,
                    cantidad_pendiente_anterior=cantidad_pendiente,
                    es_continuacion=True,
                    nivel_fragmentacion=tarea.nivel_fragmentacion + 1,
                    estado='PENDIENTE',
                    operador=tarea.operador,
                    kilos_fabricados=0,
                    cantidad_completada=0
                )
                
                log_tarea_fragmentada(logger_tareas, 'NUEVA_CONTINUACION', tarea_continuada)
            
            # Calcular nuevas fechas de planificación basadas en estándares
            if tarea_continuada.tarea_original.estandar > 0:
                from ..services.time_calculations import TimeCalculator
                calculator = TimeCalculator()
                fecha_inicio = datetime.combine(siguiente_dia, time(7, 45))
                calculo = calculator.calculate_working_days(
                    fecha_inicio,
                    float(cantidad_pendiente),
                    float(tarea_continuada.tarea_original.estandar)
                )
                
                if 'error' not in calculo:
                    tarea_continuada.fecha_planificada_inicio = calculo['intervals'][0]['fecha_inicio']
                    tarea_continuada.fecha_planificada_fin = calculo['next_available_time']
                    tarea_continuada.save()
            
            return tarea_continuada
            
        except Exception as e:
            print(f"Error en _crear_o_actualizar_continuacion: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Intentar crear de manera segura
            return TareaFragmentada.objects.create(
                tarea_original=tarea.tarea_original,
                tarea_padre=tarea,
                programa=tarea.programa,
                fecha=siguiente_dia,
                cantidad_asignada=cantidad_pendiente,
                cantidad_pendiente_anterior=cantidad_pendiente,
                es_continuacion=True,
                nivel_fragmentacion=tarea.nivel_fragmentacion + 1,
                estado='PENDIENTE',
                operador=tarea.operador,
                kilos_fabricados=0,
                cantidad_completada=0
            )

    def _procesar_tarea_fin_dia(self, tarea, fecha_actual):
        log_tarea_fragmentada(logger_tareas, 'INICIO_PROCESAR_FIN_DIA', tarea)
        cambios = []
        estado_original = {
                'estado': tarea.estado,
            'cantidad_completada': float(tarea.cantidad_completada),
            'cantidad_pendiente': float(tarea.cantidad_pendiente)
        }

        # CORRECCIÓN: Calcular porcentaje basado en la cantidad asignada, no en cantidad_total_dia
        porcentaje_cumplimiento = (float(tarea.cantidad_completada) / float(tarea.cantidad_asignada)) * 100 if float(tarea.cantidad_asignada) > 0 else 0

        # Si la tarea está completada (100% o más)
        if porcentaje_cumplimiento >= 100:
            tarea.estado = 'COMPLETADO'
            tarea.save()

            # Eliminar TODAS las continuaciones futuras relacionadas
            continuaciones_futuras = TareaFragmentada.objects.filter(
                tarea_original=tarea.tarea_original,
                fecha__gt=fecha_actual,
                es_continuacion=True
            )
            
            for continuacion in continuaciones_futuras:
                continuacion.delete()

            cambios.append({
                'tarea_id': tarea.id,
                'tipo': 'COMPLETADO',
                'estado_original': estado_original,
                'estado_nuevo': {
                    'estado': 'COMPLETADO',
                    'cantidad_completada': float(tarea.cantidad_completada),
                    'continuaciones_eliminadas': [c.id for c in continuaciones_futuras]
                }
            })
        # Solo crear continuación si realmente hay pendiente
        elif tarea.cantidad_pendiente > 0:
            siguiente_dia = self.obtener_siguiente_dia_laboral(fecha_actual)
            tarea_continuada = self._crear_o_actualizar_continuacion(
                tarea=tarea,
                siguiente_dia=siguiente_dia,
                cantidad_pendiente=tarea.cantidad_pendiente
            )
            
            tarea.estado = 'CONTINUADO'
            tarea.save()

            cambios.append({
                'tarea_id': tarea.id,
                'tipo': 'CONTINUACION',
                'estado_original': estado_original,
                'estado_nuevo': {
                    'estado': 'CONTINUADO',
                    'continuacion_id': tarea_continuada.id,
                    'cantidad_pendiente': float(tarea.cantidad_pendiente)
                }
            })
        else:
            # Si no hay pendiente, marcar como completada
            tarea.estado = 'COMPLETADO'
            tarea.save()

        return cambios
 


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerar_tareas_programa(request, programa_id):
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        
        # Eliminar tareas fragmentadas existentes
        TareaFragmentada.objects.filter(programa=programa).delete()
        
        # Eliminar reportes diarios existentes
        ReporteDiarioPrograma.objects.filter(programa=programa).delete()
        
        time_calculator = TimeCalculator()
        scheduler = ProductionScheduler(time_calculator)
        
        # Obtener datos del timeline
        program_ots = ProgramaOrdenTrabajo.objects.filter(
            programa=programa
        ).select_related(
            'orden_trabajo',
            'orden_trabajo__ruta_ot'
        ).prefetch_related(
            'orden_trabajo__ruta_ot__items',
            'orden_trabajo__ruta_ot__items__proceso',
            'orden_trabajo__ruta_ot__items__maquina'
        ).order_by('prioridad')
        
        # Preparar datos para la regeneración
        ordenes_trabajo = []
        for prog_ot in program_ots:
            ot = prog_ot.orden_trabajo
            ot_data = {
                'orden_trabajo': ot.id,
                'orden_trabajo_codigo_ot': ot.codigo_ot,
                'orden_trabajo_descripcion_producto_ot': ot.descripcion_producto_ot,
                'procesos': []
            }

            ruta = getattr(ot, 'ruta_ot', None)
            if ruta:
                for item in ruta.items.all().order_by('item'):
                    proceso_data = {
                        'id': item.id,
                        'item': item.item,
                        'descripcion': item.proceso.descripcion if item.proceso else None,
                        'maquina_id': item.maquina.id if item.maquina else None,
                        'cantidad': item.cantidad_pedido,
                        'estandar': item.estandar,
                        'prioridad': prog_ot.prioridad
                    }
                    ot_data['procesos'].append(proceso_data)
            
            ordenes_trabajo.append(ot_data)
        
        # Regenerar tareas fragmentadas
        success = scheduler.create_fragmented_tasks(programa, ordenes_trabajo)
        
        if success:
            return Response({
                'message': 'Tareas fragmentadas regeneradas correctamente',
                'tareas_generadas': TareaFragmentada.objects.filter(programa=programa).count()
            })
        else:
            return Response(
                {'error': 'Error al regenerar tareas fragmentadas'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except Exception as e:
        print(f"Error regenerando tareas: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_production_details(request, task_id):
    try:
        tarea = TareaFragmentada.objects.select_related(
            'tarea_original__ruta__orden_trabajo',
            'tarea_original__proceso',
            'tarea_original__maquina',
            'operador'
        ).get(id=task_id)
        
        return Response({
            'numero_ot': tarea.tarea_original.ruta.orden_trabajo.codigo_ot,
            'etapa': tarea.tarea_original.item,
            'cantidad_unidades': tarea.cantidad_asignada,
            'saldo_pendiente': tarea.cantidad_pendiente,
            'codigo_producto': tarea.tarea_original.ruta.orden_trabajo.codigo_producto_salida,
            'nombre_producto': tarea.tarea_original.ruta.orden_trabajo.descripcion_producto_ot,
            'materia_prima': tarea.tarea_original.ruta.orden_trabajo.materia_prima.descripcion if tarea.tarea_original.ruta.orden_trabajo.materia_prima else '',
            'proceso': tarea.tarea_original.proceso.descripcion,
            'maquina': tarea.tarea_original.maquina.descripcion,
            'estandar_hora': tarea.tarea_original.estandar,
            'rut_trabajador': tarea.operador.rut if tarea.operador else '',
            'horas_trabajadas': 0,  # Esto vendría de EjecucionTarea
            'sobretiempo': 0,  # Esto vendría de EjecucionTarea
        })
    except TareaFragmentada.DoesNotExist:
        return Response(
            {"error": "Tarea no encontrada"},
            status=status.HTTP_404_NOT_FOUND
        )