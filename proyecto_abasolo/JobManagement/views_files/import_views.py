from django.http import JsonResponse
from django.db import IntegrityError, transaction
from django.core.exceptions import MultipleObjectsReturned
from datetime import datetime, timedelta
import csv, chardet

from ..models import (
    OrdenTrabajo,
    TipoOT,
    SituacionOT,
    RutaOT,
    ItemRuta,
    Maquina,
    Proceso, 
    EmpresaOT
)

from Client.models import Cliente
from Utils.models import MeasurementUnit, MateriaPrima

def importar_ordenes_trabajo(path_file):
    created_count = 0
    updated_count = 0
    failed_count = 0
    errors = []

    with open(path_file, 'rb') as f:
        result = chardet.detect(f.read())
        encoding = result['encoding']

    print(f'Usando la codificación detectada: {encoding}')
    try:
        with open(path_file, 'r', encoding=encoding) as file:
            reader = csv.reader(file, delimiter='$')
            next(reader)

            for row in reader:
                #if row[2].strip() in ['P', 'S']:
                try:
                    if len(row) != 24:
                        print(f"Fila inválida: {row}")
                        continue
                    
                    codigo_ot = int(row[0].strip())
                    tipo_ot_codigo = row[1].strip()
                    situacion_ot_codigo = row[2].strip()
                    try:
                        fecha_emision = datetime.strptime(row[3].strip(), '%Y/%m/%d')
                    except ValueError:
                        fecha_emision = None

                    try:
                        fecha_proc = datetime.strptime(row[4].strip(), '%Y/%m/%d')
                    except ValueError:
                        fecha_proc = None

                    try:
                        fecha_termino = datetime.strptime(row[5].strip(), '%Y/%m/%d')
                    except ValueError:
                        fecha_termino = None

                    cliente_codigo = row[7].strip()
                    nro_nota_venta_ot = row[8].strip()
                    item_nota_venta = int(row[9].strip())
                    referencia_nota_venta = int(row[10].strip())
                    codigo_producto_inicial = row[11].strip()
                    codigo_producto_salida = row[12].strip()
                    descripcion_producto_ot = row[13].strip()

                    try:
                        cantidad_str = row[14].strip()
                        puntos = puntos = ['', ' ', '.', '. ',' .']

                        if cantidad_str in puntos:
                            cantidad = 0.0
                        else:
                            cantidad = float(cantidad_str)
                    except (ValueError, IndexError) as e:
                        print(f'Error al convertir la cantidad en la fila: {row}: {str(e)}')
                        cantidad = 0.0

                    unidad_medida_codigo = row[15].strip()

                    try:
                        cantidad_avance_str = row[16].strip()
                        puntos = ['', ' ', '.', '. ',' .']
                        if cantidad_avance_str in puntos:
                            cantidad_avance = 0.0
                        else:
                            cantidad_avance = float(cantidad_avance_str)
                    except(ValueError, IndexError):
                        print(f'Error al convertir la cantidad_avance en la fila: {row} : {str(e)}')
                        cantidad_avance = 0.0

                    try:
                        peso_unitario_str = row[17].strip()
                        puntos = ['', ' ', '.', '. ',' .']
                        if peso_unitario_str in puntos:
                            peso_unitario = 0.0
                        else: 
                            peso_unitario = float(peso_unitario_str)
                    except(ValueError, IndexError) as e:
                        print(f'Error al convertir el peso unitario en la fila: {row} : {str(e)}')
                        peso_unitario = 0.0

                    materia_prima_codigo = row[18].strip()

                    try:
                        cantidad_materia_prima_str = row[17].strip()
                        puntos = ['', ' ', '.', '. ',' .']
                        if cantidad_materia_prima_str in puntos:
                            cantidad_materia_prima = 0.0
                        else:
                            cantidad_materia_prima = float(cantidad_materia_prima_str)
                    
                    except(ValueError, IndexError) as e:
                        print(f'Error al convertir la cantidad de materia prima en la fila: {row} : {str(e)}')
                        cantidad_materia_prima = 0.0

                    unidad_materia_prima_codigo = row[20].strip()

                    observacion_ot = row[21].strip()
                    empresa_codigo = row[22].strip()

                    multa_valor = row[23].strip()
                    
                    tipo_ot, _ = TipoOT.objects.get_or_create(codigo_tipo_ot=tipo_ot_codigo)

                    situacion_ot, _ = SituacionOT.objects.get_or_create(codigo_situacion_ot=situacion_ot_codigo)

                    if cliente_codigo != '000000' and len(cliente_codigo) < 7 and cliente_codigo != '':
                        cliente, _ = Cliente.objects.get_or_create(codigo_cliente=cliente_codigo)
                    else:
                        cliente = None

                    unidad_medida, _ = MeasurementUnit.objects.get_or_create(codigo_und_medida=unidad_materia_prima_codigo)

                    materia_prima, _ = MateriaPrima.objects.get_or_create(codigo=materia_prima_codigo)

                    unidad_medida_mprima, _ = MeasurementUnit.objects.get_or_create(codigo_und_medida=unidad_materia_prima_codigo)

                    empresa, _ = EmpresaOT.objects.get_or_create(codigo_empresa=empresa_codigo)

                    multa = multa_valor == 'M'

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
                        }
                        )
                        if created:
                            print(f'Orden de trabajo {codigo_ot} creada.')
                            created_count+=1
                        else:
                            print(f'Orden de trabajo {codigo_ot} actualizada.')
                            updated_count+=1
                    else:
                        print('Situación no correspondiente. Saltando...')
                        continue
                    

                except (ValueError, IntegrityError) as e:
                    print(f'Error al procesar la fila {row}: {str(e)}')
                    failed_count += 1
                    errors.append(str(e))

                except Exception as e:
                    print(f'Error inesperado al procesar la fila {row}: {str(e)}')
                    failed_count += 1
                    errors.append(str(e))
    except UnicodeDecodeError:
        print(f'Error de codificación con {encoding}')
    
    return {
        'success': True,
        'created_count': created_count,
        'updated_count': updated_count,
        'failed_count': failed_count,
        'errors': errors
    }

