from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import timedelta

from ..models import ProgramaProduccion
from ..services.metrics_engine import MetricsEngine
import logging


class ProgramaKPIsView(APIView):
    """
    Vista para obtener KPIs principales del programa
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.metrics_engine = MetricsEngine()
        self.logger = logging.getLogger('metrics')
    
    def get(self, request, programa_id):
        """
        Obtiene los KPIs principales del programa
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            kpis = self.metrics_engine.get_programa_kpis(programa)
            
            return Response({
                'success': True,
                'programa_id': programa_id,
                'programa_nombre': programa.nombre,
                'kpis': kpis,
                'fecha_consulta': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo KPIs programa {programa_id}: {str(e)}")
            return Response({
                'error': f'Error obteniendo KPIs: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DashboardPrincipalView(APIView):
    """
    Vista para el dashboard principal con métricas resumidas
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.metrics_engine = MetricsEngine()
    
    def get(self, request, programa_id):
        """
        Obtiene datos para el dashboard principal
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            # KPIs principales
            kpis = self.metrics_engine.get_programa_kpis(programa)
            
            # Métricas del día actual
            hoy = timezone.now().date()
            metricas_hoy = self.metrics_engine.get_daily_metrics(programa, hoy)
            
            # Análisis de tendencias (últimos 7 días)
            tendencias = self.metrics_engine.generate_trend_analysis(programa, days=7)
            
            # Resumen ejecutivo
            resumen_ejecutivo = self._generate_executive_summary(kpis, metricas_hoy, tendencias)
            
            return Response({
                'success': True,
                'dashboard': {
                    'kpis_principales': kpis,
                    'metricas_hoy': metricas_hoy,
                    'tendencias_semana': tendencias,
                    'resumen_ejecutivo': resumen_ejecutivo
                },
                'ultima_actualizacion': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error generando dashboard: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_executive_summary(self, kpis, metricas_hoy, tendencias):
        """Genera resumen ejecutivo para el dashboard"""
        alertas = []
        destacados = []
        
        # Análisis de KPIs
        if kpis['eficiencia_general']['porcentaje'] < 70:
            alertas.append({
                'tipo': 'EFICIENCIA_BAJA',
                'mensaje': 'Eficiencia general por debajo del 70%',
                'valor': kpis['eficiencia_general']['porcentaje'],
                'prioridad': 'ALTA'
            })
        
        if kpis['cumplimiento_plazos']['porcentaje'] < 80:
            alertas.append({
                'tipo': 'PLAZOS_RIESGO',
                'mensaje': 'Cumplimiento de plazos en riesgo',
                'valor': kpis['cumplimiento_plazos']['porcentaje'],
                'prioridad': 'MEDIA'
            })
        
        # Destacados positivos
        if kpis['eficiencia_general']['porcentaje'] > 85:
            destacados.append({
                'tipo': 'EFICIENCIA_ALTA',
                'mensaje': 'Excelente eficiencia general',
                'valor': kpis['eficiencia_general']['porcentaje']
            })
        
        if kpis['utilizacion_recursos']['general'] > 80:
            destacados.append({
                'tipo': 'RECURSOS_OPTIMIZADOS',
                'mensaje': 'Buena utilización de recursos',
                'valor': kpis['utilizacion_recursos']['general']
            })
        
        return {
            'alertas': alertas,
            'destacados': destacados,
            'estado_general': self._determine_overall_status(kpis),
            'recomendaciones_principales': self._get_top_recommendations(kpis)
        }
    
    def _determine_overall_status(self, kpis):
        """Determina el estado general basado en KPIs"""
        eficiencia = kpis['eficiencia_general']['porcentaje']
        cumplimiento = kpis['cumplimiento_plazos']['porcentaje']
        utilizacion = kpis['utilizacion_recursos']['general']
        
        promedio = (eficiencia + cumplimiento + utilizacion) / 3
        
        if promedio >= 85:
            return 'EXCELENTE'
        elif promedio >= 70:
            return 'BUENO'
        elif promedio >= 55:
            return 'REGULAR'
        else:
            return 'CRITICO'
    
    def _get_top_recommendations(self, kpis):
        """Obtiene las principales recomendaciones"""
        recomendaciones = []
        
        # Basado en calidad de planificación
        if 'calidad_planificacion' in kpis and 'recomendaciones' in kpis['calidad_planificacion']:
            recomendaciones.extend(kpis['calidad_planificacion']['recomendaciones'][:2])
        
        # Basado en utilización de recursos
        if 'utilizacion_recursos' in kpis and 'oportunidades_mejora' in kpis['utilizacion_recursos']:
            recomendaciones.extend(kpis['utilizacion_recursos']['oportunidades_mejora'][:2])
        
        return recomendaciones[:3]  # Top 3 recomendaciones


class MetricasDiariasView(APIView):
    """
    Vista para obtener métricas específicas de un día
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.metrics_engine = MetricsEngine()
    
    def get(self, request, programa_id):
        """
        Obtiene métricas para una fecha específica
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            # Obtener fecha del query parameter
            fecha_str = request.query_params.get('fecha')
            if fecha_str:
                fecha = parse_date(fecha_str)
                if not fecha:
                    return Response({
                        'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                fecha = timezone.now().date()
            
            metricas = self.metrics_engine.get_daily_metrics(programa, fecha)
            
            return Response({
                'success': True,
                'metricas_dia': metricas
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error obteniendo métricas diarias: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TendenciasView(APIView):
    """
    Vista para análisis de tendencias
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.metrics_engine = MetricsEngine()
    
    def get(self, request, programa_id):
        """
        Obtiene análisis de tendencias para un período
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            # Obtener período del query parameter
            days = request.query_params.get('days', '7')
            try:
                days = int(days)
                if days < 1 or days > 30:
                    days = 7
            except ValueError:
                days = 7
            
            tendencias = self.metrics_engine.generate_trend_analysis(programa, days=days)
            
            return Response({
                'success': True,
                'analisis_tendencias': tendencias
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error generando análisis de tendencias: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ComparacionPeriodosView(APIView):
    """
    Vista para comparar métricas entre diferentes períodos
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.metrics_engine = MetricsEngine()
    
    def post(self, request, programa_id):
        """
        Compara métricas entre dos períodos
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            # Obtener períodos de comparación
            periodo1 = request.data.get('periodo1', {})
            periodo2 = request.data.get('periodo2', {})
            
            # Validar períodos
            if not self._validate_periodo(periodo1) or not self._validate_periodo(periodo2):
                return Response({
                    'error': 'Períodos de comparación inválidos'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener métricas para cada período
            metricas_p1 = self._get_periodo_metrics(programa, periodo1)
            metricas_p2 = self._get_periodo_metrics(programa, periodo2)
            
            # Generar comparación
            comparacion = self._generate_comparison(metricas_p1, metricas_p2, periodo1, periodo2)
            
            return Response({
                'success': True,
                'comparacion': comparacion
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error en comparación de períodos: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_periodo(self, periodo):
        """Valida la estructura de un período"""
        required_fields = ['fecha_inicio', 'fecha_fin']
        return all(field in periodo for field in required_fields)
    
    def _get_periodo_metrics(self, programa, periodo):
        """Obtiene métricas agregadas para un período"""
        fecha_inicio = parse_date(periodo['fecha_inicio'])
        fecha_fin = parse_date(periodo['fecha_fin'])
        
        # Por simplicidad, usamos las métricas del último día del período
        return self.metrics_engine.get_daily_metrics(programa, fecha_fin)
    
    def _generate_comparison(self, metricas_p1, metricas_p2, periodo1, periodo2):
        """Genera la comparación entre períodos"""
        return {
            'periodo1': {
                'descripcion': f"{periodo1['fecha_inicio']} - {periodo1['fecha_fin']}",
                'metricas': metricas_p1
            },
            'periodo2': {
                'descripcion': f"{periodo2['fecha_inicio']} - {periodo2['fecha_fin']}",
                'metricas': metricas_p2
            },
            'diferencias': {
                'produccion': {
                    'absoluta': metricas_p2['resumen']['produccion_total'] - metricas_p1['resumen']['produccion_total'],
                    'porcentual': self._calculate_percentage_change(
                        metricas_p1['resumen']['produccion_total'],
                        metricas_p2['resumen']['produccion_total']
                    )
                },
                'eficiencia': {
                    'absoluta': metricas_p2['eficiencia_dia'] - metricas_p1['eficiencia_dia'],
                    'porcentual': self._calculate_percentage_change(
                        metricas_p1['eficiencia_dia'],
                        metricas_p2['eficiencia_dia']
                    )
                }
            }
        }
    
    def _calculate_percentage_change(self, valor_anterior, valor_actual):
        """Calcula el cambio porcentual"""
        if valor_anterior == 0:
            return 100 if valor_actual > 0 else 0
        return ((valor_actual - valor_anterior) / valor_anterior) * 100


class ExportarMetricasView(APIView):
    """
    Vista para exportar métricas en diferentes formatos
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.metrics_engine = MetricsEngine()
    
    def get(self, request, programa_id):
        """
        Exporta métricas del programa
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            formato = request.query_params.get('formato', 'json')
            
            # Obtener todas las métricas
            kpis = self.metrics_engine.get_programa_kpis(programa)
            tendencias = self.metrics_engine.generate_trend_analysis(programa, days=7)
            
            data_export = {
                'programa': {
                    'id': programa.id,
                    'nombre': programa.nombre,
                    'fecha_inicio': programa.fecha_inicio.strftime('%Y-%m-%d'),
                    'fecha_fin': programa.fecha_fin.strftime('%Y-%m-%d') if programa.fecha_fin else None
                },
                'kpis': kpis,
                'tendencias': tendencias,
                'fecha_exportacion': timezone.now().isoformat()
            }
            
            if formato.lower() == 'csv':
                return self._export_as_csv(data_export)
            elif formato.lower() == 'excel':
                return self._export_as_excel(data_export)
            else:
                return Response(data_export, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({
                'error': f'Error exportando métricas: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _export_as_csv(self, data):
        """Exporta datos como CSV"""
        # Implementación simplificada
        return Response({
            'mensaje': 'Exportación CSV no implementada aún',
            'data': data
        })
    
    def _export_as_excel(self, data):
        """Exporta datos como Excel"""
        # Implementación simplificada
        return Response({
            'mensaje': 'Exportación Excel no implementada aún',
            'data': data
        })


class AlertasMetricasView(APIView):
    """
    Vista para gestionar alertas basadas en métricas
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.metrics_engine = MetricsEngine()
    
    def get(self, request, programa_id):
        """
        Obtiene alertas activas para el programa
        """
        try:
            programa = get_object_or_404(ProgramaProduccion, id=programa_id)
            
            kpis = self.metrics_engine.get_programa_kpis(programa)
            alertas = self._generate_alerts(kpis, programa)
            
            return Response({
                'success': True,
                'alertas': alertas,
                'total_alertas': len(alertas),
                'alertas_criticas': len([a for a in alertas if a['prioridad'] == 'CRITICA'])
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error obteniendo alertas: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_alerts(self, kpis, programa):
        """Genera alertas basadas en KPIs"""
        alertas = []
        
        # Alerta por eficiencia baja
        if kpis['eficiencia_general']['porcentaje'] < 60:
            alertas.append({
                'id': 'eficiencia_baja',
                'tipo': 'EFICIENCIA',
                'titulo': 'Eficiencia General Baja',
                'descripcion': f"La eficiencia está en {kpis['eficiencia_general']['porcentaje']}%, por debajo del umbral de 60%",
                'prioridad': 'CRITICA' if kpis['eficiencia_general']['porcentaje'] < 50 else 'ALTA',
                'valor_actual': kpis['eficiencia_general']['porcentaje'],
                'umbral': 60,
                'fecha_deteccion': timezone.now().isoformat()
            })
        
        # Alerta por cumplimiento de plazos
        if kpis['cumplimiento_plazos']['porcentaje'] < 80:
            alertas.append({
                'id': 'plazos_riesgo',
                'tipo': 'PLAZOS',
                'titulo': 'Riesgo en Cumplimiento de Plazos',
                'descripcion': f"Cumplimiento en {kpis['cumplimiento_plazos']['porcentaje']}%, por debajo del 80%",
                'prioridad': 'ALTA',
                'valor_actual': kpis['cumplimiento_plazos']['porcentaje'],
                'umbral': 80,
                'fecha_deteccion': timezone.now().isoformat()
            })
        
        # Alerta por recursos sobrecargados
        if 'utilizacion_recursos' in kpis:
            maquinas_sobrecargadas = kpis['utilizacion_recursos']['maquinas'].get('maquinas_sobrecargadas', [])
            if maquinas_sobrecargadas:
                alertas.append({
                    'id': 'maquinas_sobrecargadas',
                    'tipo': 'RECURSOS',
                    'titulo': 'Máquinas Sobrecargadas',
                    'descripcion': f"{len(maquinas_sobrecargadas)} máquinas con utilización >90%",
                    'prioridad': 'MEDIA',
                    'detalles': maquinas_sobrecargadas,
                    'fecha_deteccion': timezone.now().isoformat()
                })
        
        return alertas 