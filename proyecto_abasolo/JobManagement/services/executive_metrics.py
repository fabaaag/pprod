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
from Product.models import Producto


class ExecutiveMetricsEngine:
    """
    Motor de métricas ejecutivas para dashboards de gerencia
    Enfocado en KPIs de alto nivel que solicitan los ejecutivos
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutos
    
    def get_resumen_ejecutivo_completo(self, programa: ProgramaProduccion) -> Dict:
        """
        Genera el resumen ejecutivo completo que típicamente solicitan
        """
        return {
            'produccion_fisica': self.get_metricas_produccion_fisica(programa),
            'eficiencia_operacional': self.get_eficiencia_operacional(programa),
            'utilizacion_recursos': self.get_utilizacion_recursos_detallada(programa),
            'cumplimiento_entregas': self.get_cumplimiento_entregas(programa),
            'costos_estimados': self.get_costos_estimados(programa),
            'comparativas_historicas': self.get_comparativas_historicas(programa),
            'alertas_ejecutivas': self.get_alertas_ejecutivas(programa),
            'proyecciones': self.get_proyecciones(programa)
        }
    
    def get_metricas_produccion_fisica(self, programa: ProgramaProduccion) -> Dict:
        """
        Métricas de producción física - lo más solicitado
        """
        # Obtener todas las órdenes del programa con sus pesos
        ordenes_programa = ProgramaOrdenTrabajo.objects.filter(
            programa=programa
        ).select_related('orden_trabajo')
        
        # Calcular kilos planificados
        kilos_planificados_total = 0
        kilos_fabricados_total = 0
        unidades_planificadas_total = 0
        unidades_fabricadas_total = 0
        
        detalles_por_producto = []
        
        for pot in ordenes_programa:
            ot = pot.orden_trabajo
            peso_unitario = float(ot.peso_unitario or 0)
            cantidad_planificada = float(ot.cantidad or 0)
            cantidad_fabricada = float(ot.cantidad_avance or 0)
            
            kilos_plan_ot = cantidad_planificada * peso_unitario
            kilos_fab_ot = cantidad_fabricada * peso_unitario
            
            kilos_planificados_total += kilos_plan_ot
            kilos_fabricados_total += kilos_fab_ot
            unidades_planificadas_total += cantidad_planificada
            unidades_fabricadas_total += cantidad_fabricada
            
            # Detalle por producto
            detalles_por_producto.append({
                'orden_codigo': ot.codigo_ot,
                'producto_codigo': ot.codigo_producto_inicial or 'N/A',
                'descripcion': ot.descripcion_producto_ot or 'Sin descripción',
                'peso_unitario': peso_unitario,
                'unidades_planificadas': cantidad_planificada,
                'unidades_fabricadas': cantidad_fabricada,
                'kilos_planificados': round(kilos_plan_ot, 2),
                'kilos_fabricados': round(kilos_fab_ot, 2),
                'porcentaje_avance': round((cantidad_fabricada / cantidad_planificada * 100) if cantidad_planificada > 0 else 0, 2),
                'cliente': ot.cliente.nombre if ot.cliente else 'Sin cliente'
            })
        
        # Métricas agregadas por día
        metricas_diarias = self._get_produccion_por_dia(programa)
        
        # Eficiencia de conversión (kg/unidad real vs planificado)
        eficiencia_conversion = 100
        if kilos_planificados_total > 0 and unidades_fabricadas_total > 0:
            kg_por_unidad_planificado = kilos_planificados_total / unidades_planificadas_total
            kg_por_unidad_real = kilos_fabricados_total / unidades_fabricadas_total
            eficiencia_conversion = (kg_por_unidad_planificado / kg_por_unidad_real * 100) if kg_por_unidad_real > 0 else 100
        
        return {
            'resumen_general': {
                'kilos_planificados': round(kilos_planificados_total, 2),
                'kilos_fabricados': round(kilos_fabricados_total, 2),
                'kilos_pendientes': round(kilos_planificados_total - kilos_fabricados_total, 2),
                'porcentaje_completado_kilos': round((kilos_fabricados_total / kilos_planificados_total * 100) if kilos_planificados_total > 0 else 0, 2),
                'unidades_planificadas': round(unidades_planificadas_total, 2),
                'unidades_fabricadas': round(unidades_fabricadas_total, 2),
                'eficiencia_conversion': round(eficiencia_conversion, 2)
            },
            'detalle_por_producto': sorted(detalles_por_producto, key=lambda x: x['kilos_planificados'], reverse=True),
            'produccion_diaria': metricas_diarias,
            'analisis_desperdicios': self._analizar_desperdicios(programa),
            'tendencia_produccion': self._calcular_tendencia_produccion(metricas_diarias)
        }
    
    def get_eficiencia_operacional(self, programa: ProgramaProduccion) -> Dict:
        """
        Eficiencia operacional detallada
        """
        tareas = TareaFragmentada.objects.filter(programa=programa)
        
        # Eficiencia por máquina
        eficiencia_por_maquina = []
        maquinas_usadas = tareas.values('tarea_original__maquina').distinct()
        
        for maquina_data in maquinas_usadas:
            maquina_id = maquina_data['tarea_original__maquina']
            if not maquina_id:
                continue
                
            from ..models import Maquina
            maquina = Maquina.objects.get(id=maquina_id)
            
            tareas_maquina = tareas.filter(tarea_original__maquina=maquina)
            
            # Calcular eficiencia basada en estándares
            eficiencia_promedio = 0
            total_tareas_con_estandar = 0
            
            for tarea in tareas_maquina:
                if tarea.tarea_original.estandar and tarea.cantidad_completada:
                    tiempo_teorico = float(tarea.cantidad_completada) / tarea.tarea_original.estandar
                    
                    # Calcular tiempo real (simplificado)
                    if tarea.fecha_real_inicio and tarea.fecha_real_fin:
                        tiempo_real_horas = (tarea.fecha_real_fin - tarea.fecha_real_inicio).total_seconds() / 3600
                        if tiempo_real_horas > 0:
                            eficiencia_tarea = (tiempo_teorico / tiempo_real_horas) * 100
                            eficiencia_promedio += eficiencia_tarea
                            total_tareas_con_estandar += 1
            
            if total_tareas_con_estandar > 0:
                eficiencia_promedio = eficiencia_promedio / total_tareas_con_estandar
            else:
                eficiencia_promedio = 100  # Asumir 100% si no hay datos
            
            eficiencia_por_maquina.append({
                'maquina_codigo': maquina.codigo_maquina,
                'maquina_descripcion': maquina.descripcion,
                'eficiencia_promedio': round(eficiencia_promedio, 2),
                'tareas_completadas': tareas_maquina.filter(estado='COMPLETADO').count(),
                'tareas_total': tareas_maquina.count(),
                'porcentaje_cumplimiento': round((tareas_maquina.filter(estado='COMPLETADO').count() / tareas_maquina.count() * 100) if tareas_maquina.count() > 0 else 0, 2)
            })
        
        # Eficiencia por operador
        eficiencia_por_operador = self._calcular_eficiencia_operadores(tareas)
        
        # OEE (Overall Equipment Effectiveness) simplificado
        oee_por_maquina = self._calcular_oee_simplificado(programa)
        
        return {
            'eficiencia_por_maquina': sorted(eficiencia_por_maquina, key=lambda x: x['eficiencia_promedio'], reverse=True),
            'eficiencia_por_operador': eficiencia_por_operador,
            'oee_por_maquina': oee_por_maquina,
            'resumen_eficiencia': {
                'eficiencia_promedio_programa': round(sum(m['eficiencia_promedio'] for m in eficiencia_por_maquina) / len(eficiencia_por_maquina), 2) if eficiencia_por_maquina else 0,
                'mejor_maquina': max(eficiencia_por_maquina, key=lambda x: x['eficiencia_promedio']) if eficiencia_por_maquina else None,
                'maquina_critica': min(eficiencia_por_maquina, key=lambda x: x['eficiencia_promedio']) if eficiencia_por_maquina else None
            }
        }
    
    def get_utilizacion_recursos_detallada(self, programa: ProgramaProduccion) -> Dict:
        """
        Utilización detallada de recursos con métricas ejecutivas
        """
        tareas = TareaFragmentada.objects.filter(programa=programa)
        
        # Utilización por día de la semana
        utilizacion_por_dia_semana = {}
        
        # Utilización por turno (si tuviéramos turnos)
        utilizacion_por_turno = {
            'turno_mañana': {'horas_utilizadas': 0, 'horas_disponibles': 0},
            'turno_tarde': {'horas_utilizadas': 0, 'horas_disponibles': 0},
            'turno_noche': {'horas_utilizadas': 0, 'horas_disponibles': 0}
        }
        
        # Cuellos de botella identificados
        cuellos_botella = self._identificar_cuellos_botella_detallados(programa)
        
        # Capacidad vs demanda
        analisis_capacidad = self._analizar_capacidad_vs_demanda(programa)
        
        return {
            'utilizacion_por_dia_semana': utilizacion_por_dia_semana,
            'utilizacion_por_turno': utilizacion_por_turno,
            'cuellos_botella': cuellos_botella,
            'analisis_capacidad': analisis_capacidad,
            'recomendaciones_optimizacion': self._generar_recomendaciones_optimizacion(programa)
        }
    
    def get_cumplimiento_entregas(self, programa: ProgramaProduccion) -> Dict:
        """
        Análisis de cumplimiento de entregas y plazos
        """
        ordenes = ProgramaOrdenTrabajo.objects.filter(programa=programa)
        
        cumplimiento_por_cliente = {}
        cumplimiento_por_producto = {}
        
        for pot in ordenes:
            ot = pot.orden_trabajo
            
            # Análisis por cliente
            cliente_nombre = ot.cliente.nombre if ot.cliente else 'Sin cliente'
            if cliente_nombre not in cumplimiento_por_cliente:
                cumplimiento_por_cliente[cliente_nombre] = {
                    'ordenes_total': 0,
                    'ordenes_a_tiempo': 0,
                    'ordenes_retrasadas': 0,
                    'kilos_total': 0,
                    'kilos_entregados': 0
                }
            
            cumplimiento_por_cliente[cliente_nombre]['ordenes_total'] += 1
            cumplimiento_por_cliente[cliente_nombre]['kilos_total'] += float(ot.cantidad or 0) * float(ot.peso_unitario or 0)
            cumplimiento_por_cliente[cliente_nombre]['kilos_entregados'] += float(ot.cantidad_avance or 0) * float(ot.peso_unitario or 0)
            
            # Determinar si está a tiempo (simplificado)
            if ot.fecha_termino and timezone.now().date() <= ot.fecha_termino:
                cumplimiento_por_cliente[cliente_nombre]['ordenes_a_tiempo'] += 1
            else:
                cumplimiento_por_cliente[cliente_nombre]['ordenes_retrasadas'] += 1
        
        # Calcular porcentajes
        for cliente in cumplimiento_por_cliente.values():
            if cliente['ordenes_total'] > 0:
                cliente['porcentaje_cumplimiento'] = round((cliente['ordenes_a_tiempo'] / cliente['ordenes_total']) * 100, 2)
                cliente['porcentaje_entrega_kilos'] = round((cliente['kilos_entregados'] / cliente['kilos_total']) * 100, 2) if cliente['kilos_total'] > 0 else 0
        
        return {
            'cumplimiento_por_cliente': cumplimiento_por_cliente,
            'cumplimiento_por_producto': cumplimiento_por_producto,
            'resumen_general': {
                'porcentaje_cumplimiento_global': self._calcular_cumplimiento_global(ordenes),
                'ordenes_criticas': self._identificar_ordenes_criticas(ordenes),
                'proyeccion_entregas': self._proyectar_entregas(programa)
            }
        }
    
    def get_costos_estimados(self, programa: ProgramaProduccion) -> Dict:
        """
        Estimaciones de costos (preparado para cuando tengan datos de precios)
        """
        # Preparar estructura para futuros datos de costos
        estructura_costos = {
            'costos_materiales': {
                'planificado': 0,
                'real': 0,
                'variacion': 0,
                'nota': 'Datos no disponibles - configurar precios de materiales'
            },
            'costos_mano_obra': {
                'horas_planificadas': self._calcular_horas_planificadas(programa),
                'horas_reales': self._calcular_horas_reales(programa),
                'costo_hora_estimado': 0,  # Para configurar
                'costo_total_estimado': 0,
                'nota': 'Configurar costo por hora de mano de obra'
            },
            'costos_maquina': {
                'horas_maquina_planificadas': self._calcular_horas_maquina(programa),
                'costo_hora_maquina_estimado': 0,  # Para configurar
                'costo_total_estimado': 0,
                'nota': 'Configurar costo por hora de máquina'
            },
            'indicadores_preparados': {
                'costo_por_kilo': 'Pendiente configuración precios',
                'costo_por_unidad': 'Pendiente configuración precios',
                'margen_estimado': 'Pendiente configuración precios de venta',
                'roi_programa': 'Pendiente configuración costos e ingresos'
            }
        }
        
        return estructura_costos
    
    def get_comparativas_historicas(self, programa: ProgramaProduccion) -> Dict:
        """
        Comparativas con programas anteriores
        """
        # Buscar programas anteriores similares
        programas_anteriores = ProgramaProduccion.objects.filter(
            created_at__lt=programa.created_at
        ).order_by('-created_at')[:5]  # Últimos 5 programas
        
        comparativas = []
        
        for prog_anterior in programas_anteriores:
            metricas_anterior = self.get_metricas_produccion_fisica(prog_anterior)
            
            comparativas.append({
                'programa_id': prog_anterior.id,
                'programa_nombre': prog_anterior.nombre,
                'fecha_inicio': prog_anterior.fecha_inicio.strftime('%Y-%m-%d'),
                'kilos_planificados': metricas_anterior['resumen_general']['kilos_planificados'],
                'kilos_fabricados': metricas_anterior['resumen_general']['kilos_fabricados'],
                'eficiencia': metricas_anterior['resumen_general']['porcentaje_completado_kilos']
            })
        
        # Calcular tendencias
        if comparativas:
            tendencia_eficiencia = 'mejorando' if len(comparativas) >= 2 and comparativas[0]['eficiencia'] > comparativas[1]['eficiencia'] else 'estable'
        else:
            tendencia_eficiencia = 'sin_datos'
        
        return {
            'programas_anteriores': comparativas,
            'tendencias': {
                'eficiencia': tendencia_eficiencia,
                'productividad': 'estable',  # Calcular cuando tengamos más datos
                'cumplimiento': 'estable'
            },
            'benchmarks': {
                'mejor_programa': max(comparativas, key=lambda x: x['eficiencia']) if comparativas else None,
                'promedio_industria': 85.0,  # Valor de referencia
                'objetivo_empresa': 90.0   # Para configurar
            }
        }
    
    def get_alertas_ejecutivas(self, programa: ProgramaProduccion) -> List[Dict]:
        """
        Alertas específicas para nivel ejecutivo
        """
        alertas = []
        
        # Obtener métricas básicas
        metricas_prod = self.get_metricas_produccion_fisica(programa)
        
        # Alerta por bajo cumplimiento de kilos
        porcentaje_kilos = metricas_prod['resumen_general']['porcentaje_completado_kilos']
        if porcentaje_kilos < 70:
            alertas.append({
                'tipo': 'PRODUCCION_BAJA',
                'prioridad': 'CRITICA' if porcentaje_kilos < 50 else 'ALTA',
                'titulo': 'Cumplimiento de Producción Bajo',
                'descripcion': f'Solo se ha completado el {porcentaje_kilos}% de los kilos planificados',
                'impacto_ejecutivo': 'Riesgo de incumplimiento de entregas a clientes',
                'accion_recomendada': 'Revisar asignación de recursos y prioridades'
            })
        
        # Alerta por retrasos en programa
        dias_transcurridos = (timezone.now().date() - programa.fecha_inicio).days
        if programa.fecha_fin:
            dias_totales = (programa.fecha_fin - programa.fecha_inicio).days
            porcentaje_tiempo = (dias_transcurridos / dias_totales * 100) if dias_totales > 0 else 0
            
            if porcentaje_tiempo > porcentaje_kilos + 15:  # Retraso significativo
                alertas.append({
                    'tipo': 'RETRASO_PROGRAMA',
                    'prioridad': 'ALTA',
                    'titulo': 'Programa Retrasado vs Plan',
                    'descripcion': f'Transcurrido {porcentaje_tiempo:.1f}% del tiempo pero solo {porcentaje_kilos:.1f}% de producción',
                    'impacto_ejecutivo': 'Riesgo de retrasos en entregas programadas',
                    'accion_recomendada': 'Evaluar reasignación de recursos o extensión de plazos'
                })
        
        # Alerta por eficiencia de máquinas
        eficiencia = self.get_eficiencia_operacional(programa)
        if eficiencia['resumen_eficiencia']['eficiencia_promedio_programa'] < 75:
            alertas.append({
                'tipo': 'EFICIENCIA_BAJA',
                'prioridad': 'MEDIA',
                'titulo': 'Eficiencia Operacional Baja',
                'descripcion': f"Eficiencia promedio: {eficiencia['resumen_eficiencia']['eficiencia_promedio_programa']}%",
                'impacto_ejecutivo': 'Incremento en costos operacionales',
                'accion_recomendada': 'Revisar procesos y capacitación de operadores'
            })
        
        return alertas
    
    def get_proyecciones(self, programa: ProgramaProduccion) -> Dict:
        """
        Proyecciones basadas en tendencias actuales
        """
        metricas_prod = self.get_metricas_produccion_fisica(programa)
        
        # Proyección de finalización
        porcentaje_completado = metricas_prod['resumen_general']['porcentaje_completado_kilos']
        
        if programa.fecha_fin and porcentaje_completado > 0:
            dias_transcurridos = (timezone.now().date() - programa.fecha_inicio).days
            dias_totales_proyectados = (dias_transcurridos / porcentaje_completado * 100) if porcentaje_completado > 0 else 0
            fecha_finalizacion_proyectada = programa.fecha_inicio + timedelta(days=dias_totales_proyectados)
            
            retraso_proyectado = (fecha_finalizacion_proyectada - programa.fecha_fin).days if fecha_finalizacion_proyectada > programa.fecha_fin else 0
        else:
            fecha_finalizacion_proyectada = None
            retraso_proyectado = 0
        
        return {
            'finalizacion': {
                'fecha_proyectada': fecha_finalizacion_proyectada.strftime('%Y-%m-%d') if fecha_finalizacion_proyectada else None,
                'fecha_planificada': programa.fecha_fin.strftime('%Y-%m-%d') if programa.fecha_fin else None,
                'retraso_dias': retraso_proyectado,
                'probabilidad_cumplimiento': max(0, 100 - (retraso_proyectado * 5))  # Heurística simple
            },
            'produccion': {
                'kilos_proyectados_fin_programa': metricas_prod['resumen_general']['kilos_planificados'],
                'ritmo_actual_kg_dia': self._calcular_ritmo_actual(programa),
                'ritmo_requerido_kg_dia': self._calcular_ritmo_requerido(programa)
            },
            'recursos': {
                'utilizacion_proyectada': self._proyectar_utilizacion_recursos(programa),
                'capacidad_adicional_requerida': self._calcular_capacidad_adicional(programa)
            }
        }
    
    # Métodos auxiliares privados
    def _get_produccion_por_dia(self, programa: ProgramaProduccion) -> List[Dict]:
        """Obtiene producción agregada por día"""
        tareas = TareaFragmentada.objects.filter(programa=programa)
        
        produccion_por_dia = {}
        
        for tarea in tareas:
            fecha_str = tarea.fecha.strftime('%Y-%m-%d')
            if fecha_str not in produccion_por_dia:
                produccion_por_dia[fecha_str] = {
                    'fecha': fecha_str,
                    'kilos_planificados': 0,
                    'kilos_fabricados': 0,
                    'unidades_planificadas': 0,
                    'unidades_fabricadas': 0
                }
            
            # Obtener peso del producto
            if tarea.tarea_original.ruta and hasattr(tarea.tarea_original.ruta, 'orden_trabajo'):
                ot = tarea.tarea_original.ruta.orden_trabajo
                peso_unitario = float(ot.peso_unitario or 0)
                
                kilos_plan = float(tarea.cantidad_asignada) * peso_unitario
                kilos_fab = float(tarea.cantidad_completada) * peso_unitario
                
                produccion_por_dia[fecha_str]['kilos_planificados'] += kilos_plan
                produccion_por_dia[fecha_str]['kilos_fabricados'] += kilos_fab
                produccion_por_dia[fecha_str]['unidades_planificadas'] += float(tarea.cantidad_asignada)
                produccion_por_dia[fecha_str]['unidades_fabricadas'] += float(tarea.cantidad_completada)
        
        return sorted(produccion_por_dia.values(), key=lambda x: x['fecha'])
    
    def _analizar_desperdicios(self, programa: ProgramaProduccion) -> Dict:
        """Analiza desperdicios y pérdidas"""
        tareas = TareaFragmentada.objects.filter(programa=programa)
        
        total_perdidas = sum(float(item.cantidad_perdida_proceso or 0) for item in ItemRuta.objects.filter(ruta__items__in=tareas.values_list('tarea_original', flat=True)))
        total_planificado = sum(float(tarea.cantidad_asignada) for tarea in tareas)
        
        porcentaje_desperdicio = (total_perdidas / total_planificado * 100) if total_planificado > 0 else 0
        
        return {
            'total_perdidas': round(total_perdidas, 2),
            'porcentaje_desperdicio': round(porcentaje_desperdicio, 2),
            'costo_estimado_desperdicios': 0,  # Para configurar cuando tengan precios
            'principales_causas': ['Configurar análisis de causas de desperdicios']
        }
    
    def _calcular_tendencia_produccion(self, datos_diarios: List[Dict]) -> str:
        """Calcula tendencia de producción"""
        if len(datos_diarios) < 3:
            return 'insuficientes_datos'
        
        # Comparar últimos 3 días
        ultimos_3 = datos_diarios[-3:]
        if ultimos_3[-1]['kilos_fabricados'] > ultimos_3[0]['kilos_fabricados']:
            return 'mejorando'
        elif ultimos_3[-1]['kilos_fabricados'] < ultimos_3[0]['kilos_fabricados']:
            return 'deteriorando'
        else:
            return 'estable'
    
    def _calcular_eficiencia_operadores(self, tareas) -> List[Dict]:
        """Calcula eficiencia por operador"""
        operadores_data = {}
        
        for tarea in tareas.filter(operador__isnull=False):
            op_id = tarea.operador.id
            if op_id not in operadores_data:
                operadores_data[op_id] = {
                    'operador_nombre': tarea.operador.nombre,
                    'tareas_asignadas': 0,
                    'tareas_completadas': 0,
                    'cantidad_total_asignada': 0,
                    'cantidad_total_completada': 0
                }
            
            operadores_data[op_id]['tareas_asignadas'] += 1
            operadores_data[op_id]['cantidad_total_asignada'] += float(tarea.cantidad_asignada)
            
            if tarea.estado == 'COMPLETADO':
                operadores_data[op_id]['tareas_completadas'] += 1
                operadores_data[op_id]['cantidad_total_completada'] += float(tarea.cantidad_completada)
        
        # Calcular eficiencia
        for datos in operadores_data.values():
            datos['eficiencia_tareas'] = round((datos['tareas_completadas'] / datos['tareas_asignadas'] * 100) if datos['tareas_asignadas'] > 0 else 0, 2)
            datos['eficiencia_cantidad'] = round((datos['cantidad_total_completada'] / datos['cantidad_total_asignada'] * 100) if datos['cantidad_total_asignada'] > 0 else 0, 2)
        
        return list(operadores_data.values())
    
    def _calcular_oee_simplificado(self, programa: ProgramaProduccion) -> List[Dict]:
        """Calcula OEE simplificado por máquina"""
        # OEE = Disponibilidad × Rendimiento × Calidad
        # Por ahora un cálculo simplificado
        return [
            {
                'maquina': 'Todas las máquinas',
                'disponibilidad': 85,  # Para calcular con datos reales
                'rendimiento': 80,     # Para calcular con datos reales
                'calidad': 95,         # Para calcular con datos reales
                'oee': 64.6,           # 85 × 80 × 95 / 10000
                'nota': 'Cálculo simplificado - configurar con datos reales'
            }
        ]
    
    # Los demás métodos auxiliares serían implementaciones simplificadas por ahora
    def _identificar_cuellos_botella_detallados(self, programa): return []
    def _analizar_capacidad_vs_demanda(self, programa): return {}
    def _generar_recomendaciones_optimizacion(self, programa): return []
    def _calcular_cumplimiento_global(self, ordenes): return 0
    def _identificar_ordenes_criticas(self, ordenes): return []
    def _proyectar_entregas(self, programa): return {}
    def _calcular_horas_planificadas(self, programa): return 0
    def _calcular_horas_reales(self, programa): return 0
    def _calcular_horas_maquina(self, programa): return 0
    def _calcular_ritmo_actual(self, programa): return 0
    def _calcular_ritmo_requerido(self, programa): return 0
    def _proyectar_utilizacion_recursos(self, programa): return 0
    def _calcular_capacidad_adicional(self, programa): return 0 