def importar_ots_from_file(request):
    path_file = 'W:\\ot.txt'
    result = importar_ordenes_trabajo(path_file)
    if result['success']:
        return JsonResponse({
            'message': 'OrdenTrabajo instances imported successfully',
            'created_count': result['created_count'],
            'updated_count': result['updated_count'],
            'failed_count': result['failed_count'],
            'errors': result['errors'],
        }, status=200)
    else:
        return JsonResponse({'error': result['errors']}, status=500)

def importar_rutas_ot(path_file):
    created_count = 0
    updated_count = 0
    failed_count = 0
    errors = []
    ordenes = OrdenTrabajo.objects.all()
    codigos_ot = []
    for orden in ordenes:
        codigos_ot.append(orden.codigo_ot)

    with open(path_file, 'rb') as f:
        resultado = chardet.detect(f.read())
        encoding = resultado['encoding']
    print(f'Usando la codificación detectada: {encoding}')
    try:
        with open(path_file, 'r', encoding=encoding) as file:
            reader = csv.reader(file, delimiter='@')
            next(reader)

    
            for idx, row in enumerate(reader):
                try:
                    if len(row) != 9:
                        print(f'Fila inválida: {idx}')
                        continue
                    
                    codigo_ot = int(row[0].strip())
                    if codigo_ot in codigos_ot:
                        item = int(row[1].strip())

                        codigo_proceso = row[2].strip()
                        codigo_maquina = row[3].strip()

                        estandar = int(row[4].strip())
                        try:
                            cantidad_pedido_str = row[5].strip()
                            puntos = ['', ' ', '.', '. ',' .']

                            if cantidad_pedido_str in puntos:
                                cantidad_pedido = 0.0
                            else:
                                cantidad_pedido = float(cantidad_pedido_str)
                        except(ValueError, IndexError) as e:
                            print(f'Error al convretir la cantidad_pedido en la fila: {idx} - {str(e)}')

                        try:
                            cantidad_terminado_str = row[6].strip()
                            puntos = ['', ' ', '.', '. ',' .']

                            if cantidad_terminado_str in puntos:
                                cantidad_terminado = 0.0
                            else:
                                cantidad_terminado = float(cantidad_terminado_str)
                        except(ValueError, IndexError) as e:
                            print(f'Error al convertir la cantidad_terminado en la fila: {idx} - {str(e)}')

                        try:
                            cantidad_terminado_str = row[6].strip()
                            puntos = ['', ' ', '.', '. ',' .']

                            if cantidad_terminado_str in puntos:
                                cantidad_terminado = 0.0
                            else:
                                cantidad_terminado = float(cantidad_terminado_str)
                        except(ValueError, IndexError) as e:
                            print(f'Error al convertir la cantidad_terminado en la fila: {idx} - {str(e)}')

                        try:
                            cantidad_perdida_str = row[7].strip()
                            puntos = ['', ' ', '.', '. ',' .']

                            if cantidad_perdida_str in puntos:
                                cantidad_perdida = 0.0
                            else:
                                cantidad_perdida = float(cantidad_perdida_str)

                        except(ValueError, IndexError) as e:
                            print(f'Error al convertir la cantidad_perdida en la fila: {row} - {str(e)}')

                        try:
                            terminado_sin_actualizar_str = row[8].strip()
                            puntos = ['', ' ', '.', '. ', ' .']

                            if terminado_sin_actualizar_str in puntos:
                                terminado_sin_actualizar = 0.0
                            else:
                                terminado_sin_actualizar = float(terminado_sin_actualizar_str)
                        
                        except(ValueError, IndexError) as e: 
                            print(f'Error al convertir el campo terminado_sin_actualizar en la fila: {idx} - {str(e)}')

                        try:
                            three_months_ago = datetime.now().date() - timedelta(days=90)
                        except:
                            continue
                        
                        
                        orden_trabajo = ordenes.get(codigo_ot=codigo_ot)

                        situacion_ot = orden_trabajo.situacion_ot.codigo_situacion_ot
                        fecha_termino = orden_trabajo.fecha_termino
                        

                        ruta_ot, created_ruta = RutaOT.objects.get_or_create(orden_trabajo=orden_trabajo)
                        ### crear rutas que matcheen con la ots existentes en el sistema.
                        try:
                            maquina = Maquina.objects.get(codigo_maquina=codigo_maquina)
                        except Maquina.DoesNotExist:
                            continue

                        try:
                            proceso = Proceso.objects.get(codigo_proceso=codigo_proceso)
                        except Proceso.DoesNotExist:
                            continue
                        except MultipleObjectsReturned:
                            proceso = Proceso.objects.filter(codigo_proceso=codigo_proceso).first()

                        try:
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
                                        'terminado_sin_actualizar' : terminado_sin_actualizar,

                                    }
                                )

                                if not created_item:
                                    if situacion_ot in ['C', 'A']:
                                        pass
                                    elif situacion_ot == 'T' and fecha_termino <= three_months_ago and fecha_termino is not None:
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

                                    print(f'ItemRuta de OT {item_ruta} actualizado.')
                                    updated_count +=1
                                else:
                                    print(f'ItemRuta de OT {item_ruta} creada.')
                                    created_count +=1
                        except Exception as e:
                            print(f'Error inesperado al procesar la fila {row}: {str(e)}')
                            failed_count += 1
                            errors.append(str(e))
                    else:
                        print(f'Orden {codigo_ot} no válida.')
                        continue
                    
                except (ValueError, IntegrityError) as e:
                    print(f'Error al procesar la fila: {row} : {str(e)}')
                    failed_count += 1
                    errors.append(str(e))
                except Exception as e:
                    print(f'Error inesperado al procesar la fila {row}: {str(e)}')
                    failed_count += 1
                    errors.append(str(e))
    except UnicodeDecodeError:
        print(f'Error de codificación con {encoding}')

    return {
        'success': True,
        'created_count': created_count,
        'updated_count': updated_count,
        'failed_count': failed_count,
        'errors': errors
    }

