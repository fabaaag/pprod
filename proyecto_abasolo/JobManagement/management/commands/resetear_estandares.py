from django.core.management.base import BaseCommand
from django.db import transaction
from JobManagement.models import EstandarMaquinaProceso
import logging
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Elimina registros de EstandaresMaquinaProceso según los criterios especificados'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = None #Inicializar logger como None

    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-no-principales',
            action="store_true",
            help='Eliminar solo los estándares no principales',
            default=False
        )
        parser.add_argument(
            '--producto_id',
            type=int,
            help='ID específico de un producto (opcional)'
        )
        parser.add_argument(
            '--pieza_id',
            type=int,
            help='ID específico de un pieza (opcional)'
        )
        parser.add_argument(
            '--proceso_id',
            type=int,
            help='ID específico de una proceso (opcional)'
        )
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirmar la eliminación',
            default=False
        )
        parser.add_argument(
            '--log_file',
            type=str,
            help='Archivo para guardar el log detallado (opcional)',
            default='resetear_estandares.log'
        )

    def setup_logging(self, log_file):
        """Configura el logging para el comando"""
        # Asegurarse de que el directorio de logs existe
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def log_info(self, mensaje):
        """Registra un mensaje informativo"""
        self.logger.info(mensaje)
        self.stdout.write(self.style.SUCCESS(mensaje))

    def log_error(self, mensaje):
        """Registra un mensaje de error"""
        self.logger.error(mensaje)
        self.stdout.write(self.style.ERROR(mensaje))

    def handle(self, *args, **options):
        try:
            #Configurar logging
            log_file = options.get('log_file', 'resetear_estandares.log')
            self.setup_logging(log_file)

            solo_no_principales = options['solo_no_principales']
            producto_id = options['producto_id']
            pieza_id = options['pieza_id']
            proceso_id = options['proceso_id']
            confirmar = options['confirmar']

            self.log_info(f"Iniciando reseteo de estándares - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            #Construir la consulta según los filtros
            query = EstandarMaquinaProceso.objects.all()

            if solo_no_principales:
                query = query.filter(es_principal=False)
                self.log_info("Filtrando solo estándares NO principales")

            if producto_id:
                query = query.filter(producto_id=producto_id)
                self.log_info(f"Filtrando por producto_id={producto_id}")
                
            if pieza_id:
                query = query.filter(pieza_id=pieza_id)
                self.log_info(f"Filtrando por pieza_id={pieza_id}")

            if proceso_id:
                query = query.filter(proceso_id=proceso_id)
                self.log_info(f"Filtrando por proceso_id={proceso_id}")

            #Contar registros afectados
            cantidad = query.count()
            self.log_info(f"Se eliminarán {cantidad} registros de estándares")

            #Verificar confirmación
            if not confirmar:
                self.log_info("Para confirmar la eliminación, ejecuma nuevamente con --confirmar")
                return
            
            #Ejecutar la eliminación
            if cantidad > 0:
                with transaction.atomic():
                    query.delete()
                self.log_info(f"Se han eliminado {cantidad} registros correctamente")
            else:
                self.log_info("No hay registros que cumplan con los criterios para eliminar")
            
            self.log_info(f"Proceso completado - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write(f"Log detallado guardado en: {os.path.abspath(log_file)}")

        except Exception as e:
            self.log_error(f"Error general: {str(e)}")
            raise