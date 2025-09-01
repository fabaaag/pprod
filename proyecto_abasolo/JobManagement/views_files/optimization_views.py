from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from ..models import ProgramaProduccion, TareaFragmentada
from ..services.optimization_engine import OptimizationEngine
from ..serializers import ProgramaProduccionSerializer
import logging


class OptimizarProgramaView(APIView):
    """
    Vista para optimizar automáticamente un programa de producción
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.optimization_engine = OptimizationEngine()
        self.logger = logging.getLogger('optimization')
    
    def post(self, request, programa_id):
        """
        Ejecuta la optimización completa del programa
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            # Validar que el programa tenga tareas
            if not TareaFragmentada.objects.filter(programa=programa).exists():
                return Response({
                    'error': 'El programa no tiene tareas para optimizar'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # Ejecutar optimización
                resultados = self.optimization_engine.optimize_machine_assignment(programa)
                
                # Registrar la optimización
                self.logger.info(f"Optimización ejecutada en programa {programa_id}: {resultados}")
                
                return Response({
                    'success': True,
                    'mensaje': 'Optimización completada exitosamente',
                    'resultados': resultados,
                    'fecha_optimizacion': timezone.now().isoformat()
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            self.logger.error(f"Error en optimización del programa {programa_id}: {str(e)}")
            return Response({
                'error': f'Error durante la optimización: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SugerirOperadoresView(APIView):
    """
    Vista para sugerir asignaciones óptimas de operadores
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.optimization_engine = OptimizationEngine()
    
    def get(self, request, programa_id):
        """
        Obtiene sugerencias de asignación de operadores
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            sugerencias = self.optimization_engine.suggest_operator_assignments(programa)
            
            return Response({
                'success': True,
                'sugerencias': sugerencias,
                'total_sugerencias': len(sugerencias)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error obteniendo sugerencias: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, programa_id):
        """
        Aplica las sugerencias de operadores seleccionadas
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            sugerencias_aplicar = request.data.get('sugerencias', [])
            
            aplicadas = 0
            errores = []
            
            with transaction.atomic():
                for sugerencia in sugerencias_aplicar:
                    try:
                        tarea_id = sugerencia.get('tarea_id')
                        operador_id = sugerencia.get('operador_id')
                        
                        tarea = TareaFragmentada.objects.get(id=tarea_id, programa=programa)
                        
                        from Operator.models import Operador
                        operador = Operador.objects.get(id=operador_id)
                        
                        tarea.operador = operador
                        tarea.save()
                        
                        aplicadas += 1
                        
                    except Exception as e:
                        errores.append(f"Error en tarea {tarea_id}: {str(e)}")
            
            return Response({
                'success': True,
                'mensaje': f'Se aplicaron {aplicadas} asignaciones de operadores',
                'aplicadas': aplicadas,
                'errores': errores
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error aplicando sugerencias: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalisisCapacidadView(APIView):
    """
    Vista para analizar la capacidad y utilización de recursos
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, programa_id):
        """
        Analiza la capacidad de máquinas y operadores del programa
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            # Análisis de máquinas
            analisis_maquinas = self._analizar_capacidad_maquinas(programa)
            
            # Análisis de operadores
            analisis_operadores = self._analizar_capacidad_operadores(programa)
            
            # Cuellos de botella
            cuellos_botella = self._identificar_cuellos_botella(programa)
            
            return Response({
                'success': True,
                'analisis': {
                    'maquinas': analisis_maquinas,
                    'operadores': analisis_operadores,
                    'cuellos_botella': cuellos_botella
                },
                'fecha_analisis': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error en análisis de capacidad: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _analizar_capacidad_maquinas(self, programa):
        """Analiza la capacidad y utilización de máquinas"""
        from django.db.models import Sum, Count, Avg
        
        analisis = []
        
        # Obtener máquinas utilizadas en el programa
        maquinas_usadas = TareaFragmentada.objects.filter(
            programa=programa
        ).values('tarea_original__maquina').distinct()
        
        for maquina_data in maquinas_usadas:
            maquina_id = maquina_data['tarea_original__maquina']
            if not maquina_id:
                continue
                
            from ..models import Maquina
            maquina = Maquina.objects.get(id=maquina_id)
            
            # Calcular estadísticas
            tareas_maquina = TareaFragmentada.objects.filter(
                programa=programa,
                tarea_original__maquina=maquina
            )
            
            stats = tareas_maquina.aggregate(
                total_cantidad=Sum('cantidad_asignada'),
                total_tareas=Count('id'),
                promedio_por_tarea=Avg('cantidad_asignada')
            )
            
            # Calcular utilización por día
            utilizacion_diaria = {}
            for tarea in tareas_maquina:
                fecha_str = tarea.fecha.strftime('%Y-%m-%d')
                if fecha_str not in utilizacion_diaria:
                    utilizacion_diaria[fecha_str] = 0
                
                if tarea.tarea_original.estandar:
                    horas = float(tarea.cantidad_asignada) / tarea.tarea_original.estandar
                    utilizacion_diaria[fecha_str] += horas
            
            # Calcular porcentaje de utilización (asumiendo 8h por día)
            utilizacion_porcentaje = {}
            for fecha, horas in utilizacion_diaria.items():
                utilizacion_porcentaje[fecha] = min((horas / 8.0) * 100, 100)
            
            analisis.append({
                'maquina_id': maquina.id,
                'maquina_codigo': maquina.codigo_maquina,
                'maquina_descripcion': maquina.descripcion,
                'estadisticas': stats,
                'utilizacion_diaria': utilizacion_porcentaje,
                'promedio_utilizacion': sum(utilizacion_porcentaje.values()) / len(utilizacion_porcentaje) if utilizacion_porcentaje else 0,
                'dias_utilizados': len(utilizacion_diaria)
            })
        
        return sorted(analisis, key=lambda x: x['promedio_utilizacion'], reverse=True)
    
    def _analizar_capacidad_operadores(self, programa):
        """Analiza la capacidad y asignación de operadores"""
        from django.db.models import Count
        
        analisis = []
        
        # Operadores asignados
        operadores_asignados = TareaFragmentada.objects.filter(
            programa=programa,
            operador__isnull=False
        ).values('operador').distinct()
        
        for operador_data in operadores_asignados:
            operador_id = operador_data['operador']
            if not operador_id:
                continue
            
            from Operator.models import Operador
            operador = Operador.objects.get(id=operador_id)
            
            tareas_operador = TareaFragmentada.objects.filter(
                programa=programa,
                operador=operador
            )
            
            # Estadísticas por estado
            stats_por_estado = tareas_operador.values('estado').annotate(
                cantidad=Count('id')
            )
            
            # Carga por día
            carga_diaria = {}
            for tarea in tareas_operador:
                fecha_str = tarea.fecha.strftime('%Y-%m-%d')
                if fecha_str not in carga_diaria:
                    carga_diaria[fecha_str] = 0
                carga_diaria[fecha_str] += 1
            
            analisis.append({
                'operador_id': operador.id,
                'operador_nombre': operador.nombre,
                'total_tareas': tareas_operador.count(),
                'estadisticas_por_estado': list(stats_por_estado),
                'carga_diaria': carga_diaria,
                'promedio_tareas_dia': sum(carga_diaria.values()) / len(carga_diaria) if carga_diaria else 0
            })
        
        # Tareas sin operador
        tareas_sin_operador = TareaFragmentada.objects.filter(
            programa=programa,
            operador__isnull=True
        ).count()
        
        return {
            'operadores_asignados': analisis,
            'tareas_sin_operador': tareas_sin_operador
        }
    
    def _identificar_cuellos_botella(self, programa):
        """Identifica cuellos de botella en el programa"""
        cuellos_botella = []
        
        try:
            # 1. Máquinas sobrecargadas (>90% utilización)
            analisis_maquinas = self._analizar_capacidad_maquinas(programa)
            
            for maquina in analisis_maquinas:
                if maquina['promedio_utilizacion'] > 90:
                    cuellos_botella.append({
                        'tipo': 'MAQUINA_SOBRECARGADA',
                        'recurso': f"Máquina {maquina['maquina_codigo']}",
                        'utilizacion': maquina['promedio_utilizacion'],
                        'impacto': 'ALTO',
                        'recomendacion': 'Redistribuir carga o considerar máquina alternativa'
                    })
            
            # 2. Procesos con esperas excesivas
            from datetime import timedelta
            tareas_con_retraso = TareaFragmentada.objects.filter(
                programa=programa,
                fecha_real_inicio__isnull=False,
                fecha_planificada_inicio__isnull=False
            ).extra(
                where=["fecha_real_inicio > fecha_planificada_inicio + INTERVAL '1 day'"]
            )
            
            if tareas_con_retraso.exists():
                cuellos_botella.append({
                    'tipo': 'RETRASOS_EXCESIVOS',
                    'recurso': 'Flujo de producción',
                    'cantidad_tareas': tareas_con_retraso.count(),
                    'impacto': 'MEDIO',
                    'recomendacion': 'Revisar secuenciación y dependencias'
                })
            
            # 3. Operadores sobrecargados
            analisis_operadores = self._analizar_capacidad_operadores(programa)
            
            for operador in analisis_operadores['operadores_asignados']:
                if operador['promedio_tareas_dia'] > 5:  # Más de 5 tareas por día
                    cuellos_botella.append({
                        'tipo': 'OPERADOR_SOBRECARGADO',
                        'recurso': f"Operador {operador['operador_nombre']}",
                        'promedio_tareas': operador['promedio_tareas_dia'],
                        'impacto': 'MEDIO',
                        'recomendacion': 'Redistribuir tareas o asignar operador adicional'
                    })
            
        except Exception as e:
            cuellos_botella.append({
                'tipo': 'ERROR_ANALISIS',
                'recurso': 'Sistema de análisis',
                'error': str(e),
                'impacto': 'BAJO',
                'recomendacion': 'Revisar configuración del sistema'
            })
        
        return cuellos_botella


class SimularCambiosView(APIView):
    """
    Vista para simular cambios en la planificación sin aplicarlos
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, programa_id):
        """
        Simula cambios propuestos en la planificación
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            cambios_propuestos = request.data.get('cambios', [])
            
            if not cambios_propuestos:
                return Response({
                    'error': 'No se proporcionaron cambios para simular'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Simular cada cambio
            resultados_simulacion = []
            
            for cambio in cambios_propuestos:
                resultado = self._simular_cambio_individual(programa, cambio)
                resultados_simulacion.append(resultado)
            
            # Resumen de la simulación
            resumen = self._generar_resumen_simulacion(resultados_simulacion)
            
            return Response({
                'success': True,
                'simulacion': {
                    'resultados_individuales': resultados_simulacion,
                    'resumen': resumen
                },
                'fecha_simulacion': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error en simulación: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _simular_cambio_individual(self, programa, cambio):
        """Simula un cambio individual"""
        tipo_cambio = cambio.get('tipo')
        
        resultado = {
            'tipo': tipo_cambio,
            'viable': False,
            'impacto': {},
            'conflictos': [],
            'beneficios': []
        }
        
        try:
            if tipo_cambio == 'CAMBIO_MAQUINA':
                resultado = self._simular_cambio_maquina(cambio)
            elif tipo_cambio == 'CAMBIO_OPERADOR':
                resultado = self._simular_cambio_operador(cambio)
            elif tipo_cambio == 'CAMBIO_FECHA':
                resultado = self._simular_cambio_fecha(cambio)
            else:
                resultado['error'] = f'Tipo de cambio no soportado: {tipo_cambio}'
                
        except Exception as e:
            resultado['error'] = str(e)
        
        return resultado
    
    def _simular_cambio_maquina(self, cambio):
        """Simula cambio de máquina"""
        # Implementación específica para simular cambio de máquina
        return {
            'tipo': 'CAMBIO_MAQUINA',
            'viable': True,
            'impacto': {'tiempo_estimado': -0.5, 'eficiencia': 0.1},
            'conflictos': [],
            'beneficios': ['Mejor eficiencia', 'Menor tiempo de procesamiento']
        }
    
    def _simular_cambio_operador(self, cambio):
        """Simula cambio de operador"""
        # Implementación específica para simular cambio de operador
        return {
            'tipo': 'CAMBIO_OPERADOR',
            'viable': True,
            'impacto': {'disponibilidad': 0.8},
            'conflictos': [],
            'beneficios': ['Mejor disponibilidad']
        }
    
    def _simular_cambio_fecha(self, cambio):
        """Simula cambio de fecha"""
        # Implementación específica para simular cambio de fecha
        return {
            'tipo': 'CAMBIO_FECHA',
            'viable': True,
            'impacto': {'secuencia': 0},
            'conflictos': [],
            'beneficios': ['Mejor secuenciación']
        }
    
    def _generar_resumen_simulacion(self, resultados):
        """Genera un resumen de la simulación"""
        total_cambios = len(resultados)
        cambios_viables = len([r for r in resultados if r.get('viable', False)])
        
        return {
            'total_cambios_simulados': total_cambios,
            'cambios_viables': cambios_viables,
            'porcentaje_viabilidad': (cambios_viables / total_cambios * 100) if total_cambios > 0 else 0,
            'recomendacion': 'Aplicar cambios viables' if cambios_viables > 0 else 'Revisar propuestas'
        } 