def importar_rutaot_file(request):
    path_file = 'W:\\ruta_ot.txt'
    result = importar_rutas_ot(path_file)
    if result['success']:
        return JsonResponse({
            'message': 'RutaOT instances imported successfully',
            'created_count': result['created_count'],
            'updated_count': result['updated_count'],
            'failed_count': result['failed_count'],
            'errors': result['errors'],
        }, status=200)
    else:
        return JsonResponse({'error': result['errors']}, status=500)

def importar_avances_produccion(fecha_referencia, programa_id=None):
    """
    Importa solo los avances de producción sin eliminar datos existentes
    Similar a las funciones existentes pero solo actualiza cantidades
    """

    path_ot = 'W:\\ot.txt'
    path_ruta = 'W:\\ruta_ot.txt'

    resultado = {
        'fecha_referencia': fecha_referencia,
        'programa_id': programa_id,
        'ots_procesadas': 0,
        'items_actualizados': 0,
        'cambios_detectados': [],
        'errores': []
    }

    try:
        # 1. Procesar avances de OTs
        avances_ots = procesar_avances_ots(path_ot, programa_id)
        resultado['ots_procesadas'] = len(avances_ots)

        # 2. Procesar avances de ItemRutas
        cambios_items = procesar_avances_items_ruta(path_ruta, programa_id)
        resultado['items_actualizados'] = len(cambios_items)
        resultado['cambios_detectados'] = cambios_items

        return resultado
    
    except Exception as e:
        resultado['errores'].append(str(e))
        return resultado
    
