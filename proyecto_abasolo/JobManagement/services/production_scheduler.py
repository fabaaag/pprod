from datetime import datetime, timedelta, date, time
import traceback
from .time_calculations import TimeCalculator
from ..models import TareaFragmentada, ProgramaOrdenTrabajo, Maquina, ItemRuta, ReporteDiarioPrograma, EjecucionTarea, OrdenTrabajo
from Operator.models import AsignacionOperador
from .machine_availability import MachineAvailabilityService
from .logging_utils import setup_logging
from ..utils import log_scheduler_operation, log_machine_availability, log_timeline_update, DecimalEncoder
import logging
import json
from django.db import transaction



class ProcessNode:
    def __init__(self, proceso_id, proceso_data, fecha_inicio, fecha_fin, ot_id, ot_data=None):
        self.proceso_id = proceso_id
        self.proceso_data = proceso_data
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.ot_id = ot_id
        self.ot_data = ot_data or {}  # ✅ AÑADIDO: Información de la OT
        self.intervals = []
        self.prioridad = 0
        self.maquina_id = proceso_data.get('maquina_id')
        # ✅ CORRECCIÓN: Inicializar siguiente_proceso
        self.siguiente_proceso = None
        
    def actualizar_fechas(self, nueva_fecha_inicio):
        """Actualiza las fechas del proceso y sus intervalos"""
        try:
            # Asegurarnos que la nueva fecha sea un día laboral
            if not TimeCalculator.is_working_day(nueva_fecha_inicio.date()):
                nueva_fecha_inicio = datetime.combine(
                    TimeCalculator.get_next_working_day(nueva_fecha_inicio.date()),
                    TimeCalculator.WORKDAY_START
                )
            
            # Si la hora está fuera del horario laboral, ajustar al inicio del siguiente día
            if nueva_fecha_inicio.time() < TimeCalculator.WORKDAY_START:
                nueva_fecha_inicio = datetime.combine(nueva_fecha_inicio.date(), TimeCalculator.WORKDAY_START)
            elif nueva_fecha_inicio.time() > TimeCalculator.WORKDAY_END:
                siguiente_dia = TimeCalculator.get_next_working_day(nueva_fecha_inicio.date())
                nueva_fecha_inicio = datetime.combine(siguiente_dia, TimeCalculator.WORKDAY_START)

            # Recalcular los intervalos usando TimeCalculator
            calculo_tiempo = TimeCalculator().calculate_working_days(
                nueva_fecha_inicio,
                float(self.proceso_data['cantidad']),
                float(self.proceso_data['estandar'])
            )
            
            if 'error' not in calculo_tiempo:
                self.fecha_inicio = nueva_fecha_inicio
                self.fecha_fin = calculo_tiempo['next_available_time']
                self.intervals = calculo_tiempo['intervals']
        except Exception as e:
            # ✅ LOG DE ERROR PARA DEBUGGING
            print(f"[ProcessNode] Error en actualizar_fechas: {str(e)}")
            import traceback
            traceback.print_exc()

    def propagar_ajuste(self, tiempo_setup=timedelta(minutes=30), procesos_por_maquina=None):
        """Propaga el ajuste a los procesos siguientes considerando tanto máquinas como dependencias"""
        try:
            # Primero, ajustar procesos de la misma máquina
            if procesos_por_maquina and self.maquina_id:
                procesos_misma_maquina = procesos_por_maquina.get(self.maquina_id, [])
                if self in procesos_misma_maquina:  # ✅ VERIFICAR QUE EL PROCESO ESTÉ EN LA LISTA
                    procesos_misma_maquina.sort(key=lambda x: x.prioridad)
                    
                    mi_indice = procesos_misma_maquina.index(self)
                    fecha_maquina_disponible = self.fecha_fin + tiempo_setup
                    
                    # Ajustar procesos posteriores de la misma máquina
                    for proceso in procesos_misma_maquina[mi_indice + 1:]:
                        if proceso.fecha_inicio < fecha_maquina_disponible:
                            proceso.actualizar_fechas(fecha_maquina_disponible)
                            proceso.propagar_ajuste(tiempo_setup, procesos_por_maquina)
                        fecha_maquina_disponible = proceso.fecha_fin + tiempo_setup

            # Luego, propagar a los procesos siguientes de la misma OT
            if hasattr(self, 'siguiente_proceso') and self.siguiente_proceso is not None:
                siguiente_proceso = self.siguiente_proceso
                while siguiente_proceso:
                    nueva_fecha_inicio = max(
                        self.fecha_fin + tiempo_setup,
                        siguiente_proceso.fecha_inicio
                    )
                    
                    if nueva_fecha_inicio > siguiente_proceso.fecha_inicio:
                        siguiente_proceso.actualizar_fechas(nueva_fecha_inicio)
                        # Propagar también a los procesos que usan la misma máquina
                        siguiente_proceso.propagar_ajuste(tiempo_setup, procesos_por_maquina)
                    
                    siguiente_proceso = siguiente_proceso.siguiente_proceso
        except Exception as e:
            # ✅ LOG DE ERROR PARA DEBUGGING
            print(f"[ProcessNode] Error en propagar_ajuste: {str(e)}")
            import traceback
            traceback.print_exc()

    def agregar_intervalo(self, interval_data):
        """Agrega un intervalo de tiempo al proceso"""
        self.intervals.append(interval_data)

