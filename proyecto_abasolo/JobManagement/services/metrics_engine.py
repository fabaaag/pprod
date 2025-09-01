from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import json
from django.db.models import (
    Sum, Avg, Count, Max, Min, Q, F, 
    Case, When, DecimalField, Value
)
from django.utils import timezone
from ..models import (
    ProgramaProduccion, TareaFragmentada, ItemRuta, 
    OrdenTrabajo, ProgramaOrdenTrabajo, EjecucionTarea,
    ReporteDiarioPrograma, HistorialPlanificacion,
    Maquina, Proceso
)
from Operator.models import Operador, AsignacionOperador


class MetricsEngine:
    """
    Motor de métricas avanzado para análisis del sistema de producción
    """
    
    def __init__(self):
        self.cache_metrics = {}
        self.cache_timeout = 300  # 5 minutos
    
    def get_programa_kpis(self, programa: ProgramaProduccion) -> Dict:
        """
        Obtiene KPIs principales del programa
        """
        cache_key = f"programa_kpis_{programa.id}_{timezone.now().strftime('%Y%m%d_%H%M')}"
        
        if cache_key in self.cache_metrics:
            return self.cache_metrics[cache_key]
        
        kpis = {
            'eficiencia_general': self._calculate_overall_efficiency(programa),
            'cumplimiento_plazos': self._calculate_deadline_compliance(programa),
            'utilizacion_recursos': self._calculate_resource_utilization(programa),
            'calidad_planificacion': self._calculate_planning_quality(programa),
            'productividad': self._calculate_productivity_metrics(programa),
            'estado_actual': self._get_current_status(programa)
        }
        
        self.cache_metrics[cache_key] = kpis
        return kpis
    
    def _calculate_overall_efficiency(self, programa: ProgramaProduccion) -> Dict:
        """
        Calcula la eficiencia general del programa
        """
        tareas = TareaFragmentada.objects.filter(programa=programa)
        
        if not tareas.exists():
            return {'porcentaje': 0, 'tendencia': 'neutral', 'detalles': {}}
        
        # Eficiencia por progreso
        progreso_total = tareas.aggregate(
            total_planificado=Sum('cantidad_asignada'),
            total_completado=Sum('cantidad_completada')
        )
        
        eficiencia_progreso = 0
        if progreso_total['total_planificado'] and progreso_total['total_planificado'] > 0:
            eficiencia_progreso = (
                progreso_total['total_completado'] / progreso_total['total_planificado']
            ) * 100
        
        # Eficiencia temporal
        tareas_con_fechas = tareas.filter(
            fecha_planificada_inicio__isnull=False,
            fecha_real_inicio__isnull=False
        )
        
        eficiencia_temporal = 100  # Por defecto
        if tareas_con_fechas.exists():
            tareas_a_tiempo = tareas_con_fechas.filter(
                fecha_real_inicio__lte=F('fecha_planificada_inicio') + timedelta(hours=2)
            ).count()
            eficiencia_temporal = (tareas_a_tiempo / tareas_con_fechas.count()) * 100
        
        # Promedio ponderado
        eficiencia_general = (eficiencia_progreso * 0.7) + (eficiencia_temporal * 0.3)
        
        # Determinar tendencia
        tendencia = self._calculate_efficiency_trend(programa)
        
        return {
            'porcentaje': round(eficiencia_general, 2),
            'tendencia': tendencia,
            'detalles': {
                'eficiencia_progreso': round(eficiencia_progreso, 2),
                'eficiencia_temporal': round(eficiencia_temporal, 2),
                'tareas_analizadas': tareas.count(),
                'tareas_completadas': tareas.filter(estado='COMPLETADO').count()
            }
        }
    
    def _calculate_deadline_compliance(self, programa: ProgramaProduccion) -> Dict:
        """
        Calcula el cumplimiento de plazos
        """
        ordenes = ProgramaOrdenTrabajo.objects.filter(programa=programa)
        
        if not ordenes.exists():
            return {'porcentaje': 100, 'ordenes_analizadas': 0, 'retrasos': []}
        
        ordenes_a_tiempo = 0
        retrasos_identificados = []
        
        for orden in ordenes:
            # Verificar si la orden está dentro del plazo
            progreso_orden = self._get_orden_progress(orden.orden_trabajo, programa)
            
            if progreso_orden['estado'] == 'COMPLETADA':
                if progreso_orden['fecha_completada'] <= programa.fecha_fin:
                    ordenes_a_tiempo += 1
                else:
                    dias_retraso = (progreso_orden['fecha_completada'] - programa.fecha_fin).days
                    retrasos_identificados.append({
                        'orden_id': orden.orden_trabajo.id,
                        'codigo_ot': orden.orden_trabajo.codigo_ot,
                        'dias_retraso': dias_retraso,
                        'impacto': self._classify_delay_impact(dias_retraso)
                    })
            elif progreso_orden['estado'] == 'EN_PROCESO':
                # Proyectar fecha de finalización
                fecha_proyectada = self._project_completion_date(orden.orden_trabajo, programa)
                if fecha_proyectada and fecha_proyectada > programa.fecha_fin:
                    dias_retraso_proyectado = (fecha_proyectada - programa.fecha_fin).days
                    retrasos_identificados.append({
                        'orden_id': orden.orden_trabajo.id,
                        'codigo_ot': orden.orden_trabajo.codigo_ot,
                        'dias_retraso_proyectado': dias_retraso_proyectado,
                        'impacto': self._classify_delay_impact(dias_retraso_proyectado),
                        'es_proyeccion': True
                    })
        
        porcentaje_cumplimiento = (ordenes_a_tiempo / ordenes.count()) * 100
        
        return {
            'porcentaje': round(porcentaje_cumplimiento, 2),
            'ordenes_analizadas': ordenes.count(),
            'ordenes_a_tiempo': ordenes_a_tiempo,
            'retrasos': retrasos_identificados,
            'nivel_riesgo': self._assess_delay_risk(retrasos_identificados)
        }
    
    def _calculate_resource_utilization(self, programa: ProgramaProduccion) -> Dict:
        """
        Calcula la utilización de recursos (máquinas y operadores)
        """
        # Utilización de máquinas
        utilizacion_maquinas = self._calculate_machine_utilization(programa)
        
        # Utilización de operadores
        utilizacion_operadores = self._calculate_operator_utilization(programa)
        
        # Utilización general
        utilizacion_general = (
            utilizacion_maquinas['promedio'] * 0.6 + 
            utilizacion_operadores['promedio'] * 0.4
        )
        
        return {
            'general': round(utilizacion_general, 2),
            'maquinas': utilizacion_maquinas,
            'operadores': utilizacion_operadores,
            'recursos_criticos': self._identify_critical_resources(programa),
            'oportunidades_mejora': self._identify_improvement_opportunities(
                utilizacion_maquinas, utilizacion_operadores
            )
        }
    
    def _calculate_machine_utilization(self, programa: ProgramaProduccion) -> Dict:
        """
        Calcula la utilización específica de máquinas
        """
        tareas_por_maquina = TareaFragmentada.objects.filter(
            programa=programa
        ).values(
            'tarea_original__maquina__id',
            'tarea_original__maquina__codigo_maquina',
            'tarea_original__maquina__descripcion'
        ).annotate(
            total_horas=Sum(
                Case(
                    When(tarea_original__estandar__gt=0, 
                         then=F('cantidad_asignada') / F('tarea_original__estandar')),
                    default=Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ),
            dias_utilizados=Count('fecha', distinct=True)
        )
        
        utilizaciones = []
        total_utilizacion = 0
        
        for maquina in tareas_por_maquina:
            if maquina['dias_utilizados'] > 0:
                horas_disponibles = maquina['dias_utilizados'] * 8  # 8 horas por día
                utilizacion = (float(maquina['total_horas'] or 0) / horas_disponibles) * 100
                utilizacion = min(utilizacion, 100)  # Cap al 100%
                
                utilizaciones.append({
                    'maquina_id': maquina['tarea_original__maquina__id'],
                    'codigo': maquina['tarea_original__maquina__codigo_maquina'],
                    'descripcion': maquina['tarea_original__maquina__descripcion'],
                    'utilizacion_porcentaje': round(utilizacion, 2),
                    'horas_utilizadas': float(maquina['total_horas'] or 0),
                    'horas_disponibles': horas_disponibles,
                    'dias_activos': maquina['dias_utilizados']
                })
                
                total_utilizacion += utilizacion
        
        promedio_utilizacion = total_utilizacion / len(utilizaciones) if utilizaciones else 0
        
        return {
            'promedio': round(promedio_utilizacion, 2),
            'detalle_por_maquina': sorted(utilizaciones, key=lambda x: x['utilizacion_porcentaje'], reverse=True),
            'maquinas_subutilizadas': [m for m in utilizaciones if m['utilizacion_porcentaje'] < 50],
            'maquinas_sobrecargadas': [m for m in utilizaciones if m['utilizacion_porcentaje'] > 90]
        }
    
    def _calculate_operator_utilization(self, programa: ProgramaProduccion) -> Dict:
        """
        Calcula la utilización específica de operadores
        """
        tareas_por_operador = TareaFragmentada.objects.filter(
            programa=programa,
            operador__isnull=False
        ).values(
            'operador__id',
            'operador__nombre'
        ).annotate(
            total_tareas=Count('id'),
            tareas_completadas=Count('id', filter=Q(estado='COMPLETADO')),
            dias_asignados=Count('fecha', distinct=True)
        )
        
        utilizaciones = []
        
        for operador in tareas_por_operador:
            # Asumimos que un operador puede manejar 4 tareas por día eficientemente
            capacidad_maxima = operador['dias_asignados'] * 4
            utilizacion = (operador['total_tareas'] / capacidad_maxima) * 100 if capacidad_maxima > 0 else 0
            
            utilizaciones.append({
                'operador_id': operador['operador__id'],
                'nombre': operador['operador__nombre'],
                'utilizacion_porcentaje': round(min(utilizacion, 100), 2),
                'tareas_asignadas': operador['total_tareas'],
                'tareas_completadas': operador['tareas_completadas'],
                'eficiencia': round((operador['tareas_completadas'] / operador['total_tareas']) * 100, 2) if operador['total_tareas'] > 0 else 0,
                'dias_activos': operador['dias_asignados']
            })
        
        # Operadores sin tareas asignadas
        operadores_sin_tareas = AsignacionOperador.objects.filter(
            activo=True
        ).exclude(
            operador__in=TareaFragmentada.objects.filter(
                programa=programa
            ).values_list('operador', flat=True)
        ).count()
        
        promedio_utilizacion = sum(o['utilizacion_porcentaje'] for o in utilizaciones) / len(utilizaciones) if utilizaciones else 0
        
        return {
            'promedio': round(promedio_utilizacion, 2),
            'detalle_por_operador': sorted(utilizaciones, key=lambda x: x['utilizacion_porcentaje'], reverse=True),
            'operadores_sin_asignar': operadores_sin_tareas,
            'operadores_subutilizados': [o for o in utilizaciones if o['utilizacion_porcentaje'] < 40],
            'operadores_sobrecargados': [o for o in utilizaciones if o['utilizacion_porcentaje'] > 80]
        }
    
    def _calculate_planning_quality(self, programa: ProgramaProduccion) -> Dict:
        """
        Evalúa la calidad de la planificación
        """
        # Métricas de calidad
        continuidad_score = self._evaluate_task_continuity(programa)
        secuenciacion_score = self._evaluate_sequencing_quality(programa)
        balanceamiento_score = self._evaluate_load_balancing(programa)
        flexibilidad_score = self._evaluate_planning_flexibility(programa)
        
        # Score general (promedio ponderado)
        calidad_general = (
            continuidad_score * 0.25 +
            secuenciacion_score * 0.30 +
            balanceamiento_score * 0.25 +
            flexibilidad_score * 0.20
        )
        
        return {
            'score_general': round(calidad_general, 2),
            'nivel': self._classify_quality_level(calidad_general),
            'componentes': {
                'continuidad': round(continuidad_score, 2),
                'secuenciacion': round(secuenciacion_score, 2),
                'balanceamiento': round(balanceamiento_score, 2),
                'flexibilidad': round(flexibilidad_score, 2)
            },
            'recomendaciones': self._generate_quality_recommendations(
                continuidad_score, secuenciacion_score, 
                balanceamiento_score, flexibilidad_score
            )
        }
    
    def _calculate_productivity_metrics(self, programa: ProgramaProduccion) -> Dict:
        """
        Calcula métricas de productividad
        """
        tareas = TareaFragmentada.objects.filter(programa=programa)
        
        # Productividad por día
        productividad_diaria = tareas.values('fecha').annotate(
            produccion_dia=Sum('cantidad_completada'),
            tareas_completadas=Count('id', filter=Q(estado='COMPLETADO'))
        ).order_by('fecha')
        
        # Velocidad de producción
        velocidad_promedio = self._calculate_average_production_speed(programa)
        
        # Throughput
        throughput = self._calculate_throughput(programa)
        
        # Eficiencia vs estándar
        eficiencia_estandar = self._calculate_standard_efficiency(programa)
        
        return {
            'productividad_diaria': list(productividad_diaria),
            'velocidad_promedio': velocidad_promedio,
            'throughput': throughput,
            'eficiencia_vs_estandar': eficiencia_estandar,
            'tendencias': self._analyze_productivity_trends(productividad_diaria)
        }
    
    def get_daily_metrics(self, programa: ProgramaProduccion, fecha: date) -> Dict:
        """
        Obtiene métricas específicas para un día
        """
        tareas_dia = TareaFragmentada.objects.filter(
            programa=programa,
            fecha=fecha
        )
        
        return {
            'fecha': fecha.strftime('%Y-%m-%d'),
            'resumen': {
                'tareas_programadas': tareas_dia.count(),
                'tareas_iniciadas': tareas_dia.filter(estado__in=['EN_PROCESO', 'COMPLETADO']).count(),
                'tareas_completadas': tareas_dia.filter(estado='COMPLETADO').count(),
                'produccion_total': tareas_dia.aggregate(Sum('cantidad_completada'))['cantidad_completada__sum'] or 0
            },
            'eficiencia_dia': self._calculate_daily_efficiency(tareas_dia),
            'utilizacion_recursos': self._calculate_daily_resource_utilization(tareas_dia),
            'incidencias': self._identify_daily_issues(tareas_dia),
            'comparacion_planificado': self._compare_planned_vs_actual(tareas_dia)
        }
    
    def generate_trend_analysis(self, programa: ProgramaProduccion, days: int = 7) -> Dict:
        """
        Genera análisis de tendencias para los últimos N días
        """
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=days)
        
        # Obtener métricas diarias
        metricas_diarias = []
        fecha_actual = fecha_inicio
        
        while fecha_actual <= fecha_fin:
            if self._is_working_day(fecha_actual):
                metrics = self.get_daily_metrics(programa, fecha_actual)
                metricas_diarias.append(metrics)
            fecha_actual += timedelta(days=1)
        
        # Análisis de tendencias
        tendencias = {
            'productividad': self._analyze_productivity_trend(metricas_diarias),
            'eficiencia': self._analyze_efficiency_trend(metricas_diarias),
            'cumplimiento': self._analyze_compliance_trend(metricas_diarias),
            'utilizacion': self._analyze_utilization_trend(metricas_diarias)
        }
        
        # Predicciones
        predicciones = self._generate_predictions(metricas_diarias)
        
        return {
            'periodo': {
                'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
                'dias_analizados': len(metricas_diarias)
            },
            'metricas_diarias': metricas_diarias,
            'tendencias': tendencias,
            'predicciones': predicciones,
            'alertas': self._generate_trend_alerts(tendencias)
        }
    
    # Métodos auxiliares
    def _is_working_day(self, fecha: date) -> bool:
        """Verifica si una fecha es día laboral"""
        return fecha.weekday() < 5  # Lunes=0, Viernes=4
    
    def _calculate_efficiency_trend(self, programa: ProgramaProduccion) -> str:
        """Calcula la tendencia de eficiencia"""
        # Implementación simplificada
        return 'mejorando'  # 'mejorando', 'estable', 'deteriorando'
    
    def _get_orden_progress(self, orden: OrdenTrabajo, programa: ProgramaProduccion) -> Dict:
        """Obtiene el progreso de una orden específica"""
        # Implementación simplificada
        return {
            'estado': 'EN_PROCESO',
            'porcentaje': 75,
            'fecha_completada': None
        }
    
    def _project_completion_date(self, orden: OrdenTrabajo, programa: ProgramaProduccion) -> Optional[date]:
        """Proyecta la fecha de finalización de una orden"""
        # Implementación simplificada
        return None
    
    def _classify_delay_impact(self, dias_retraso: int) -> str:
        """Clasifica el impacto de un retraso"""
        if dias_retraso <= 1:
            return 'BAJO'
        elif dias_retraso <= 3:
            return 'MEDIO'
        else:
            return 'ALTO'
    
    def _assess_delay_risk(self, retrasos: List[Dict]) -> str:
        """Evalúa el nivel de riesgo basado en retrasos"""
        if not retrasos:
            return 'BAJO'
        
        alto_impacto = len([r for r in retrasos if r.get('impacto') == 'ALTO'])
        if alto_impacto > 0:
            return 'ALTO'
        
        medio_impacto = len([r for r in retrasos if r.get('impacto') == 'MEDIO'])
        if medio_impacto > 2:
            return 'MEDIO'
        
        return 'BAJO'
    
    def _identify_critical_resources(self, programa: ProgramaProduccion) -> List[Dict]:
        """Identifica recursos críticos"""
        return []  # Implementación simplificada
    
    def _identify_improvement_opportunities(self, maquinas: Dict, operadores: Dict) -> List[str]:
        """Identifica oportunidades de mejora"""
        opportunities = []
        
        if maquinas['promedio'] < 60:
            opportunities.append("Optimizar asignación de máquinas")
        
        if operadores['promedio'] < 50:
            opportunities.append("Balancear carga de operadores")
        
        if len(maquinas.get('maquinas_sobrecargadas', [])) > 0:
            opportunities.append("Redistribuir carga de máquinas sobrecargadas")
        
        return opportunities
    
    def _get_current_status(self, programa: ProgramaProduccion) -> Dict:
        """Obtiene el estado actual del programa"""
        tareas = TareaFragmentada.objects.filter(programa=programa)
        
        estados = tareas.values('estado').annotate(cantidad=Count('id'))
        
        return {
            'estado_general': self._determine_program_status(programa),
            'distribucion_estados': list(estados),
            'fecha_actualizacion': timezone.now().isoformat()
        }
    
    def _determine_program_status(self, programa: ProgramaProduccion) -> str:
        """Determina el estado general del programa"""
        hoy = timezone.now().date()
        
        if hoy < programa.fecha_inicio:
            return 'PROGRAMADO'
        elif hoy > programa.fecha_fin:
            return 'FINALIZADO'
        else:
            return 'EN_EJECUCION'
    
    # Los demás métodos auxiliares pueden implementarse según necesidad específica
    def _evaluate_task_continuity(self, programa: ProgramaProduccion) -> float:
        return 75.0  # Implementación simplificada
    
    def _evaluate_sequencing_quality(self, programa: ProgramaProduccion) -> float:
        return 80.0  # Implementación simplificada
    
    def _evaluate_load_balancing(self, programa: ProgramaProduccion) -> float:
        return 70.0  # Implementación simplificada
    
    def _evaluate_planning_flexibility(self, programa: ProgramaProduccion) -> float:
        return 85.0  # Implementación simplificada
    
    def _classify_quality_level(self, score: float) -> str:
        if score >= 85:
            return 'EXCELENTE'
        elif score >= 70:
            return 'BUENO'
        elif score >= 55:
            return 'REGULAR'
        else:
            return 'DEFICIENTE'
    
    def _generate_quality_recommendations(self, cont: float, seq: float, bal: float, flex: float) -> List[str]:
        recommendations = []
        
        if cont < 60:
            recommendations.append("Mejorar continuidad entre tareas")
        if seq < 60:
            recommendations.append("Optimizar secuenciación de procesos")
        if bal < 60:
            recommendations.append("Balancear mejor la carga de trabajo")
        if flex < 60:
            recommendations.append("Aumentar flexibilidad en la planificación")
        
        return recommendations
    
    def _calculate_average_production_speed(self, programa: ProgramaProduccion) -> Dict:
        return {'unidades_por_hora': 0, 'tendencia': 'estable'}  # Implementación simplificada
    
    def _calculate_throughput(self, programa: ProgramaProduccion) -> Dict:
        return {'ordenes_por_dia': 0, 'eficiencia': 0}  # Implementación simplificada
    
    def _calculate_standard_efficiency(self, programa: ProgramaProduccion) -> Dict:
        return {'porcentaje': 100, 'variacion': 0}  # Implementación simplificada
    
    def _analyze_productivity_trends(self, data: List[Dict]) -> Dict:
        return {'direccion': 'estable', 'pendiente': 0}  # Implementación simplificada
    
    def _calculate_daily_efficiency(self, tareas) -> float:
        return 75.0  # Implementación simplificada
    
    def _calculate_daily_resource_utilization(self, tareas) -> Dict:
        return {'maquinas': 80, 'operadores': 75}  # Implementación simplificada
    
    def _identify_daily_issues(self, tareas) -> List[Dict]:
        return []  # Implementación simplificada
    
    def _compare_planned_vs_actual(self, tareas) -> Dict:
        return {'variacion_porcentaje': 5}  # Implementación simplificada
    
    def _analyze_productivity_trend(self, metricas: List[Dict]) -> Dict:
        return {'direccion': 'mejorando', 'tasa_cambio': 2.5}  # Implementación simplificada
    
    def _analyze_efficiency_trend(self, metricas: List[Dict]) -> Dict:
        return {'direccion': 'estable', 'tasa_cambio': 0.1}  # Implementación simplificada
    
    def _analyze_compliance_trend(self, metricas: List[Dict]) -> Dict:
        return {'direccion': 'mejorando', 'tasa_cambio': 1.2}  # Implementación simplificada
    
    def _analyze_utilization_trend(self, metricas: List[Dict]) -> Dict:
        return {'direccion': 'estable', 'tasa_cambio': 0.5}  # Implementación simplificada
    
    def _generate_predictions(self, metricas: List[Dict]) -> Dict:
        return {
            'productividad_proxima_semana': 85,
            'fecha_completacion_estimada': (timezone.now() + timedelta(days=10)).date().strftime('%Y-%m-%d')
        }  # Implementación simplificada
    
    def _generate_trend_alerts(self, tendencias: Dict) -> List[Dict]:
        return []  # Implementación simplificada 