def procesar_avances_ots(path_file, programa_id=None):
    """Procesa solo los cambios en cantidad_avance de las OTs"""

    avances_procesados = []

    # Obtener OTs del programa si se especifica
    if programa_id:
        ots_programa = OrdenTrabajo.objects.filter(
            programaordentrabajo__programa_id=programa_id
        ).values_list('codigo_ot', flat=True)
    else:
        ots_programa = None

    #Detectar encoding como en la función original
    with open(path_file, 'rb') as f:
        result = chardet.detect(f.read())
        encoding = result['encoding']

    with open(path_file, 'r', encoding=encoding) as file:
        reader = csv.reader(file, delimiter='$')
        next(reader) #saltar header

        for row in reader:
            try:
                if len(row) != 24:
                    continue

                codigo_ot = int(row[0].strip())

                #Solo procesar OTs del programa si se especifica
                if ots_programa and codigo_ot not in ots_programa:
                    continue

                #Leer cantidad_avance del archivo
                try:
                    cantidad_avance_str = row[16].strip()
                    puntos = ['', ' ', '.', '. ', ' .']
                    if cantidad_avance_str in puntos:
                        cantidad_avance_nueva = 0.0
                    else:
                        cantidad_avance_nueva = float(cantidad_avance_str)
                except (ValueError, IndexError):
                    continue

                # Buscar OT existente
                try:
                    ot = OrdenTrabajo.objects.get(codigo_ot=codigo_ot)
                    cantidad_anterior = float(ot.cantidad_avance)

                    #Solo actualizar si hay diferencia
                    if abs(cantidad_avance_nueva - cantidad_anterior) > 0.01:
                        ot.cantidad_avance = cantidad_avance_nueva
                        ot.save(update_fields=['cantidad_avance'])

                        avances_procesados.append({
                            'codigo_ot': codigo_ot,
                            'cantidad_anterior': cantidad_anterior,
                            'cantidad_nueva': cantidad_avance_nueva,
                            'diferencia': cantidad_avance_nueva - cantidad_anterior
                        })

                except OrdenTrabajo.DoesNotExist:
                    continue

            except Exception as e:
                print(f"Error procesando OT {codigo_ot}: {str(e)}")
                continue
            
        return avances_procesados
    
