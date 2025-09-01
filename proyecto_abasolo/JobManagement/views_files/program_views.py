import trace
from django.db import transaction
from django.utils.dateparse import parse_date
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, time, timedelta

from numpy import isin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics
from rest_framework.authentication import TokenAuthentication, SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view

from ..models import (
    ProgramaProduccion, 
    ProgramaOrdenTrabajo, 
    OrdenTrabajo, 
    Proceso,
    Maquina,
    ItemRuta,
    RutaOT,
    TareaFragmentada,
    EmpresaOT,
    ReporteDiarioPrograma,
    HistorialPlanificacion,
    Ruta, RutaPieza,
    EstandarMaquinaProceso
)
from Operator.models import AsignacionOperador, Operador
from ..serializers import ProgramaProduccionSerializer, EmpresaOTSerializer
from ..services.time_calculations import TimeCalculator
from ..services.production_scheduler import ProductionScheduler
from ..services.machine_availability import MachineAvailabilityService

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A3, A2, A1
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

import traceback, logging, os


class ProgramListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = ProgramaProduccion.objects.all()
    serializer_class = ProgramaProduccionSerializer

    def delete(self, request, pk):
        try:
            print(f"Intentando eliminar el programa con ID: {pk}")
            programa = ProgramaProduccion.objects.get(id=pk)
            ordenes_asociadas = ProgramaOrdenTrabajo.objects.filter(programa=programa)

            if ordenes_asociadas.exists():
                ordenes_asociadas.delete()
                print(f"Ordenes de trabajo asociadas eliminadas para programa {pk}")
            
            programa.delete()
            print(f"Programa {pk} eliminado exitósamente.")
            return Response({
                "message": "Programa eliminado correctamente"
            }, status=status.HTTP_200_OK)
        
        except ProgramaProduccion.DoesNotExist:
            print(f"Programa {pk} no encontrado")
            return Response({
                "error": "Programa no encontrado"
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            print(f"Error al eliminar el programa {pk}: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": f"Error al eliminar el programa: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      
class ProgramCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        data = request.data
        
        # Validar datos requeridos (mantenemos validación existente)
        if 'fecha_inicio' not in data:
            return Response(
                {"detail": "Fecha de inicio es requerida."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificación inicial de OTs (mantenemos código existente)
        for ot_id in data.get('ordenes', []):
            print(f"Verificando OT con ID: {ot_id}")
            try:
                orden_trabajo = OrdenTrabajo.objects.select_related(
                    'ruta_ot',
                    'situacion_ot'
                ).prefetch_related(
                    'ruta_ot__items',
                    'ruta_ot__items__proceso',
                    'ruta_ot__items__maquina'
                ).get(id=ot_id)
                print(f"OT encontrada: {orden_trabajo.id} - {orden_trabajo.codigo_ot}")
            except OrdenTrabajo.DoesNotExist:
                print(f"OT con Id {ot_id} no encontrada")
                raise NotFound(f"Orden de trabajo con ID {ot_id} no encontrada.")
        
        try:
            with transaction.atomic():
                # Crear ProgramaProduccion (mantenemos código existente)
                fecha_inicio = parse_date(data.get('fecha_inicio'))
                if not fecha_inicio:
                    return Response(
                        {"detail": "Fecha de inicio no válida"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                programa = ProgramaProduccion.objects.create(
                    nombre=data.get('nombre'),
                    fecha_inicio=fecha_inicio
                )
                print("Programa creado:", programa.id)

                # Lista para almacenar datos para el scheduler
                ordenes_trabajo_scheduler = []
                
                # Crear relaciones ProgramaOrdenTrabajo (mantenemos código existente y añadimos preparación para scheduler)
                for index, ot_id in enumerate(data.get('ordenes', [])):
                    try:
                        orden_trabajo = OrdenTrabajo.objects.get(id=ot_id)
                        
                        # Crear la relación ProgramaOrdenTrabajo (existente)
                        pot = ProgramaOrdenTrabajo.objects.create(
                            programa=programa,
                            orden_trabajo=orden_trabajo,
                            prioridad=index  # Usamos index como prioridad
                        )
                        print(f"Relación creada: {pot}")

                        # NUEVO: Preparar datos para el scheduler
                        if orden_trabajo.ruta_ot:
                            ot_data = {
                                'orden_trabajo': orden_trabajo.id,
                                'orden_trabajo_codigo_ot': orden_trabajo.codigo_ot,
                                'orden_trabajo_descripcion_producto_ot': orden_trabajo.descripcion_producto_ot,
                                'procesos': []
                            }
                            
                            for item in orden_trabajo.ruta_ot.items.all().order_by('item'):
                                proceso_data = {
                                    'id': item.id,
                                    'item': item.item,
                                    'descripcion': item.proceso.descripcion if item.proceso else None,
                                    'maquina_id': item.maquina.id if item.maquina else None,
                                    'cantidad': item.cantidad_pedido,
                                    'estandar': item.estandar,
                                    'prioridad': pot.prioridad
                                }
                                ot_data['procesos'].append(proceso_data)
                            
                            ordenes_trabajo_scheduler.append(ot_data)
                            print(f"Datos preparados para scheduler - OT: {orden_trabajo.codigo_ot}")

                    except OrdenTrabajo.DoesNotExist:
                        raise NotFound(f"Orden de trabajo con ID {ot_id} no encontrada.")
                    except Exception as e:
                        print(f"Error procesando OT {ot_id}: {str(e)}")
                        raise

                # NUEVO: Crear tareas fragmentadas
                try:
                    scheduler = ProductionScheduler(TimeCalculator())
                    print("Iniciando creación de tareas fragmentadas...")
                    
                    if not scheduler.create_fragmented_tasks(programa, ordenes_trabajo_scheduler):
                        print("Error en create_fragmented_tasks")
                        # No lanzamos excepción, solo registramos el error
                    else:
                        print("Tareas fragmentadas creadas exitosamente")

                    # Intentar calcular fecha fin con el scheduler
                    try:
                        fecha_fin = scheduler.calculate_program_end_date(programa, ordenes_trabajo_scheduler)
                        if fecha_fin:
                            programa.fecha_fin = fecha_fin
                            print(f"Nueva fecha fin calculada: {fecha_fin}")
                        else:
                            programa.fecha_fin = programa.fecha_inicio
                            print("Usando fecha inicio como fecha fin (fallback)")
                    except Exception as e:
                        print(f"Error calculando fecha fin: {str(e)}")
                        programa.fecha_fin = programa.fecha_inicio
                        print("Usando fecha inicio como fecha fin (error)")

                except Exception as e:
                    print(f"Error en operaciones del scheduler: {str(e)}")
                    programa.fecha_fin = programa.fecha_inicio
                    print("Usando fecha inicio como fecha fin (error en scheduler)")

                # Guardar fecha fin (mantenemos código existente)
                programa.save(update_fields=['fecha_fin'])
                print(f"Programa guardado con fecha fin: {programa.fecha_fin}")

                # Serializar y devolver respuesta (mantenemos código existente)
                serializer = ProgramaProduccionSerializer(programa)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            print(f"Error creando programa: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"detail": "Ha ocurrido un error en el servidor.", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update_ruta_ot_items(self, ruta_ot, items_data):
        for item_data in items_data:
            try:
                item = ruta_ot.items.get(item=item_data['item'])
                if 'maquina' in item_data:
                    item.maquina = Maquina.objects.get(id=item_data['maquina'])
                if 'estandar' in item_data:
                    item.estandar = item_data['estandar']
                item.save()
            except Exception as e:
                print("Error updating ItemRuta:", e)

    # En ProgramCreateView
    def verificar_creacion_programa(self, programa_id):
        """Verifica que todos los elementos necesarios se hayan creado"""
        try:
            programa = ProgramaProduccion.objects.get(id=programa_id)
            
            # Verificar TareaFragmentada
            tareas = TareaFragmentada.objects.filter(programa=programa).count()
            print(f"Tareas fragmentadas creadas: {tareas}")
            
            # Verificar ReporteDiarioPrograma
            reportes = ReporteDiarioPrograma.objects.filter(programa=programa).count()
            print(f"Reportes diarios creados: {reportes}")
            
            return {
                'tareas_fragmentadas': tareas,
                'reportes_diarios': reportes
            }
        except Exception as e:
            print(f"Error en verificación: {str(e)}")
            return None

class ProgramDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.time_calculator = TimeCalculator()
        self.production_scheduler = ProductionScheduler(self.time_calculator)
        self.machine_availability = MachineAvailabilityService()

    def get_procesos_con_asignaciones(self, programa_id):
        """Obtiene los procesos y sus asignaciones de operadores para un programa específico"""
        try:
            asignaciones = AsignacionOperador.objects.filter(
                programa_id=programa_id
            ).select_related(
                'operador',
                'item_ruta',
                'item_ruta__proceso',
                'item_ruta__maquina'
            )
            return {
                asignacion.item_ruta_id: {
                    'operador_id': asignacion.operador.id,
                    'operador_nombre': asignacion.operador.nombre,
                    'fecha_inicio': asignacion.fecha_inicio,
                    'fecha_fin': asignacion.fecha_fin,
                } for asignacion in asignaciones
            }
        
        except Exception as e:
            print(f"Error obteniendo asignaciones: {str(e)}")
            return {}
        
    def get(self, request, pk):
        try:
            #print(f"[Backend] Iniciando obtención de programa {pk}")
            self.programa_id = pk
            programa = ProgramaProduccion.objects.get(id=pk)
            #print(f"[Backend] Programa encontrado: {programa.nombre}")

            try:
                #Usar el production_scheduler para calcular la fecha fin
                #print(f"[Backend] Calculando fecha fin para programa {pk}")
                fecha_fin = self.production_scheduler.calculate_program_end_date(programa)
                #print(f"[Backend] Fecha fin calculada: {fecha_fin}")
                
                if fecha_fin != programa.fecha_fin:
                    programa.fecha_fin = fecha_fin
                    programa.save(update_fields=['fecha_fin'])
                    programa.refresh_from_db()
            except Exception as e:
                print(f"[Backend] Error calculando fecha fin: {str(e)}")
                # No dejar que este error detenga toda la vista
                fecha_fin = programa.fecha_inicio

            #print(f"[Backend] Serializando programa {pk}")
            serializer = ProgramaProduccionSerializer(programa)
            
            #print(f"[Backend] Obteniendo asignaciones para programa {pk}")
            asignaciones_por_item = self.get_procesos_con_asignaciones(pk)
            
            #print(f"[Backend] Obteniendo órdenes de trabajo para programa {pk}")
            ordenes_trabajo = self.get_ordenes_trabajo(programa)

            for ot in ordenes_trabajo:
                for proceso in ot['procesos']:
                    if proceso['id'] in asignaciones_por_item:
                        proceso['asignacion'] = asignaciones_por_item[proceso['id']]

            try:
                #print(f"[Backend] Generando timeline para programa {pk}")
                routes_data = self.production_scheduler._generate_base_timeline(programa, ordenes_trabajo)
                print(f"[Backend] Timeline generado exitosamente")
            except Exception as e:
                print(f"[Backend] Error generando timeline: {str(e)}")
                # No dejar que este error detenga toda la vista
                routes_data = {"groups": [], "items": []}

            response_data = {
                "program": serializer.data,
                "ordenes_trabajo": ordenes_trabajo,
                "routes_data": routes_data
            }

            #print(f"[Backend] Enviando respuesta para programa {pk}")
            return Response(response_data, status=status.HTTP_200_OK)
        
        except ProgramaProduccion.DoesNotExist:
            print(f"[Backend] Programa {pk} no encontrado")
            return Response(
                {'error': 'Programa no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            print(f"[Backend] Error general obteniendo programa {pk}: {str(e)}")
            return Response(
                {'error': f'Error interno del servidor: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def get_ordenes_trabajo(self, programa):
        """Obtiene las órdenes de trabajo del programa dado."""
        try:
            program_ots = ProgramaOrdenTrabajo.objects.filter(
                programa=programa
            ).select_related(
                'orden_trabajo',
                'orden_trabajo__ruta_ot',
            ).prefetch_related(
                'orden_trabajo__ruta_ot__items',
                'orden_trabajo__ruta_ot__items__proceso',
                'orden_trabajo__ruta_ot__items__maquina',
            ).order_by('prioridad')

            ordenes_trabajo = []

            for prog_ot in program_ots:
                ot_data = self.format_orden_trabajo(prog_ot.orden_trabajo, programa.id)
                if ot_data:
                    ordenes_trabajo.append(ot_data)
            return ordenes_trabajo
        except Exception as e:
            print(f'Error obteniendo órdenes de trabajo: {str(e)}')
            return []
        
    def format_orden_trabajo(self, orden_trabajo, programa_id=None):
        """Formatea una orden de trabajo para la respuesta de la API"""
        try:
            programa_id = programa_id or getattr(self, 'programa_id', None)

            if not programa_id:
                print(f"Advertencia: No se proporcionó programa_id para la orden {orden_trabajo.id}")

            ot_data = {
                'orden_trabajo': orden_trabajo.id,
                'orden_trabajo_codigo_ot': orden_trabajo.codigo_ot,
                'orden_trabajo_codigo_producto_salida': orden_trabajo.codigo_producto_salida,
                'orden_trabajo_descripcion_producto_ot': orden_trabajo.descripcion_producto_ot,
                'orden_trabajo_cantidad_avance': orden_trabajo.cantidad_avance,
                'orden_trabajo_cantidad_pedido': orden_trabajo.cantidad,
                'orden_trabajo_peso': orden_trabajo.peso_unitario,
                'orden_trabajo_valor': orden_trabajo.valor,
                'procesos': []
            }
            ruta = getattr(orden_trabajo, 'ruta_ot', None)
            if ruta:
                for item in ruta.items.all().order_by('item'):
                    asignacion = None
                    if programa_id:
                        asignacion = AsignacionOperador.objects.filter(
                            programa_id=programa_id,
                            item_ruta_id=item.id
                        ).first()

                    operador_id = None
                    operador_nombre = None
                    asignacion_data = None
                    
                    if asignacion:
                        operador_id = asignacion.operador.id
                        operador_nombre = asignacion.operador.nombre
                        asignacion_data = {
                            'id': asignacion.id,
                            'fecha_asignacion': asignacion.created_at.isoformat() if asignacion.created_at else None
                        }

                    proceso_data = {
                        #datos principales
                        'id': item.id,
                        'item': item.item,
                        'proceso_id': item.proceso.id if item.proceso else None,
                        'codigo_proceso': item.proceso.codigo_proceso if item.proceso else None, 
                        'descripcion': item.proceso.descripcion if item.proceso else None,
                        'item_estado': item.estado_proceso,
                        #maquina related
                        'maquina_id': item.maquina.id if item.maquina else None,
                        'maquina_descripcion': item.maquina.descripcion if item.maquina else None,
                        #cantidades, estandar
                        'cantidad': item.cantidad_pedido,
                        'cantidad_terminada': item.cantidad_terminado_proceso,
                        'estandar': item.estandar,
                        #operador
                        'operador_id': operador_id,
                        'operador_nombre': operador_nombre,
                        'asignacion': asignacion_data,
                        
                    }
                    ot_data['procesos'].append(proceso_data)

                return ot_data
        except Exception as e:
            print(f"Error formateando orden de trabajo {orden_trabajo.id}: {str(e)}")
            return None
        
    def put(self, request, pk):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=pk)
            #print(f"Actualizando programa {pk}")
            #print(f"Datos recibidos: {request.data}")

            with transaction.atomic():
                # Manejar tanto el formato 'ordenes' como 'order_ids'
                ordenes_data = request.data.get('ordenes', request.data.get('order_ids', []))
                
                for orden_data in ordenes_data:
                    # Manejar ambos formatos de ID de orden
                    orden_id = orden_data.get('orden_trabajo', orden_data.get('id'))
                    #print(f"Procesando orden: {orden_id}")
                    
                    try:
                        programa_ot = ProgramaOrdenTrabajo.objects.get(
                            programa=programa,
                            orden_trabajo_id=orden_id
                        )
                        
                        # Manejar ambos formatos de prioridad
                        prioridad = orden_data.get('prioridad', orden_data.get('priority'))
                        if prioridad is not None:
                            programa_ot.prioridad = prioridad
                            programa_ot.save()
                            #print(f"Prioridad actualizada para OT {orden_id} a {prioridad}")

                        if 'procesos' in orden_data:
                            for proceso in orden_data['procesos']:
                                #print(f"Procesando proceso: {proceso}")
                                try:
                                    item_ruta = ItemRuta.objects.get(id=proceso['id'])
                                    #print(f"ItemRuta encontrado: {item_ruta}")
                                    cambios = False

                                    if 'maquina_id' in proceso and proceso['maquina_id']:
                                        maquina = get_object_or_404(Maquina, id=proceso['maquina_id'])
                                        item_ruta.maquina = maquina
                                        cambios = True
                                        #print(f"Máquina actualizada a: {maquina}")

                                    if 'estandar' in proceso:
                                        try:
                                            nuevo_estandar = int(proceso['estandar'])
                                            if nuevo_estandar >= 0:
                                                item_ruta.estandar = nuevo_estandar
                                                cambios = True
                                                #print(f"Estándar actualizado a: {nuevo_estandar}")
                                            else:
                                                print(f"Valor de estándar inválido: {nuevo_estandar}")
                                        except (ValueError, TypeError) as e:
                                            print(f"Error al convertir estándar: {e}")
                                            continue

                                    if cambios:
                                        item_ruta.save()
                                        print(f"ItemRuta {item_ruta.id} guardado con éxito")

                                except ItemRuta.DoesNotExist:
                                    print(f"No se encontró ItemRuta con id {proceso['id']}")
                                except Exception as e:
                                    print(f"Error procesando proceso: {str(e)}")
                                    raise

                    except ProgramaOrdenTrabajo.DoesNotExist:
                        print(f"No se encontró ProgramaOrdenTrabajo para orden {orden_id}")
                    except Exception as e:
                        print(f"Error procesando orden {orden_id}: {str(e)}")
                        raise

                # Recalcular fechas si se solicita
                if request.data.get('recalculate_dates', True):
                    fecha_fin = self.production_scheduler.calculate_program_end_date(programa)
                    programa.fecha_fin = fecha_fin
                    programa.save()
                    print(f"Fecha fin actualizada a: {fecha_fin}")

                    #2. Reajustar las fechas de las tareas fragmentadas
                    if request.data.get('reajustar _tareas', True):
                        print("Reajustando fechas de tareas fragmentadas...")
                        resultado_reajuste = self.production_scheduler.reajustar_fechas_tareas_fragmentadas(programa)
                        print(f"Resultado del reauste: {resultado_reajuste}")

                return Response({
                    "message": "Programa actualizado correctamente",
                    "fecha_fin": programa.fecha_fin
                }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error general: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": f"Error al actualizar el programa: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def verificar_estado_produccion(self, programa_id):
        """Verifica el estado actual de la producción y detecta retrasos"""
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        tareas_retrasadas = []
        
        for prog_ot in programa.programaordentrabajo_set.all():
            for item_ruta in prog_ot.orden_trabajo.ruta_ot.items.all():
                asignacion = AsignacionOperador.objects.filter(
                    programa=programa,
                    item_ruta=item_ruta
                ).first()
                
                if asignacion and asignacion.fecha_inicio and asignacion.fecha_fin:
                    # Convertir las fechas a strings antes de hacer los cálculos
                    tiempo_transcurrido = (timezone.now() - asignacion.fecha_inicio).total_seconds() / 3600  # en horas
                    tiempo_total = (asignacion.fecha_fin - asignacion.fecha_inicio).total_seconds() / 3600  # en horas
                    
                    if tiempo_total > 0:  # Evitar división por cero
                        progreso_esperado = (tiempo_transcurrido / tiempo_total) * 100
                        
                        if progreso_esperado > item_ruta.porcentaje_cumplimiento + 20:
                            tareas_retrasadas.append({
                                'ot_codigo': item_ruta.ruta.orden_trabajo.codigo_ot,
                                'proceso': item_ruta.proceso.descripcion,
                                'retraso': float(progreso_esperado - item_ruta.porcentaje_cumplimiento),
                                'operador': asignacion.operador.nombre if asignacion.operador else 'Sin asignar',
                                'fecha_inicio': asignacion.fecha_inicio.strftime('%Y-%m-%d %H:%M:%S'),
                                'fecha_fin': asignacion.fecha_fin.strftime('%Y-%m-%d %H:%M:%S')
                            })
        
        return tareas_retrasadas

    def identificar_cuellos_botella(self, programa):
        """Identifica cuellos de botella en la producción"""
        cuellos_botella = []
        maquinas_usadas = Maquina.objects.filter(
            itemruta__ruta__orden_trabajo__programaordentrabajo__programa=programa
        ).distinct()

        for maquina in maquinas_usadas:
            carga = self.machine_availability.calcular_carga_maquina(maquina, programa)
            
            # Consideramos cuello de botella si la carga supera 8 horas
            if carga['carga_total'] > 8:
                cuellos_botella.append({
                    'maquina_codigo': maquina.codigo_maquina,
                    'maquina_descripcion': maquina.descripcion,
                    'tiempo_total': carga['carga_total'],
                    'tareas_afectadas': carga['desglose']
                })

        return cuellos_botella

    def post(self, request, pk):
        """Endpoint para verificar estado y problemas"""
        try:
            programa = get_object_or_404(ProgramaProduccion, id=pk)
            
            tareas_retrasadas = self.verificar_estado_produccion(pk)
            cuellos_botella = self.identificar_cuellos_botella(programa)

            # Asegurarse de que todas las fechas estén en formato string
            for c in cuellos_botella:
                #Si hay fechas en los cuellos de botella, convertirlas a string
                if 'fecha_inicio' in c and isinstance(c['fecha_inicio'], datetime):
                    c['fecha_inicio'] = c['fecha_inicio'].strftime('%Y-%m-%d %H:%M:%S')
                if 'fecha_fin' in c and isinstance(c['fecha_fin'], datetime):
                    c['fecha_fin'] = c['fecha_fin'].strftime('%Y-%m-%d %H:%M:%S')
            
            return Response({
                'estado': 'actualizado',
                'tareas_retrasadas': len(tareas_retrasadas),
                'tareas_retrasadas_detalle': tareas_retrasadas,
                'cuellos_botella': len(cuellos_botella),
                'cuellos_botella_detalle': cuellos_botella,
                'acciones_tomadas': []  # Por ahora no hay acciones automáticas
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error al verificar estado: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': f'Error al verificar estado: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 2. Métodos de acción correctiva
    def aplicar_acciones_correctivas(self, tarea_retrasada):
        """
        Implementa acciones correctivas para tareas retrasadas
        """
        item_ruta = tarea_retrasada['item_ruta']
        asignacion = tarea_retrasada['asignacion']
        retraso = tarea_retrasada['retraso']
        
        acciones_tomadas = []

        # 1. Ajustar estimaciones
        if retraso > 30:  # Si el retraso es mayor al 30%
            nuevo_estandar = self.calcular_nuevo_estandar(item_ruta)
            item_ruta.estandar = nuevo_estandar
            item_ruta.save()
            acciones_tomadas.append(f"Estándar ajustado a {nuevo_estandar}")

        # 2. Buscar recursos alternativos
        if retraso > 40:
            recursos_alt = self.buscar_recursos_disponibles(item_ruta)
            if recursos_alt:
                self.reasignar_recursos(item_ruta, recursos_alt)
                acciones_tomadas.append("Recursos reasignados")

        # 3. Fragmentar tarea si es necesario
        if retraso > 50:
            self.fragmentar_tarea(item_ruta, asignacion)
            acciones_tomadas.append("Tarea fragmentada")

        return acciones_tomadas


class EmpresaListView(APIView):
    def get(self, request):
        empresas = EmpresaOT.objects.all()
        serializer = EmpresaOTSerializer(empresas, many=True)
        return Response(serializer.data)
    
logger = logging.getLogger(__name__)
class GenerateProgramPDF(APIView):
    def __init__(self):
        super().__init__()
        # Inicializar el time calculator y el scheduler
        self.time_calculator = TimeCalculator()
        self.production_scheduler = ProductionScheduler(self.time_calculator)

    def get_ordenes_trabajo(self, programa):
        """Obtiene las órdenes de trabajo del programa dado."""
        try:
            program_ots = ProgramaOrdenTrabajo.objects.filter(
                programa=programa
            ).select_related(
                'orden_trabajo',
                'orden_trabajo__ruta_ot',
            ).prefetch_related(
                'orden_trabajo__ruta_ot__items',
                'orden_trabajo__ruta_ot__items__proceso',
                'orden_trabajo__ruta_ot__items__maquina',
            ).order_by('prioridad')

            ordenes_trabajo = []
            for prog_ot in program_ots:
                ot = prog_ot.orden_trabajo
                ot_data = {
                    'orden_trabajo_codigo_ot': ot.codigo_ot,
                    'orden_trabajo_descripcion_producto_ot': ot.descripcion_producto_ot,
                    'procesos': []
                }
    
                ruta = getattr(ot, 'ruta_ot', None)
                if ruta:
                    for item in ruta.items.all().order_by('item'):
                        #Obtener asignación de operador si existe
                        asignacion = AsignacionOperador.objects.filter(
                            programa=programa,
                            item_ruta=item
                        ).first()

                        #Obtener fechas de inicio y fin del proceso
                        fechas_proceso = self.get_fechas_procesos(programa, item)

                        proceso_data = {
                            'item': item.item,
                            'codigo_proceso': item.proceso.codigo_proceso if item.proceso else None,
                            'descripcion': item.proceso.descripcion if item.proceso else None,
                            'maquina_codigo': item.maquina.codigo_maquina if item.maquina else None,
                            'maquina_descripcion': item.maquina.descripcion if item.maquina else None,
                            'operador_nombre': asignacion.operador.nombre if asignacion and asignacion.operador else 'No asignado',
                            'cantidad': item.cantidad_pedido,
                            'estandar': item.estandar,
                            'fecha_inicio': fechas_proceso.get('fecha_inicio'),
                            'fecha_fin': fechas_proceso.get('fecha_fin')
                        }
                        ot_data['procesos'].append(proceso_data)
                
                ordenes_trabajo.append(ot_data)
            return ordenes_trabajo
        except Exception as e:
            logger.error(f'Error obteniendo órdenes de trabajo: {str(e)}')
            logger.error(traceback.format_exc())
            raise

    def get_fechas_procesos(self, programa, item_ruta):
        """Obtiene las fechas de inicio y fin para un proceso específico."""
        try:
            # Intentar obtener fechas de asignación primero
            asignacion = AsignacionOperador.objects.filter(
                programa=programa,
                item_ruta=item_ruta
            ).first()

            if asignacion and asignacion.fecha_inicio and asignacion.fecha_fin:
                return {
                    'fecha_inicio': asignacion.fecha_inicio,
                    'fecha_fin': asignacion.fecha_fin
                }

            # Si no hay asignación, obtener todas las OTs del programa
            program_ots = ProgramaOrdenTrabajo.objects.filter(
                programa=programa
            ).select_related(
                'orden_trabajo',
                'orden_trabajo__ruta_ot'
            ).prefetch_related(
                'orden_trabajo__ruta_ot__items'
            ).order_by('prioridad')

            # Preparar datos para el scheduler
            ordenes_trabajo = []
            for prog_ot in program_ots:
                ot = prog_ot.orden_trabajo
                ot_data = {
                    'orden_trabajo': ot.id,
                    'orden_trabajo_codigo_ot': ot.codigo_ot,
                    'orden_trabajo_descripcion_producto_ot': ot.descripcion_producto_ot,
                    'procesos': []
                }

                if ot.ruta_ot:
                    for item in ot.ruta_ot.items.all().order_by('item'):
                        proceso_data = {
                            'id': item.id,
                            'item': item.item,
                            'descripcion': item.proceso.descripcion if item.proceso else None,
                            'maquina_id': item.maquina.id if item.maquina else None,
                            'maquina_descripcion': item.maquina.descripcion if item.maquina else None,
                            'cantidad': item.cantidad_pedido,
                            'estandar': item.estandar,
                            'prioridad': prog_ot.prioridad
                        }
                        ot_data['procesos'].append(proceso_data)
            
                ordenes_trabajo.append(ot_data)

            # Generar timeline data para todas las OTs
            timeline_data = self.production_scheduler.generate_timeline_data(programa, ordenes_trabajo)

            # Buscar el proceso específico en el timeline completo
            if timeline_data.get('items'):
                proceso_items = [
                    item for item in timeline_data['items'] 
                    if item['proceso_id'] == f"proc_{item_ruta.id}"
                ]

                if proceso_items:
                    # Ordenar items por fecha
                    proceso_items.sort(key=lambda x: datetime.strptime(x['start_time'], '%Y-%m-%d %H:%M:%S'))
                    
                    fecha_inicio = datetime.strptime(proceso_items[0]['start_time'], '%Y-%m-%d %H:%M:%S')
                    
                    # Calcular la fecha fin real basada en la cantidad total y los intervalos
                    cantidad_total = float(item_ruta.cantidad_pedido)
                    cantidad_acumulada = 0
                    fecha_fin = None
                    
                    for item in proceso_items:
                        cantidad_acumulada += float(item['cantidad_intervalo'])
                        fecha_fin = datetime.strptime(item['end_time'], '%Y-%m-%d %H:%M:%S')
                        
                        # Si ya procesamos toda la cantidad, esta es la fecha fin real
                        if cantidad_acumulada >= cantidad_total:
                            break

                    if fecha_fin:
                        return {
                            'fecha_inicio': fecha_inicio,
                            'fecha_fin': fecha_fin
                        }

            return {
                'fecha_inicio': None,
                'fecha_fin': None,
                'error': 'No se pudieron calcular las fechas del proceso'
            }

        except Exception as e:
            logger.error(f'Error obteniendo fechas de proceso: {str(e)}')
            logger.error(traceback.format_exc())
            return {
                'fecha_inicio': None,
                'fecha_fin': None,
                'error': str(e)
            }

    def get(self, request, pk):
        try:
            logger.info(f"Iniciando generación de PDF para programa {pk}")

            # Obtener el programa
            programa = get_object_or_404(ProgramaProduccion, pk=pk)
            logger.info(f"Programa encontrado: {programa.nombre}")

            # Obtener datos necesarios para el PDF
            try:
                ordenes_trabajo = self.get_ordenes_trabajo(programa)
                logger.info(f"Órdenes de trabajo obtenidas: {len(ordenes_trabajo)}")
            except Exception as e:
                logger.error(f"Error al obtener órdenes de trabajo: {str(e)}")
                logger.error(traceback.format_exc())
                return Response(
                    {"detail": f'Error al obtener datos de órdenes de trabajo: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Verificar si hay datos para generar el PDF
            if not ordenes_trabajo:
                logger.warning(f"No hay órdenes de trabajo en el programa {pk}")
                return Response(
                    {"detail": "No hay órdenes de trabajo en este programa para generar el PDF"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generar el PDF
            try:
                logger.info("Generando PDF...")

                # Crear directorio temporal si no existe
                temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                    logger.info(f"Directorio temporal creado: {temp_dir}")

                # Generar nombre de archivo único
                import uuid
                pdf_filename = f"programa_{pk}_{uuid.uuid4().hex[:8]}.pdf"
                pdf_path = os.path.join(temp_dir, pdf_filename)
                logger.info(f"Ruta del PDF: {pdf_path}")

                # Crear el documento con orientación horizontal
                doc = SimpleDocTemplate(
                    pdf_path, 
                    pagesize=landscape(letter),
                    rightMargin=20,
                    leftMargin=20,
                    topMargin=30,
                    bottomMargin=30
                )
                elements = []

                # Estilos 
                styles = getSampleStyleSheet()
                title_style = styles['Heading1']
                subtitle_style = styles['Heading2']
                normal_style = styles['Normal']
                
                # Estilo para texto en celdas
                cell_style = ParagraphStyle(
                    'CellStyle',
                    parent=normal_style,
                    fontSize=8,
                    leading=9,
                    wordWrap='CJK',
                    alignment=0  # 0=left
                )
                
                # Estilo para texto centrado en celdas
                cell_style_center = ParagraphStyle(
                    'CellStyleCenter',
                    parent=cell_style,
                    alignment=1  # 1=center
                )

                # Estilo personalizado para títulos centrados
                centered_title = ParagraphStyle(
                    'CenteredTitle',
                    parent=title_style,
                    alignment=1,  # 0=left, 1=center, 2=right
                    spaceAfter=10
                )

                # Título 
                elements.append(Paragraph(f"Programa de Producción: {programa.nombre}", centered_title))
                elements.append(Paragraph(f"Fecha Inicio: {programa.fecha_inicio.strftime('%d/%m/%Y')} - Fecha Fin: {programa.fecha_fin.strftime('%d/%m/%Y') if programa.fecha_fin else 'No definida'}", centered_title))
                elements.append(Spacer(1, 10))

                # Crear una única tabla para todo el programa
                data = []
                
                # Encabezados de la tabla - usar Paragraph para permitir ajuste de texto
                headers = [
                    Paragraph('<b>OT</b>', cell_style_center),
                    Paragraph('<b>Item</b>', cell_style_center),
                    Paragraph('<b>Proceso</b>', cell_style_center),
                    Paragraph('<b>Máquina</b>', cell_style_center),
                    Paragraph('<b>Operador</b>', cell_style_center),
                    Paragraph('<b>Cantidad</b>', cell_style_center),
                    Paragraph('<b>Estándar</b>', cell_style_center),
                    Paragraph('<b>Fecha Inicio</b>', cell_style_center),
                    Paragraph('<b>Fecha Fin</b>', cell_style_center)
                ]
                data.append(headers)
                
                # Procesar cada orden de trabajo
                for ot in ordenes_trabajo:
                    # Agregar fila con información de la OT
                    ot_row = [
                        Paragraph(f"{ot['orden_trabajo_codigo_ot']}", cell_style_center),
                        "",
                        Paragraph(f"{ot['orden_trabajo_descripcion_producto_ot']}", cell_style),
                        "", "", "", "", "", ""
                    ]
                    data.append(ot_row)
                    
                    # Agregar procesos
                    for proceso in ot.get('procesos', []):
                        # Formatear fechas
                        fecha_inicio_str = proceso.get('fecha_inicio').strftime('%d/%m/%Y %H:%M') if proceso.get('fecha_inicio') else 'No definida'
                        fecha_fin_str = proceso.get('fecha_fin').strftime('%d/%m/%Y %H:%M') if proceso.get('fecha_fin') else 'No definida'
                        
                        # Crear fila con Paragraphs para permitir ajuste de texto
                        proceso_row = [
                            "",  # OT ya incluido en la fila anterior
                            Paragraph(str(proceso.get('item', '')), cell_style_center),
                            Paragraph(f"{proceso.get('codigo_proceso', '')} - {proceso.get('descripcion', '')}", cell_style),
                            Paragraph(f"{proceso.get('maquina_codigo', 'No asignada')} - {proceso.get('maquina_descripcion', '')}", cell_style),
                            Paragraph(proceso.get('operador_nombre', 'No asignado'), cell_style),
                            Paragraph(str(proceso.get('cantidad', 0)), cell_style_center),
                            Paragraph(str(proceso.get('estandar', 0)), cell_style_center),
                            Paragraph(fecha_inicio_str, cell_style_center),
                            Paragraph(fecha_fin_str, cell_style_center)
                        ]
                        data.append(proceso_row)
                    
                    # NO agregar filas vacías entre órdenes de trabajo
                
                # Crear tabla con todos los datos - ajustar anchos de columna
                col_widths = [50, 30, 140, 140, 80, 40, 40, 60, 60]  # Ajustar según necesidades
                table = Table(data, colWidths=col_widths, repeatRows=1)
                
                # Aplicar estilos a la tabla
                style = TableStyle([
                    # Estilo para encabezados
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Alineación vertical al centro
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    
                    # Bordes para todas las celdas
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    
                    # Alineación para columnas numéricas
                    ('ALIGN', (5, 1), (6, -1), 'CENTER'),  # CANTIDAD Y ESTÁNDAR
                    ('ALIGN', (7, 1), (8, -1), 'CENTER'),  # FECHAS
                    
                    # Ajustar el espacio interno de las celdas
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ])
                
                # Identificar filas de OT para aplicar estilos específicos
                ot_rows = []
                row_idx = 1  # Empezar después de los encabezados
                
                for ot in ordenes_trabajo:
                    ot_rows.append(row_idx)
                    row_idx += 1 + len(ot.get('procesos', []))  # OT + sus procesos (sin fila vacía)
                
                # Aplicar estilos a filas de OT
                for row in ot_rows:
                    style.add('BACKGROUND', (0, row), (-1, row), colors.lightgrey)
                    style.add('FONTNAME', (0, row), (-1, row), 'Helvetica-Bold')
                    style.add('SPAN', (2, row), (-1, row))  # Combinar celdas para descripción
                
                table.setStyle(style)
                elements.append(table)
                
                # Construir el PDF
                doc.build(elements)
                logger.info("PDF generado correctamente")
                
                # Verificar que el PDF se generó correctamente
                if not os.path.exists(pdf_path):
                    raise Exception("El archivo PDF no se creó correctamente")
                
                if os.path.getsize(pdf_path) == 0:
                    raise Exception("El archivo PDF está vacío")
                
                # Devolver el PDF
                with open(pdf_path, 'rb') as pdf:
                    response = HttpResponse(pdf.read(), content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="programa_{pk}.pdf"'
                    
                    # Eliminar el archivo temporal después de enviarlo
                    try:
                        os.remove(pdf_path)
                        logger.info(f'Archivo temporal eliminado: {pdf_path}')
                    except Exception as e:
                        logger.warning(f'No se pudo eliminar el archivo temporal: {str(e)}')
                    
                    return response
            
            except Exception as e:
                logger.error(f"Error al generar el PDF: {str(e)}")
                logger.error(traceback.format_exc())
                return Response(
                    {'detail': f'Error al generar el PDF: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception as e:
            logger.error(f"Error general en GenerateProgramPDF: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {"detail": f"Error al procesar la solicitud: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AddOrdersToProgram(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.time_calculator = TimeCalculator()
        self.production_scheduler = ProductionScheduler(self.time_calculator)

    def post(self, request, pk):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=pk)
            ordenes_ids = request.data.get('ordenes', [])

            if not ordenes_ids:
                return Response({
                    "error": "No se proporcionaron órdenes para añadir"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # Obtener la última prioridad usada en el programa
                ultima_prioridad = ProgramaOrdenTrabajo.objects.filter(
                    programa=programa
                ).order_by('-prioridad').first()

                prioridad_inicial = (ultima_prioridad.prioridad + 1) if ultima_prioridad else 0

                ordenes_agregadas = []
                for idx, orden_id in enumerate(ordenes_ids):
                    try:
                        orden = OrdenTrabajo.objects.get(id=orden_id)

                        # Verificar si la orden ya está en el programa
                        if ProgramaOrdenTrabajo.objects.filter(
                            programa=programa,
                            orden_trabajo=orden
                        ).exists():
                            continue

                        # Crear nueva relación programa-orden
                        ProgramaOrdenTrabajo.objects.create(
                            programa=programa,
                            orden_trabajo=orden,
                            prioridad=prioridad_inicial + idx
                        )
                        ordenes_agregadas.append(orden.codigo_ot)

                    except OrdenTrabajo.DoesNotExist:
                        return Response({
                            "error": f"Orden de trabajo {orden_id} no encontrada"
                        }, status=status.HTTP_404_NOT_FOUND)
                    
                # Recalcular fechas del programa
                fecha_fin = self.production_scheduler.calculate_program_end_date(programa)
                programa.fecha_fin = fecha_fin
                programa.save()

                return Response({
                    "message": "Órdenes agregadas correctamente",
                    "ordenes_agregadas": ordenes_agregadas,
                    "fecha_fin": programa.fecha_fin
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": f"Error al agregar órdenes al programa: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ReajustarProgramaView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.machine_availability = MachineAvailabilityService()

    def post(self, request, pk):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=pk)
            
            # Obtener ajustes necesarios
            ajustes = self.machine_availability.obtener_ajustes_necesarios(programa)
            
            if ajustes:
                return Response({
                    "requiere_ajustes": True,
                    "ajustes_sugeridos": [
                        {
                            "orden_trabajo": str(ajuste['orden_trabajo']),
                            "proceso": {
                                "id": ajuste['proceso'].id,
                                "descripcion": ajuste['proceso'].descripcion
                            },
                            "maquina": {
                                "id": ajuste['maquina'].id,
                                "codigo": ajuste['maquina'].codigo_maquina
                            },
                            "fecha_original": ajuste['fecha_original'].strftime("%Y-%m-%d %H:%M"),
                            "fecha_propuesta": ajuste['fecha_ajustada'].strftime("%Y-%m-%d %H:%M")
                        } for ajuste in ajustes
                    ],
                    "fecha_actual": programa.fecha_fin.strftime("%Y-%m-%d %H:%M") if programa.fecha_fin else None
                }, status=status.HTTP_200_OK)
            
            return Response({
                "requiere_ajustes": False,
                "mensaje": "El programa no requiere ajustes"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": f"Error al verificar ajustes del programa: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# En program_views.py - Modificar la vista existente
class ProgramHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=pk)
            fecha = request.GET.get('fecha')
            
            if fecha:
                historial = HistorialPlanificacion.objects.filter(
                    programa=programa,
                    fecha_referencia__lte=fecha
                ).order_by('-fecha_referencia').first()
                
                if historial:
                    timeline_data = historial.timeline_data.copy() if historial.timeline_data else {}
                    
                    # Asegurarnos de que existan las estructuras básicas
                    if 'grupos' not in timeline_data:
                        timeline_data['grupos'] = []
                    if 'items' not in timeline_data:
                        timeline_data['items'] = []
                    if 'cambios' not in timeline_data:
                        timeline_data['cambios'] = []
                    if 'metadata' not in timeline_data:
                        timeline_data['metadata'] = {}

                    # Asegurarnos de que cada item tenga un estado válido
                    for item in timeline_data.get('items', []):
                        if 'estado' not in item or not item['estado']:
                            item['estado'] = 'PENDIENTE'

                    # Construir el resumen con validaciones
                    resumen = {
                        'tareas_totales': timeline_data.get('metadata', {}).get('tareas_totales', 0),
                        'tareas_completadas': len([c for c in timeline_data.get('cambios', []) 
                                                 if c.get('tipo') == 'COMPLETADO']),
                        'tareas_continuadas': len([c for c in timeline_data.get('cambios', []) 
                                                 if c.get('tipo') == 'CONTINUACION']),
                        'fecha_cierre': historial.fecha_reajuste.isoformat() if historial.fecha_reajuste else None
                    }

                    return Response({
                        'fecha_referencia': historial.fecha_referencia,
                        'tipo_reajuste': historial.tipo_reajuste,
                        'timeline_data': timeline_data,
                        'resumen': resumen
                    })
                else:
                    return Response({
                        'error': 'No hay registros históricos para esta fecha'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                # Devolver lista de todos los registros históricos
                historiales = HistorialPlanificacion.objects.filter(
                    programa=programa
                ).order_by('-fecha_reajuste')
                
                return Response([{
                    'id': registro.id,
                    'fecha_reajuste': registro.fecha_reajuste,
                    'fecha_referencia': registro.fecha_referencia,
                    'tipo_reajuste': registro.tipo_reajuste,
                    'resumen': {
                        'tareas_totales': registro.timeline_data.get('metadata', {}).get('tareas_totales', 0),
                        'tareas_completadas': len([c for c in registro.timeline_data.get('cambios', []) if c['tipo'] == 'COMPLETADO']),
                        'tareas_continuadas': len([c for c in registro.timeline_data.get('cambios', []) if c['tipo'] == 'CONTINUACION']),
                        'fecha_cierre': registro.fecha_reajuste.isoformat() if registro.fecha_reajuste else None
                    }
                } for registro in historiales])
            
        except Exception as e:
            print(f"Error en ProgramHistoryView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, pk, historial_id):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=pk)
            historial = get_object_or_404(HistorialPlanificacion, 
                                        id=historial_id, 
                                        programa=programa)
            
            # Verificar que el usuario es administrador
            if not request.user.is_staff:
                return Response(
                    {'error': 'No tiene permisos para realizar esta acción'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            historial.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            print(f"Error eliminando historial: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class TimelinePlanningView(APIView):
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.time_calculator = TimeCalculator()
        self.production_scheduler = ProductionScheduler(self.time_calculator)
        self.machine_availability = MachineAvailabilityService()
    
    def get(self, request, pk):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=pk)
            fecha_solicitada = request.GET.get('fecha', None)
            fecha = datetime.strptime(fecha_solicitada, '%Y-%m-%d').date() if fecha_solicitada else None
            
            print(f"[DEBUG] Generando timeline de planificación para programa {pk}")
            
            # Obtener las órdenes de trabajo del programa
            ordenes_trabajo = self._get_ordenes_trabajo(programa)
            
            # Generar la timeline base (sin tareas fragmentadas/continuaciones)
            timeline_data = self._generate_base_timeline(programa, ordenes_trabajo)
            
            return Response({
                'programa': {
                    'id': programa.id,
                    'nombre': programa.nombre,
                    'fecha': fecha_solicitada or programa.fecha_inicio.strftime('%Y-%m-%d')
                },
                'groups': timeline_data.get('groups', []),
                'items': timeline_data.get('items', [])
            })
            
        except Exception as e:
            print(f"Error en TimelinePlanningView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_ordenes_trabajo(self, programa):
        """Obtiene las órdenes de trabajo del programa dado."""
        try:
            program_ots = ProgramaOrdenTrabajo.objects.filter(
                programa=programa
            ).select_related(
                'orden_trabajo',
                'orden_trabajo__ruta_ot',
            ).prefetch_related(
                'orden_trabajo__ruta_ot__items',
                'orden_trabajo__ruta_ot__items__proceso',
                'orden_trabajo__ruta_ot__items__maquina',
            ).order_by('prioridad')

            ordenes_trabajo = []
            for prog_ot in program_ots:
                ot_data = self._format_orden_trabajo(prog_ot.orden_trabajo, programa.id)
                if ot_data:
                    ordenes_trabajo.append(ot_data)
            return ordenes_trabajo
        except Exception as e:
            print(f'Error obteniendo órdenes de trabajo: {str(e)}')
            return []
    
    def _format_orden_trabajo(self, orden_trabajo, programa_id=None):
        """Formatea una orden de trabajo para la respuesta API"""
        try:
            ot_data = {
                'orden_trabajo': orden_trabajo.id,
                'orden_trabajo_codigo_ot': orden_trabajo.codigo_ot,
                'orden_trabajo_descripcion_producto_ot': orden_trabajo.descripcion_producto_ot,
                'procesos': []
            }
            
            # Obtener la ruta y sus procesos
            ruta = getattr(orden_trabajo, 'ruta_ot', None)
            if ruta:
                for item in ruta.items.all().order_by('item'):
                    # Obtener asignación de operador si existe
                    asignacion = None
                    if programa_id:
                        asignacion = AsignacionOperador.objects.filter(
                            programa_id=programa_id,
                            item_ruta_id=item.id
                        ).first()
                    
                    operador_id = None
                    operador_nombre = None
                    asignacion_data = None
                    
                    if asignacion:
                        operador_id = asignacion.operador.id
                        operador_nombre = asignacion.operador.nombre
                        asignacion_data = {
                            'id': asignacion.id,
                            'fecha_asignacion': asignacion.created_at.isoformat() if asignacion.created_at else None
                        }

                    proceso_data = {
                        'id': item.id,
                        'item': item.item,
                        'codigo_proceso': item.proceso.codigo_proceso if item.proceso else None, 
                        'descripcion': item.proceso.descripcion if item.proceso else None,
                        'maquina_id': item.maquina.id if item.maquina else None,
                        'maquina_descripcion': item.maquina.descripcion if item.maquina else None,
                        'cantidad': item.cantidad_pedido,
                        'estandar': item.estandar,
                        'operador_id': operador_id,
                        'operador_nombre': operador_nombre,
                        'asignacion': asignacion_data
                    }
                    ot_data['procesos'].append(proceso_data)

                return ot_data
        except Exception as e:
            print(f"Error formateando orden de trabajo {orden_trabajo.id}: {str(e)}")
            return None
    
    def _generate_base_timeline(self, programa, ordenes_trabajo):
        """Genera la línea de tiempo base (sin considerar tareas fragmentadas)"""
        return self.production_scheduler._generate_base_timeline(programa, ordenes_trabajo)


class UpdateProductStandardView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            item_ruta_id = request.data.get('item_ruta_id')
            maquina_id = request.data.get('maquina_id')
            nuevo_estandar = request.data.get('nuevo_estandar')

            if not item_ruta_id:
                return Response(
                    {"error" : "Se requiere el ID del item_ruta"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            item_ruta = get_object_or_404(ItemRuta, id=item_ruta_id)

            #Obtener la orden de trabajo y el código del producto
            ot_codigo = item_ruta.ruta.orden_trabajo
            orden_trabajo = OrdenTrabajo.objects.get(codigo_ot=ot_codigo)
            #print(ot_codigo)
            codigo_producto_salida = orden_trabajo.codigo_producto_salida
            codigo_producto_inicial = orden_trabajo.codigo_producto_inicial

            if not codigo_producto_salida or not codigo_producto_inicial:
                return Response(
                    {"error": f"La OT {orden_trabajo.codigo_ot} no tiene coódigo de producto o pieza asociado"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Usar código de saida por defecto, o inicial si no hay salida
            codigo_buscar = codigo_producto_salida or codigo_producto_inicial

            #Importamos los modelos necesarios
            from Product.models import Producto, Pieza
            from JobManagement.models import EstandarMaquinaProceso

            #Obtener máquina si se especificó 
            maquina = None
            if maquina_id:
                try:
                    maquina = Maquina.objects.get(id=maquina_id)
                except Maquina.DoesNotExist:
                    return Response(
                        {"error": f"No se encontró la máquina con ID {maquina_id}"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                #Si no se especificó máquina, usar la del item_ruta
                maquina = item_ruta.maquina

            #Si no se especificó estandar, usar el de item_ruta
            estandar = nuevo_estandar if nuevo_estandar is not None else item_ruta.estandar

            #Verificar que tengamos proceso y máquina válidos
            if not item_ruta.proceso or not maquina:
                return Response({
                    "error": "Se requiere un proceso y máquina válidos"
                }, status=status.HTTP_400_BAD_REQUEST)

            #Buscar primero si es un producto
            producto = Producto.objects.filter(codigo_producto=codigo_buscar).first()

            if producto:
                #Usar update_or_create para el modelo EstandarMaquinaProceso
                estandar_obj, created = EstandarMaquinaProceso.objects.update_or_create(
                    producto=producto,
                    proceso=item_ruta.proceso,
                    maquina=maquina,
                    defaults={
                        'estandar': estandar,
                        'es_principal': True #Consideramos principal la que se guarda desde el programa
                    }
                )
                return Response({
                    "message": f"Estándar del producto {created and 'creado' or 'actualizado'} correctamente.",
                    "tipo": "producto",
                    "codigo": producto.codigo_producto,
                    "proceso": item_ruta.proceso.descripcion,
                    "maquina": maquina.descripcion,
                    "nuevo_estandar": estandar
                }, status=status.HTTP_200_OK)
            
            #Si no es produto, intentamos buscar como pieza
            pieza = Pieza.objects.filter(codigo_pieza=codigo_buscar).first

            if pieza:
                #Usar update_or_create para el modelo EstandarMaquinaProceso
                estandar_obj, created = EstandarMaquinaProceso.objects.update_or_create(
                    pieza=pieza,
                    proceso=item_ruta.proceso,
                    maquina=maquina,
                    defaults={
                        'estandar': estandar,
                        'es_principal': True #Consideramos principal la que se guarda desde el programa
                    }
                )

                return Response({
                    "message": f"Estándar de la pieza {created and 'creado' or 'actualizado'} correctamente.",
                    "tipo": "pieza",
                    "codigo": pieza.codigo_pieza,
                    "proceso": item_ruta.proceso.descripcion,
                    "maquina": maquina.descripcion,
                    "nuevo_estandar": estandar
                }, status=status.HTTP_200_OK)
            
            #Si no encontramos ni el producto ni pieza
            return Response({
                "error": f"No se encontró producto ni pieza con código {codigo_buscar}"
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            print(f"Error en UpdateProductStandardView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": f"Error al actualizar el estándar: {str(e)}"
            })
        
    def get(self, request, pk):
        """
        Obtiene las máquinas compatibles para un proceso específico
        junto con sus estándares para un producto
        Query params:
        proceso: Id del proceso"""
        try:
            proceso_id = request.query_params.get('proceso_id')
            tipo = request.query_params.get('tipo')
            objeto_id = request.query_params.get('objeto_id')

            if not proceso_id:
                return Response({
                    "error": "Se requiere el ID del proceso"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            proceso = get_object_or_404(Proceso, id=proceso_id)
            maquinas_compatibles = proceso.get_maquinas_compatibles()

            # Si se proporciona tipo y objeto_id, buscar estándares existentes
            estandares = {}
            if tipo and objeto_id:
                #Importamos los modelos necesarios
                from Product.models import Producto, Pieza
                from JobManagement.models import EstandarMaquinaProceso

                #Buscar estándares usando el modelo EstandarMaquinaProceso
                if tipo == 'producto':
                    producto = get_object_or_404(Producto, id=objeto_id)
                    estandares_obj = EstandarMaquinaProceso.objects.filter(
                        producto=producto,
                        proceso=proceso
                    )

                    #Crear diccionario de estándares por máquina
                    estandares = {e.maquina_id: e.estandar for e in estandares_obj}

                elif tipo == 'pieza':
                    pieza = get_object_or_404(Pieza, id=objeto_id)
                    estandares_obj = EstandarMaquinaProceso.objects.filter(
                        pieza=pieza,
                        proceso=proceso
                    )
                    #Crear diccionario de estándares por máquina
                    estandares = {e.maquina: e.estandar for e in estandares_obj}

            #Formatear datos de máquians incluyendo estándares
            maquinas_data = []
            for maquina in maquinas_compatibles:
                maquina_data = {
                    'id': maquina.id,
                    'codigo': maquina.codigo_maquina,
                    'descripcion': maquina.descripcion,
                    'estandar': estandares.get(maquina.id, 0) #Si no existe estandar para esta máquina
                }
                maquinas_data.append(maquina_data)

            return Response({
                "proceso_id": proceso_id,
                "maquinas_compatibles": maquinas_data
            })
        
        except Exception as e:
            print(f"Error obteniendo máquinas compatibles: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": f"Error al obtener máquinas compatibles: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    

# En proyecto_abasolo/JobManagement/views.py - Agregar nueva clase
class TareaTimeRealtimeUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, tarea_id):
        """Actualiza una tarea en tiempo real desde la timeline"""
        try:
            tarea = get_object_or_404(TareaFragmentada, id=tarea_id)
            
            # Datos del request
            cantidad_completada = request.data.get('cantidad_completada', tarea.cantidad_completada)
            observaciones = request.data.get('observaciones', '')
            operador_id = request.data.get('operador_id')
            
            # Actualizar tarea
            datos_anteriores = {
                'cantidad_completada': str(tarea.cantidad_completada),
                'estado': tarea.estado,
                'porcentaje': str(tarea.porcentaje_cumplimiento)
            }
            
            # Aplicar cambios
            tarea.actualizar_tiempo_real(cantidad_completada, request.user)
            
            if observaciones:
                tarea.observaciones = observaciones
                
            if operador_id:
                operador = get_object_or_404(Operador, id=operador_id)
                tarea.operador = operador
                
            tarea.save()
            
            # Respuesta con datos actualizados + timeline actualizada
            timeline_actualizada = self.get_timeline_actualizada(tarea.programa)
            
            return Response({
                'success': True,
                'tarea': {
                    'id': tarea.id,
                    'cantidad_completada': float(tarea.cantidad_completada),
                    'porcentaje_cumplimiento': float(tarea.porcentaje_cumplimiento),
                    'estado': tarea.estado,
                    'ultima_actualizacion': tarea.ultima_actualizacion_tiempo_real
                },
                'timeline_actualizada': timeline_actualizada
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_timeline_actualizada(self, programa):
        """Obtiene la timeline actualizada después del cambio"""
        # Usar el scheduler existente para regenerar timeline
        
        calculator = TimeCalculator()
        scheduler = ProductionScheduler(calculator)
        
        # Obtener OTs del programa
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
        
        return scheduler.generate_timeline_data(programa, program_ots)

class ProgramaTimelineRealtimeView(APIView):
    """Vista para obtener timeline en modo tiempo real"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, programa_id):
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            # Generar timeline tiempo real directamente de ItemRuta
            timeline_tiempo_real = self.generar_timeline_tiempo_real(programa)
            
            return Response(timeline_tiempo_real)
            
        except Exception as e:
            return Response({
                'error': f'Error obteniendo timeline tiempo real: {str(e)}'
            }, status=500)
    
    def generar_timeline_tiempo_real(self, programa):
        """Genera timeline tiempo real basado en ItemRuta actuales"""
        grupos_ot = []
        grupos_timeline = []
        items_timeline = []
        item_id_counter = 1
        
        # Obtener todas las OTs del programa ordenadas por prioridad
        programa_ots = ProgramaOrdenTrabajo.objects.filter(programa=programa).order_by('prioridad')
        
        for prog_ot in programa_ots:
            if not hasattr(prog_ot.orden_trabajo, 'ruta_ot') or not prog_ot.orden_trabajo.ruta_ot:
                continue
                
            orden_trabajo = prog_ot.orden_trabajo
            
            # Grupo OT principal para la respuesta
            grupo_ot = {
                "id": f"ot_{orden_trabajo.codigo_ot}",
                "orden_trabajo_id": orden_trabajo.id,
                "orden_trabajo_codigo_ot": orden_trabajo.codigo_ot,
                "descripcion": orden_trabajo.descripcion_producto_ot or f"OT {orden_trabajo.codigo_ot}",
                "cantidad_total": float(orden_trabajo.cantidad),
                "cantidad_avance": float(orden_trabajo.cantidad_avance),
                "prioridad": prog_ot.prioridad,
                "porcentaje_avance_ot": (float(orden_trabajo.cantidad_avance) / float(orden_trabajo.cantidad) * 100) if orden_trabajo.cantidad > 0 else 0,
                "procesos": []
            }
            
            # Grupo principal OT para timeline (solo contenedor)
            grupo_ot_timeline = {
                "id": f"ot_{orden_trabajo.codigo_ot}",
                "title": f"📋 OT {orden_trabajo.codigo_ot} - {orden_trabajo.descripcion_producto_ot or 'Sin descripción'}",
                "rightTitle": f"{grupo_ot['porcentaje_avance_ot']:.1f}%",
                "stackItems": True,
                "height": 60,
                "className": "timeline-group-ot"
            }
            grupos_timeline.append(grupo_ot_timeline)
            
            # Obtener todos los ItemRuta de esta OT
            items_ruta = orden_trabajo.ruta_ot.items.all().order_by('item')
            
            for item_ruta in items_ruta:
                # Calcular progreso del proceso
                cantidad_total = float(item_ruta.cantidad_pedido)
                cantidad_completada = float(item_ruta.cantidad_terminado_proceso)
                cantidad_pendiente = cantidad_total - cantidad_completada
                porcentaje = (cantidad_completada / cantidad_total * 100) if cantidad_total > 0 else 0
                
                # Datos del proceso para la respuesta
                elemento_proceso = {
                    "id": f"itemruta_{item_ruta.id}",
                    "item_ruta_id": item_ruta.id,
                    "item": item_ruta.item,
                    "proceso": {
                        "id": item_ruta.proceso.id,
                        "codigo": item_ruta.proceso.codigo_proceso,
                        "descripcion": item_ruta.proceso.descripcion
                    },
                    "maquina": {
                        "id": item_ruta.maquina.id if item_ruta.maquina else None,
                        "codigo": item_ruta.maquina.codigo_maquina if item_ruta.maquina else "Sin asignar",
                        "descripcion": item_ruta.maquina.descripcion if item_ruta.maquina else "Sin máquina"
                    },
                    "estandar": float(item_ruta.estandar) if item_ruta.estandar else 0,
                    
                    # Cantidades y progreso  
                    "cantidad_total": cantidad_total,
                    "cantidad_completada": cantidad_completada,
                    "cantidad_pendiente": cantidad_pendiente,
                    "porcentaje_completado": round(porcentaje, 1),
                    
                    # Estado del proceso
                    "estado_proceso": item_ruta.estado_proceso,
                    "estado_visual": self.determinar_estado_item(item_ruta),
                    "color_progreso": self.get_color_progreso(porcentaje, item_ruta.estado_proceso),
                    
                    # Operador asignado
                    "operador_actual": {
                        "id": item_ruta.operador_actual.id,
                        "nombre": f"{item_ruta.operador_actual.nombre} {item_ruta.operador_actual.apellido}"
                    } if item_ruta.operador_actual else None,
                    
                    # Fechas reales
                    "fecha_inicio_real": item_ruta.fecha_inicio_real,
                    "fecha_fin_real": item_ruta.fecha_fin_real,
                    "ultima_actualizacion": item_ruta.ultima_actualizacion_progreso,
                    
                    # Para interactividad
                    "clickeable": item_ruta.permite_progreso_directo,
                    "observaciones": item_ruta.observaciones_progreso,
                    "es_ultimo_proceso_ot": item_ruta.es_ultimo_proceso_ot,
                    
                    # Información adicional para el modal
                    "cantidad_en_proceso": float(item_ruta.cantidad_en_proceso) if hasattr(item_ruta, 'cantidad_en_proceso') else 0,
                    "cantidad_perdida_proceso": float(item_ruta.cantidad_perdida_proceso) if hasattr(item_ruta, 'cantidad_perdida_proceso') else 0,
                    "historial_progreso": item_ruta.historial_progreso[-5:] if hasattr(item_ruta, 'historial_progreso') and item_ruta.historial_progreso else []
                }
                
                grupo_ot["procesos"].append(elemento_proceso)
                
                # Grupo proceso para timeline
                proceso_timeline_id = f"proceso_{item_ruta.id}"
                grupo_proceso_timeline = {
                    "id": proceso_timeline_id,
                    "title": f"🔧 {item_ruta.item}. {item_ruta.proceso.descripcion}",
                    "rightTitle": f"{porcentaje:.1f}% ({cantidad_completada:.0f}/{cantidad_total:.0f})",
                    "parent": f"ot_{orden_trabajo.codigo_ot}",
                    "height": 40,
                    "className": f"timeline-group-proceso estado-{item_ruta.estado_proceso.lower()}"
                }
                grupos_timeline.append(grupo_proceso_timeline)
                
                # Item timeline con fechas reales o estimadas
                start_time = item_ruta.fecha_inicio_real if item_ruta.fecha_inicio_real else timezone.now()
                
                # Calcular duración basada en estándar o usar default
                if item_ruta.estandar and item_ruta.estandar > 0 and cantidad_total > 0:
                    duracion_horas = cantidad_total / item_ruta.estandar
                else:
                    duracion_horas = 4  # Default 4 horas
                    
                end_time = item_ruta.fecha_fin_real if item_ruta.fecha_fin_real else (
                    start_time + timedelta(hours=duracion_horas)
                )
                
                item_timeline = {
                    "id": item_id_counter,
                    "group": proceso_timeline_id,
                    "title": f"{item_ruta.estado_proceso} - {porcentaje:.1f}%",
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "className": f"timeline-item-{item_ruta.estado_proceso.lower()}",
                    "canMove": False,
                    "canResize": False,
                    "itemProps": {
                        "data-item-ruta-id": item_ruta.id,
                        "data-ot-codigo": orden_trabajo.codigo_ot,
                        "data-proceso-descripcion": item_ruta.proceso.descripcion,
                        "data-porcentaje": porcentaje,
                        "data-estado": item_ruta.estado_proceso,
                        "data-clickeable": item_ruta.permite_progreso_directo,
                        "style": {
                            "backgroundColor": self.get_color_progreso(porcentaje, item_ruta.estado_proceso),
                            "borderRadius": "4px",
                            "color": "white",
                            "border": "1px solid rgba(255,255,255,0.3)",
                            "fontSize": "11px",
                            "padding": "2px 4px"
                        }
                    }
                }
                items_timeline.append(item_timeline)
                item_id_counter += 1
            
            # Solo agregar OT si tiene procesos
            if grupo_ot["procesos"]:
                grupos_ot.append(grupo_ot)
        
        return {
            "tipo": "TIEMPO_REAL_MEJORADO",
            "groups": grupos_timeline,  # Para react-calendar-timeline
            "items": items_timeline,    # Para react-calendar-timeline
            "ots": grupos_ot,          # Para cards/vistas alternativas
            "metadata": {
                "fecha_actualizacion": timezone.now().isoformat(),
                "programa_id": programa.id,
                "total_ots": len(grupos_ot),
                "total_procesos": sum(len(grupo["procesos"]) for grupo in grupos_ot),
                "progreso_general": self.calcular_progreso_general(grupos_ot)
            }
        }
    
    def calcular_progreso_general(self, grupos_ot):
        """Calcula el progreso general del programa"""
        if not grupos_ot:
            return 0.0
            
        total_cantidad = 0
        total_avance = 0
        
        for grupo in grupos_ot:
            ot_cantidad = grupo["cantidad_total"]
            ot_avance = grupo["cantidad_avance"]
            total_cantidad += ot_cantidad
            total_avance += ot_avance
        
        return (total_avance / total_cantidad * 100) if total_cantidad > 0 else 0.0
    
    def determinar_estado_item(self, item_ruta):
        """Determina el estado visual del item"""
        if item_ruta.estado_proceso == 'COMPLETADO':
            return 'COMPLETADO'
        elif item_ruta.estado_proceso == 'EN_PROCESO':
            return 'EN_PROCESO'
        elif item_ruta.operador_actual:
            return 'ASIGNADO'
        else:
            return 'PENDIENTE'
    
    def get_color_progreso(self, porcentaje, estado_proceso):
        """Obtiene el color para la barra de progreso"""
        if estado_proceso == 'COMPLETADO' or porcentaje >= 100:
            return '#28a745'  # Verde - Completado
        elif estado_proceso == 'EN_PROCESO':
            if porcentaje >= 75:
                return '#007bff'  # Azul - Avanzado
            elif porcentaje >= 50:
                return '#ffc107'  # Amarillo - En progreso
            else:
                return '#fd7e14'  # Naranja - Iniciado
        elif estado_proceso == 'PAUSADO':
            return '#dc3545'  # Rojo - Pausado
        else:
            return '#6c757d'  # Gris - Pendiente

# AGREGAR al final del archivo:

# ========================================================================
# VISTAS PARA PROGRESO DIRECTO DE ITEMRUTA
# ========================================================================

class ItemRutaProgressView(APIView):
    """Vista para actualizar progreso directo de ItemRuta"""
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, item_ruta_id):
        """Actualiza el progreso de un ItemRuta específico"""
        try:
            item_ruta = get_object_or_404(ItemRuta, id=item_ruta_id)
            
            # Validar que el item permite progreso directo
            if not item_ruta.permite_progreso_directo:
                return Response({
                    'error': 'Este item no permite actualizaciones de progreso directo'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Extraer datos del request
            cantidad_completada_nueva = request.data.get('cantidad_completada', 0)
            operador_id = request.data.get('operador_id')
            observaciones = request.data.get('observaciones', '')
            
            # Obtener operador si se proporciona
            operador = None
            if operador_id:
                try:
                    from Operator.models import Operador
                    operador = Operador.objects.get(id=operador_id)
                except Operador.DoesNotExist:
                    return Response({
                        'error': 'Operador no encontrado'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Actualizar progreso
            item_ruta.actualizar_progreso(
                cantidad_completada_nueva=float(cantidad_completada_nueva),
                operador=operador,
                observaciones=observaciones,
                usuario=request.user
            )
            
            # Serializar respuesta
            response_data = {
                'id': item_ruta.id,
                'item': item_ruta.item,
                'cantidad_pedido': item_ruta.cantidad_pedido,
                'cantidad_terminado_proceso': item_ruta.cantidad_terminado_proceso,
                'cantidad_pendiente': item_ruta.cantidad_pendiente,
                'porcentaje_completado': item_ruta.porcentaje_completado,
                'estado_proceso': item_ruta.estado_proceso,
                'fecha_inicio_real': item_ruta.fecha_inicio_real,
                'fecha_fin_real': item_ruta.fecha_fin_real,
                'operador_actual': {
                    'id': item_ruta.operador_actual.id,
                    'nombre': f"{item_ruta.operador_actual.nombre} {item_ruta.operador_actual.apellido}"
                } if item_ruta.operador_actual else None,
                'observaciones_progreso': item_ruta.observaciones_progreso,
                'ultima_actualizacion': item_ruta.ultima_actualizacion_progreso,
                # Información de la OT
                'orden_trabajo': {
                    'codigo_ot': item_ruta.ruta.orden_trabajo.codigo_ot,
                    'cantidad_avance': item_ruta.ruta.orden_trabajo.cantidad_avance,
                    'es_ultimo_proceso': item_ruta.es_ultimo_proceso_ot
                } if item_ruta.ruta.orden_trabajo else None,
                
                # NUEVOS CAMPOS IMPORTANTES:
                'cantidad_en_proceso': item_ruta.cantidad_en_proceso,
                'cantidad_perdida_proceso': item_ruta.cantidad_perdida_proceso,
                'terminado_sin_actualizar': item_ruta.terminado_sin_actualizar,
                'historial_progreso': item_ruta.historial_progreso[-10:],  # Últimos 10 cambios
                
                # TIEMPOS REALES
                'fecha_inicio_real': item_ruta.fecha_inicio_real,
                'fecha_fin_real': item_ruta.fecha_fin_real,
                'duracion_real_minutos': self.calcular_duracion_real(item_ruta),
                
                # EFICIENCIA
                'velocidad_actual': self.calcular_velocidad_actual(item_ruta),
                'eficiencia_vs_estandar': self.calcular_eficiencia(item_ruta),
                
                # CONTEXTO DE LA OT
                'ot_tiene_multa': item_ruta.ruta.orden_trabajo.multa,
                'ot_observaciones': item_ruta.ruta.orden_trabajo.observacion_ot,
                'peso_unitario': item_ruta.ruta.orden_trabajo.peso_unitario,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def calcular_duracion_real(self, item_ruta):
        """Calcula la duración real en minutos del proceso"""
        if item_ruta.fecha_inicio_real and item_ruta.fecha_fin_real:
            delta = item_ruta.fecha_fin_real - item_ruta.fecha_inicio_real
            return round(delta.total_seconds() / 60, 2)  # Convertir a minutos
        elif item_ruta.fecha_inicio_real and item_ruta.estado_proceso == 'EN_PROCESO':
            # Proceso en curso, calcular tiempo transcurrido
            from django.utils import timezone
            delta = timezone.now() - item_ruta.fecha_inicio_real
            return round(delta.total_seconds() / 60, 2)
        return None
    
    def calcular_velocidad_actual(self, item_ruta):
        """Calcula la velocidad actual en unidades por hora"""
        duracion_minutos = self.calcular_duracion_real(item_ruta)
        if duracion_minutos and duracion_minutos > 0 and item_ruta.cantidad_terminado_proceso > 0:
            # Convertir minutos a horas
            duracion_horas = duracion_minutos / 60
            return round(float(item_ruta.cantidad_terminado_proceso) / duracion_horas, 2)
        return None
    
    def calcular_eficiencia(self, item_ruta):
        """Calcula la eficiencia vs estándar"""
        velocidad_actual = self.calcular_velocidad_actual(item_ruta)
        if velocidad_actual and item_ruta.estandar and item_ruta.estandar > 0:
            # El estándar está en unidades por hora
            return round((velocidad_actual / item_ruta.estandar) * 100, 2)
        return None

class ItemRutaIniciarProcesoView(APIView):
    """Vista para iniciar un proceso de ItemRuta"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, item_ruta_id):
        """Inicia el proceso de un ItemRuta"""
        try:
            item_ruta = get_object_or_404(ItemRuta, id=item_ruta_id)
            
            operador_id = request.data.get('operador_id')
            observaciones = request.data.get('observaciones', '')
            
            # Obtener operador
            operador = None
            if operador_id:
                try:
                    from Operator.models import Operador
                    operador = Operador.objects.get(id=operador_id)
                except Operador.DoesNotExist:
                    return Response({
                        'error': 'Operador no encontrado'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Iniciar proceso
            item_ruta.iniciar_proceso(operador=operador, observaciones=observaciones)
            
            return Response({
                'message': 'Proceso iniciado correctamente',
                'estado_proceso': item_ruta.estado_proceso,
                'fecha_inicio_real': item_ruta.fecha_inicio_real
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProgramaItemsProgressView(APIView):
    """Vista para obtener el progreso de todos los ItemRuta de un programa"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, programa_id):
        """Obtiene el progreso actual de todos los ItemRuta del programa"""
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            # Obtener todas las OTs del programa
            programa_ots = ProgramaOrdenTrabajo.objects.filter(programa=programa).order_by('prioridad')
            
            items_progress = []
            
            for prog_ot in programa_ots:
                if hasattr(prog_ot.orden_trabajo, 'ruta_ot') and prog_ot.orden_trabajo.ruta_ot:
                    items = prog_ot.orden_trabajo.ruta_ot.items.all().order_by('item')
                    
                    for item in items:
                        items_progress.append({
                            'id': item.id,
                            'item': item.item,
                            'proceso': {
                                'id': item.proceso.id,
                                'codigo': item.proceso.codigo_proceso,
                                'descripcion': item.proceso.descripcion
                            },
                            'maquina': {
                                'id': item.maquina.id,
                                'codigo': item.maquina.codigo_maquina,
                                'descripcion': item.maquina.descripcion
                            },
                            'cantidad_pedido': item.cantidad_pedido,
                            'cantidad_terminado_proceso': item.cantidad_terminado_proceso,
                            'cantidad_pendiente': item.cantidad_pendiente,
                            'porcentaje_completado': item.porcentaje_completado,
                            'estado_proceso': item.estado_proceso,
                            'estandar': item.estandar,
                            'fecha_inicio_real': item.fecha_inicio_real,
                            'fecha_fin_real': item.fecha_fin_real,
                            'operador_actual': {
                                'id': item.operador_actual.id,
                                'nombre': f"{item.operador_actual.nombre} {item.operador_actual.apellido}"
                            } if item.operador_actual else None,
                            'observaciones_progreso': item.observaciones_progreso,
                            'ultima_actualizacion': item.ultima_actualizacion_progreso,
                            'permite_progreso_directo': item.permite_progreso_directo,
                            'es_ultimo_proceso_ot': item.es_ultimo_proceso_ot,
                            # Información de la OT
                            'orden_trabajo': {
                                'codigo_ot': prog_ot.orden_trabajo.codigo_ot,
                                'prioridad': prog_ot.prioridad,
                                'cantidad': prog_ot.orden_trabajo.cantidad,
                                'cantidad_avance': prog_ot.orden_trabajo.cantidad_avance,
                                'descripcion': prog_ot.orden_trabajo.descripcion_producto_ot
                            }
                        })
            
            return Response({
                'programa': {
                    'id': programa.id,
                    'nombre': programa.nombre,
                    'fecha_inicio': programa.fecha_inicio,
                    'fecha_fin': programa.fecha_fin
                },
                'items': items_progress
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# AGREGAR al final del archivo program_views.py (después de ItemRutaProgressView):

class FinalizarDiaView(APIView):
    """Vista para finalizar el día y regenerar planificación"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, programa_id):
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        fecha_finalizacion = request.data.get('fecha', timezone.now().date())
        
        # CORRECCIÓN: Asegurar que fecha_finalizacion sea un objeto date
        if isinstance(fecha_finalizacion, str):
            try:
                fecha_finalizacion = datetime.strptime(fecha_finalizacion, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    "success": False,
                    "error": "Formato de fecha inválido. Use YYYY-MM-DD"
                }, status=400)
        
        try:
            #print(f"[DEBUG] Iniciando finalización de día {fecha_finalizacion} para programa {programa_id}")
            
            # 1. Obtener timeline actual ANTES de guardar snapshot
            #print("[DEBUG] Obteniendo timeline actual...")
            timeline_actual = self.get_timeline_actual(programa)
            #print(f"[DEBUG] Timeline obtenida: {len(timeline_actual.get('groups', []))} grupos, {len(timeline_actual.get('items', []))} items")
            
            # 2. Recopilar progresos reales del día
            #print("[DEBUG] Recopilando progresos del día...")
            progresos_dia = self.recopilar_progresos_dia(programa, fecha_finalizacion)
            #print(f"[DEBUG] Progresos encontrados: {len(progresos_dia)}")
            
            # 3. Guardar snapshot de la timeline actual CON DATOS
            #print("[DEBUG] Creando snapshot...")
            snapshot = self.crear_snapshot_dia(programa, fecha_finalizacion, timeline_actual, request.user)
            #print(f"[DEBUG] Snapshot creado: {snapshot.id if snapshot else 'ERROR'}")
            
            # 4. Regenerar planificación para mañana
            nueva_timeline = None
            nueva_fecha_inicio = self.calcular_siguiente_dia_laboral(fecha_finalizacion)
            
            if progresos_dia:  # Solo si hay progresos
                #print("[DEBUG] Regenerando planificación...")
                nueva_timeline = self.regenerar_planificacion(programa, progresos_dia)
                # Actualizar fecha de inicio del programa
                programa.fecha_inicio = nueva_fecha_inicio
                programa.save(update_fields=['fecha_inicio'])
                #print(f"[DEBUG] Nueva fecha inicio: {nueva_fecha_inicio}")
            
            # CORRECCIÓN: Formatear correctamente la fecha para el response
            fecha_siguiente_str = nueva_fecha_inicio.strftime('%Y-%m-%d') if nueva_fecha_inicio else None
            
            return Response({
                "success": True,
                "mensaje": f"Día {fecha_finalizacion} finalizado exitosamente",
                "progresos_registrados": len(progresos_dia),
                "fecha_siguiente_inicio": fecha_siguiente_str,
                "snapshot_id": snapshot.id if snapshot else None,
                "regeneracion_realizada": bool(progresos_dia),
                # NUEVO: Información de debug
                "debug_info": {
                    "timeline_groups": len(timeline_actual.get('groups', [])),
                    "timeline_items": len(timeline_actual.get('items', [])),
                    "progresos_detalle": progresos_dia[:3] if progresos_dia else []  # Primeros 3 para debug
                }
            })
            
        except Exception as e:
            print(f"Error en FinalizarDiaView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                "success": False,
                "error": f"Error finalizando día: {str(e)}"
            }, status=500)
    
    def get_timeline_actual(self, programa):
        """Obtiene la timeline actual del programa usando ProgramaTimelineRealtimeView"""
        try:
            #print(f"[DEBUG] Obteniendo timeline tiempo real para programa {programa.id}")
            
            # Usar directamente el método que sabemos funciona
            timeline_view = ProgramaTimelineRealtimeView()
            timeline_data = timeline_view.generar_timeline_tiempo_real(programa)
            
            #print(f"[DEBUG] Timeline generada: tipo={timeline_data.get('tipo')}")
            #print(f"[DEBUG] Grupos: {len(timeline_data.get('groups', []))}")
            #print(f"[DEBUG] Items: {len(timeline_data.get('items', []))}")
            #print(f"[DEBUG] OTs: {len(timeline_data.get('ots', []))}")
            
            return timeline_data
            
        except Exception as e:
            print(f"[ERROR] Error obteniendo timeline actual: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Fallback: usar método básico
            try:
                #print("[DEBUG] Intentando método fallback...")
                ordenes_trabajo = self._get_ordenes_trabajo_basico(programa)
                
                return {
                    "tipo": "FALLBACK_FINALIZACION",
                    "groups": [],
                    "items": [],
                    "ots": ordenes_trabajo,
                    "metadata": {
                        "fecha_generacion": timezone.now().isoformat(),
                        "metodo": "fallback",
                        "total_ots": len(ordenes_trabajo)
                    }
                }
            except Exception as e2:
                print(f"[ERROR] Error en fallback: {str(e2)}")
                return {
                    "tipo": "ERROR_TIMELINE", 
                    "groups": [], 
                    "items": [],
                    "ots": [],
                    "error": str(e),
                    "error_fallback": str(e2)
                }
    
    def _get_ordenes_trabajo_basico(self, programa):
        """Versión básica para obtener órdenes de trabajo sin depender de scheduler"""
        try:
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

            ordenes_trabajo = []
            for prog_ot in program_ots:
                if hasattr(prog_ot.orden_trabajo, 'ruta_ot') and prog_ot.orden_trabajo.ruta_ot:
                    ot_data = {
                        'id': prog_ot.orden_trabajo.id,
                        'orden_trabajo_codigo_ot': prog_ot.orden_trabajo.codigo_ot,
                        'orden_trabajo_descripcion_producto_ot': prog_ot.orden_trabajo.descripcion_producto_ot,
                        'cantidad_total': float(prog_ot.orden_trabajo.cantidad),
                        'cantidad_avance': float(prog_ot.orden_trabajo.cantidad_avance),
                        'prioridad': prog_ot.prioridad,
                        'procesos': []
                    }
                    
                    # Procesos de la OT
                    for item in prog_ot.orden_trabajo.ruta_ot.items.all().order_by('item'):
                        proceso_data = {
                            'id': item.id,
                            'item': item.item,
                            'proceso': {
                                'id': item.proceso.id,
                                'codigo': item.proceso.codigo_proceso,
                                'descripcion': item.proceso.descripcion
                            },
                            'maquina': {
                                'id': item.maquina.id if item.maquina else None,
                                'codigo': item.maquina.codigo_maquina if item.maquina else "Sin asignar",
                                'descripcion': item.maquina.descripcion if item.maquina else "Sin máquina"
                            },
                            'cantidad_total': float(item.cantidad_pedido),
                            'cantidad_completada': float(item.cantidad_terminado_proceso),
                            'porcentaje_completado': float(item.porcentaje_completado),
                            'estado_proceso': item.estado_proceso,
                            'estandar': float(item.estandar) if item.estandar else 0,
                            'operador_actual': {
                                'id': item.operador_actual.id,
                                'nombre': f"{item.operador_actual.nombre} {item.operador_actual.apellido}"
                            } if item.operador_actual else None
                        }
                        ot_data['procesos'].append(proceso_data)
                    
                    ordenes_trabajo.append(ot_data)
            
            return ordenes_trabajo
            
        except Exception as e:
            print(f"[ERROR] Error en _get_ordenes_trabajo_basico: {str(e)}")
            return []
    
    def crear_snapshot_dia(self, programa, fecha, timeline_data, usuario):
        """Crea un snapshot JSON del día CON VALIDACIÓN"""
        try:
            #print(f"[DEBUG] Creando snapshot para fecha {fecha}")
            #print(f"[DEBUG] Timeline data tipo: {type(timeline_data)}")
            #print(f"[DEBUG] Timeline keys: {timeline_data.keys() if isinstance(timeline_data, dict) else 'NO ES DICT'}")
            
            # VALIDAR que timeline_data no esté vacío
            if not timeline_data or not isinstance(timeline_data, dict):
                print("[WARNING] Timeline data está vacío o no es dict, usando estructura mínima")
                timeline_data = {
                    "tipo": "SNAPSHOT_VACIO",
                    "groups": [],
                    "items": [],
                    "ots": [],
                    "metadata": {
                        "fecha_snapshot": timezone.now().isoformat(),
                        "advertencia": "Timeline vacío al momento del snapshot"
                    }
                }
            
            # Asegurar estructura mínima
            timeline_snapshot = {
                "tipo": timeline_data.get("tipo", "SNAPSHOT_FINALIZACION"),
                "groups": timeline_data.get("groups", []),
                "items": timeline_data.get("items", []),
                "ots": timeline_data.get("ots", []),
                "metadata": {
                    **timeline_data.get("metadata", {}),
                    "fecha_snapshot": timezone.now().isoformat(),
                    "programa_id": programa.id,
                    "fecha_finalizacion": fecha.isoformat() if hasattr(fecha, 'isoformat') else str(fecha),
                    "usuario_finalizacion": usuario.id if usuario else None
                }
            }
            
            #print(f"[DEBUG] Snapshot final: grupos={len(timeline_snapshot['groups'])}, items={len(timeline_snapshot['items'])}, ots={len(timeline_snapshot['ots'])}")
            
            snapshot = HistorialPlanificacion.objects.create(
                programa=programa,
                fecha_referencia=fecha,
                tipo_reajuste='FINALIZACION_DIA',
                timeline_data=timeline_snapshot,  # Usar la estructura validada
                creado_por=usuario,
                observaciones=f"Finalización automática del día {fecha}"
            )
            
            print(f"[DEBUG] Snapshot creado exitosamente con ID: {snapshot.id}")
            return snapshot
            
        except Exception as e:
            print(f"[ERROR] Error creando snapshot: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def recopilar_progresos_dia(self, programa, fecha):
        """Recopila todos los progresos reales del día"""
        try:
            print(f"[DEBUG] Buscando ItemRuta con progreso en fecha {fecha}")
            
            # Obtener todos los ItemRuta del programa que tuvieron actividad hoy
            items_con_progreso = ItemRuta.objects.filter(
                ruta__orden_trabajo__programaordentrabajo__programa=programa,
                ultima_actualizacion_progreso__date=fecha
            ).select_related(
                'proceso',
                'maquina', 
                'operador_actual',
                'ruta__orden_trabajo'
            )
            
            print(f"[DEBUG] Encontrados {items_con_progreso.count()} ItemRuta con progreso")
            
            progresos = []
            for item in items_con_progreso:
                # Obtener cantidad anterior (del historial si existe)
                cantidad_anterior = self.get_cantidad_anterior(item, fecha)
                
                progreso = {
                    "item_ruta_id": item.id,
                    "proceso": item.proceso.descripcion,
                    "maquina": item.maquina.descripcion if item.maquina else "Sin máquina",
                    "orden_trabajo": item.ruta.orden_trabajo.codigo_ot,
                    "cantidad_anterior": cantidad_anterior,
                    "cantidad_actual": float(item.cantidad_terminado_proceso),
                    "avance_dia": float(item.cantidad_terminado_proceso) - cantidad_anterior,
                    "porcentaje_completado": float(item.porcentaje_completado),
                    "estado": item.estado_proceso,
                    "operador": item.operador_actual.nombre if item.operador_actual else "Sin asignar",
                    "operador_id": item.operador_actual.id if item.operador_actual else None,
                    "ultima_actualizacion": item.ultima_actualizacion_progreso.isoformat() if item.ultima_actualizacion_progreso else None
                }
                progresos.append(progreso)
                print(f"[DEBUG] Progreso: OT {progreso['orden_trabajo']}, Item {item.item}, avance: {progreso['avance_dia']}")
            
            print(f"[DEBUG] Total progresos recopilados: {len(progresos)}")
            return progresos
            
        except Exception as e:
            print(f"[ERROR] Error recopilando progresos: {str(e)}")
            return []
    
    def get_cantidad_anterior(self, item_ruta, fecha):
        """Obtiene la cantidad anterior al día especificado"""
        try:
            # Buscar en el historial de progreso
            historial = item_ruta.historial_progreso or []
            
            # Buscar el último registro antes de la fecha especificada
            cantidad_anterior = 0
            for registro in reversed(historial):  # Empezar por el más reciente
                try:
                    fecha_registro = datetime.fromisoformat(registro['fecha']).date()
                    if fecha_registro < fecha:
                        if registro['tipo'] == 'ACTUALIZACION_PROGRESO':
                            cantidad_anterior = registro['datos'].get('cantidad_nueva', 0)
                            break
                except (KeyError, ValueError):
                    continue
            
            return float(cantidad_anterior)
            
        except Exception as e:
            print(f"[ERROR] Error obteniendo cantidad anterior: {str(e)}")
            return 0.0
    
    def regenerar_planificacion(self, programa, progresos_dia):
        """Regenera la planificación basada en el progreso real"""
        try:
            print("[DEBUG] Iniciando regeneración de planificación...")
            
            # Por ahora, solo retornamos la timeline actual actualizada
            # En el futuro aquí iría la lógica de replanificación inteligente
            timeline_actualizada = self.get_timeline_actual(programa)
            
            print("[DEBUG] Regeneración completada (usando timeline actual)")
            return timeline_actualizada
            
        except Exception as e:
            print(f"[ERROR] Error regenerando planificación: {str(e)}")
            return None
    
    def calcular_siguiente_dia_laboral(self, fecha_actual):
        """Calcula el siguiente día laboral"""
        try:
            # CORRECCIÓN: Asegurar que fecha_actual sea un objeto date
            if isinstance(fecha_actual, datetime):
                fecha_actual = fecha_actual.date()
            
            # Si es viernes, el siguiente día laboral es lunes
            # Si es cualquier otro día, es el día siguiente
            siguiente_dia = fecha_actual + timedelta(days=1)
            
            # Asegurar que sea día laboral (lunes a viernes)
            while siguiente_dia.weekday() >= 5:  # 5=sábado, 6=domingo
                siguiente_dia += timedelta(days=1)
            
            return siguiente_dia
            
        except Exception as e:
            print(f"[ERROR] Error calculando siguiente día laboral: {str(e)}")
            return fecha_actual + timedelta(days=1)  # Fallback


class ItemRutaEstadoView(APIView):
    """Vista para actualizar solo el estado de un ItemRuta"""
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, item_ruta_id):
        """Actualiza solo el estado del ItemRuta"""
        try:
            item_ruta = get_object_or_404(ItemRuta, id=item_ruta_id)
            nuevo_estado = request.data.get('estado_proceso')
            
            # Validar que el estado sea válido
            estados_validos = ['PENDIENTE', 'EN_PROCESO', 'COMPLETADO', 'PAUSADO', 'CANCELADO']
            if nuevo_estado not in estados_validos:
                return Response({
                    'error': f'Estado inválido. Estados válidos: {estados_validos}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Actualizar estado
            estado_anterior = item_ruta.estado_proceso
            item_ruta.estado_proceso = nuevo_estado
            
            # Lógica especial según el estado
            if nuevo_estado == 'EN_PROCESO' and not item_ruta.fecha_inicio_real:
                item_ruta.fecha_inicio_real = timezone.now()
            elif nuevo_estado == 'COMPLETADO':
                if not item_ruta.fecha_fin_real:
                    item_ruta.fecha_fin_real = timezone.now()
                # Si se marca como completado pero no tiene cantidad terminada, usar cantidad pedida
                if item_ruta.cantidad_terminado_proceso == 0:
                    item_ruta.cantidad_terminado_proceso = item_ruta.cantidad_pedido
                    item_ruta.porcentaje_completado = 100
            elif nuevo_estado == 'PAUSADO' and estado_anterior == 'EN_PROCESO':
                # Registrar pausa en el historial
                pass
            
            # Registrar cambio en historial
            item_ruta.registrar_cambio_progreso('CAMBIO_ESTADO', {
                'estado_anterior': estado_anterior,
                'estado_nuevo': nuevo_estado,
                'usuario': request.user.id if request.user else None,
                'fecha_cambio': timezone.now().isoformat()
            })
            
            item_ruta.save()
            
            return Response({
                'id': item_ruta.id,
                'estado_proceso': item_ruta.estado_proceso,
                'fecha_inicio_real': item_ruta.fecha_inicio_real,
                'fecha_fin_real': item_ruta.fecha_fin_real,
                'cantidad_terminado_proceso': item_ruta.cantidad_terminado_proceso,
                'porcentaje_completado': item_ruta.porcentaje_completado,
                'message': f'Estado actualizado de {estado_anterior} a {nuevo_estado}'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# AGREGAR estas clases justo antes de la línea donde dice "class FinalizarDiaView(APIView):"

class ObtenerTimelineActualView(APIView):
    """Vista para obtener la timeline actual de un programa en cualquier momento"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, programa_id):
        """Obtiene la timeline completa actual del programa"""
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            print(f"[TIMELINE ACTUAL] Generando timeline para programa {programa_id}")
            
            # 1. Usar ProgramaTimelineRealtimeView para obtener datos completos
            timeline_view = ProgramaTimelineRealtimeView()
            timeline_data = timeline_view.generar_timeline_tiempo_real(programa)
            
            # 2. Agregar información adicional del programa
            programa_info = {
                'id': programa.id,
                'nombre': programa.nombre,
                'fecha_inicio': programa.fecha_inicio.isoformat(),
                'fecha_fin': programa.fecha_fin.isoformat() if programa.fecha_fin else None,
                'created_at': programa.created_at.isoformat() if programa.created_at else None,
                'updated_at': programa.updated_at.isoformat() if programa.updated_at else None,
            }
            
            # 3. Agregar información de asignaciones de operadores
            asignaciones_info = []
            try:
                from Operator.models import AsignacionOperador
                asignaciones = AsignacionOperador.objects.filter(programa=programa).select_related('operador', 'item_ruta')
                for asig in asignaciones:
                    asignaciones_info.append({
                        'id': asig.id,
                        'operador_id': asig.operador.id if asig.operador else None,
                        'operador_nombre': asig.operador.nombre if asig.operador else None,
                        'item_ruta_id': asig.item_ruta.id,
                        'fecha_inicio': asig.fecha_inicio.isoformat() if asig.fecha_inicio else None,
                        'fecha_fin': asig.fecha_fin.isoformat() if asig.fecha_fin else None,
                    })
            except ImportError:
                pass
            
            # 4. Crear estructura completa de timeline
            timeline_completa = {
                "version": "1.0",
                "fecha_generacion": timezone.now().isoformat(),
                "programa": programa_info,
                "timeline": timeline_data,
                "asignaciones": asignaciones_info,
                "estadisticas": {
                    "total_ots": len(timeline_data.get('ots', [])),
                    "total_procesos": sum(len(ot.get('procesos', [])) for ot in timeline_data.get('ots', [])),
                    "progreso_general": timeline_data.get('metadata', {}).get('progreso_general', 0),
                    "grupos_timeline": len(timeline_data.get('groups', [])),
                    "items_timeline": len(timeline_data.get('items', []))
                }
            }
            
            print(f"[TIMELINE ACTUAL] Timeline generada exitosamente:")
            print(f"  - OTs: {timeline_completa['estadisticas']['total_ots']}")
            print(f"  - Procesos: {timeline_completa['estadisticas']['total_procesos']}")
            print(f"  - Progreso: {timeline_completa['estadisticas']['progreso_general']:.1f}%")
            
            return Response(timeline_completa)
            
        except Exception as e:
            print(f"[TIMELINE ACTUAL] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': f'Error obteniendo timeline actual: {str(e)}'
            }, status=500)


class ValidarDiaFinalizadoView(APIView):
    """Vista para validar si un día específico ya fue finalizado"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, programa_id):
        """Verifica si una fecha específica ya fue finalizada"""
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            fecha_consulta = request.GET.get('fecha')
            
            if not fecha_consulta:
                return Response({
                    'error': 'Se requiere el parámetro fecha (YYYY-MM-DD)'
                }, status=400)
            
            try:
                fecha_obj = datetime.strptime(fecha_consulta, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
                }, status=400)
            
            # Buscar historial de finalización para esta fecha
            historial_dia = HistorialPlanificacion.objects.filter(
                programa=programa,
                fecha_referencia=fecha_obj,
                tipo_reajuste='FINALIZACION_DIA'
            ).order_by('-fecha_reajuste')
            
            if historial_dia.exists():
                ultimo_cierre = historial_dia.first()
                return Response({
                    'dia_finalizado': True,
                    'fecha_consultada': fecha_consulta,
                    'ultimo_cierre': {
                        'id': ultimo_cierre.id,
                        'fecha_cierre': ultimo_cierre.fecha_reajuste.isoformat(),
                        'usuario': ultimo_cierre.creado_por.username if ultimo_cierre.creado_por else 'Sistema',
                        'observaciones': ultimo_cierre.observaciones,
                        'tiene_datos': bool(ultimo_cierre.timeline_data and 
                                          any(ultimo_cierre.timeline_data.get(k) for k in ['groups', 'items', 'ots']))
                    },
                    'total_cierres': historial_dia.count()
                })
            else:
                return Response({
                    'dia_finalizado': False,
                    'fecha_consultada': fecha_consulta,
                    'puede_finalizar': True
                })
            
        except Exception as e:
            return Response({
                'error': f'Error validando día: {str(e)}'
            }, status=500)
        

# ✅ AGREGAR AL FINAL DEL ARCHIVO

class AnalizarAvancesOTView(APIView):
    """
    Analiza las inconsistencias entre cantidad_avance de la OT 
    y el progreso real del último proceso
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, programa_id, ot_id):
        try:
            # Obtener la OT
            ot = OrdenTrabajo.objects.get(id=ot_id)
            items_ruta = ItemRuta.objects.filter(ruta__orden_trabajo=ot).order_by('item')
            
            # ✅ LÓGICA CORREGIDA
            avance_ot = float(ot.cantidad_avance)
            cantidad_total_ot = float(ot.cantidad)
            
            # El último proceso determina el avance real de la OT
            ultimo_proceso = items_ruta.last() if items_ruta.exists() else None
            avance_real_ot = 0
            
            if ultimo_proceso:
                avance_real_ot = float(ultimo_proceso.cantidad_terminado_proceso)
            
            # Análisis por proceso
            analisis_procesos = []
            for item in items_ruta:
                cantidad_proceso = float(item.cantidad_pedido)
                cantidad_terminada = float(item.cantidad_terminado_proceso)
                porcentaje_proceso = (cantidad_terminada / cantidad_proceso * 100) if cantidad_proceso > 0 else 0
                
                analisis_procesos.append({
                    'item_ruta_id': item.id,
                    'item': item.item,
                    'proceso': {
                        'id': item.proceso.id,
                        'codigo': item.proceso.codigo_proceso,
                        'descripcion': item.proceso.descripcion
                    },
                    'cantidad_total': cantidad_proceso,
                    'cantidad_terminada': cantidad_terminada,
                    'cantidad_pendiente': cantidad_proceso - cantidad_terminada,
                    'porcentaje_completado': round(porcentaje_proceso, 2),
                    'estado_proceso': getattr(item, 'estado_proceso', 'PENDIENTE'),
                    'es_ultimo_proceso': item == ultimo_proceso
                })
            
            # ✅ DETECTAR INCONSISTENCIAS CORRECTAS
            inconsistencias = []
            
            # 1. Avance OT vs último proceso (la única comparación válida)
            if abs(avance_ot - avance_real_ot) > 0.01:
                inconsistencias.append({
                    'tipo': 'DESBALANCE_ULTIMO_PROCESO',
                    'descripcion': f'El avance de la OT ({avance_ot}) no coincide con el último proceso completado ({avance_real_ot})',
                    'diferencia': avance_ot - avance_real_ot,
                    'proceso_afectado': ultimo_proceso.proceso.descripcion if ultimo_proceso else 'No hay procesos'
                })
            
            # 2. Procesos posteriores con más avance que anteriores (flujo ilógico INTELIGENTE)
            for i, item in enumerate(items_ruta[1:], 1):
                item_anterior = items_ruta[i-1]
                
                # ✅ NUEVA LÓGICA: Respetar configuración de flexibilidad
                if hasattr(item, 'permite_salto_proceso') and item.permite_salto_proceso:
                    continue  # Saltar validación si está permitido
                
                if hasattr(item, 'tipo_dependencia') and item.tipo_dependencia == 'INDEPENDIENTE':
                    continue  # No requiere validación
                
                elif hasattr(item, 'tipo_dependencia') and item.tipo_dependencia == 'ESTRICTA':
                    # Solo aplicar validación estricta si está configurado como estricto
                    if (float(item.cantidad_terminado_proceso) > float(item_anterior.cantidad_terminado_proceso)):
                        inconsistencias.append({
                            'tipo': 'FLUJO_ILLOGICO_ESTRICTO',
                            'descripcion': f'Proceso {item.proceso.descripcion} ({item.cantidad_terminado_proceso}) tiene más avance que el proceso anterior {item_anterior.proceso.descripcion} ({item_anterior.cantidad_terminado_proceso})',
                            'item_ruta_id': item.id,
                            'item_anterior_id': item_anterior.id
                        })
                else:
                    # Si no tiene configuración, usar lógica por defecto (comportamiento actual)
                    if (float(item.cantidad_terminado_proceso) > float(item_anterior.cantidad_terminado_proceso)):
                        inconsistencias.append({
                            'tipo': 'FLUJO_ILLOGICO',
                            'descripcion': f'Proceso {item.proceso.descripcion} ({item.cantidad_terminado_proceso}) tiene más avance que el proceso anterior {item_anterior.proceso.descripcion} ({item_anterior.cantidad_terminado_proceso})',
                            'item_ruta_id': item.id,
                            'item_anterior_id': item_anterior.id
                        })
            
            # 3. Estados vs cantidades inconsistentes
            for item in items_ruta:
                estado = getattr(item, 'estado_proceso', 'PENDIENTE')
                cantidad_terminada = float(item.cantidad_terminado_proceso)
                cantidad_total = float(item.cantidad_pedido)
                
                if estado == 'COMPLETADO' and cantidad_terminada < cantidad_total:
                    inconsistencias.append({
                        'tipo': 'ESTADO_INCORRECTO',
                        'descripcion': f'Proceso {item.proceso.descripcion} marcado como COMPLETADO pero solo tiene {cantidad_terminada}/{cantidad_total} terminadas',
                        'item_ruta_id': item.id
                    })
                elif estado == 'PENDIENTE' and cantidad_terminada > 0:
                    inconsistencias.append({
                        'tipo': 'ESTADO_INCORRECTO',
                        'descripcion': f'Proceso {item.proceso.descripcion} marcado como PENDIENTE pero tiene {cantidad_terminada} unidades terminadas',
                        'item_ruta_id': item.id
                    })
            
            return Response({
                'ot': {
                    'id': ot.id,
                    'codigo': ot.codigo_ot,
                    'descripcion': ot.descripcion_producto_ot,
                    'cantidad_total': cantidad_total_ot,
                    'cantidad_avance': avance_ot,
                    'porcentaje_avance_ot': (avance_ot / cantidad_total_ot * 100) if cantidad_total_ot > 0 else 0
                },
                'resumen': {
                    'avance_ultimo_proceso': avance_real_ot,
                    'diferencia_avance': avance_ot - avance_real_ot,
                    'hay_inconsistencias': len(inconsistencias) > 0,
                    'total_procesos': len(items_ruta),
                    'procesos_iniciados': len([p for p in analisis_procesos if p['cantidad_terminada'] > 0]),
                    'procesos_completados': len([p for p in analisis_procesos if p['porcentaje_completado'] >= 100]),
                    'ultimo_proceso': ultimo_proceso.proceso.descripcion if ultimo_proceso else 'No definido'
                },
                'procesos': analisis_procesos,
                'inconsistencias': inconsistencias,
                'sugerencias_correccion': self._calcular_sugerencias_correccion(ot, items_ruta, avance_ot, avance_real_ot)
            })
            
        except OrdenTrabajo.DoesNotExist:
            return Response({'error': 'Orden de trabajo no encontrada'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def _calcular_sugerencias_correccion(self, ot, items_ruta, avance_ot, avance_real_ot):
        """
        Calcula sugerencias basadas en la lógica correcta
        """
        sugerencias = []
        diferencia = avance_ot - avance_real_ot
        ultimo_proceso = items_ruta.last() if items_ruta.exists() else None
        
        if abs(diferencia) > 0.01 and ultimo_proceso:
            if diferencia > 0:  # La OT tiene más avance registrado que el último proceso
                sugerencias.append({
                    'tipo': 'ACTUALIZAR_ULTIMO_PROCESO',
                    'descripcion': f'Actualizar último proceso ({ultimo_proceso.proceso.descripcion}) de {avance_real_ot} a {avance_ot} unidades',
                    'item_ruta_id': ultimo_proceso.id,
                    'cantidad_actual': avance_real_ot,
                    'cantidad_sugerida': avance_ot
                })
            else:  # El último proceso tiene más avance que la OT registrada
                sugerencias.append({
                    'tipo': 'ACTUALIZAR_AVANCE_OT',
                    'descripcion': f'Actualizar avance de OT de {avance_ot} a {avance_real_ot} (basado en último proceso)',
                    'avance_actual': avance_ot,
                    'avance_sugerido': avance_real_ot
                })
            
            # Sugerencia adicional: Cascada hacia atrás
            if diferencia > 0:
                sugerencias.append({
                    'tipo': 'CASCADA_HACIA_ATRAS',
                    'descripcion': f'Propagar {avance_ot} unidades hacia atrás desde el último proceso hasta el primero',
                    'distribucion': self._calcular_cascada_atras(items_ruta, avance_ot)
                })
        
        return sugerencias

    def _calcular_cascada_atras(self, items_ruta, cantidad_objetivo):
        """
        Calcula cómo propagar el avance desde el último proceso hacia atrás
        """
        distribucion = []
        
        # Empezar desde el último proceso hacia el primero
        for item in reversed(items_ruta):
            cantidad_actual = float(item.cantidad_terminado_proceso)
            cantidad_maxima = float(item.cantidad_pedido)
            cantidad_sugerida = min(cantidad_objetivo, cantidad_maxima)
            
            distribucion.insert(0, {  # Insertar al inicio para mantener orden
                'item_ruta_id': item.id,
                'item': item.item,
                'proceso': item.proceso.descripcion,
                'cantidad_actual': cantidad_actual,
                'cantidad_sugerida': cantidad_sugerida,
                'incremento': cantidad_sugerida - cantidad_actual
            })
        
        return distribucion

    def _detectar_flujo_illogico_inteligente(self, items_ruta):
        """
        Detecta flujos ilógicos solo cuando realmente son problemáticos
        """
        inconsistencias = []
        
        for i, item in enumerate(items_ruta[1:], 1):
            item_anterior = items_ruta[i-1]
            
            cantidad_actual = float(item.cantidad_terminado_proceso)
            cantidad_anterior = float(item_anterior.cantidad_terminado_proceso)
            
            # ✅ NUEVA LÓGICA: Solo es ilógico si:
            if cantidad_actual > cantidad_anterior:
                
                # 1. El proceso anterior está marcado como completado pero no tiene toda la cantidad
                if (item_anterior.estado_proceso == 'COMPLETADO' and 
                    cantidad_anterior < float(item_anterior.cantidad_pedido)):
                    inconsistencias.append({
                        'tipo': 'FLUJO_ILLOGICO_CRITICO',
                        'descripcion': f'Proceso {item_anterior.proceso.descripcion} marcado como completado pero proceso posterior {item.proceso.descripcion} tiene más avance',
                        'severidad': 'ALTA'
                    })
                
                # 2. La diferencia es demasiado grande (>20% de la cantidad pedida)
                elif (cantidad_actual - cantidad_anterior) > (float(item_anterior.cantidad_pedido) * 0.2):
                    inconsistencias.append({
                        'tipo': 'FLUJO_ILLOGICO_SOSPECHOSO',
                        'descripcion': f'Diferencia muy grande entre procesos: {cantidad_actual - cantidad_anterior} unidades',
                        'severidad': 'MEDIA'
                    })
                
                # 3. El proceso anterior está "PENDIENTE" pero el posterior tiene avance
                elif item_anterior.estado_proceso == 'PENDIENTE' and cantidad_actual > 0:
                    inconsistencias.append({
                        'tipo': 'FLUJO_ILLOGICO_MENOR',
                        'descripcion': f'Proceso anterior pendiente pero posterior con avance (posible trabajo paralelo)',
                        'severidad': 'BAJA'
                    })
        
        return inconsistencias


class AplicarReconciliacionAvancesView(APIView):
    """
    Aplica la reconciliación de avances sugerida
    """
    
    permission_classes = [IsAuthenticated]

    def post(self, request, programa_id, ot_id):
        try:
            data = request.data
            tipo_aplicacion = data.get('tipo_aplicacion')
            ajustes = data.get('ajustes', [])
            
            with transaction.atomic():
                # Aplicar los ajustes según el tipo
                if tipo_aplicacion == 'MANUAL':
                    # Aplicar ajustes manuales específicos
                    for ajuste in ajustes:
                        item_ruta = ItemRuta.objects.get(id=ajuste['item_ruta_id'])
                        nueva_cantidad = float(ajuste['nueva_cantidad'])
                        
                        # Validar que no exceda la cantidad pedida
                        if nueva_cantidad > float(item_ruta.cantidad_pedido):
                            return Response({
                                'error': f'La cantidad {nueva_cantidad} excede la cantidad pedida ({item_ruta.cantidad_pedido}) para el proceso {item_ruta.proceso.descripcion}'
                            }, status=400)
                        
                        # Actualizar cantidad y estado si es necesario
                        item_ruta.cantidad_terminado_proceso = nueva_cantidad
                        
                        # Actualizar estado basado en el progreso
                        porcentaje = (nueva_cantidad / float(item_ruta.cantidad_pedido)) * 100
                        if porcentaje >= 100:
                            item_ruta.estado_proceso = 'COMPLETADO'
                        elif porcentaje > 0:
                            item_ruta.estado_proceso = 'EN_PROCESO'
                        else:
                            item_ruta.estado_proceso = 'PENDIENTE'
                        
                        item_ruta.save()
                
                elif tipo_aplicacion == 'DISTRIBUCION_PROPORCIONAL':
                    # Aplicar distribución proporcional sugerida
                    distribucion = data.get('distribucion', [])
                    for dist in distribucion:
                        item_ruta = ItemRuta.objects.get(id=dist['item_ruta_id'])
                        item_ruta.cantidad_terminado_proceso = dist['cantidad_sugerida']
                        item_ruta.save()
                
                elif tipo_aplicacion == 'RESETEAR_AVANCES':
                    # Resetear todos los avances de ItemRuta a 0
                    ot = OrdenTrabajo.objects.get(id=ot_id)
                    ItemRuta.objects.filter(ruta__orden_trabajo=ot).update(
                        cantidad_terminado_proceso=0,
                        estado_proceso='PENDIENTE'
                    )
                    
                    # También resetear el avance de la OT si se solicita
                    if data.get('resetear_ot_tambien', False):
                        ot.cantidad_avance = 0
                        ot.save()
                
                # Recalcular el avance total de la OT basado en ItemRutas
                ot = OrdenTrabajo.objects.get(id=ot_id)
                items_ruta = ItemRuta.objects.filter(ruta__orden_trabajo=ot)
                total_cantidad_completada = sum(float(item.cantidad_terminado_proceso) for item in items_ruta)
                
                # Actualizar cantidad_avance de la OT
                ot.cantidad_avance = total_cantidad_completada
                ot.save()
                
                return Response({
                    'success': True,
                    'message': 'Reconciliación aplicada correctamente',
                    'nuevo_avance_ot': float(ot.cantidad_avance),
                    'total_avance_procesos': total_cantidad_completada
                })
                
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ListarOTsConInconsistenciasView(APIView):
    """
    Lista todas las OTs del programa que tienen inconsistencias de avance
    """
    
    permission_classes = [IsAuthenticated]

    def get(self, request, programa_id):
        try:
            programa = ProgramaProduccion.objects.get(id=programa_id)
            ordenes_programa = ProgramaOrdenTrabajo.objects.filter(programa=programa).order_by('prioridad')
            
            ots_con_inconsistencias = []
            
            for orden_programa in ordenes_programa:
                ot = orden_programa.orden_trabajo
                items_ruta = ItemRuta.objects.filter(ruta__orden_trabajo=ot).order_by('item')
                
                avance_ot = float(ot.cantidad_avance)
                total_avance_items = sum(float(item.cantidad_terminado_proceso) for item in items_ruta)
                
                inconsistencias = []
                
                # Verificar desbalance
                if abs(avance_ot - total_avance_items) > 0.01:
                    inconsistencias.append('DESBALANCE_TOTAL')
                
                # Verificar saltos de proceso
                for i, item in enumerate(items_ruta[1:], 1):
                    item_anterior = items_ruta[i-1]
                    if (float(item.cantidad_terminado_proceso) > 0 and 
                        float(item_anterior.cantidad_terminado_proceso) < float(item_anterior.cantidad_pedido)):
                        inconsistencias.append('SALTO_PROCESO')
                        break
                
                # Verificar estados inconsistentes
                for item in items_ruta:
                    if hasattr(item, 'estado_proceso') and item.estado_proceso == 'COMPLETADO':
                        if float(item.cantidad_terminado_proceso) == 0:
                            inconsistencias.append('ESTADO_SIN_CANTIDAD')
                            break
                
                if inconsistencias or avance_ot > 0:  # Incluir también OTs con avance histórico
                    ots_con_inconsistencias.append({
                        'ot_id': ot.id,
                        'codigo_ot': ot.codigo_ot,
                        'descripcion': ot.descripcion_producto_ot,
                        'cantidad_total': float(ot.cantidad),
                        'avance_ot': avance_ot,
                        'avance_procesos': total_avance_items,
                        'diferencia': avance_ot - total_avance_items,
                        'inconsistencias': list(set(inconsistencias)),
                        'tiene_avance_historico': avance_ot > 0,
                        'procesos_con_avance': len([item for item in items_ruta if float(item.cantidad_terminado_proceso) > 0])
                    })
            
            return Response({
                'programa': {
                    'id': programa.id,
                    'nombre': programa.nombre
                },
                'total_ots': len(ordenes_programa),
                'ots_con_inconsistencias': len(ots_con_inconsistencias),
                'ots_con_avance_historico': len([ot for ot in ots_con_inconsistencias if ot['tiene_avance_historico']]),
                'ots': ots_con_inconsistencias
            })
            
        except ProgramaProduccion.DoesNotExist:
            return Response({'error': 'Programa no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Prefetch, F
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta

from ..models import IngresoProduccion, ItemRuta, TareaFragmentada
from Operator.models import Operador, AsignacionOperador
from Machine.models import FallasMaquina

class ListarOperadoresAPIView(APIView):
    """API para listar todos los operadores activos"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Obtener todos los operadores activos
            operadores = Operador.objects.filter(activo=True).select_related('empresa').order_by('nombre')
            
            # Serializar operadores con información adicional
            operadores_data = []
            for operador in operadores:
                # Contar asignaciones del día (sin filtro 'activa' que no existe)
                asignaciones_hoy = AsignacionOperador.objects.filter(
                    operador=operador,
                    fecha_asignacion=date.today()
                ).count()
                
                # Contar ingresos del día
                ingresos_hoy = IngresoProduccion.objects.filter(
                    operador=operador,
                    fecha_ingreso__date=date.today()
                ).count()
                
                operadores_data.append({
                    'id': operador.id,
                    'nombre': operador.nombre,
                    'rut': operador.rut,
                    'empresa': {
                        'id': operador.empresa.id if operador.empresa else None,
                        'nombre': operador.empresa.apodo if operador.empresa else 'Sin empresa'
                    },
                    'asignaciones_hoy': asignaciones_hoy,
                    'ingresos_hoy': ingresos_hoy,
                    'tiene_trabajo_activo': asignaciones_hoy > 0,
                    'activo': operador.activo
                })
            
            return Response({
                'success': True,
                'operadores': operadores_data,
                'total_operadores': len(operadores_data),
                'operadores_con_trabajo': len([op for op in operadores_data if op['tiene_trabajo_activo']])
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardOperadorAPIView(APIView):
    """Dashboard del operador con sus asignaciones y progreso de OTs"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, operador_id):
        try:
            operador = get_object_or_404(Operador, id=operador_id, activo=True)
            
            # Obtener asignaciones del día (sin filtro 'activa')
            asignaciones_hoy = AsignacionOperador.objects.filter(
                operador=operador,
                fecha_asignacion=date.today()
            ).select_related(
                'item_ruta__ruta__orden_trabajo__cliente',
                'item_ruta__proceso',
                'item_ruta__maquina',
                'programa'
            ).prefetch_related(
                'item_ruta__ruta__orden_trabajo'
            )
            
            # ✅ CORRECCIÓN: Obtener ingresos SIN slice primero
            ingresos_base = IngresoProduccion.objects.filter(
                operador=operador,
                fecha_ingreso__date=date.today()
            ).select_related('fallas', 'asignacion__item_ruta__proceso')
            
            # Calcular estadísticas ANTES del slice
            total_producido = ingresos_base.aggregate(
                total=Sum('cantidad')
            )['total'] or Decimal('0')
            
            total_ingresos = ingresos_base.count()
            ingresos_con_fallas = ingresos_base.filter(fallas__isnull=False).count()
            
            # AHORA sí aplicar slice para obtener los últimos ingresos para mostrar
            ingresos_hoy = ingresos_base.order_by('-fecha_ingreso')[:10]
            
            # Serializar asignaciones con detalles de OT y progreso
            asignaciones_data = []
            for asignacion in asignaciones_hoy:
                item_ruta = asignacion.item_ruta
                ot = item_ruta.ruta.orden_trabajo
                
                # Calcular estado del proceso basado en cantidad_terminado_proceso
                if item_ruta.cantidad_terminado_proceso == 0:
                    estado_proceso = 'PENDIENTE'
                elif item_ruta.cantidad_terminado_proceso >= item_ruta.cantidad_pedido:
                    estado_proceso = 'COMPLETADO'
                else:
                    estado_proceso = 'EN_PROCESO'
                
                asignacion_data = {
                    'id': asignacion.id,
                    'fecha_asignacion': asignacion.fecha_asignacion.date(),
                    'orden_trabajo': {
                        'id': ot.id,
                        'codigo_ot': ot.codigo_ot,
                        'descripcion': ot.descripcion_producto_ot,
                        'cliente': {
                            'nombre': ot.cliente.nombre if ot.cliente else 'Sin cliente',
                            'codigo': ot.cliente.codigo_cliente if ot.cliente else ''
                        },
                        'fecha_termino': ot.fecha_termino,
                        'cantidad_total': float(ot.cantidad),
                        'cantidad_avance_ot': float(ot.cantidad_avance)
                    },
                    'item_ruta': {
                        'id': item_ruta.id,
                        'item': item_ruta.item,
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
                        'estandar': item_ruta.estandar,
                        'cantidad_pedido': float(item_ruta.cantidad_pedido),
                        'cantidad_terminada': float(item_ruta.cantidad_terminado_proceso),
                        'cantidad_pendiente': float(item_ruta.cantidad_pendiente),
                        'porcentaje_completado': float(item_ruta.porcentaje_completado),
                        'estado_proceso': estado_proceso,
                        'permite_ingreso': getattr(item_ruta, 'permite_progreso_directo', True),
                        'ultima_actualizacion': getattr(item_ruta, 'ultima_actualizacion_progreso', None)
                    },
                    'programa': {
                        'id': asignacion.programa.id,
                        'nombre': asignacion.programa.nombre
                    } if asignacion.programa else None
                }
                
                # Agregar información de TareaFragmentada si existe
                tarea_fragmentada = TareaFragmentada.objects.filter(
                    tarea_original=item_ruta,
                    operador=operador,
                    fecha=date.today()
                ).first()
                
                if tarea_fragmentada:
                    asignacion_data['tarea_fragmentada'] = {
                        'id': tarea_fragmentada.id,
                        'cantidad_asignada': float(tarea_fragmentada.cantidad_asignada),
                        'cantidad_completada': float(tarea_fragmentada.cantidad_completada),
                        'cantidad_pendiente': float(tarea_fragmentada.cantidad_pendiente),
                        'estado': tarea_fragmentada.estado,
                        'porcentaje_cumplimiento': float(tarea_fragmentada.porcentaje_cumplimiento)
                    }
                
                asignaciones_data.append(asignacion_data)
            
            # Serializar últimos ingresos (ahora ya son solo 10)
            ingresos_data = []
            for ingreso in ingresos_hoy:
                ingreso_data = {
                    'id': ingreso.id,
                    'cantidad': float(ingreso.cantidad),
                    'fecha_ingreso': ingreso.fecha_ingreso,
                    'falla': {
                        'id': ingreso.fallas.id,
                        'descripcion': ingreso.fallas.descripcion
                    } if ingreso.fallas else None
                }
                
                # Datos del proceso si existe asignación
                if ingreso.asignacion and ingreso.asignacion.item_ruta:
                    item = ingreso.asignacion.item_ruta
                    ingreso_data.update({
                        'proceso': item.proceso.descripcion,
                        'orden_trabajo': item.ruta.orden_trabajo.codigo_ot,
                        'maquina': item.maquina.descripcion if item.maquina else 'Sin máquina'
                    })
                
                ingresos_data.append(ingreso_data)
            
            return Response({
                'success': True,
                'operador': {
                    'id': operador.id,
                    'nombre': operador.nombre,
                    'rut': operador.rut,
                    'empresa': operador.empresa.apodo if operador.empresa else 'Sin empresa'
                },
                'estadisticas_hoy': {
                    'total_asignaciones': len(asignaciones_data),
                    'total_producido': float(total_producido),
                    'total_ingresos': total_ingresos,
                    'ingresos_con_fallas': ingresos_con_fallas,
                    'eficiencia_promedio': self._calcular_eficiencia_promedio(asignaciones_hoy)
                },
                'asignaciones': asignaciones_data,
                'ultimos_ingresos': ingresos_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _calcular_eficiencia_promedio(self, asignaciones):
        """Calcula la eficiencia promedio basada en el progreso de las asignaciones"""
        if not asignaciones:
            return 0.0
        
        total_porcentaje = sum(
            float(asig.item_ruta.porcentaje_completado) 
            for asig in asignaciones
        )
        return round(total_porcentaje / len(asignaciones), 2)

class IngresarProduccionAPIView(APIView):
    """API para ingresar nueva producción y actualizar avance de rutas OT"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, operador_id):
        """Obtiene formulario de ingreso con asignaciones y fallas disponibles"""
        try:
            operador = get_object_or_404(Operador, id=operador_id, activo=True)
            
            # Obtener asignaciones del día con procesos que permiten ingreso
            asignaciones = AsignacionOperador.objects.filter(
                operador=operador,
                fecha_asignacion=date.today()
            ).select_related(
                'item_ruta__ruta__orden_trabajo',
                'item_ruta__proceso',
                'item_ruta__maquina'
            ).filter(
                # Solo ItemRuta que no estén completados
                item_ruta__cantidad_terminado_proceso__lt=F('item_ruta__cantidad_pedido')
            )
            
            # Serializar asignaciones disponibles para ingreso
            asignaciones_data = []
            for asignacion in asignaciones:
                item_ruta = asignacion.item_ruta
                ot = item_ruta.ruta.orden_trabajo
                
                # Determinar estado
                if item_ruta.cantidad_terminado_proceso == 0:
                    estado_proceso = 'PENDIENTE'
                elif item_ruta.cantidad_terminado_proceso >= item_ruta.cantidad_pedido:
                    estado_proceso = 'COMPLETADO'
                else:
                    estado_proceso = 'EN_PROCESO'
                
                asignaciones_data.append({
                    'id': asignacion.id,
                    'item_ruta_id': item_ruta.id,
                    'orden_trabajo': {
                        'codigo_ot': ot.codigo_ot,
                        'descripcion': ot.descripcion_producto_ot
                    },
                    'proceso': {
                        'id': item_ruta.proceso.id,
                        'descripcion': item_ruta.proceso.descripcion
                    },
                    'maquina': {
                        'id': item_ruta.maquina.id,
                        'descripcion': item_ruta.maquina.descripcion
                    } if item_ruta.maquina else None,
                    'cantidades': {
                        'pedido': float(item_ruta.cantidad_pedido),
                        'terminada': float(item_ruta.cantidad_terminado_proceso),
                        'pendiente': float(item_ruta.cantidad_pendiente),
                        'porcentaje': float(item_ruta.porcentaje_completado)
                    },
                    'estandar': item_ruta.estandar,
                    'estado_proceso': estado_proceso,
                    'permite_ingreso': getattr(item_ruta, 'permite_progreso_directo', True)
                })
            
            # Obtener fallas disponibles (sin filtro 'activa' si no existe)
            try:
                fallas = FallasMaquina.objects.filter(activa=True).order_by('descripcion')
            except:
                # Si no existe el campo 'activa', obtener todas las fallas
                fallas = FallasMaquina.objects.all().order_by('descripcion')
            
            fallas_data = [
                {
                    'id': falla.id,
                    'descripcion': falla.descripcion,
                    'requiere_observaciones': getattr(falla, 'requiere_observaciones', False)
                }
                for falla in fallas
            ]
            
            return Response({
                'success': True,
                'operador': {
                    'id': operador.id,
                    'nombre': operador.nombre
                },
                'asignaciones_disponibles': asignaciones_data,
                'fallas_disponibles': fallas_data,
                'total_asignaciones': len(asignaciones_data)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, operador_id):
        """Procesa el ingreso de producción y actualiza avance de rutas"""
        try:
            operador = get_object_or_404(Operador, id=operador_id, activo=True)
            
            # Extraer y validar datos
            asignacion_id = request.data.get('asignacion_id')
            cantidad_ingresada = request.data.get('cantidad')
            falla_id = request.data.get('falla_id')
            observaciones = request.data.get('observaciones', '')
            tipo_ingreso = request.data.get('tipo_ingreso', 'INCREMENTAL')
            
            # Validaciones básicas
            errores = self._validar_datos_ingreso(
                asignacion_id, cantidad_ingresada, operador
            )
            if errores:
                return Response({
                    'success': False,
                    'errores': errores
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # Obtener asignación y validar pertenencia al operador
                asignacion = AsignacionOperador.objects.select_related(
                    'item_ruta__ruta__orden_trabajo',
                    'item_ruta__proceso',
                    'item_ruta__maquina'
                ).get(
                    id=asignacion_id,
                    operador=operador
                )
                
                item_ruta = asignacion.item_ruta
                cantidad_decimal = Decimal(str(cantidad_ingresada))
                
                # Validar que no exceda lo pendiente
                if tipo_ingreso == 'INCREMENTAL':
                    nueva_cantidad_total = item_ruta.cantidad_terminado_proceso + cantidad_decimal
                else:  # TOTAL
                    nueva_cantidad_total = cantidad_decimal
                
                if nueva_cantidad_total > item_ruta.cantidad_pedido:
                    return Response({
                        'success': False,
                        'error': f'La cantidad excede lo pedido. Máximo permitido: {item_ruta.cantidad_pendiente}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Obtener falla si se reportó
                falla = None
                if falla_id:
                    try:
                        falla = FallasMaquina.objects.get(id=falla_id)
                    except FallasMaquina.DoesNotExist:
                        return Response({
                            'success': False,
                            'error': 'Falla no encontrada'
                        }, status=status.HTTP_400_BAD_REQUEST)
                
                # Crear registro de ingreso
                ingreso = IngresoProduccion.objects.create(
                    asignacion=asignacion,
                    operador=operador,
                    cantidad=cantidad_decimal,
                    fallas=falla
                )
                
                # Actualizar progreso del ItemRuta manualmente
                item_ruta.cantidad_terminado_proceso = nueva_cantidad_total
                item_ruta.save()
                
                # Respuesta detallada
                response_data = {
                    'success': True,
                    'message': f'Producción registrada: {cantidad_decimal} unidades',
                    'ingreso': {
                        'id': ingreso.id,
                        'cantidad': float(ingreso.cantidad),
                        'fecha_ingreso': ingreso.fecha_ingreso,
                        'falla_reportada': falla.descripcion if falla else None
                    },
                    'item_ruta_actualizado': {
                        'id': item_ruta.id,
                        'cantidad_terminada_anterior': float(item_ruta.cantidad_terminado_proceso - cantidad_decimal) if tipo_ingreso == 'INCREMENTAL' else 0,
                        'cantidad_terminada_nueva': float(item_ruta.cantidad_terminado_proceso),
                        'cantidad_pendiente': float(item_ruta.cantidad_pendiente),
                        'porcentaje_completado': float(item_ruta.porcentaje_completado),
                        'es_completado': item_ruta.cantidad_terminado_proceso >= item_ruta.cantidad_pedido
                    }
                }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
        except AsignacionOperador.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Asignación no válida para este operador'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validar_datos_ingreso(self, asignacion_id, cantidad, operador):
        """Valida los datos del ingreso"""
        errores = []
        
        if not asignacion_id:
            errores.append('Debe seleccionar una asignación')
        
        try:
            cantidad_decimal = Decimal(str(cantidad))
            if cantidad_decimal <= 0:
                errores.append('La cantidad debe ser mayor a 0')
        except (ValueError, TypeError):
            errores.append('Cantidad inválida')
        
        return errores

class FallasDisponiblesAPIView(APIView):
    """API para obtener las fallas disponibles para reportar"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Intentar con filtro 'activa', si no existe obtener todas
            try:
                fallas = FallasMaquina.objects.filter(activa=True).order_by('descripcion')
            except:
                fallas = FallasMaquina.objects.all().order_by('descripcion')
            
            fallas_data = []
            for falla in fallas:
                fallas_data.append({
                    'id': falla.id,
                    'descripcion': falla.descripcion,
                    'requiere_observaciones': getattr(falla, 'requiere_observaciones', False),
                    'activa': getattr(falla, 'activa', True)
                })
            
            return Response({
                'success': True,
                'fallas': fallas_data,
                'total_fallas': len(fallas_data)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


"""----------------------"""
@api_view(['GET'])
def get_estandar_from_producto(request, program_id):
    #Obtener est. actualizado revisando el est de ruta_producto/pieza
    from Product.models import Producto, Pieza

    try:
        ot_id = request.query_params.get('ot_id')
        proc_id = request.query_params.get('proceso_id')
        maq_id= request.query_params.get('maquina_id')

        if not all([ot_id, proc_id, maq_id]):
            return Response({"error": "Faltan parámetros requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        ot = get_object_or_404(OrdenTrabajo, id=ot_id)

        estandar = None
        if ot.codigo_producto_salida:
            try:
                producto = Producto.objects.filter(codigo_producto=ot.codigo_producto_salida).first()
                if producto:
                    #Usar estandarmaquinaproceso en lugar de ruta para mayor precision
                    estandar_obj = EstandarMaquinaProceso.objects.filter(
                        producto=producto,
                        proceso_id=proc_id,
                        maquina_id=maq_id
                    ).first()

                    if estandar_obj and estandar_obj.estandar > 0:
                        estandar = estandar_obj.estandar
            except Exception as e:
                print(f'Error al buscar estándar de producto: {e}')

        if estandar is None and ot.codigo_producto_salida:
            try:
                pieza = Pieza.objects.filter(codigo_pieza=ot.codigo_producto_salida).first()
                if pieza:
                    estandar_obj = EstandarMaquinaProceso.objects.filter(
                        pieza=pieza,
                        proceso_id=proc_id,
                        maquina_id=maq_id
                    ).first()

                    if estandar_obj and estandar_obj.estandar > 0:
                        estandar = estandar_obj.estandar
            except Exception as e:
                print(f"Error al buscar estándar de pieza: {e}")
        
        #Devolver el estándar encontrado o null
        return Response({
            "estandar": estandar,
            "ot_id": ot_id,
            "proceso_id": proc_id,
            "maquina_id": maq_id
        })
    except Exception as e:
        print(f"Error al obtener el estandar actualizado: {e}")
        return Response({"error": str(e)}, status=500)
        
@api_view(['POST'])
def update_item_ruta_states(request, program_id):
    """
    Actualiza los estados de los item_ruta según sus avances actuales
    """
    from JobManagement.models import ItemRuta, ProgramaProduccion, ProgramaOrdenTrabajo, OrdenTrabajo
    from django.db import connection, transaction
    import time

    try:
        # Configurar timeout más largo para transacciones
        if connection.vendor == 'sqlite':
            # Para SQLite, configurar un timeout más largo antes de intentar
            cursor = connection.cursor()
            cursor.execute('PRAGMA busy_timeout = 30000;')  # 30 segundos
            connection.commit()

        # Verificar si el programa existe
        programa = get_object_or_404(ProgramaProduccion, id=program_id)

        
        # Obtener todas las órdenes de trabajo del programa a través de ProgramaOrdenTrabajo
        ot_ids = ProgramaOrdenTrabajo.objects.filter(programa=programa).values_list('orden_trabajo_id', flat=True)
        
        rutas_ot = RutaOT.objects.filter(orden_trabajo_id__in=ot_ids).values_list('id', flat=True)

        # Obtener todos los item_ruta asociados a estas OTs
        items_ruta = ItemRuta.objects.filter(ruta_id__in=rutas_ot)

        # Procesar en lotes más pequeños para reducir el tiempo de bloqueo
        BATCH_SIZE = 50
        items_count = items_ruta.count()
        batch_count = (items_count + BATCH_SIZE - 1) // BATCH_SIZE  # Redondeo hacia arriba
        
        # Contadores para el resumen
        total_actualizados = 0
        pendientes_a_proceso = 0
        proceso_a_completado = 0
        
        for batch_num in range(batch_count):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, items_count)

            batch_items = items_ruta[start_idx:end_idx]

            #Usar transacción atómica solo para este lote
            with transaction.atomic():
                # Iterar y actualizar cada item_ruta según su avance
                for item in items_ruta:
                    estado_original = item.estado_proceso
                    
                    # Determinar estado basado en porcentaje de avance
                    if item.cantidad_terminado_proceso >= item.cantidad_pedido:
                        nuevo_estado = 'COMPLETADO'
                        if estado_original != nuevo_estado:
                            proceso_a_completado += 1
                    elif item.cantidad_terminado_proceso < item.cantidad_pedido and item.cantidad_terminado_proceso > 0:
                        nuevo_estado = 'EN PROCESO'
                        if estado_original == 'PENDIENTE':
                            pendientes_a_proceso += 1
                    else:
                        nuevo_estado = 'PENDIENTE'
                        
                    # Actualizar solo si hay cambio de estado
                    if estado_original != nuevo_estado:
                        item.estado_proceso = nuevo_estado
                        item.save(update_fields=['estado_proceso'])
                        total_actualizados += 1

            # Pequeña pausa entre lotes para liberar conexiones
            if batch_count > 1:
                time.sleep(0.1)
        
        return Response({
            'success': True,
            'message': f'Estados actualizados correctamente',
            'total_actualizados': total_actualizados,
            'pendientes_a_proceso': pendientes_a_proceso,
            'proceso_a_completado': proceso_a_completado,
            'items_procesados': items_count,
            'lotes_procesados': batch_count
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error al actualizar estados: {str(e)}'
        }, status=500)

@api_view(['GET'])
def get_proceso_fechas_planificadas(request, programa_id, item_ruta_id):
    """
    Obtiene las fechas planificadas (inicio y fin) para un proceso específico
    basándose en la timeline del programa.
    
    Args:
        programa_id: ID del programa de producción
        item_ruta_id: ID del ItemRuta (proceso)
        
    Returns:
        {
            "fecha_inicio": "2025-08-26T08:00:00",
            "fecha_fin": "2025-08-26T10:00:00",
            "multiple_blocks": false,
            "total_items": 1,
            "detalle_bloques": [...]
        }
    """
    try:
        # Validar que existan el programa y el proceso
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        item_ruta = get_object_or_404(ItemRuta, id=item_ruta_id)
        
        # Verificar que el proceso pertenezca a una OT del programa
        programa_ots = ProgramaOrdenTrabajo.objects.filter(
            programa=programa,
            orden_trabajo=item_ruta.ruta.orden_trabajo
        )
        
        if not programa_ots.exists():
            return Response(
                {"error": "El proceso no pertenece a ninguna OT de este programa"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Inicializar el scheduler
        time_calculator = TimeCalculator()
        scheduler = ProductionScheduler(time_calculator)
        
        # Obtener las fechas planificadas para este proceso
        fechas_planificadas = scheduler.get_process_scheduled_dates(programa, f"proc_{item_ruta_id}")
        
        if not fechas_planificadas:
            return Response(
                {"error": "No se encontraron fechas planificadas para este proceso"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(fechas_planificadas)
        
    except Exception as e:
        return Response(
            {"error": f"Error al obtener fechas planificadas: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

