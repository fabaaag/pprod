from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
import logging
from django.db.models import Q, Sum, Avg
from ..models import (
    Maquina, Proceso, EstandarMaquinaProceso, 
    TareaFragmentada, ItemRuta, ProgramaProduccion
)
from Operator.models import AsignacionOperador, Operador
from Machine.models import DisponibilidadMaquina
from .time_calculations import TimeCalculator


class OptimizationEngine:
    """
    Motor de optimización para mejorar la planificación automática
    """
    
    def __init__(self):
        self.time_calculator = TimeCalculator()
        self.logger = logging.getLogger('optimization')
    
    def optimize_machine_assignment(self, programa: ProgramaProduccion) -> Dict:
        """
        Optimiza la asignación de máquinas para todo el programa
        """
        resultados = {
            'optimizaciones_aplicadas': 0,
            'tiempo_total_reducido': 0,
            'eficiencia_mejorada': [],
            'conflictos_resueltos': 0
        }
        
        try:
            # 1. Obtener todas las tareas del programa
            tareas = TareaFragmentada.objects.filter(programa=programa)
            
            # 2. Agrupar por proceso para análisis conjunto
            tareas_por_proceso = {}
            for tarea in tareas:
                if tarea.tarea_original.proceso:
                    proceso_id = tarea.tarea_original.proceso.id
                    if proceso_id not in tareas_por_proceso:
                        tareas_por_proceso[proceso_id] = []
                    tareas_por_proceso[proceso_id].append(tarea)
            
            # 3. Optimizar cada grupo de procesos
            for proceso_id, lista_tareas in tareas_por_proceso.items():
                optimizacion = self._optimize_process_group(lista_tareas)
                resultados['optimizaciones_aplicadas'] += optimizacion['cambios']
                resultados['tiempo_total_reducido'] += optimizacion['tiempo_ahorrado']
                resultados['conflictos_resueltos'] += optimizacion['conflictos_resueltos']
            
            # 4. Balancear cargas entre máquinas
            balance = self._balance_machine_loads(programa)
            resultados['eficiencia_mejorada'] = balance['mejoras']
            
            self.logger.info(f"Optimización completada para programa {programa.id}: {resultados}")
            return resultados
            
        except Exception as e:
            self.logger.error(f"Error en optimización: {str(e)}")
            return resultados
    
    def _optimize_process_group(self, tareas: List[TareaFragmentada]) -> Dict:
        """
        Optimiza un grupo de tareas del mismo proceso
        """
        resultado = {'cambios': 0, 'tiempo_ahorrado': 0, 'conflictos_resueltos': 0}
        
        if not tareas:
            return resultado
        
        proceso = tareas[0].tarea_original.proceso
        
        # Obtener máquinas disponibles para este proceso
        maquinas_compatibles = self._get_compatible_machines(proceso)
        
        # Analizar eficiencia actual vs potencial
        for tarea in tareas:
            mejor_maquina = self._find_best_machine(tarea, maquinas_compatibles)
            
            if mejor_maquina and mejor_maquina != tarea.tarea_original.maquina:
                # Calcular beneficio del cambio
                beneficio = self._calculate_change_benefit(tarea, mejor_maquina)
                
                if beneficio['mejora_tiempo'] > 0 and beneficio['viable']:
                    # Aplicar el cambio
                    self._apply_machine_change(tarea, mejor_maquina)
                    resultado['cambios'] += 1
                    resultado['tiempo_ahorrado'] += beneficio['mejora_tiempo']
        
        return resultado
    
    def _get_compatible_machines(self, proceso: Proceso) -> List[Maquina]:
        """
        Obtiene máquinas compatibles con un proceso específico
        """
        return Maquina.objects.filter(
            estadomaquina__tipos_maquina__in=proceso.tipos_maquina_compatibles.all(),
            estadomaquina__estado_operatividad__estado='OP'
        ).distinct()
    
    def _find_best_machine(self, tarea: TareaFragmentada, maquinas: List[Maquina]) -> Optional[Maquina]:
        """
        Encuentra la mejor máquina para una tarea específica
        """
        mejor_maquina = None
        mejor_score = -1
        
        # Obtener el producto/pieza de la tarea
        item_ruta = tarea.tarea_original
        producto = None
        pieza = None
        
        if hasattr(item_ruta.ruta, 'orden_trabajo'):
            ot = item_ruta.ruta.orden_trabajo
            if ot.codigo_producto_inicial:
                from Product.models import Producto, Pieza
                try:
                    producto = Producto.objects.get(codigo_producto=ot.codigo_producto_inicial)
                except Producto.DoesNotExist:
                    try:
                        pieza = Pieza.objects.get(codigo_pieza=ot.codigo_producto_inicial)
                    except Pieza.DoesNotExist:
                        pass
        
        for maquina in maquinas:
            score = self._calculate_machine_score(
                maquina=maquina,
                proceso=tarea.tarea_original.proceso,
                producto=producto,
                pieza=pieza,
                fecha=tarea.fecha,
                cantidad=tarea.cantidad_asignada
            )
            
            if score > mejor_score:
                mejor_score = score
                mejor_maquina = maquina
        
        return mejor_maquina
    
    def _calculate_machine_score(self, maquina: Maquina, proceso: Proceso, 
                                producto=None, pieza=None, fecha=None, cantidad=0) -> float:
        """
        Calcula un score para una máquina considerando múltiples factores
        """
        score = 0.0
        
        try:
            # 1. Score por estándar (eficiencia)
            estandar = self._get_estandar(maquina, proceso, producto, pieza)
            if estandar and estandar > 0:
                score += (estandar / 1000.0) * 40  # 40% del score
            
            # 2. Score por disponibilidad
            if fecha:
                disponibilidad = self._check_machine_availability(maquina, fecha)
                score += disponibilidad * 30  # 30% del score
            
            # 3. Score por carga actual (preferir máquinas menos cargadas)
            carga_actual = self._get_current_load(maquina, fecha)
            score += (1.0 - min(carga_actual, 1.0)) * 20  # 20% del score
            
            # 4. Score por continuidad (preferir la misma máquina si es posible)
            if hasattr(maquina, '_is_current_machine') and maquina._is_current_machine:
                score += 10  # 10% del score
            
        except Exception as e:
            self.logger.warning(f"Error calculando score para máquina {maquina.id}: {str(e)}")
        
        return score
    
    def _get_estandar(self, maquina: Maquina, proceso: Proceso, producto=None, pieza=None) -> int:
        """
        Obtiene el estándar para una combinación máquina-proceso-producto/pieza
        """
        try:
            if producto:
                estandar_obj = EstandarMaquinaProceso.objects.filter(
                    maquina=maquina,
                    proceso=proceso,
                    producto=producto
                ).first()
            elif pieza:
                estandar_obj = EstandarMaquinaProceso.objects.filter(
                    maquina=maquina,
                    proceso=proceso,
                    pieza=pieza
                ).first()
            else:
                return 0
            
            return estandar_obj.estandar if estandar_obj else 0
            
        except Exception:
            return 0
    
    def _check_machine_availability(self, maquina: Maquina, fecha) -> float:
        """
        Verifica la disponibilidad de una máquina en una fecha específica
        Returns: 0.0 - 1.0 (0 = no disponible, 1 = totalmente disponible)
        """
        try:
            disponibilidad = DisponibilidadMaquina.objects.filter(
                maquina=maquina,
                fecha=fecha
            ).first()
            
            if not disponibilidad or not disponibilidad.disponible:
                return 0.0
            
            horas_disponibles = disponibilidad.get_horas_efectivas()
            horas_totales = 8.0  # Jornada completa
            
            return min(horas_disponibles / horas_totales, 1.0)
            
        except Exception:
            return 0.5  # Valor por defecto si no se puede determinar
    
    def _get_current_load(self, maquina: Maquina, fecha) -> float:
        """
        Obtiene la carga actual de una máquina para una fecha específica
        Returns: 0.0 - 1.0+ (0 = sin carga, 1+ = sobrecarga)
        """
        try:
            carga_actual = maquina.calcular_carga_fecha(fecha)
            capacidad_total = 8.0  # Horas de trabajo por día
            
            return carga_actual / capacidad_total
            
        except Exception:
            return 0.0
    
    def _calculate_change_benefit(self, tarea: TareaFragmentada, nueva_maquina: Maquina) -> Dict:
        """
        Calcula el beneficio de cambiar una tarea a una nueva máquina
        """
        beneficio = {
            'mejora_tiempo': 0,
            'mejora_eficiencia': 0,
            'viable': False,
            'conflictos': []
        }
        
        try:
            # Obtener estándares
            estandar_actual = tarea.tarea_original.estandar or 0
            estandar_nuevo = self._get_estandar(
                nueva_maquina,
                tarea.tarea_original.proceso,
                # Necesitaríamos el producto/pieza aquí
            )
            
            if estandar_nuevo > estandar_actual:
                # Calcular mejora en tiempo
                if estandar_actual > 0:
                    tiempo_actual = float(tarea.cantidad_asignada) / estandar_actual
                    tiempo_nuevo = float(tarea.cantidad_asignada) / estandar_nuevo
                    beneficio['mejora_tiempo'] = tiempo_actual - tiempo_nuevo
                    beneficio['mejora_eficiencia'] = (estandar_nuevo - estandar_actual) / estandar_actual
                
                # Verificar viabilidad
                disponible, mensaje = nueva_maquina.validar_disponibilidad(
                    tarea.fecha,
                    tarea.cantidad_asignada,
                    estandar_nuevo
                )
                
                beneficio['viable'] = disponible
                if not disponible:
                    beneficio['conflictos'].append(mensaje)
            
        except Exception as e:
            self.logger.warning(f"Error calculando beneficio: {str(e)}")
        
        return beneficio
    
    def _apply_machine_change(self, tarea: TareaFragmentada, nueva_maquina: Maquina):
        """
        Aplica el cambio de máquina a una tarea
        """
        try:
            # Guardar máquina anterior para logging
            maquina_anterior = tarea.tarea_original.maquina
            
            # Cambiar la máquina en el ItemRuta
            tarea.tarea_original.maquina = nueva_maquina
            tarea.tarea_original.save()
            
            # Registrar el cambio en el historial
            cambio = {
                'tipo': 'OPTIMIZACION_MAQUINA',
                'maquina_anterior': maquina_anterior.id if maquina_anterior else None,
                'maquina_nueva': nueva_maquina.id,
                'fecha_cambio': datetime.now().isoformat(),
                'motivo': 'Optimización automática'
            }
            
            if not hasattr(tarea, 'historial_cambios') or not tarea.historial_cambios:
                tarea.historial_cambios = []
            
            tarea.historial_cambios.append(cambio)
            tarea.save()
            
            self.logger.info(f"Máquina optimizada para tarea {tarea.id}: {maquina_anterior} -> {nueva_maquina}")
            
        except Exception as e:
            self.logger.error(f"Error aplicando cambio de máquina: {str(e)}")
    
    def _balance_machine_loads(self, programa: ProgramaProduccion) -> Dict:
        """
        Balancea las cargas entre máquinas del programa
        """
        resultado = {'mejoras': []}
        
        try:
            # Obtener estadísticas de carga por máquina
            cargas_por_maquina = {}
            tareas = TareaFragmentada.objects.filter(programa=programa)
            
            for tarea in tareas:
                maquina_id = tarea.tarea_original.maquina.id
                if maquina_id not in cargas_por_maquina:
                    cargas_por_maquina[maquina_id] = {
                        'maquina': tarea.tarea_original.maquina,
                        'carga_total': 0,
                        'dias_utilizados': set(),
                        'tareas': []
                    }
                
                cargas_por_maquina[maquina_id]['carga_total'] += float(tarea.cantidad_asignada)
                cargas_por_maquina[maquina_id]['dias_utilizados'].add(tarea.fecha)
                cargas_por_maquina[maquina_id]['tareas'].append(tarea)
            
            # Identificar desequilibrios y aplicar mejoras
            for maquina_id, datos in cargas_por_maquina.items():
                carga_promedio = datos['carga_total'] / len(datos['dias_utilizados']) if datos['dias_utilizados'] else 0
                
                mejora = {
                    'maquina_id': maquina_id,
                    'carga_promedio': carga_promedio,
                    'dias_utilizados': len(datos['dias_utilizados']),
                    'utilizacion': 'ALTA' if carga_promedio > 80 else 'MEDIA' if carga_promedio > 40 else 'BAJA'
                }
                
                resultado['mejoras'].append(mejora)
            
        except Exception as e:
            self.logger.error(f"Error balanceando cargas: {str(e)}")
        
        return resultado

    def suggest_operator_assignments(self, programa: ProgramaProduccion) -> List[Dict]:
        """
        Sugiere asignaciones óptimas de operadores
        """
        sugerencias = []
        
        try:
            # Obtener tareas sin operador asignado
            tareas_sin_operador = TareaFragmentada.objects.filter(
                programa=programa,
                operador__isnull=True,
                estado__in=['PENDIENTE', 'EN_PROCESO']
            )
            
            for tarea in tareas_sin_operador:
                # Buscar operadores calificados
                operadores_calificados = self._find_qualified_operators(tarea)
                
                if operadores_calificados:
                    mejor_operador = self._select_best_operator(tarea, operadores_calificados)
                    
                    sugerencias.append({
                        'tarea_id': tarea.id,
                        'operador_sugerido': mejor_operador.id,
                        'operador_nombre': mejor_operador.nombre,
                        'score_compatibilidad': self._calculate_operator_score(tarea, mejor_operador),
                        'disponibilidad': self._check_operator_availability(mejor_operador, tarea.fecha)
                    })
            
        except Exception as e:
            self.logger.error(f"Error sugiriendo operadores: {str(e)}")
        
        return sugerencias
    
    def _find_qualified_operators(self, tarea: TareaFragmentada) -> List[Operador]:
        """
        Encuentra operadores calificados para una tarea específica
        """
        try:
            maquina = tarea.tarea_original.maquina
            
            # Buscar operadores con asignaciones a esta máquina
            asignaciones = AsignacionOperador.objects.filter(
                maquina=maquina,
                activo=True
            ).select_related('operador')
            
            return [asignacion.operador for asignacion in asignaciones]
            
        except Exception:
            return []
    
    def _select_best_operator(self, tarea: TareaFragmentada, operadores: List[Operador]) -> Operador:
        """
        Selecciona el mejor operador para una tarea
        """
        mejor_operador = None
        mejor_score = -1
        
        for operador in operadores:
            score = self._calculate_operator_score(tarea, operador)
            if score > mejor_score:
                mejor_score = score
                mejor_operador = operador
        
        return mejor_operador or operadores[0]
    
    def _calculate_operator_score(self, tarea: TareaFragmentada, operador: Operador) -> float:
        """
        Calcula un score para un operador considerando múltiples factores
        """
        score = 0.0
        
        try:
            # Score por experiencia en la máquina
            asignacion = AsignacionOperador.objects.filter(
                operador=operador,
                maquina=tarea.tarea_original.maquina,
                activo=True
            ).first()
            
            if asignacion:
                score += 50.0  # Base score por estar asignado
                
                # Bonus por nivel de experiencia si existe
                if hasattr(asignacion, 'nivel_experiencia'):
                    score += asignacion.nivel_experiencia * 10
            
            # Score por disponibilidad
            disponibilidad = self._check_operator_availability(operador, tarea.fecha)
            score += disponibilidad * 30
            
            # Score por carga actual (preferir operadores menos ocupados)
            carga_actual = self._get_operator_current_load(operador, tarea.fecha)
            score += (1.0 - min(carga_actual, 1.0)) * 20
            
        except Exception as e:
            self.logger.warning(f"Error calculando score operador: {str(e)}")
        
        return score
    
    def _check_operator_availability(self, operador: Operador, fecha) -> float:
        """
        Verifica la disponibilidad de un operador
        """
        # Por ahora retornamos 1.0, pero aquí se podría integrar
        # con un sistema de horarios/turnos del operador
        return 1.0
    
    def _get_operator_current_load(self, operador: Operador, fecha) -> float:
        """
        Obtiene la carga actual de un operador
        """
        try:
            tareas_asignadas = TareaFragmentada.objects.filter(
                operador=operador,
                fecha=fecha,
                estado__in=['PENDIENTE', 'EN_PROCESO']
            ).count()
            
            # Asumimos que un operador puede manejar máximo 3 tareas por día
            return min(tareas_asignadas / 3.0, 1.0)
            
        except Exception:
            return 0.0 