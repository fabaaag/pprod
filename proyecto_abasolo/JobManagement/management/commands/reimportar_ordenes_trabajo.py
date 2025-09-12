from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from django.core.exceptions import MultipleObjectsReturned
from datetime import datetime, timedelta
import csv
import chardet
import logging
import os

from JobManagement.models import (
    OrdenTrabajo,
    TipoOT,
    SituacionOT,
    RutaOT,
    ItemRuta,
    Maquina,
    Proceso, 
    EmpresaOT,
    ProgramaOrdenTrabajo,
    TareaFragmentada,
    EjecucionTarea,
    ReporteDiarioPrograma,
    HistorialPlanificacion
)

from Client.models import Cliente
from Utils.models import MeasurementUnit, MateriaPrima

from Product.models import Producto, Pieza


import os
import platform
import subprocess
from pathlib import Path


class Command(BaseCommand):
    help = 'Reimporta órdenes de trabajo borrando primero los registros existentes'
    
    # RUTAS FIJAS DE LOS ARCHIVOS - Ubicación de red
    ARCHIVO_OT = None # r'\\WEBSERVER\migracion\ot.txt'
    ARCHIVO_RUTA_OT = None #r'\\WEBSERVER\migracion\ruta_ot.txt'

    def obtener_ruta_archivos(self):
        """Determina la ruta de los archivos según el sistema operativo o pregunta al usuario"""
        if platform.system() == 'Windows':
            self.ARCHIVO_OT = r'\\WEBSERVER\migracion\ot.txt'
            self.ARCHIVO_RUTA_OT = r'\\WEBSERVER\migracion\ruta_ot.txt'
            return True
            
        # En Linux, intentar encontrar automáticamente
        posibles_rutas_base = [
            "/home/faba/Escritorio/archivos de import",  # <-- tu ruta local primero
            f"/run/user/{os.getuid()}/gvfs/smb-share:server=webserver,share=migracion",
            f"{os.path.expanduser('~')}/.gvfs/smb-share on webserver/migracion",
            "/media/smb-share/migracion"
        ]
        
        for ruta_base in posibles_rutas_base:
            if os.path.exists(ruta_base):
                self.ARCHIVO_OT = os.path.join(ruta_base, "ot.txt")
                self.ARCHIVO_RUTA_OT = os.path.join(ruta_base, "ruta_ot.txt")
                self.log_info(f"Se encontró la ruta de la compartición: {ruta_base}")
                return True
                
        # Si no se encontró automáticamente, preguntar al usuario
        self.stdout.write(self.style.WARNING("\n¡ATENCIÓN! No se pudo encontrar automáticamente la ruta a los archivos compartidos."))
        self.stdout.write(self.style.WARNING("Por favor, siga estos pasos:"))
        self.stdout.write("1. Abra el explorador de archivos")
        self.stdout.write("2. Navegue a la carpeta compartida usando smb://webserver/migracion/")
        self.stdout.write("3. Una vez allí, copie los archivos ot.txt y ruta_ot.txt a una carpeta local")
        self.stdout.write("4. Ingrese la ruta completa a la carpeta local donde copió los archivos:")
        
        carpeta_local = input("> ")
        
        if not carpeta_local or not os.path.exists(carpeta_local):
            # Intentar crear un directorio temporal y sugerir copiar los archivos allí
            temp_dir = os.path.join(os.path.expanduser("~"), "temp_migracion")
            os.makedirs(temp_dir, exist_ok=True)
            
            self.log_error(f"La carpeta {carpeta_local} no existe o no se especificó.")
            self.stdout.write(self.style.WARNING(f"Por favor, copie los archivos a: {temp_dir}"))
            self.stdout.write("Luego presione Enter para continuar...")
            input()
            
            carpeta_local = temp_dir
            
        self.ARCHIVO_OT = os.path.join(carpeta_local, "ot.txt")
        self.ARCHIVO_RUTA_OT = os.path.join(carpeta_local, "ruta_ot.txt")
        
        return True


    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirmar la eliminación y reimportación',
            default=False
        )
        parser.add_argument(
            '--log-file',
            type=str,
            help='Archivo para guardar el log detallado (opcional)',
            default='reimportar_ot.log'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se eliminaría sin realizar cambios',
            default=False
        )

    def setup_logging(self, log_file):
        """Configura el logging para el comando"""
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
        if hasattr(self, 'logger'):
            self.logger.info(mensaje)
        self.stdout.write(self.style.SUCCESS(mensaje))

    def log_error(self, mensaje):
        """Registra un mensaje de error"""
        if hasattr(self, 'logger'):
            self.logger.error(mensaje)
        self.stdout.write(self.style.ERROR(mensaje))

    def log_warning(self, mensaje):
        """Registra un mensaje de advertencia"""
        if hasattr(self, 'logger'):
            self.logger.warning(mensaje)
        self.stdout.write(self.style.WARNING(mensaje))

    def limpiar_datos_existentes(self, dry_run=False):
        """Elimina todos los datos relacionados con las órdenes de trabajo"""
        self.log_info("=== INICIANDO LIMPIEZA DE DATOS EXISTENTES ===")
        
        # Contar registros antes de eliminar
        conteos = {
            'programa_orden_trabajo': ProgramaOrdenTrabajo.objects.count(),
            'item_ruta': ItemRuta.objects.count(),
            'ruta_ot': RutaOT.objects.count(),
            'orden_trabajo': OrdenTrabajo.objects.count(),
        }

        self.log_info(f"Registros encontrados para eliminar:")
        for tabla, cantidad in conteos.items():
            self.log_info(f"  - {tabla}: {cantidad}")

        if dry_run:
            self.log_warning("MODO DRY-RUN: No se eliminarán registros")
            return conteos

        try:
            with transaction.atomic():
                # Eliminar en orden de dependencias (desde las hojas hacia la raíz)
                self.log_info("Eliminando ProgramaOrdenTrabajo...")
                ProgramaOrdenTrabajo.objects.all().delete()

                self.log_info("Eliminando ItemRuta...")
                ItemRuta.objects.all().delete()

                self.log_info("Eliminando RutaOT...")
                RutaOT.objects.all().delete()

                self.log_info("Eliminando OrdenTrabajo...")
                OrdenTrabajo.objects.all().delete()

            self.log_info("=== LIMPIEZA COMPLETADA EXITOSAMENTE ===")
            return conteos

        except Exception as e:
            self.log_error(f"Error durante la limpieza: {str(e)}")
            raise

    def importar_ordenes_trabajo(self):
        """Importa órdenes de trabajo desde archivo fijo"""
        self.log_info(f"=== INICIANDO IMPORTACIÓN DE ÓRDENES DE TRABAJO ===")
        self.log_info(f"Archivo: {self.ARCHIVO_OT}")

        created_count = 0
        updated_count = 0
        failed_count = 0
        errors = []

        # Detectar codificación
        with open(self.ARCHIVO_OT, 'rb') as f:
            result = chardet.detect(f.read())
            encoding = result['encoding']

        self.log_info(f'Usando codificación detectada: {encoding}')

        try:
            with open(self.ARCHIVO_OT, 'r', encoding=encoding) as file:
                reader = csv.reader(file, delimiter='$')
                next(reader)  # Saltar header

                for row_num, row in enumerate(reader, start=2):
                    try:
                        if len(row) != 25:
                            self.log_error(f"Fila {row_num} inválida: esperadas 24 columnas, obtenidas {len(row)}")
                            failed_count += 1
                            continue
                        
                        # Parsear datos básicos
                        codigo_ot = int(row[0].strip())
                        tipo_ot_codigo = row[1].strip()
                        situacion_ot_codigo = row[2].strip()

                        # Parsear fechas
                        try:
                            fecha_emision = datetime.strptime(row[3].strip(), '%Y/%m/%d') if row[3].strip() else None
                        except ValueError:
                            fecha_emision = None

                        try:
                            fecha_proc = datetime.strptime(row[4].strip(), '%Y/%m/%d') if row[4].strip() else None
                        except ValueError:
                            fecha_proc = None

                        try:
                            fecha_termino = datetime.strptime(row[5].strip(), '%Y/%m/%d') if row[5].strip() else None
                        except ValueError:
                            fecha_termino = None

                        # Datos de cliente y producto
                        cliente_codigo = row[7].strip()
                        nro_nota_venta_ot = row[8].strip()
                        item_nota_venta = int(row[9].strip()) if row[9].strip() else 0
                        referencia_nota_venta = int(row[10].strip()) if row[10].strip() else None
                        codigo_producto_inicial = row[11].strip()
                        codigo_producto_salida = row[12].strip()
                        descripcion_producto_ot = row[13].strip()

                        # Parsear cantidades
                        cantidad = self._parse_decimal(row[14].strip())
                        unidad_medida_codigo = row[15].strip()
                        cantidad_avance = self._parse_decimal(row[16].strip())
                        peso_unitario = self._parse_decimal(row[17].strip())
                        materia_prima_codigo = row[18].strip()
                        cantidad_materia_prima = self._parse_decimal(row[19].strip())
                        unidad_materia_prima_codigo = row[20].strip()
                        observacion_ot = row[21].strip()
                        empresa_codigo = row[22].strip()
                        multa_valor = row[23].strip()
                        valor_unitario = row[24].strip()

                        # Crear objetos relacionados
                        tipo_ot, _ = TipoOT.objects.get_or_create(codigo_tipo_ot=tipo_ot_codigo)
                        situacion_ot, _ = SituacionOT.objects.get_or_create(codigo_situacion_ot=situacion_ot_codigo)

                        # Cliente (solo si es válido)
                        cliente = None
                        if cliente_codigo and cliente_codigo != '000000' and len(cliente_codigo) < 7:
                            cliente, _ = Cliente.objects.get_or_create(codigo_cliente=cliente_codigo)

                        # Unidades de medida
                        unidad_medida, _ = MeasurementUnit.objects.get_or_create(codigo_und_medida=unidad_medida_codigo)
                        unidad_medida_mprima, _ = MeasurementUnit.objects.get_or_create(codigo_und_medida=unidad_materia_prima_codigo)

                        # Materia prima
                        materia_prima = None
                        if materia_prima_codigo:
                            materia_prima, _ = MateriaPrima.objects.get_or_create(codigo=materia_prima_codigo)

                        # Empresa
                        empresa, _ = EmpresaOT.objects.get_or_create(codigo_empresa=empresa_codigo)

                        # Multa
                        multa = multa_valor == 'M'


                        # Solo importar órdenes con situación P o S
                        if situacion_ot.codigo_situacion_ot in ['P', 'S']:
                            orden_trabajo, created = OrdenTrabajo.objects.update_or_create(
                                codigo_ot=codigo_ot,
                                defaults={
                                    'tipo_ot': tipo_ot,
                                    'situacion_ot': situacion_ot,
                                    'fecha_emision': fecha_emision,
                                    'fecha_proc': fecha_proc,
                                    'fecha_termino': fecha_termino,
                                    'cliente': cliente,
                                    'nro_nota_venta_ot': nro_nota_venta_ot,
                                    'item_nota_venta': item_nota_venta,
                                    'referencia_nota_venta': referencia_nota_venta,
                                    'codigo_producto_inicial': codigo_producto_inicial,
                                    'codigo_producto_salida': codigo_producto_salida,
                                    'descripcion_producto_ot': descripcion_producto_ot,
                                    'cantidad': cantidad,
                                    'unidad_medida': unidad_medida,
                                    'cantidad_avance': cantidad_avance,
                                    'peso_unitario': peso_unitario,
                                    'materia_prima': materia_prima,
                                    'cantidad_mprima': cantidad_materia_prima,
                                    'unidad_medida_mprima': unidad_medida_mprima,
                                    'observacion_ot': observacion_ot,
                                    'empresa': empresa,
                                    'multa': multa,
                                    'valor': valor_unitario
                                }
                            )

                            if created:
                                self.log_info(f'Orden de trabajo {codigo_ot} creada.')
                                created_count += 1
                            else:
                                self.log_info(f'Orden de trabajo {codigo_ot} actualizada.')
                                updated_count += 1
                        else:
                            continue

                    except (ValueError, IntegrityError) as e:
                        error_msg = f'Error en fila {row_num}: {str(e)}'
                        self.log_error(error_msg)
                        failed_count += 1
                        errors.append(error_msg)

                    except Exception as e:
                        error_msg = f'Error inesperado en fila {row_num}: {str(e)}'
                        self.log_error(error_msg)
                        failed_count += 1
                        errors.append(error_msg)

        except UnicodeDecodeError as e:
            error_msg = f'Error de codificación con {encoding}: {str(e)}'
            self.log_error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

        resultado = {
            'success': True,
            'created_count': created_count,
            'updated_count': updated_count,
            'failed_count': failed_count,
            'errors': errors
        }

        self.log_info(f"=== IMPORTACIÓN DE ÓRDENES COMPLETADA ===")
        self.log_info(f"Creadas: {created_count}, Actualizadas: {updated_count}, Fallidas: {failed_count}")

        return resultado

    def importar_rutas_ot(self):
        """Importa rutas de órdenes de trabajo desde archivo fijo"""
        self.log_info(f"=== INICIANDO IMPORTACIÓN DE RUTAS OT ===")
        self.log_info(f"Archivo: {self.ARCHIVO_RUTA_OT}")

        created_count = 0
        updated_count = 0
        failed_count = 0
        errors = []
        estandares_corregidos = 0

        # Obtener códigos de OT existentes
        ordenes = OrdenTrabajo.objects.all()
        codigos_ot = set(orden.codigo_ot for orden in ordenes)
        self.log_info(f"Encontradas {len(codigos_ot)} órdenes de trabajo existentes")

        # Detectar codificación
        with open(self.ARCHIVO_RUTA_OT, 'rb') as f:
            resultado = chardet.detect(f.read())
            encoding = resultado['encoding']

        self.log_info(f'Usando codificación detectada: {encoding}')

        try:
            with open(self.ARCHIVO_RUTA_OT, 'r', encoding=encoding) as file:
                reader = csv.reader(file, delimiter='@')
                next(reader)  # Saltar header

                for row_num, row in enumerate(reader, start=2):
                    try:
                        if len(row) != 9:
                            self.log_error(f'Fila {row_num} inválida: esperadas 9 columnas, obtenidas {len(row)}')
                            failed_count += 1
                            continue

                        codigo_ot = int(row[0].strip())
                        
                        # Solo procesar si la OT existe
                        if codigo_ot not in codigos_ot:
                            continue

                        item = int(row[1].strip())
                        codigo_proceso = row[2].strip()
                        codigo_maquina = row[3].strip()
                        estandar = int(row[4].strip()) if row[4].strip() else 0

                        
                        # Parsear cantidades
                        cantidad_pedido = self._parse_decimal(row[5].strip())
                        cantidad_terminado = self._parse_decimal(row[6].strip())
                        cantidad_perdida = self._parse_decimal(row[7].strip())
                        terminado_sin_actualizar = self._parse_decimal(row[8].strip())

                        # Validaciones adicionales para OTs terminadas
                        three_months_ago = datetime.now().date() - timedelta(days=90)
                        orden_trabajo = ordenes.get(codigo_ot=codigo_ot)
                        situacion_ot = orden_trabajo.situacion_ot.codigo_situacion_ot
                        fecha_termino = orden_trabajo.fecha_termino

                        # Obtener el código de producto o pieza desde la OT
                        codigo_prod_pieza = orden_trabajo.codigo_producto_salida

                        # Buscar primero como Producto
                        objeto = Producto.objects.filter(codigo_producto=codigo_prod_pieza).first()
                        ruta_objeto = None

                        if objeto:
                            # Si es producto, buscar la ruta asociada
                            ruta_objeto = getattr(objeto, 'ruta', None)
                        else:
                            # Si no es producto, buscar como Pieza
                            objeto = Pieza.objects.filter(codigo_pieza=codigo_prod_pieza).first()
                            if objeto:
                                ruta_objeto = getattr(objeto, 'ruta_pieza', None)

                        # Si encontramos la ruta, buscar el estándar correspondiente
                        estandar_ruta = 0
                        if ruta_objeto:
                            # Buscar el item de ruta que coincida con el proceso y máquina
                            item_ruta_obj = ruta_objeto.items.filter(
                                proceso__codigo_proceso=codigo_proceso,
                                maquina__codigo_maquina=codigo_maquina
                            ).first()
                            if item_ruta_obj:
                                estandar_ruta = item_ruta_obj.estandar

                        # Si el estándar del archivo es 0, usar el de la ruta
                        if estandar == 0 and estandar_ruta:
                            estandar = estandar_ruta
                            estandares_corregidos += 1


                        # Crear RutaOT si no existe
                        ruta_ot, created_ruta = RutaOT.objects.get_or_create(orden_trabajo=orden_trabajo)

                        # Obtener máquina y proceso
                        try:
                            maquina = Maquina.objects.get(codigo_maquina=codigo_maquina)
                        except Maquina.DoesNotExist:
                            self.log_warning(f"Máquina {codigo_maquina} no encontrada en fila {row_num}")
                            continue

                        try:
                            proceso = Proceso.objects.get(codigo_proceso=codigo_proceso)
                        except Proceso.DoesNotExist:
                            self.log_warning(f"Proceso {codigo_proceso} no encontrado en fila {row_num}")
                            continue
                        except MultipleObjectsReturned:
                            proceso = Proceso.objects.filter(codigo_proceso=codigo_proceso).first()
                            self.log_warning(f"Múltiples procesos {codigo_proceso} encontrados, usando el primero")

                        # Crear ItemRuta
                        with transaction.atomic():
                            item_ruta, created_item = ItemRuta.objects.get_or_create(
                                ruta=ruta_ot,
                                item=item,
                                defaults={
                                    'maquina': maquina,
                                    'proceso': proceso,
                                    'estandar': estandar,
                                    'cantidad_pedido': cantidad_pedido,
                                    'cantidad_terminado_proceso': cantidad_terminado,
                                    'cantidad_perdida_proceso': cantidad_perdida,
                                    'terminado_sin_actualizar': terminado_sin_actualizar,
                                }
                            )

                            if not created_item:
                                # Lógica para actualizar según situación de la OT
                                if situacion_ot in ['C', 'A']:
                                    pass  # No actualizar
                                elif situacion_ot == 'T' and fecha_termino and fecha_termino <= three_months_ago:
                                    item_ruta.cantidad_pedido = cantidad_pedido
                                    item_ruta.cantidad_terminado_proceso = cantidad_terminado
                                    item_ruta.cantidad_perdida_proceso = cantidad_perdida
                                    item_ruta.terminado_sin_actualizar = terminado_sin_actualizar
                                    item_ruta.save()
                                elif situacion_ot not in ['C', 'A', 'T']:
                                    item_ruta.cantidad_pedido = cantidad_pedido
                                    item_ruta.cantidad_terminado_proceso = cantidad_terminado
                                    item_ruta.cantidad_perdida_proceso = cantidad_perdida
                                    item_ruta.terminado_sin_actualizar = terminado_sin_actualizar
                                    item_ruta.save()

                                updated_count += 1
                            else:
                                created_count += 1

                    except (ValueError, IntegrityError) as e:
                        error_msg = f'Error en fila {row_num}: {str(e)}'
                        self.log_error(error_msg)
                        failed_count += 1
                        errors.append(error_msg)

                    except Exception as e:
                        error_msg = f'Error inesperado en fila {row_num}: {str(e)}'
                        self.log_error(error_msg)
                        failed_count += 1
                        errors.append(error_msg)

                self.log_info(f"Estandares corregidos desde producto/pieza: {estandares_corregidos}")

        except UnicodeDecodeError as e:
            error_msg = f'Error de codificación con {encoding}: {str(e)}'
            self.log_error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

        resultado = {
            'success': True,
            'created_count': created_count,
            'updated_count': updated_count,
            'failed_count': failed_count,
            'errors': errors
        }

        self.log_info(f"=== IMPORTACIÓN DE RUTAS COMPLETADA ===")
        self.log_info(f"Creadas: {created_count}, Actualizadas: {updated_count}, Fallidas: {failed_count}")

        return resultado

    def _parse_decimal(self, value_str):
        """Convierte string a decimal manejando valores vacíos"""
        if not value_str or value_str.strip() in ['', ' ', '.', '. ', ' .']:
            return 0.0
        try:
            return float(value_str)
        except ValueError:
            return 0.0

    def verificar_archivos(self):
        """Verifica que los archivos fijos existan"""
        archivos_faltantes = []
        
        if not os.path.exists(self.ARCHIVO_OT):
            archivos_faltantes.append(self.ARCHIVO_OT)
            
        if not os.path.exists(self.ARCHIVO_RUTA_OT):
            archivos_faltantes.append(self.ARCHIVO_RUTA_OT)
            
        return archivos_faltantes

    def handle(self, *args, **options):
        try:
            # Configurar logging
            log_file = options['log_file']
            self.setup_logging(log_file)

            self.obtener_ruta_archivos()

            confirmar = options['confirmar']
            dry_run = options['dry_run']

            self.log_info(f"=== INICIANDO COMANDO REIMPORTAR ÓRDENES DE TRABAJO ===")
            self.log_info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_info(f"Archivo OT: {self.ARCHIVO_OT}")
            self.log_info(f"Archivo Rutas OT: {self.ARCHIVO_RUTA_OT}")

            # Verificar archivos
            archivos_faltantes = self.verificar_archivos()
            if archivos_faltantes:
                for archivo in archivos_faltantes:
                    self.log_error(f"Archivo no encontrado: {archivo}")
                return

            # Verificar confirmación
            if not confirmar and not dry_run:
                self.log_warning("ADVERTENCIA: Esta operación eliminará TODOS los datos de órdenes de trabajo existentes.")
                self.log_warning("Para confirmar la operación, ejecute nuevamente con --confirmar")
                self.log_warning("Para ver qué se eliminaría sin realizar cambios, use --dry-run")
                return

            # Limpiar datos existentes
            conteos_eliminados = self.limpiar_datos_existentes(dry_run)

            if dry_run:
                self.log_info("MODO DRY-RUN: No se realizarán más operaciones")
                return

            # Importar órdenes de trabajo
            resultado_ot = self.importar_ordenes_trabajo()
            if not resultado_ot['success']:
                self.log_error("Error en importación de órdenes de trabajo")
                return

            # Importar rutas de órdenes de trabajo
            resultado_rutas = self.importar_rutas_ot()
            if not resultado_rutas['success']:
                self.log_error("Error en importación de rutas de órdenes de trabajo")
                return

            # Resumen final
            self.log_info("=== RESUMEN FINAL ===")
            self.log_info("Datos eliminados:")
            for tabla, cantidad in conteos_eliminados.items():
                self.log_info(f"  - {tabla}: {cantidad}")

            self.log_info("Órdenes de trabajo:")
            self.log_info(f"  - Creadas: {resultado_ot['created_count']}")
            self.log_info(f"  - Actualizadas: {resultado_ot['updated_count']}")
            self.log_info(f"  - Fallidas: {resultado_ot['failed_count']}")

            self.log_info("Rutas de órdenes:")
            self.log_info(f"  - Creadas: {resultado_rutas['created_count']}")
            self.log_info(f"  - Actualizadas: {resultado_rutas['updated_count']}")
            self.log_info(f"  - Fallidas: {resultado_rutas['failed_count']}")

            self.log_info(f"=== PROCESO COMPLETADO EXITOSAMENTE ===")
            self.log_info(f"Log detallado guardado en: {os.path.abspath(log_file)}")

        except Exception as e:
            self.log_error(f"Error general en el comando: {str(e)}")
            raise