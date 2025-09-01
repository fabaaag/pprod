def calcular_progreso_acumulado(fragmento):
    """
    Calcula el progreso acumulado de una tarea fragmentada y todas sus continuaciones.
    
    Args:
        fragmento: Instancia de TareaFragmentada
        
    Returns:
        float: Porcentaje de progreso acumulado (0-100)
    """
    # Cantidad total completada en este fragmento y sus continuaciones
    total_completado = fragmento.cantidad_completada
    
    # Función recursiva auxiliar para sumar cantidades completadas
    def sumar_completado_recursivamente(frag):
        suma = 0
        # Obtener todas las continuaciones directas
        continuaciones = frag.continuaciones.all()
        for cont in continuaciones:
            suma += cont.cantidad_completada
            # Sumar recursivamente las continuaciones de las continuaciones
            suma += sumar_completado_recursivamente(cont)
        return suma
    
    # Añadir cantidades completadas de todas las continuaciones
    total_completado += sumar_completado_recursivamente(fragmento)
    
    # Obtener cantidad total asignada originalmente a la tarea raíz
    tarea_original = fragmento
    while tarea_original.tarea_padre:
        tarea_original = tarea_original.tarea_padre
    
    # La cantidad original es la asignada a la primera tarea de la cadena
    cantidad_original = tarea_original.cantidad_asignada
    
    # Calcular porcentaje
    if cantidad_original > 0:
        porcentaje = (total_completado / cantidad_original) * 100
        return min(100, round(porcentaje, 2))  # Limitamos a 100% máximo
    return 0

import logging
from datetime import datetime
import os
import json
import traceback
from decimal import Decimal
from .services.logging_utils import setup_logging


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)


# Funciones helper para logging específico
def log_tarea_fragmentada(logger, accion, tarea, datos_adicionales=None):
    """Logger específico para tareas fragmentadas"""
    mensaje = f"""
    Acción: {accion}
    Tarea ID: {tarea.id}
    Tarea Original ID: {tarea.tarea_original_id}
    Estado: {tarea.estado}
    Fecha: {tarea.fecha}
    Cantidad Asignada: {tarea.cantidad_asignada}
    Cantidad Completada: {tarea.cantidad_completada}
    Es Continuación: {tarea.es_continuacion}
    """
    if datos_adicionales:
        mensaje += f"\nDatos Adicionales: {datos_adicionales}"
    
    logger.info(mensaje)

def log_timeline_update(logger, programa_id, tipo_actualizacion, detalles=None):
    """Logger específico para actualizaciones de timeline"""
    mensaje = {
        "timestamp": datetime.now().isoformat(),
        "programa_id": programa_id,
        "tipo": tipo_actualizacion,
        "detalles": detalles
    }
    logger.info(f"[TIMELINE] {json.dumps(mensaje, indent=2)}")

# Nuevas funciones de logging añadidas
def log_scheduler_operation(logger, operacion, detalles):
    """
    Función mejorada para logging de operaciones del scheduler
    Args:
        logger: Logger instance
        operacion (str): Tipo de operación
        detalles (dict/str): Detalles de la operación
    """
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operacion': operacion,
            'detalles': detalles
        }
        
        # Agregar stack trace solo para errores
        if isinstance(operacion, str) and operacion.startswith('ERROR'):
            log_entry['stack_trace'] = traceback.format_stack()
            logger.error(json.dumps(log_entry, cls=DecimalEncoder, indent=2))
        else:
            logger.info(json.dumps(log_entry, cls=DecimalEncoder))
            
    except Exception as e:
        # Fallback básico si falla el logging
        print(f"Error en logging: {str(e)}")
        print(f"Operación: {operacion}")
        print(f"Detalles: {detalles}")

def log_machine_availability(logger, maquina_id, fecha, estado, detalles=None):
    """Logger específico para disponibilidad de máquinas"""
    mensaje = {
        "timestamp": datetime.now().isoformat(),
        "maquina_id": maquina_id,
        "fecha": fecha.isoformat() if isinstance(fecha, datetime) else fecha,
        "estado": estado,
        "detalles": detalles
    }
    logger.info(f"[MAQUINA] {json.dumps(mensaje, indent=2)}")