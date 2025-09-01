from genericpath import exists
from django.core.management.base import BaseCommand
from django.db import transaction
from JobManagement.models import Ruta, RutaPieza, EstandarMaquinaProceso
from Product.models import Producto, Pieza
import logging
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Crea registros base de EstandarMaquinaProceso a partir de las rutas existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--producto_id',
            type=int,
            help='ID específico de un producto (opcional)'
        )
        parser.add_argument(
            '--pieza_id',
            type=int,
            help='ID específico de una pieza (opcional)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar la creación incluso si ya existen registros'
        )
        parser.add_argument(
            '--log-file',
            type=str,
            help='Archivo para guardar el log detallado (opcional)',
            default='estadares_base.log'
        )

    def setup_logging(self, log_file):
        """Configura el logging para el comando"""
        #Asegurarse de que el directorio de logs existe
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

    def procesar_rutas_producto(self, producto_id=None, force=False):
        """Procesa las rutas de productos para crear estándares"""
        query = Ruta.objects.select_related('producto', 'proceso', 'maquina')

        if producto_id:
            query = query.filter(producto_id=producto_id)

        total = query.count()
        self.log_info(f"Procesando {total} rutas de productos...")

        creados = 0
        actualizados = 0
        errores = 0
        for ruta in query:
            try:
                if not ruta.producto or not ruta.proceso or not ruta.maquina:
                    self.log_error(f"Ruta {ruta.id} incompleta, saltando...")
                    errores += 1
                    continue

                #Verificar si ya existe un estándar
                existe = EstandarMaquinaProceso.objects.filter(
                    producto=ruta.producto,
                    proceso=ruta.proceso,
                    maquina=ruta.maquina,
                ).exists()

                if existe and not force:
                    self.log_info(f"Ya existe estándar para producto {ruta.producto.codigo_producto}, proceso {ruta.proceso.codigo_proceso}, maquina { ruta.maquina.codigo_maquina}. Saltando...") 
                    continue

                
                #Crear o actualizar el estándar
                estandar, creado = EstandarMaquinaProceso.objects.update_or_create(
                    producto=ruta.producto,
                    proceso=ruta.proceso,
                    maquina=ruta.maquina,
                    defaults={
                        'estandar': ruta.estandar or 0,
                        'es_principal': True
                    }
                )

                if creado:
                    creados += 1
                    self.log_info(f"Creado estándar para producto {ruta.producto.codigo_producto}, proceso: {ruta.proceso.codigo_proceso}, máquina {ruta.maquina.codigo_maquina}")
                else:
                    actualizados += 1
                    self.log_info(f"Actualizado estándar para producto {ruta.producto.codigo_producto}, proceso: {ruta.proceso.codigo_proceso}, máquina {ruta.maquina.codigo_maquina}")

            except Exception as e:
                errores += 1
                self.log_error(f"Erorr procesando ruta {ruta.id}: {str(e)}")

        return {
            'total': total,
            'creados': creados,
            'actualizados': actualizados,
            'errores': errores
        }
    
    def procesar_rutas_pieza(self, pieza_id=None, force=False):
        """Procesa las rutas de piezas para crear estándares"""
        query = RutaPieza.objects.select_related('pieza', 'proceso', 'maquina')

        if pieza_id:
            query = query.filter(pieza_id=pieza_id)

        total = query.count()
        self.log_info(f"Procesando {total} rutas de piezas...")

        creados = 0
        actualizados = 0
        errores = 0
        for ruta in query:
            try:
                if not ruta.pieza or not ruta.proceso or not ruta.maquina: 
                    self.log_error(f"Ruta {ruta.id} incomplete, saltando...")
                    errores += 1
                    continue

                #Verificar si ya existe un estándar
                existe = EstandarMaquinaProceso.objects.filter(
                    pieza=ruta.pieza,
                    proceso=ruta.proceso,
                    maquina=ruta.maquina
                ).exists()

                if existe and not force:
                    self.log_info(f"Ya existe estándar para pieza {ruta.pieza.codigo_pieza}, proceso {ruta.proceso.codigo_proceso}, máquina {ruta.maquina.codigo_maquina}. Saltando...")
                    continue

                #Crear o actualizar el estándar
                estandar, creado = EstandarMaquinaProceso.objects.update_or_create(
                    pieza=ruta.pieza,
                    proceso=ruta.proceso,
                    maquina=ruta.maquina,
                    defaults={
                        'estandar': ruta.estandar or 0,
                        'es_principal': True
                    }
                )

                if creado:
                    creados += 1
                    self.log_info(f"Creado estándar para pieza {ruta.pieza.codigo_pieza}, proceso: {ruta.proceso.codigo_proceso}, maquina {ruta.maquina.codigo_maquina}")
                else:
                    actualizados += 1
                    self.log_info(f"Actualizado estándar para pieza {ruta.pieza.codigo_pieza}, proceso: {ruta.proceso.codigo_proceso}, maquina {ruta.maquina.codigo_maquina}")

            except Exception as e:
                errores += 1
                self.log_error(f"Error procesando ruta {ruta.id}: {str(e)}")

        return {
            'total': total,
            'creados': creados,
            'actualizados': actualizados,
            'errores': errores
        }
    
    def handle(self, *args, **options):
        try:
            #Configurar logging
            log_file = options['log_file']
            self.setup_logging(log_file)

            producto_id = options['producto_id']
            pieza_id = options['pieza_id']
            force = options['force']

            self.log_info(f"Iniciando creación de estándares base - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            with transaction.atomic():
                #Procesar productos
                if not pieza_id:
                    resultados_producto = self.procesar_rutas_producto(producto_id, force)
                    self.log_info(f'Resumen productos: {resultados_producto}')

                #Procesar piezas
                if not producto_id:
                    resultados_pieza = self.procesar_rutas_pieza(pieza_id, force)
                    self.log_info(f'Resumen piezas: {resultados_pieza}')

            self.log_info(f"Proceso completado - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write(f"Log detallado guardado en: {os.path.abspath(log_file)}")

        except Exception as e:
            self.log_error(f"Error en general: {str(e)}")
            raise
