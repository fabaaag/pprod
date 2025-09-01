from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from JobManagement.models import (
    ProgramaProduccion, 
    TareaFragmentada, 
    ReporteDiarioPrograma, 
    ProgramaOrdenTrabajo,
    EjecucionTarea,
    HistorialPlanificacion
)
from JobManagement.services.production_scheduler import ProductionScheduler
from JobManagement.services.time_calculations import TimeCalculator
import logging
import os
from datetime import datetime
import traceback
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

class Command(BaseCommand):
    help = 'Regenera completamente las tareas fragmentadas, reportes y historial de programas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--programa_id',
            type=int,
            help='ID específico de un programa (opcional)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar la regeneración incluso si ya existen tareas',
            default=True
        )
        parser.add_argument(
            '--log-file',
            type=str,
            help='Archivo para guardar el log detallado (opcional)',
            default='regeneracion_programa.log'
        )

    def setup_logging(self, log_file):
        """Configura el logging para el comando"""
        # Asegurarse de que el archivo anterior se elimine para evitar logs mezclados
        if os.path.exists(log_file):
            os.remove(log_file)
            
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def log_detalle(self, tipo, mensaje, datos=None, error=None):
        """Función helper para logging estructurado"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'tipo': tipo,
            'mensaje': mensaje
        }
        if datos:
            log_entry['datos'] = datos
        if error:
            log_entry['error'] = str(error)
            log_entry['traceback'] = traceback.format_exc()
            self.logger.error(json.dumps(log_entry, indent=2, cls=DecimalEncoder))
        else:
            self.logger.info(json.dumps(log_entry, indent=2, cls=DecimalEncoder))

    def limpiar_programa(self, programa):
        """Limpia todos los datos relacionados con un programa"""
        try:
            self.log_detalle('LIMPIEZA', f"Iniciando limpieza del programa {programa.id}")
            
            # Guardar conteos para el log
            conteos_iniciales = {
                'ejecuciones': EjecucionTarea.objects.filter(tarea__programa=programa).count(),
                'historial': HistorialPlanificacion.objects.filter(programa=programa).count(),
                'tareas': TareaFragmentada.objects.filter(programa=programa).count(),
                'reportes': ReporteDiarioPrograma.objects.filter(programa=programa).count()
            }
            
            # Eliminar todo en orden
            with transaction.atomic():
                EjecucionTarea.objects.filter(tarea__programa=programa).delete()
                HistorialPlanificacion.objects.filter(programa=programa).delete()
                TareaFragmentada.objects.filter(programa=programa).delete()
                ReporteDiarioPrograma.objects.filter(programa=programa).delete()
            
            self.log_detalle('LIMPIEZA', 'Limpieza completada', conteos_iniciales)
            return True
        except Exception as e:
            self.log_detalle('ERROR_LIMPIEZA', 'Error durante la limpieza', error=e)
            return False

    def preparar_ordenes_trabajo(self, programa):
        """Prepara los datos de órdenes de trabajo en el formato requerido"""
        try:
            self.log_detalle('PREPARACION', f"Preparando órdenes de trabajo para programa {programa.id}")
            
            ordenes_trabajo = []
            programa_ots = ProgramaOrdenTrabajo.objects.filter(programa=programa).select_related(
                'orden_trabajo',
                'orden_trabajo__ruta_ot'
            ).prefetch_related(
                'orden_trabajo__ruta_ot__items',
                'orden_trabajo__ruta_ot__items__proceso',
                'orden_trabajo__ruta_ot__items__maquina'
            )

            for pot in programa_ots:
                ot = pot.orden_trabajo
                if not ot.ruta_ot:
                    self.log_detalle('ADVERTENCIA', f"OT {ot.codigo_ot} sin ruta definida")
                    continue

                procesos = []
                for item in ot.ruta_ot.items.all().order_by('item'):
                    # Validación detallada de cada proceso
                    validacion = {
                        'item_id': item.id,
                        'estandar': item.estandar,
                        'cantidad': item.cantidad_pedido,
                        'tiene_proceso': bool(item.proceso),
                        'tiene_maquina': bool(item.maquina)
                    }
                    
                    if not item.estandar or not item.cantidad_pedido:
                        self.log_detalle('ADVERTENCIA', 
                            f"Proceso inválido en OT {ot.codigo_ot}", 
                            validacion
                        )
                        continue

                    procesos.append({
                        'id': item.id,
                        'item': item.item,
                        'descripcion': item.proceso.descripcion if item.proceso else None,
                        'maquina_id': item.maquina.id if item.maquina else None,
                        'cantidad': item.cantidad_pedido,
                        'estandar': item.estandar,
                        'prioridad': pot.prioridad
                    })

                if procesos:
                    ordenes_trabajo.append({
                        'orden_trabajo': ot.id,
                        'orden_trabajo_codigo_ot': ot.codigo_ot,
                        'orden_trabajo_descripcion_producto_ot': ot.descripcion_producto_ot,
                        'procesos': procesos
                    })

            self.log_detalle('PREPARACION', 'Preparación completada', {
                'total_ordenes': len(ordenes_trabajo),
                'ordenes_codigos': [ot['orden_trabajo_codigo_ot'] for ot in ordenes_trabajo]
            })
            return ordenes_trabajo

        except Exception as e:
            self.log_detalle('ERROR_PREPARACION', 'Error preparando órdenes', error=e)
            return []

    def handle(self, *args, **options):
        try:
            # Configurar logging
            log_file = options['log_file']
            self.setup_logging(log_file)
            
            scheduler = ProductionScheduler(TimeCalculator())
            programa_id = options['programa_id']
            force = options['force']
            
            # Obtener programas
            if programa_id:
                programas = ProgramaProduccion.objects.filter(id=programa_id)
                self.log_detalle('INICIO', f"Regenerando programa específico ID: {programa_id}")
            else:
                programas = ProgramaProduccion.objects.all()
                self.log_detalle('INICIO', f"Regenerando {programas.count()} programas")

            for programa in programas:
                try:
                    with transaction.atomic():
                        self.log_detalle('PROGRAMA', f"Procesando programa {programa.id} - {programa.nombre}")

                        # Limpiar datos existentes
                        if not self.limpiar_programa(programa):
                            raise Exception("Error en la limpieza del programa")

                        # Preparar datos de órdenes de trabajo
                        ordenes_trabajo = self.preparar_ordenes_trabajo(programa)
                        if not ordenes_trabajo:
                            raise Exception("No se encontraron órdenes de trabajo válidas")

                        # Crear nuevas tareas fragmentadas
                        try:
                            resultado = scheduler.create_fragmented_tasks(programa, ordenes_trabajo)
                            if not resultado:
                                raise Exception("El scheduler retornó False")
                            
                            # Verificar la creación
                            conteos_finales = {
                                'tareas': TareaFragmentada.objects.filter(programa=programa).count(),
                                'reportes': ReporteDiarioPrograma.objects.filter(programa=programa).count(),
                                'historial': HistorialPlanificacion.objects.filter(programa=programa).count()
                            }
                            
                            self.log_detalle('EXITO', f"Programa {programa.id} regenerado", conteos_finales)
                            
                        except Exception as e:
                            self.log_detalle('ERROR_SCHEDULER', 'Error en create_fragmented_tasks', error=e)
                            raise

                except Exception as e:
                    self.log_detalle('ERROR_PROGRAMA', f"Error procesando programa {programa.id}", error=e)

            self.stdout.write(f"\nLog detallado guardado en: {os.path.abspath(log_file)}")

        except Exception as e:
            self.log_detalle('ERROR_GENERAL', "Error general en el comando", error=e)
            raise