def procesar_avances_items_ruta(path_file, programa_id=None):
    """Procesa solo los cambios en cantidades de ItemRuta"""

    cambios_procesados = []

    #Obtener códigos de OT del programa si se especifica
    if programa_id:
        ots_programa = OrdenTrabajo.objects.filter(
            programaordentrabajo__programa_id=programa_id
        ).values_list('codigo_ot', flat=True)
    else:
        ots_programa = None

    #Detectar encoding
    with open(path_file, 'rb') as f:
        resultado = chardet.detect(f.read())
        encoding = resultado['encoding']

    with open(path_file, 'r', encoding=encoding) as file:
        reader = csv.reader(file, delimiter='@')
        next(reader) #Saltar header

        for idx, row in enumerate(reader):
            try:
                if len(row) != 9:
                    continue

                codigo_ot = int(row[0].strip())

                #Solo procesar OTs del programa
                if ots_programa and codigo_ot not in ots_programa:
                    continue

                item = int(row[1].strip())
                codigo_proceso = row[2].strip()

                #Leer cantidades del archivo
                try:
                    #Cantidad terminado
                    cantidad_terminado_str = row[6].strip()
                    puntos = ['', ' ', '.', '. ', ' .']
                    if cantidad_terminado_str in puntos:
                        cantidad_terminado_nueva = 0.0
                    else:
                        cantidad_terminado_nueva = float(cantidad_terminado_str)
                    
                    #Cantidad perdida
                    cantidad_perdida_str = row[7].strip()
                    if cantidad_perdida_str in puntos:
                        cantidad_perdida_nueva = 0.0
                    else:
                        cantidad_perdida_nueva = float(cantidad_perdida_str)

                except (ValueError,  IndexError):
                    continue

                #Buscar ItemRuta existente
                try:
                    item_ruta = ItemRuta.objects.select_related('ruta__orden_trabajo', 'proceso').get(
                        ruta__orden_trabajo__codigo_ot=codigo_ot,
                        item=item,
                        proceso__codigo_proceso=codigo_proceso
                    )

                    #Guardar valores anteriores
                    cantidad_terminado_anterior = float(item_ruta.cantidad_terminado_proceso)
                    cantidad_perdida_anterior = float(item_ruta.cantidad_perdida_proceso)
                    estado_anterior = item_ruta.estado_proceso

                    #Verificar si hay cambios significativos
                    cambio_terminado = abs(cantidad_terminado_nueva - cantidad_terminado_anterior) > 0.01
                    cambio_perdida = abs(cantidad_perdida_nueva - cantidad_perdida_anterior) > 0.01

                    if cambio_terminado or cambio_perdida:
                        #Aplicar cambios usando el método del modelo
                        if cambio_terminado:
                            item_ruta.actualizar_progreso(
                                cantidad_completada_nueva=cantidad_terminado_nueva,
                                observaciones="Importado de sistema externo"
                            )

                        if cambio_perdida:
                            item_ruta.cantidad_perdida_proceso = cantidad_perdida_nueva
                            item_ruta.save(update_fields=['cantidad_perdida_proceso'])

                        #Registrar el cambio
                        cambio = {
                            'codigo_ot': codigo_ot,
                            'item': item,
                            'codigo_proceso': codigo_proceso,
                            'proceso_descripcion': item_ruta.proceso.descripcion,
                            'cambios': {
                                'cantidad_terminado': {
                                    'anterior': cantidad_terminado_anterior,
                                    'nueva': cantidad_terminado_nueva,
                                    'diferencia': cantidad_terminado_nueva -cantidad_terminado_anterior
                                } if cambio_terminado else None,
                                'cantidad_perdida': {
                                    'anterior': cantidad_perdida_anterior,
                                    'nueva': cantidad_perdida_nueva,
                                    'diferencia': cantidad_perdida_nueva - cantidad_perdida_anterior
                                } if cambio_perdida else None,
                                'estado': {
                                    'anterior': estado_anterior,
                                    'nuevo': item_ruta.estado_proceso
                                }
                            }
                        }

                        cambios_procesados.append(cambio)

                except ItemRuta.DoesNotExist:
                    continue

            except Exception as e:
                print(f"Error procesando ItemRuta fila {idx}: {str(e)}")
                continue

        return cambios_procesados