class ProductionScheduler:
    def __init__(self, time_calculator):
        self.time_calculator = time_calculator if time_calculator else TimeCalculator()
        self.machine_availability = MachineAvailabilityService()
        # Configurar logger
        loggers = setup_logging()
        self.scheduler_logger = logging.getLogger('scheduler')
        self.timeline_logger = logging.getLogger('timeline')


    
        
    def log_scheduler_operation(self, operacion, detalles):
        """Método helper para logging de operaciones del scheduler"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operacion': operacion,
            'detalles': detalles
        }
        self.scheduler_logger.info(f"[SCHEDULER] {json.dumps(log_entry, cls=DecimalEncoder)}")

    def generate_timeline_data(self, programa, ordenes_trabajo, fecha_referencia=None):
        """
        Genera datos del timeline considerando una fecha de referencia opcional
        """
        log_timeline_update(
            self.timeline_logger,
            programa.id,
            "GENERAR_TIMELINE",
            {
                "ordenes": len(ordenes_trabajo),
                "fecha_inicio": programa.fecha_inicio.strftime("%Y-%m-%d"),
                "fecha_fin": programa.fecha_fin.strftime("%Y-%m-%d") if programa.fecha_fin else "No definida"
            }
        )
        try:
            # Eliminar prints existentes y reemplazar con logs específicos
            if fecha_referencia:
                # Obtener el estado de las tareas hasta esa fecha
                tareas = TareaFragmentada.objects.filter(
                    programa=programa,
                    fecha__lte=fecha_referencia
                )
            else:
                # Obtener todas las tareas actuales
                tareas = TareaFragmentada.objects.filter(
                    programa=programa
                )

            # Log del inicio de generación
            self.machine_availability.logger.info(f"[Timeline] Iniciando generación para programa {programa.id}")
            if fecha_referencia:
                self.machine_availability.logger.info(f"[Timeline] Fecha referencia: {fecha_referencia}")
            
            # Generar timeline base
            self.machine_availability.logger.info("[Timeline] Generando timeline base")
            timeline_data = self._generate_base_timeline(programa, ordenes_trabajo)
            
            # Log de estadísticas básicas
            self.machine_availability.logger.info(f"[Timeline] Timeline base generado: {len(timeline_data['groups'])} grupos, {len(timeline_data['items'])} items")
            
            # Agregar tareas fragmentadas
            self.machine_availability.logger.info("[Timeline] Agregando tareas fragmentadas")
            tareas_antes = len(timeline_data['items'])
            self._add_fragmented_tasks(timeline_data, programa)
            tareas_despues = len(timeline_data['items'])
            
            self.machine_availability.logger.info(f"[Timeline] Tareas fragmentadas agregadas: {tareas_despues - tareas_antes} nuevas tareas")
            
            log_timeline_update(
                self.timeline_logger,
                programa.id,
                "fin_generacion",
                "Timeline generado exitosamente"
            )
            return timeline_data
            
        except Exception as e:
            self.machine_availability.logger.error(f"[Timeline] Error en generate_timeline_data: {str(e)}")
            import traceback
            self.machine_availability.logger.error(f"[Timeline] Stack trace: {traceback.format_exc()}")
            log_timeline_update(
                self.timeline_logger,
                programa.id,
                "error_generacion",
                f"Error: {str(e)}"
            )
            return {"groups": [], "items": []}

    def _generate_base_timeline(self, programa, ordenes_trabajo):
        """
        Genera la línea de tiempo base para la planificación, respetando secuencias de procesos,
        horarios laborales y disponibilidad de máquinas.
        """
        self.machine_availability.logger.info(f"[Timeline] Iniciando generación base para {len(ordenes_trabajo)} órdenes")
        
        groups = []
        all_items = []
        procesos_por_maquina = {}
        nodos_procesos = {}

        # Primera pasada: crear todos los grupos (OTs) y sus procesos
        for ot_data in ordenes_trabajo:
            try:
                # Obtener información básica de la OT
                if isinstance(ot_data, dict):
                    ot_id = ot_data['orden_trabajo']
                    ot_codigo = ot_data['orden_trabajo_codigo_ot']
                    ot_descripcion = ot_data['orden_trabajo_descripcion_producto_ot']
                    procesos = ot_data.get('procesos', [])
                else:
                    ot_id = ot_data.orden_trabajo.id
                    ot_codigo = ot_data.orden_trabajo.codigo_ot
                    ot_descripcion = ot_data.orden_trabajo.descripcion_producto_ot
                    procesos = ot_data.orden_trabajo.ruta_ot.items.filter(estado_proceso__in=['PENDIENTE', 'EN_PROCESO']).order_by('item')

                # Crear grupo para la OT
                group = {
                    "id": f"ot_{ot_id}",
                    "orden_trabajo_codigo_ot": ot_codigo,
                    "descripcion": ot_descripcion,
                    "procesos": []  # Este array contendrá TODOS los procesos
                }
                
                # ✅ CREAR DICCIONARIO CON INFORMACIÓN COMPLETA DE LA OT
                ot_info = {
                    'orden_trabajo_codigo_ot': ot_codigo,
                    'orden_trabajo_descripcion_producto_ot': ot_descripcion,
                    'orden_trabajo_fecha_termino': 'N/A'  # Por ahora lo dejamos como N/A, se puede mejorar después
                }
                
                # Fecha inicial para los procesos de esta OT
                fecha_inicio_ot = datetime.combine(programa.fecha_inicio, self.time_calculator.WORKDAY_START)
                
                # Ordenar procesos por número de item para asegurar la secuencia correcta
                if isinstance(procesos, list):
                    procesos_ordenados = sorted(procesos, key=lambda p: p['item'] if isinstance(p, dict) else p.item)
                else:
                    procesos_ordenados = sorted(list(procesos), key=lambda p: p.item)
                
                # Referencia al nodo de proceso anterior para mantener la cadena de dependencia
                nodo_anterior = None
                
                # Procesar cada proceso de la OT
                for proceso in procesos_ordenados:
                    # Extraer información del proceso según su tipo
                    if isinstance(proceso, dict):
                        proceso_id = f"proc_{proceso['id']}"
                        descripcion = proceso['descripcion']
                        item_num = proceso['item']
                        cantidad_total = float(proceso.get('cantidad', 0))
                        cantidad_terminada = float(proceso.get('cantidad_terminada', 0))
                        cantidad = max(0, cantidad_total - cantidad_terminada)
                        estandar = float(proceso.get('estandar', 0))
                        maquina_id = proceso.get('maquina_id')
                        maquina_desc = proceso.get('maquina_descripcion', 'No asignada')
                        operador_nombre = proceso.get('operador_nombre', 'No asignado')
                        operador_id = proceso.get('operador_id')
                    else:
                        proceso_id = f"proc_{proceso.id}"
                        descripcion = proceso.proceso.descripcion if proceso.proceso else 'Sin descripción'
                        item_num = proceso.item
                        cantidad_total = float(proceso.cantidad_pedido)
                        cantidad_terminada = float(getattr(proceso, 'cantidad_terminado_proceso', 0))
                        cantidad = max(0, cantidad_total - cantidad_terminada)
                        estandar = float(proceso.estandar)
                        maquina_id = proceso.maquina.id if proceso.maquina else None
                        maquina_desc = proceso.maquina.descripcion if proceso.maquina else 'No asignada'
                        operador_nombre = proceso.operador.nombre if hasattr(proceso, 'operador') and proceso.operador else 'No asignado'
                        operador_id = proceso.operador.id if hasattr(proceso, 'operador') and proceso.operador else None
                
                    # Agregar proceso al grupo (TODOS los procesos)
                    group['procesos'].append({
                        "id": proceso_id,
                        "descripcion": descripcion,
                        "item": item_num
                    })
                    
                    # ✅ LOG DE DEPURACIÓN PARA ENTENDER POR QUÉ SE OMITEN PROCESOS
                    self.machine_availability.logger.info(
                        f"[Timeline] Proceso {proceso_id}: "
                        f"cantidad_total={cantidad_total}, "
                        f"cantidad_terminada={cantidad_terminada}, "
                        f"cantidad={cantidad}, "
                        f"estandar={estandar}"
                    )
                    
                    # ✅ TEMPORAL: INCLUIR TODOS LOS PROCESOS PARA DEBUGGING
                    # if cantidad <= 0:
                    #     self.machine_availability.logger.info(f"[Timeline] Proceso {proceso_id} completado o sin unidades restantes, omitiendo de planificación")
                    #     continue
                    
                    # Crear datos del proceso para el nodo
                    proceso_data = {
                        'id': proceso.id if not isinstance(proceso, dict) else proceso['id'],
                        'item': item_num,
                        'descripcion': descripcion,
                        'codigo_proceso': proceso.proceso.codigo_proceso if not isinstance(proceso, dict) and proceso.proceso else proceso.get('codigo_proceso', ''),
                        'maquina_id': maquina_id,
                        'maquina_codigo': proceso.maquina.codigo_maquina if not isinstance(proceso, dict) and proceso.maquina else proceso.get('maquina_codigo', ''),
                        'cantidad': float(cantidad_total - cantidad_terminada),
                        'cantidad_total': cantidad_total,
                        'cantidad_terminada': cantidad_terminada,
                        'estandar': estandar,
                        'maquina_descripcion': maquina_desc,
                        'operador_nombre': operador_nombre,
                        'operador_id': operador_id,
                        'estado_proceso': proceso.estado_proceso if not isinstance(proceso, dict) else proceso.get('estado_proceso', 'PENDIENTE'),
                        'porcentaje_completado': proceso.porcentaje_completado if not isinstance(proceso, dict) else proceso.get('porcentaje_completado', 0),
                        'fecha_inicio_real': proceso.fecha_inicio_real if not isinstance(proceso, dict) else proceso.get('fecha_inicio_real'),
                        'fecha_fin_real': proceso.fecha_fin_real if not isinstance(proceso, dict) else proceso.get('fecha_fin_real'),
                        'observaciones': proceso.observaciones if not isinstance(proceso, dict) else proceso.get('observaciones', '')
                    }
                
                    # Calcular fecha de inicio para este proceso, considerando dependencias
                    fecha_inicio_proceso = fecha_inicio_ot
                    if nodo_anterior:
                        # Si hay proceso anterior, este debe comenzar después
                        fecha_inicio_proceso = nodo_anterior.fecha_fin + timedelta(minutes=30)
                    
                    # Asegurar que la fecha sea un día laboral y esté dentro del horario
                    fecha_inicio_proceso = self._ajustar_fecha_horario_laboral(fecha_inicio_proceso)
                    
                    # Calcular fechas y duración del proceso
                    calculo_tiempo = self.time_calculator.calculate_working_days(
                        fecha_inicio_proceso,
                        cantidad,
                        estandar
                    )
                    
                    # ✅ LOG DE DEPURACIÓN PARA EL CÁLCULO DE TIEMPO
                    self.machine_availability.logger.info(
                        f"[Timeline] Cálculo tiempo para {proceso_id}: "
                        f"fecha_inicio={fecha_inicio_proceso}, "
                        f"cantidad={cantidad}, "
                        f"estandar={estandar}, "
                        f"resultado={calculo_tiempo}"
                    )
                    
                    # Crear nodo con la información calculada
                    nodo = ProcessNode(
                        proceso_id=proceso_id,
                        proceso_data=proceso_data,
                        fecha_inicio=calculo_tiempo['intervals'][0]['fecha_inicio'] if 'error' not in calculo_tiempo and calculo_tiempo['intervals'] else fecha_inicio_proceso,
                        fecha_fin=calculo_tiempo['next_available_time'] if 'error' not in calculo_tiempo else fecha_inicio_proceso + timedelta(hours=1),
                        ot_id=ot_id,
                        ot_data=ot_info  
                    )
                    
                    # Establecer dependencia con proceso anterior
                    if nodo_anterior:
                        nodo_anterior.siguiente_proceso = nodo
                    
                    # Guardar el nodo actual para referencias
                    nodos_procesos[proceso_id] = nodo
                    nodo_anterior = nodo
                    
                    # Agrupar por máquina para detectar conflictos
                    if maquina_id:
                        if maquina_id not in procesos_por_maquina:
                            procesos_por_maquina[maquina_id] = []
                        procesos_por_maquina[maquina_id].append(nodo)

                    # Generar intervalos de tiempo para este proceso
                    if 'error' not in calculo_tiempo:
                        # ✅ NUEVA LÓGICA: Crear bloques por día en lugar de por hora
                        bloques_por_dia = self._crear_bloques_por_dia(calculo_tiempo['intervals'])
                        
                        # ✅ LOG DE DEPURACIÓN PARA BLOQUES
                        self.machine_availability.logger.info(
                            f"[Timeline] Bloques creados para {proceso_id}: "
                            f"cantidad_bloques={len(bloques_por_dia)}"
                        )
                        
                        for bloque in bloques_por_dia:
                            nodo.agregar_intervalo(bloque)
                            
                            # Crear item para la visualización
                            item = {
                                "id": f"item_{proceso_data['id']}_{len(all_items)}",
                                "ot_id": f"ot_{ot_id}",
                                "proceso_id": proceso_id,
                                "name": f"{proceso_data['descripcion']} - {bloque['unidades']:.0f} de {cantidad} restantes ({cantidad_total} total)",
                                "start_time": bloque['fecha_inicio'].strftime('%Y-%m-%d %H:%M:%S'),
                                "end_time": bloque['fecha_fin'].strftime('%Y-%m-%d %H:%M:%S'),
                                "cantidad_total": float(proceso_data['cantidad_total']),
                                "cantidad_restante": float(proceso_data['cantidad']),
                                "cantidad_terminada": float(proceso_data['cantidad_terminada']),
                                "cantidad_intervalo": float(bloque['unidades']),
                                "unidades_restantes": float(bloque.get('unidades_restantes', 0)),
                                "estandar": float(proceso_data['estandar']),
                                "maquina": proceso_data['maquina_descripcion'],
                                "operador_nombre": proceso_data['operador_nombre'],
                                "asignado": proceso_data['operador_id'] is not None,
                                "tiene_avance_previo": cantidad_terminada > 0,
                                "ot_codigo": ot_info.get('orden_trabajo_codigo_ot', 'N/A'),
                                "ot_descripcion": ot_info.get('orden_trabajo_descripcion_producto_ot', 'N/A'),
                                "ot_fecha_termino": ot_info.get('orden_trabajo_fecha_termino', 'N/A'),
                                "proceso_codigo": proceso_data.get('codigo_proceso', ''),
                                "proceso_descripcion": proceso_data.get('descripcion', ''),
                                "maquina_codigo": proceso_data.get('maquina_codigo', ''),
                                "maquina_descripcion": proceso_data.get('maquina_descripcion', ''),
                                "operador_id": proceso_data.get('operador_id'),
                                "es_bloque_unificado": bloque.get('es_bloque_unificado', False),
                                "periodo": bloque.get('periodo', None),
                                "estado": proceso_data.get('estado_proceso', 'PENDIENTE'),
                                "porcentaje_avance": proceso_data.get('porcentaje_completado', 0),
                                "fecha_inicio_real": proceso_data.get('fecha_inicio_real'),
                                "fecha_fin_real": proceso_data.get('fecha_fin_real'),
                                "observaciones": proceso_data.get('observaciones', '')
                            }
                            
                            # ✅ LOG DE DEPURACIÓN
                            self.machine_availability.logger.info(
                                f"[Timeline] Item creado: OT={item['ot_codigo']}, "
                                f"Proceso={item['proceso_codigo']}, "
                                f"Descripción={item['proceso_descripcion']}, "
                                f"ID={item['id']}"
                            )
                            
                            all_items.append(item)
                    else:
                        # ✅ LOG DE ERROR EN CÁLCULO DE TIEMPO
                        self.machine_availability.logger.error(
                            f"[Timeline] Error en cálculo de tiempo para {proceso_id}: {calculo_tiempo['error']}"
                        )
                
                # Agregar el grupo una vez que tenga todos sus procesos
                groups.append(group)
            except Exception as e:
                self.machine_availability.logger.error(f"[Timeline] Error procesando OT {ot_id}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        # Segunda pasada: resolver conflictos de máquina y propagar ajustes
        for maquina_id, procesos in procesos_por_maquina.items():
            # Ordenar por prioridad y fecha de inicio
            procesos.sort(key=lambda x: (x.prioridad, x.fecha_inicio))
            
            # Verificar y resolver conflictos
            fecha_maquina_disponible = None
            
            for i, proceso in enumerate(procesos):
                if i == 0:
                    # El primer proceso establece la fecha de disponibilidad inicial
                    fecha_maquina_disponible = proceso.fecha_fin + timedelta(minutes=30)
                    continue
                
                # Si hay conflicto (este proceso comienza antes que el anterior termine + setup)
                if proceso.fecha_inicio < fecha_maquina_disponible:
                    # Ajustar este proceso para comenzar después
                    proceso.actualizar_fechas(fecha_maquina_disponible)
                    
                    # Propagar el ajuste a procesos dependientes
                    proceso.propagar_ajuste(
                        tiempo_setup=timedelta(minutes=30),
                        procesos_por_maquina=procesos_por_maquina
                    )
                
                # Actualizar la fecha de disponibilidad de la máquina
                fecha_maquina_disponible = proceso.fecha_fin + timedelta(minutes=30)
        
        # Actualizar los items con las nuevas fechas después de los ajustes
        all_items.clear()
        for nodo in nodos_procesos.values():
            for interval in nodo.intervals:
                item = {
                    "id": f"item_{nodo.proceso_data['id']}_{len(all_items)}",
                    "ot_id": f"ot_{nodo.ot_id}",
                    "proceso_id": nodo.proceso_id,
                    "name": f"{nodo.proceso_data['descripcion']} - {interval['unidades']:.0f} de {nodo.proceso_data['cantidad']:.0f} restantes ({nodo.proceso_data['cantidad_total']:.0f} total)",
                    "start_time": interval['fecha_inicio'].strftime('%Y-%m-%d %H:%M:%S'),
                    "end_time": interval['fecha_fin'].strftime('%Y-%m-%d %H:%M:%S'),
                    "cantidad_total": float(nodo.proceso_data['cantidad_total']),
                    "cantidad_restante": float(nodo.proceso_data['cantidad']),
                    "cantidad_terminada": float(nodo.proceso_data['cantidad_terminada']),
                    "cantidad_intervalo": float(interval['unidades']),
                    "unidades_restantes": float(interval.get('unidades_restantes', 0)),
                    "estandar": float(nodo.proceso_data['estandar']),
                    "maquina": nodo.proceso_data.get('maquina_descripcion', 'No asignada'),
                    "operador_nombre": nodo.proceso_data.get('operador_nombre', 'No asignado'),
                    "asignado": nodo.proceso_data.get('operador_id') is not None,
                    "tiene_avance_previo": nodo.proceso_data['cantidad_terminada'] > 0,
                    # ✅ INFORMACIÓN ADICIONAL DE LA OT
                    "ot_codigo": nodo.ot_data.get('orden_trabajo_codigo_ot', 'N/A') if hasattr(nodo, 'ot_data') else 'N/A',
                    "ot_descripcion": nodo.ot_data.get('orden_trabajo_descripcion_producto_ot', 'N/A') if hasattr(nodo, 'ot_data') else 'N/A',
                    "ot_fecha_termino": nodo.ot_data.get('orden_trabajo_fecha_termino', 'N/A') if hasattr(nodo, 'ot_data') else 'N/A',
                    # ✅ INFORMACIÓN ADICIONAL DEL PROCESO
                    "proceso_codigo": nodo.proceso_data.get('codigo_proceso', ''),
                    "proceso_descripcion": nodo.proceso_data.get('descripcion', ''),
                    "maquina_codigo": nodo.proceso_data.get('maquina_codigo', ''),
                    "maquina_descripcion": nodo.proceso_data.get('maquina_descripcion', ''),
                    "operador_id": nodo.proceso_data.get('operador_id'),
                    # ✅ ESTADO Y PROGRESO
                    "estado": nodo.proceso_data.get('estado_proceso', 'PENDIENTE'),
                    "porcentaje_avance": nodo.proceso_data.get('porcentaje_completado', 0),
                    "fecha_inicio_real": nodo.proceso_data.get('fecha_inicio_real'),
                    "fecha_fin_real": nodo.proceso_data.get('fecha_fin_real'),
                    "observaciones": nodo.proceso_data.get('observaciones', '')
                }
                all_items.append(item)

        self.machine_availability.logger.info(
            f"[Timeline] Generación base completada: "
            f"{len(groups)} grupos, {len(all_items)} items totales"
        )

        return {
            "groups": groups,
            "items": all_items
        }

    def _ajustar_fecha_horario_laboral(self, fecha):
        """
        Ajusta una fecha para asegurar que esté dentro del horario laboral
        """
        # Convertir a datetime si es date
        if isinstance(fecha, date) and not isinstance(fecha, datetime):
            fecha = datetime.combine(fecha, self.time_calculator.WORKDAY_START)
        
        # Si no es día laboral, mover al siguiente
        if not self.time_calculator.is_working_day(fecha.date()):
            fecha = datetime.combine(
                self.time_calculator.get_next_working_day(fecha.date()),
                self.time_calculator.WORKDAY_START
            )
            return fecha
        
        # Si está antes del inicio de jornada (8:00), mover al inicio
        if fecha.time() < self.time_calculator.WORKDAY_START:
            fecha = datetime.combine(fecha.date(), self.time_calculator.WORKDAY_START)
            return fecha
        
        # Si está después del fin de jornada (17:30 o 16:30 viernes), mover al inicio del siguiente día laboral
        workday_end = self.time_calculator.get_workday_end(fecha.date())
        if fecha.time() > workday_end:
            fecha = datetime.combine(
                self.time_calculator.get_next_working_day(fecha.date()),
                self.time_calculator.WORKDAY_START
            )
            return fecha
        
        # Si está en horario de almuerzo (13:00-14:00), mover al final del almuerzo
        if self.time_calculator.BREAK_START <= fecha.time() < self.time_calculator.BREAK_END:
            fecha = datetime.combine(fecha.date(), self.time_calculator.BREAK_END)
        
        return fecha

    def _crear_bloques_por_dia(self, intervals):
        """
        ✅ NUEVO MÉTODO: Agrupa intervalos por día en bloques de mañana y tarde
        para mejorar la visualización en el timeline
        """
        if not intervals:
            return []
        
        bloques = []
        intervalos_por_dia = {}
        
        # Agrupar intervalos por día
        for intervalo in intervals:
            fecha = intervalo['fecha_inicio'].date()
            if fecha not in intervalos_por_dia:
                intervalos_por_dia[fecha] = []
            intervalos_por_dia[fecha].append(intervalo)
        
        # Crear bloques por día
        for fecha, intervalos_del_dia in intervalos_por_dia.items():
            # Ordenar intervalos por hora de inicio
            intervalos_del_dia.sort(key=lambda x: x['fecha_inicio'])
            
            # Separar en bloques de mañana y tarde
            bloques_mañana = []
            bloques_tarde = []
            
            for intervalo in intervalos_del_dia:
                hora_inicio = intervalo['fecha_inicio'].time()
                
                # Si es antes del almuerzo, va en mañana
                if hora_inicio < self.time_calculator.BREAK_START:
                    bloques_mañana.append(intervalo)
                # Si es después del almuerzo, va en tarde
                elif hora_inicio >= self.time_calculator.BREAK_END:
                    bloques_tarde.append(intervalo)
                # Si está en el almuerzo, asignar según la hora de fin
                else:
                    if intervalo['fecha_fin'].time() <= self.time_calculator.BREAK_START:
                        bloques_mañana.append(intervalo)
                    else:
                        bloques_tarde.append(intervalo)
            
            # Crear bloque de mañana
            if bloques_mañana:
                bloque_mañana = self._crear_bloque_unificado(bloques_mañana, "Mañana")
                bloques.append(bloque_mañana)
            
            # Crear bloque de tarde
            if bloques_tarde:
                bloque_tarde = self._crear_bloque_unificado(bloques_tarde, "Tarde")
                bloques.append(bloque_tarde)
        
        return bloques

    def _crear_bloque_unificado(self, intervalos, periodo):
        """
        ✅ NUEVO MÉTODO: Crea un bloque unificado a partir de varios intervalos
        """
        if not intervalos:
            return None
        
        # Ordenar por fecha de inicio
        intervalos.sort(key=lambda x: x['fecha_inicio'])
        
        # Tomar la primera fecha de inicio y la última fecha de fin
        fecha_inicio = intervalos[0]['fecha_inicio']
        fecha_fin = intervalos[-1]['fecha_fin']
        
        # Sumar todas las unidades
        unidades_totales = sum(intervalo['unidades'] for intervalo in intervalos)
        
        # Calcular unidades restantes
        unidades_restantes = sum(intervalo.get('unidades_restantes', 0) for intervalo in intervalos)
        
        return {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'unidades': unidades_totales,
            'unidades_restantes': unidades_restantes,
            'periodo': periodo,
            'es_bloque_unificado': True
        }

    def _add_fragmented_tasks(self, timeline_data, programa):
        """
        Añade todas las tareas fragmentadas al timeline, incluyendo tanto
        las continuaciones como las tareas completadas y en proceso.
        """
        self.machine_availability.logger.info(f"[Timeline] Buscando tareas fragmentadas para programa {programa.id}")
        
        # Obtener TODAS las tareas fragmentadas, no solo las continuaciones
        fragmentos = TareaFragmentada.objects.filter(
            programa=programa
        ).select_related(
            'tarea_original',
            'tarea_original__proceso',
            'tarea_original__maquina',
            'tarea_original__ruta__orden_trabajo',
            'operador'
        )

        self.machine_availability.logger.info(f"[Timeline] Encontradas {fragmentos.count()} tareas fragmentadas totales")
        
        # Identificar grupos de tareas por ítem ruta
        grupos_fragmentos = {}
        for fragmento in fragmentos:
            if not fragmento.tarea_original:
                self.machine_availability.logger.warning(f"[Timeline] Fragmento {fragmento.id} sin tarea original")
                continue

            key = fragmento.tarea_original.id
            if key not in grupos_fragmentos:
                grupos_fragmentos[key] = []
            grupos_fragmentos[key].append(fragmento)
        
        # Procesar cada grupo de fragmentos
        fragmentos_agregados = 0
        for item_ruta_id, grupo_fragmentos in grupos_fragmentos.items():
            # Ordenar fragmentos por fecha y nivel de fragmentación
            grupo_fragmentos.sort(key=lambda x: (x.fecha, x.nivel_fragmentacion))
            
            # Tomar el primer fragmento como referencia para obtener el item_ruta
            item_ruta = grupo_fragmentos[0].tarea_original
            ot_id = item_ruta.ruta.orden_trabajo.id
            
            # Encontrar el grupo correspondiente
            grupo = next(
                (g for g in timeline_data["groups"] if g["id"] == f"ot_{ot_id}"),
                None
            )

            if not grupo:
                # Si no existe el grupo, intentar crearlo
                self.machine_availability.logger.info(f"[Timeline] Creando grupo para OT {ot_id}")
                ot = item_ruta.ruta.orden_trabajo
                nuevo_grupo = {
                    "id": f"ot_{ot_id}",
                    "orden_trabajo_codigo_ot": ot.codigo_ot,
                    "descripcion": ot.descripcion_producto_ot,
                    "procesos": []
                }
                timeline_data["groups"].append(nuevo_grupo)
                grupo = nuevo_grupo
                
                # También asegurar que existe el subgrupo del proceso
                proceso_id = f"proc_{item_ruta.id}"
                if not any(p["id"] == proceso_id for p in grupo.get("procesos", [])):
                    grupo["procesos"] = grupo.get("procesos", []) + [{
                        "id": proceso_id,
                        "descripcion": item_ruta.proceso.descripcion if item_ruta.proceso else "Sin descripción",
                        "item": item_ruta.item
                    }]
                
            # Agregar cada fragmento al timeline
            for fragmento in grupo_fragmentos:
                # Determinar fechas planificadas precisas o usar valores predeterminados
                fecha_inicio = fragmento.fecha_planificada_inicio
                if not fecha_inicio:
                    fecha_inicio = datetime.combine(fragmento.fecha, self.time_calculator.WORKDAY_START)
                
                fecha_fin = fragmento.fecha_planificada_fin
                if not fecha_fin:
                    fecha_fin = datetime.combine(fragmento.fecha, self.time_calculator.WORKDAY_END)
                
                # Calcular duraciones precisas si tenemos estándar y cantidad
                if fragmento.tarea_original.estandar > 0 and fragmento.cantidad_asignada > 0:
                    # Usar el TimeCalculator para obtener fechas precisas
                    calculo = self.time_calculator.calculate_working_days(
                        fecha_inicio,
                        float(fragmento.cantidad_asignada),
                        float(fragmento.tarea_original.estandar)
                    )
                    
                    if 'error' not in calculo and calculo['intervals']:
                        # Usar la primera y última fecha del intervalo calculado
                        fecha_inicio = calculo['intervals'][0]['fecha_inicio']
                        fecha_fin = calculo['next_available_time']
                
                # Determinar si es continuación o tarea original
                es_continuacion = fragmento.es_continuacion
                titulo = item_ruta.proceso.descripcion
                if es_continuacion:
                    titulo += f" (Continuación {fragmento.nivel_fragmentacion})"
                
                # Calcular porcentaje de avance
                porcentaje_avance = 0
                if fragmento.cantidad_total_dia > 0:
                    porcentaje_avance = (fragmento.cantidad_completada / fragmento.cantidad_total_dia) * 100
                
                # Construir el item del timeline con todos los datos relevantes
                item = {
                    "id": f"frag_{fragmento.id}",
                    "ot_id": f"ot_{ot_id}",
                    "proceso_id": f"proc_{item_ruta.id}",
                    "name": f"{titulo} - {fragmento.cantidad_asignada} unidades",
                    "start_time": fecha_inicio.strftime('%Y-%m-%d %H:%M:%S'),
                    "end_time": fecha_fin.strftime('%Y-%m-%d %H:%M:%S'),
                    "cantidad_total": float(fragmento.cantidad_asignada),
                    "cantidad_intervalo": float(fragmento.cantidad_asignada),
                    "cantidad_completada": float(fragmento.cantidad_completada),
                    "porcentaje_avance": porcentaje_avance,
                    "unidades_restantes": float(fragmento.cantidad_total_dia - fragmento.cantidad_completada),
                    "estandar": float(item_ruta.estandar),
                    "maquina": item_ruta.maquina.descripcion if item_ruta.maquina else "Sin máquina",
                    "es_continuacion": es_continuacion,
                    "estado": fragmento.estado,
                    "nivel_fragmentacion": fragmento.nivel_fragmentacion,
                    "operador_nombre": fragmento.operador.nombre if fragmento.operador else "No asignado",
                    "operador_id": fragmento.operador.id if fragmento.operador else None,
                    # Añadir información visual según el estado
                    "style": self._get_item_style_by_estado(fragmento.estado, porcentaje_avance)
                }
                
                timeline_data["items"].append(item)
                fragmentos_agregados += 1
                
                self.machine_availability.logger.debug(
                    f"[Timeline] Agregado {('fragmento' if es_continuacion else 'tarea')} {fragmento.id} "
                    f"de OT {ot_id}: {titulo} - {fragmento.cantidad_asignada} unidades - "
                    f"Estado: {fragmento.estado}"
                )

        self.machine_availability.logger.info(f"[Timeline] Total items agregados: {fragmentos_agregados}")
        
        # Ordenar items del timeline por fecha para mejor visualización
        timeline_data["items"].sort(key=lambda x: x["start_time"])
        
        return fragmentos_agregados

    def _get_item_style_by_estado(self, estado, porcentaje_avance=0):
        """
        Devuelve el estilo visual según el estado de la tarea.
        Esto ayuda a diferenciar visualmente los estados en el frontend.
        """
        estilos_base = {
            'borderRadius': '4px',
            'padding': '2px 6px'
        }
        
        if estado == 'COMPLETADO':
            return {
                **estilos_base,
                'backgroundColor': '#4CAF50',  # Verde
                'color': 'white'
            }
        elif estado == 'EN_PROCESO':
            return {
                **estilos_base,
                'backgroundColor': '#2196F3',  # Azul
                'color': 'white',
                'backgroundImage': f'linear-gradient(90deg, rgba(33,150,243,1) {porcentaje_avance}%, rgba(33,150,243,0.5) {porcentaje_avance}%)'
            }
        elif estado == 'CONTINUADO':
            return {
                **estilos_base,
                'backgroundColor': '#FF9800',  # Naranja
                'color': 'white'
            }
        elif estado == 'DETENIDO':
            return {
                **estilos_base,
                'backgroundColor': '#F44336',  # Rojo
                'color': 'white'
            }
        else:  # PENDIENTE u otros estados
            return {
                **estilos_base,
                'backgroundColor': '#9E9E9E',  # Gris
                'color': 'white'
            }

    def calculate_program_end_date(self, programa, ordenes_trabajo=None):
        """Calcula la fecha de finalización del programa basada en la última tarea proyectada"""
        try:
            print(f"[ProductionScheduler] Iniciando cálculo de fecha fin para programa {programa.id}")
            
            if ordenes_trabajo is None:
                print("[ProductionScheduler] Obteniendo órdenes de trabajo del programa")
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
                                'prioridad': prog_ot.prioridad  # Importante: incluir la prioridad
                            }
                            ot_data['procesos'].append(proceso_data)
                    
                    ordenes_trabajo.append(ot_data)

            print("[ProductionScheduler] Generando timeline data")
            # Generar timeline data para obtener los nodos y sus intervalos ajustados
            timeline_data = self._generate_base_timeline(programa, ordenes_trabajo)
            
            # Si no hay items, usar la fecha de inicio
            if not timeline_data.get('items'):
                return programa.fecha_inicio

            # Encontrar la fecha más tardía entre todos los intervalos
            latest_date = programa.fecha_inicio
            if isinstance(latest_date, date):
                latest_date = datetime.combine(latest_date, self.time_calculator.WORKDAY_START)

            for item in timeline_data['items']:
                try:
                    end_time = datetime.strptime(item['end_time'], '%Y-%m-%d %H:%M:%S')
                    if end_time > latest_date:
                        latest_date = end_time
                except (KeyError, ValueError) as e:
                    continue

            # Asegurarnos que la fecha final sea un día laboral
            if not TimeCalculator.is_working_day(latest_date.date()):
                latest_date = datetime.combine(
                    TimeCalculator.get_next_working_day(latest_date.date()),
                    self.time_calculator.WORKDAY_END
                )
            elif latest_date.time() > TimeCalculator.WORKDAY_END:
                siguiente_dia = TimeCalculator.get_next_working_day(latest_date.date())
                latest_date = datetime.combine(siguiente_dia, TimeCalculator.WORKDAY_END)

            print(f"[ProductionScheduler] Fecha fin calculada: {latest_date.date()}")
            return latest_date.date()

        except Exception as e:
            print(f"[ProductionScheduler] Error calculando fecha fin: {str(e)}")
            return programa.fecha_inicio

    def _get_program_orders(self, programa):
        """Obtiene las órdenes de trabajo del programa"""
        return ProgramaOrdenTrabajo.objects.filter(
            programa=programa
        ).select_related(
            'orden_trabajo',
            'orden_trabajo__ruta_ot'
        ).prefetch_related(
            'orden_trabajo__ruta_ot__items',
            'orden_trabajo__ruta_ot__items__proceso',
            'orden_trabajo__ruta_ot__items__maquina'
        ).order_by('prioridad')

    def _process_order_group(self, ot_data, programa, operador_timeline):
        try:
            # Manejar tanto objetos ProgramaOrdenTrabajo como diccionarios
            if isinstance(ot_data, dict):
                ot_id = ot_data['orden_trabajo']
                ot_codigo = ot_data['orden_trabajo_codigo_ot']
                ot_descripcion = ot_data['orden_trabajo_descripcion_producto_ot']
                procesos = ot_data.get('procesos', [])
            else:
                # Es un objeto ProgramaOrdenTrabajo
                orden_trabajo = ot_data.orden_trabajo
                ot_id = orden_trabajo.id
                ot_codigo = orden_trabajo.codigo_ot
                ot_descripcion = orden_trabajo.descripcion_producto_ot
                procesos = orden_trabajo.ruta_ot.items.all().order_by('item')

            group = {
                "id": f"ot_{ot_id}",
                "orden_trabajo_codigo_ot": ot_codigo,
                "descripcion": ot_descripcion,
                "procesos": []
            }

            # Usar la fecha de inicio del programa como fecha base
            next_available_start = datetime.combine(programa.fecha_inicio, self.time_calculator.WORKDAY_START)

            procesos_data = self._process_order_processes(
                procesos,
                ot_id,
                programa,
                operador_timeline,
                next_available_start
            )

            group['procesos'] = procesos_data['procesos']
            return {
                'group': group,
                'items': procesos_data['items']
            }
        except Exception as e:
            print(f"Error procesando grupo de OT: {str(e)}")
            return None

    def _process_order_processes(self, procesos, ot_id, programa, operador_timeline, next_available_start):
        items = []
        procesos_list = []

        for proceso in procesos:
            if isinstance(proceso, dict):
                cantidad = float(proceso['cantidad'])
                estandar = float(proceso['estandar'])
            else:
                cantidad = float(proceso.cantidad_pedido)
                estandar = float(proceso.estandar)
            
            # Obtener datos del proceso (código existente)
            if isinstance(proceso, dict):
                proceso_id = f"proc_{proceso['id']}"
                descripcion = proceso['descripcion']
                item_num = proceso['item']
                maquina_id = proceso.get('maquina_id')
                maquina_desc = proceso.get('maquina_descripcion', 'No asignada')
                operador_nombre = proceso.get('operador_nombre', 'No asignado')
                operador_id = proceso.get('operador_id')
            else:
                proceso_id = f"proc_{proceso.id}"
                descripcion = proceso.proceso.descripcion
                item_num = proceso.item
                maquina = proceso.maquina
                prioridad = None

            procesos_list.append({
                "id": proceso_id,
                "descripcion": descripcion,
                "item": item_num
            })

            if not self._is_valid_process({'estandar': estandar, 'cantidad': cantidad}):
                continue

            # Verificar disponibilidad de máquina
            if maquina:
                verificacion = self.machine_availability.verificar_conflicto(
                    maquina,  # Ahora maquina es un objeto completo
                    next_available_start,
                    next_available_start + timedelta(hours=8),
                    prioridad
                )
                
                if verificacion['tiene_conflicto']:
                    next_available_start = verificacion['fecha_disponible']

            # Calcular fechas
            dates_data = self.time_calculator.calculate_working_days(
                next_available_start,
                cantidad,
                estandar
            )

            for idx, interval in enumerate(dates_data['intervals']):
                item = self._create_timeline_item(
                    proceso,
                    ot_id,
                    proceso_id,
                    interval,
                    idx,
                    asignacion
                )
                items.append(item)

                if asignacion:
                    operador_id = asignacion['operador_id'] if isinstance(asignacion, dict) else asignacion.operador.id
                    operador_timeline[operador_id] = interval['fecha_fin']

            next_available_start = dates_data['next_available_time']
        
        return {
            'procesos': procesos_list,
            'items': items
        }

    def _is_valid_process(self, proceso):
        """Valida si un proceso tiene datos válidos para ser procesado"""
        return (
            proceso.get('estandar', 0) > 0 and
            proceso.get('cantidad', 0) > 0
        )

    def _create_timeline_item(self, proceso, ot_id, proceso_id, interval, idx, asignacion=None):
        """Crea un item individual del timeline"""
        # Manejar tanto diccionarios como objetos ItemRuta
        if isinstance(proceso, dict):
            proceso_id_num = proceso['id']
            descripcion = proceso.get('descripcion', 'Proceso')
            cantidad = float(proceso.get('cantidad', 0))
            estandar = proceso.get('estandar', 0)
        else:
            proceso_id_num = proceso.id
            descripcion = proceso.proceso.descripcion if proceso.proceso else 'Proceso'
            cantidad = float(proceso.cantidad_pedido or 0)
            estandar = proceso.estandar

        item = {
            "id": f'item_{proceso_id_num}_{idx}',
            "ot_id": f"ot_{ot_id}",
            "proceso_id": proceso_id,
            "name": f"{descripcion} - {interval['unidades']:.0f} de {cantidad:.0f} unidades",
            "start_time": interval['fecha_inicio'].strftime('%Y-%m-%d %H:%M:%S'),
            "end_time": interval['fecha_fin'].strftime('%Y-%m-%d %H:%M:%S'),
            "cantidad_total": cantidad,
            "cantidad_intervalo": float(interval['unidades']),
            "unidades_restantes": float(interval['unidades_restantes']),
            "estandar": estandar
        }

        # Añadir información de asignación si existe
        if asignacion:
            if isinstance(asignacion, dict):
                item.update({
                    "asignacion_id": asignacion.get('id'),
                    "operador_id": asignacion.get('operador_id'),
                    "operador_nombre": asignacion.get('operador_nombre'),
                    "asignado": True
                })
            else:
                item.update({
                    "asignacion_id": asignacion.id,
                    "operador_id": asignacion.operador.id,
                    "operador_nombre": asignacion.operador.nombre,
                    "asignado": True
                })
        else:
            item.update({
                "asignacion_id": None,
                "operador_id": None,
                "operador_nombre": None,
                "asignado": False
            })
        
        return item

    def _find_latest_end_date(self, timeline_data):
        """Encuentra la fecha más tardía en el timeline"""
        latest_date = None
        
        if not timeline_data or not timeline_data.get('groups'):
            return None
        
        for group in timeline_data['groups']:
            for item in group['items']:
                try:
                    end_time = datetime.strptime(item['end_time'], '%Y-%m-%d %H:%M:%S')
                    if not latest_date or end_time > latest_date:
                        latest_date = end_time
                except (KeyError, ValueError) as e:
                    print(f"Error procesando fecha fin de item: {str(e)}")
                    continue

        return latest_date.date() if latest_date else None

    def recalculate_order_dates(self, programa_ot, fecha_inicio):
        """
        Recalcula las fechas para una orden específica y sus procesos
        """
        fecha_actual = fecha_inicio
        
        for item_ruta in programa_ot.orden_trabajo.ruta_ot.items.all().order_by('item'):
            if not item_ruta.maquina or not item_ruta.estandar:
                continue
            
            calculo_tiempo = self.time_calculator.calculate_working_days(
                fecha_actual,
                item_ruta.cantidad_pedido,
                item_ruta.estandar
            )
            
            if 'error' not in calculo_tiempo:
                fecha_actual = calculo_tiempo['next_available_time']
                
                # Actualizar asignación si existe
                asignacion = AsignacionOperador.objects.filter(
                    programa=programa_ot.programa,
                    item_ruta=item_ruta
                ).first()
                
                if asignacion:
                    asignacion.fecha_inicio = calculo_tiempo['intervals'][0]['fecha_inicio']
                    asignacion.fecha_fin = fecha_actual
                    asignacion.save()
        
        return fecha_actual
    
    def validar_proceso(self, proceso, ot_data):
        """
        Valida que un proceso tenga todos los datos necesarios y válidos.
        Args:
            proceso (dict): Diccionario con los datos del proceso
            ot_data (dict): Diccionario con los datos de la OT
        Returns:
            bool: True si el proceso es válido, False en caso contrario
        """
        try:
            print(f"\nValidando proceso: {proceso}")  # Debug
            
            # Validar existencia y tipo de datos
            campos_requeridos = ['id', 'estandar', 'cantidad', 'maquina_id', 'descripcion']
            for campo in campos_requeridos:
                if campo not in proceso:
                    print(f"Campo faltante: {campo}")  # Debug
                    raise ValueError(f"Falta el campo requerido: {campo}")
                
            # Convertir y validar valores numéricos
            try:
                estandar = float(proceso['estandar'])
                cantidad = float(proceso['cantidad'])
                print(f"Valores numéricos: estandar={estandar}, cantidad={cantidad}")  # Debug
            except (ValueError, TypeError) as e:
                print(f"Error convirtiendo valores: {e}")  # Debug
                raise ValueError(f"Error en conversión de valores: {e}")
            
            if estandar <= 0:
                print(f"Estándar inválido: {estandar}")  # Debug
                raise ValueError(f"Estándar inválido: {estandar}")
            if cantidad <= 0:
                print(f"Cantidad inválida: {cantidad}")  # Debug
                raise ValueError(f"Cantidad inválida: {cantidad}")
            
            # Verificar que el ItemRuta existe
            try:
                item = ItemRuta.objects.get(id=proceso['id'])
                print(f"ItemRuta encontrado: {item.id}")  # Debug
            except ItemRuta.DoesNotExist:
                print(f"ItemRuta no encontrado: {proceso['id']}")  # Debug
                raise ValueError(f"ItemRuta con ID {proceso['id']} no existe")
                
            return True
            
        except Exception as e:
            self.log_scheduler_operation(
                "ERROR_VALIDACION",
                {
                    "proceso_id": proceso.get('id'),
                    "ot": ot_data.get('orden_trabajo'),
                    "error": str(e),
                    "proceso_data": proceso  # Añadimos los datos completos para debug
                }
            )
            print(f"Error en validación: {e}")  # Debug
            return False

    def create_fragmented_tasks(self, programa, ordenes_trabajo):
        try:
            self.log_scheduler_operation(
                "CREAR_TAREAS",
                f"Programa {programa.id}: Iniciando creación de {len(ordenes_trabajo)} órdenes"
            )
            
            # Crear savepoint para rollback parcial si es necesario
            sid = transaction.savepoint()
            
            # Primero generar la timeline para obtener las fechas correctas
            timeline_data = self._generate_base_timeline(programa, ordenes_trabajo)
            
            # Crear un diccionario para mapear cada proceso_id a su fecha y hora de inicio
            fechas_por_proceso = {}
            for item in timeline_data.get('items', []):
                proceso_id = item['proceso_id'].replace('proc_', '')
                fecha_str = item['start_time']
                fecha_inicio = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
                
                # Guardar solo la primera fecha para cada proceso (la más temprana)
                if proceso_id not in fechas_por_proceso or fecha_inicio < fechas_por_proceso[proceso_id]:
                    fechas_por_proceso[proceso_id] = fecha_inicio  # Guardamos datetime completo
            
            # Debug: imprimir fechas asignadas
            print("\nFechas asignadas por proceso:")
            for proc_id, fecha in fechas_por_proceso.items():
                print(f"Proceso {proc_id}: {fecha}")
            
            # La validación pasa correctamente aquí
            for orden in ordenes_trabajo:
                for proceso in orden.get('procesos', []):
                    if not self.validar_proceso(proceso, orden):
                        transaction.savepoint_rollback(sid)
                        return False

            tareas_creadas = 0
            try:
                # Aquí es donde está fallando
                for orden in ordenes_trabajo:
                    for proceso in orden['procesos']:
                        try:
                            item_ruta = ItemRuta.objects.get(id=proceso['id'])
                            proceso_id_str = str(proceso['id'])
                            
                            # Usar la fecha calculada en la timeline o la fecha de inicio del programa
                            fecha_hora_tarea = fechas_por_proceso.get(proceso_id_str)
                            
                            if fecha_hora_tarea:
                                fecha_tarea = fecha_hora_tarea.date()
                                hora_tarea = fecha_hora_tarea.time()
                            else:
                                fecha_tarea = programa.fecha_inicio
                                hora_tarea = self.time_calculator.WORKDAY_START
                            
                            # Añadir logging para debug
                            print(f"\nCreando tarea para ItemRuta {item_ruta.id}")
                            print(f"Fecha calculada: {fecha_tarea}")
                            print(f"Hora calculada: {hora_tarea}")
                            
                            # Crear la tarea fragmentada
                            tarea = TareaFragmentada.objects.create(
                                tarea_original=item_ruta,
                                programa=programa,
                                fecha=fecha_tarea,  # Usar la fecha calculada
                                cantidad_asignada=proceso['cantidad'],
                                estado='PENDIENTE',
                                version_planificacion=1,
                                motivo_modificacion='BASE'
                            )
                            
                            # Calcular fechas planificadas usando la hora real de la timeline
                            fecha_inicio = datetime.combine(fecha_tarea, hora_tarea)

                            # Usar calculate_working_days en lugar de calculate_end_time
                            calculo = self.time_calculator.calculate_working_days(fecha_inicio, proceso['cantidad'], proceso['estandar'])
                            fecha_fin = calculo['next_available_time']

                            tarea.fecha_planificada_inicio = fecha_inicio
                            tarea.fecha_planificada_fin = fecha_fin
                            tarea.fecha_planificada_inicio_original = fecha_inicio
                            tarea.fecha_planificada_fin_original = fecha_fin
                            tarea.save()
                            
                            self.log_scheduler_operation(
                                "TAREA_CREADA",
                                detalles={
                                    "programa_id": programa.id,
                                    "ot": orden['orden_trabajo_codigo_ot'],
                                    "proceso": proceso['descripcion'],
                                    "cantidad": proceso['cantidad'],
                                    "maquina_id": proceso['maquina_id'],
                                    "tarea_id": tarea.id,
                                    "fecha": fecha_tarea.strftime('%Y-%m-%d'),
                                    "hora": hora_tarea.strftime('%H:%M')
                                }
                            )
                            tareas_creadas += 1
                            
                        except Exception as e:
                            print(f"\nError creando tarea: {str(e)}")
                            traceback.print_exc()  # Imprimir stacktrace completo
                            raise  # Re-lanzar la excepción para que se maneje en el bloque superior

                transaction.savepoint_commit(sid)
                return True
                
            except Exception as e:
                    print(f"\nError en bloque principal: {str(e)}")
                    traceback.print_exc()  # Imprimir stacktrace completo
                    transaction.savepoint_rollback(sid)
                    return False

        except Exception as e:
            print(f"\nError general: {str(e)}")
            traceback.print_exc()  # Imprimir stacktrace completo
            return False

    def propagar_ajuste(self, tarea, usuario=None):
        """
        Propaga los ajustes de una tarea a las demás tareas afectadas,
        considerando tanto la secuencia de la OT como los conflictos de máquina.
        """
        try:
            # 1. Obtener todas las tareas del programa que podrían verse afectadas
            tareas_programa = TareaFragmentada.objects.filter(
                programa=tarea.programa,
                fecha__gte=tarea.fecha
            ).select_related(
                'tarea_original__proceso',
                'tarea_original__maquina',
                'tarea_original__ruta__orden_trabajo'
            ).order_by('fecha', 'tarea_original__ruta__orden_trabajo__prioridad')

            # 2. Crear nodos para cada tarea y guardar la planificación original
            nodos = {}
            procesos_por_maquina = {}
            planificacion_original = {}
            
            for t in tareas_programa:
                # Guardar planificación original
                planificacion_original[t.id] = {
                    'fecha_inicio': t.fecha_planificada_inicio,
                    'fecha_fin': t.fecha_planificada_fin,
                    'estado': t.estado
                }
                
                nodo = ProcessNode(
                    proceso_id=f"proc_{t.tarea_original.id}",
                    proceso_data={
                        'id': t.tarea_original.id,
                        'item': t.tarea_original.item,
                        'descripcion': t.tarea_original.proceso.descripcion,
                        'maquina_id': t.tarea_original.maquina.id if t.tarea_original.maquina else None,
                        'cantidad': t.cantidad_asignada,
                        'estandar': t.tarea_original.estandar,
                        'prioridad': t.tarea_original.ruta.orden_trabajo.programaordentrabajo_set.first().prioridad
                    },
                    fecha_inicio=t.fecha_planificada_inicio or datetime.combine(t.fecha, time(7, 45)),
                    fecha_fin=t.fecha_planificada_fin or datetime.combine(t.fecha, time(17, 45)),
                    ot_id=t.tarea_original.ruta.orden_trabajo.id
                )
                
                nodos[t.id] = nodo
                
                # Agrupar por máquina
                if t.tarea_original.maquina:
                    maquina_id = t.tarea_original.maquina.id
                    if maquina_id not in procesos_por_maquina:
                        procesos_por_maquina[maquina_id] = []
                    procesos_por_maquina[maquina_id].append(nodo)

            # 3. Establecer las relaciones entre nodos de la misma OT
            for t in tareas_programa:
                nodo_actual = nodos[t.id]
                siguiente_proceso = tareas_programa.filter(
                    tarea_original__ruta=t.tarea_original.ruta,
                    tarea_original__item__gt=t.tarea_original.item
                ).first()
                
                if siguiente_proceso:
                    nodo_actual.siguiente_proceso = nodos[siguiente_proceso.id]

            # 4. Propagar el ajuste desde el nodo de la tarea inicial
            nodo_inicial = nodos[tarea.id]
            nodo_inicial.propagar_ajuste(
                tiempo_setup=timedelta(minutes=30),
                procesos_por_maquina=procesos_por_maquina
            )

            # 5. Actualizar las tareas con las nuevas fechas y guardar historial
            for t in tareas_programa:
                nodo = nodos[t.id]
                if (nodo.fecha_inicio != t.fecha_planificada_inicio or 
                    nodo.fecha_fin != t.fecha_planificada_fin):
                    
                    # Guardar cambios en la tarea
                    t.fecha_planificada_inicio = nodo.fecha_inicio
                    t.fecha_planificada_fin = nodo.fecha_fin
                    t.version_planificacion = (t.version_planificacion or 0) + 1
                    t.motivo_modificacion = 'AJUSTE_MAQUINA'
                    t.modificado_por = usuario
                    t.save()

            return True

        except Exception as e:
            print(f"Error en propagar_ajuste: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    def reorganizar_timeline(self, programa, fecha):
        """
        Reorganiza la timeline para el día especificado, considerando conflictos de máquina
        """
        # Obtener todas las tareas del día
        tareas = TareaFragmentada.objects.filter(
            programa=programa,
            fecha=fecha
        ).select_related(
            'tarea_original__proceso',
            'tarea_original__maquina',
            'tarea_original__ruta__orden_trabajo'
        ).prefetch_related(
            'tarea_original__ruta__orden_trabajo__programaordentrabajo_set'
        ).order_by(
            'tarea_original__ruta__orden_trabajo__programaordentrabajo__prioridad',
            'tarea_original__item'
        )
        
        # Reorganizar las tareas considerando conflictos de máquina
        for tarea in tareas:
            self.propagar_ajuste(tarea)

    def _crear_snapshot_timeline(self, programa, fecha):
        """Crea un snapshot completo de la timeline para una fecha específica"""
        try:
            # Obtener todas las tareas fragmentadas para esta fecha
            tareas = TareaFragmentada.objects.filter(
                programa=programa,
                fecha__lte=fecha
            ).select_related(
                'tarea_original__proceso',
                'tarea_original__maquina',
                'tarea_original__ruta__orden_trabajo',
                'operador'
            )

            # Crear estructura de timeline
            grupos = {}
            items = []

            for tarea in tareas:
                # Crear o actualizar grupo (OT)
                grupo_id = f"ot_{tarea.tarea_original.ruta.orden_trabajo.id}"
                if grupo_id not in grupos:
                    grupos[grupo_id] = {
                        'id': grupo_id,
                        'title': f"OT {tarea.tarea_original.ruta.orden_trabajo.codigo_ot}",
                        'stackItems': True
                    }

                # Crear item
                item = {
                    'id': f"tarea_{tarea.id}",
                    'group': grupo_id,
                    'title': tarea.tarea_original.proceso.descripcion,
                    'start_time': tarea.fecha_planificada_inicio.isoformat() if tarea.fecha_planificada_inicio else None,
                    'end_time': tarea.fecha_planificada_fin.isoformat() if tarea.fecha_planificada_fin else None,
                    'estado': tarea.estado,
                    'cantidad_completada': float(tarea.cantidad_completada),
                    'cantidad_total': float(tarea.cantidad_asignada),
                    'operador': tarea.operador.nombre if tarea.operador else None,
                    'itemProps': {
                        'style': self._get_item_style(tarea)
                    }
                }
                items.append(item)

            return {
                'grupos': list(grupos.values()),
                'items': items,
                'fecha_snapshot': fecha.isoformat()
            }

        except Exception as e:
            print(f"Error creando snapshot de timeline: {str(e)}")
            return None

    def _get_item_style(self, tarea):
        """Define el estilo visual del item basado en su estado"""
        estilos_base = {
            'borderRadius': '4px',
            'padding': '2px 6px'
        }
        
        if tarea.estado == 'COMPLETADO':
            return {
                **estilos_base,
                'backgroundColor': '#4CAF50',
                'color': 'white'
            }
        elif tarea.estado == 'EN_PROCESO':
            return {
                **estilos_base,
                'backgroundColor': '#FFA726',
                'color': 'white'
            }
        elif tarea.estado == 'CONTINUADO':
            return {
                **estilos_base,
                'backgroundColor': '#2196F3',
                'color': 'white'
            }
        else:
            return {
                **estilos_base,
                'backgroundColor': '#9E9E9E',
                'color': 'white'
            }
    
    def reajustar_fechas_tareas_fragmentadas(self, programa):
        """
        Reajusta las fechas de las tareas fragmentadas basándose en la timeline actualizada.
        Esta función debe llamarse después de cambios en los procesos (prioridad, estándar, máquinas, etc.)
        que afecten la planificación del programa.
        
        Args:
            programa: El programa de producción a reajustar
            
        Returns:
            dict: Resumen de los ajustes realizados
        """
        try:
            self.log_scheduler_operation(
                "REAJUSTAR_FECHAS",
                f"Iniciando reajuste de fechas para programa {programa.id}"
            )
            
            # 1. Obtener todos los datos de las órdenes para generar la timeline actualizada
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
            
            # 2. Generar la timeline actualizada
            timeline_data = self._generate_base_timeline(programa, ordenes_trabajo)
            
            # 3. Crear un diccionario para mapear cada proceso_id a su fecha y hora de inicio
            fechas_por_proceso = {}
            for item in timeline_data.get('items', []):
                proceso_id = item['proceso_id'].replace('proc_', '')
                fecha_str = item['start_time']
                fecha_fin_str = item['end_time']
                fecha_inicio = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d %H:%M:%S')
                
                # Guardar las fechas por proceso
                if proceso_id not in fechas_por_proceso:
                    fechas_por_proceso[proceso_id] = {
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': fecha_fin,
                        'intervalos': []
                    }
                
                # Añadir el intervalo
                fechas_por_proceso[proceso_id]['intervalos'].append({
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'cantidad': float(item['cantidad_intervalo'])
                })
            
            # 4. Actualizar las tareas fragmentadas con las nuevas fechas
            tareas_actualizadas = 0
            tareas_creadas = 0
            errores = 0
            
            # Obtener todas las tareas fragmentadas del programa
            tareas_fragmentadas = TareaFragmentada.objects.filter(
                programa=programa
            ).select_related(
                'tarea_original',
                'tarea_original__proceso',
                'tarea_original__maquina'
            )
            
            # Mapeo de ItemRuta a TareaFragmentada para facilitar la búsqueda
            tareas_por_item_ruta = {}
            for tarea in tareas_fragmentadas:
                item_ruta_id = tarea.tarea_original.id
                if item_ruta_id not in tareas_por_item_ruta:
                    tareas_por_item_ruta[item_ruta_id] = []
                tareas_por_item_ruta[item_ruta_id].append(tarea)
            
            # Actualizar fechas en tareas existentes
            for item_ruta_id_str, fechas in fechas_por_proceso.items():
                try:
                    item_ruta_id = int(item_ruta_id_str)
                    
                    if item_ruta_id in tareas_por_item_ruta:
                        # Ordenar tareas por fecha para asignar secuencialmente
                        tareas = sorted(tareas_por_item_ruta[item_ruta_id], key=lambda t: t.fecha)
                        
                        # Si solo hay una tarea, usar el primer intervalo
                        if len(tareas) == 1:
                            tarea = tareas[0]
                            tarea.fecha = fechas['fecha_inicio'].date()
                            tarea.fecha_planificada_inicio = fechas['fecha_inicio']
                            tarea.fecha_planificada_fin = fechas['fecha_fin']
                            tarea.version_planificacion += 1
                            tarea.motivo_modificacion = 'AJUSTE_TIMELINE'
                            tarea.save()
                            tareas_actualizadas += 1
                        else:
                            # Distribuir los intervalos entre las tareas existentes
                            intervalos_ordenados = sorted(fechas['intervalos'], key=lambda i: i['fecha_inicio'])
                            for idx, tarea in enumerate(tareas):
                                if idx < len(intervalos_ordenados):
                                    intervalo = intervalos_ordenados[idx]
                                    tarea.fecha = intervalo['fecha_inicio'].date()
                                    tarea.fecha_planificada_inicio = intervalo['fecha_inicio']
                                    tarea.fecha_planificada_fin = intervalo['fecha_fin']
                                    tarea.version_planificacion += 1
                                    tarea.motivo_modificacion = 'AJUSTE_TIMELINE'
                                    tarea.save()
                                    tareas_actualizadas += 1
                    else:
                        # No hay tareas existentes para este item_ruta, podríamos crearlas
                        try:
                            item_ruta = ItemRuta.objects.get(id=item_ruta_id)
                            
                            # Crear tarea usando el primer intervalo
                            primer_intervalo = sorted(fechas['intervalos'], key=lambda i: i['fecha_inicio'])[0]
                            tarea = TareaFragmentada.objects.create(
                                tarea_original=item_ruta,
                                programa=programa,
                                fecha=primer_intervalo['fecha_inicio'].date(),
                                cantidad_asignada=item_ruta.cantidad_pedido,
                                estado='PENDIENTE',
                                version_planificacion=1,
                                motivo_modificacion='AJUSTE_TIMELINE',
                                fecha_planificada_inicio=primer_intervalo['fecha_inicio'],
                                fecha_planificada_fin=primer_intervalo['fecha_fin'],
                                fecha_planificada_inicio_original=primer_intervalo['fecha_inicio'],
                                fecha_planificada_fin_original=primer_intervalo['fecha_fin']
                            )
                            tareas_creadas += 1
                        except Exception as e:
                            print(f"Error creando tarea para ItemRuta {item_ruta_id}: {str(e)}")
                            errores += 1
                except Exception as e:
                    print(f"Error procesando item_ruta {item_ruta_id_str}: {str(e)}")
                    errores += 1
            
            return {
                'tareas_actualizadas': tareas_actualizadas,
                'tareas_creadas': tareas_creadas,
                'errores': errores
            }
            
        except Exception as e:
            self.log_scheduler_operation(
                "ERROR_REAJUSTE",
                f"Error reajustando fechas: {str(e)}"
            )
            print(f"Error en reajustar_fechas_tareas_fragmentadas: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'tareas_actualizadas': 0,
                'tareas_creadas': 0,
                'errores': 1,
                'error_mensaje': str(e)
            }
        
    #***************************************


class ProductionCascadeCalculator:
    def __init__(self, time_calculator):
        self.time_calculator = time_calculator

    def calculate_cascade_times(self, procesos, fecha_inicio):
        cascade_times = {}
        
        # Identificar el proceso más lento
        def get_estandar(proceso):
            if isinstance(proceso, dict):
                return float(proceso.get('estandar', float('inf')))
            else:
                return float(proceso.estandar if proceso.estandar else float('inf'))
            
        proceso_mas_lento = min(procesos, key=get_estandar)
        estandar_mas_lento = get_estandar(proceso_mas_lento)
        
        fecha_actual = fecha_inicio
        unidades_disponibles = 0
        
        for proceso in procesos:
            # Obtener ID del proceso según el tipo de objeto
            if isinstance(proceso, dict):
                proceso_id = f"proc_{proceso['id']}"
                estandar = float(proceso.get('estandar', 0))
                cantidad_total = float(proceso.get('cantidad', 0))
            else:
                proceso_id = f"proc_{proceso.id}"
                estandar = float(proceso.estandar if proceso.estandar else 0)
                cantidad_total = float(proceso.cantidad_pedido if proceso.cantidad_pedido else 0)
            
            # Calcular cantidad mínima para iniciar este proceso
            cantidad_minima = estandar  # Una hora de producción
            
            # Esperar hasta tener suficientes unidades del proceso anterior
            if unidades_disponibles < cantidad_minima:
                tiempo_espera = (cantidad_minima - unidades_disponibles) / estandar_mas_lento
                fecha_actual += timedelta(hours=tiempo_espera)
            
            # Calcular tiempo de proceso ajustado al cuello de botella
            tiempo_proceso = cantidad_total / min(estandar, estandar_mas_lento)
            
            cascade_times[proceso_id] = {
                'inicio': fecha_actual,
                'fin': fecha_actual + timedelta(hours=tiempo_proceso),
                'cantidad_por_hora': min(estandar, estandar_mas_lento)
            }
            fecha_actual = cascade_times[proceso_id]['fin']
            unidades_disponibles = cantidad_total
            
        return cascade_times

    def get_production_at_time(self, proceso_info, tiempo):
        """
        Calcula cuánto se ha producido hasta un momento específico
        """
        produccion_total = 0
        
        for intervalo in proceso_info['produccion_por_intervalo']:
            if tiempo < intervalo['fecha_inicio']:
                break
            elif tiempo >= intervalo['fecha_fin']:
                produccion_total += intervalo['unidades']
            else:
                # Calcular producción parcial en el intervalo actual
                tiempo_transcurrido = (tiempo - intervalo['fecha_inicio']).total_seconds() / 3600
                produccion_parcial = tiempo_transcurrido * proceso_info['unidades_por_hora']
                produccion_total += min(produccion_parcial, intervalo['unidades'])
                
        return min(produccion_total, proceso_info['cantidad_total'])
