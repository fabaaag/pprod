from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
import os, csv
import chardet

class Command(BaseCommand):
    help = 'Prueba la función de obtener rutas de archivos y importar avances con diagnóstico completo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--programa-id',
            type=int,
            help='ID del programa para filtrar las OTs',
            default=None
        )
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha en formato YYYY-MM-DD',
            default=str(date.today())
        )
        parser.add_argument(
            '--diagnostico-completo',
            action='store_true',
            help='Realizar diagnóstico completo BD vs archivos'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Iniciando prueba de rutas de importación'))
        
        # Importar las funciones
        try:
            from JobManagement.views_files.import_views import obtener_ruta_archivos, importar_avances_produccion
            self.stdout.write(self.style.SUCCESS('✅ Funciones importadas correctamente'))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'❌ Error importando funciones: {str(e)}'))
            return

        # 1. Probar detección de rutas
        self.stdout.write(self.style.WARNING('\n📂 PASO 1: Probando detección de rutas'))
        
        ot_path, ruta_path = obtener_ruta_archivos()
        
        self.stdout.write(f'  Ruta OT detectada: {ot_path}')
        self.stdout.write(f'  Ruta RUTA detectada: {ruta_path}')
        
        if ot_path and ruta_path:
            self.stdout.write(self.style.SUCCESS('✅ Rutas detectadas correctamente'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  No se detectaron rutas válidas'))
            return

        # 2. Verificar existencia de archivos
        self.stdout.write(self.style.WARNING('\n📄 PASO 2: Verificando archivos'))
        
        ot_existe = os.path.exists(ot_path) if ot_path else False
        ruta_existe = os.path.exists(ruta_path) if ruta_path else False
        
        self.stdout.write(f'  ot.txt existe: {"✅" if ot_existe else "❌"} {ot_path}')
        self.stdout.write(f'  ruta_ot.txt existe: {"✅" if ruta_existe else "❌"} {ruta_path}')
        
        if not (ot_existe and ruta_existe):
            self.stdout.write(self.style.WARNING('⚠️  Algunos archivos no existen, pero continuamos'))

        # 3. Verificar contenido de archivos (si existen)
        if ot_existe:
            self.stdout.write(self.style.WARNING('\n📊 PASO 3: Verificando contenido de ot.txt'))
            try:
                with open(ot_path, 'rb') as f:
                    raw_data = f.read(10000)
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']

                with open(ot_path, 'r', encoding=encoding) as f:
                    lineas_ot = len(f.readlines())
                    self.stdout.write(f'  ot.txt contiene {lineas_ot} líneas')

                # Leer primera línea para verificar formato
                with open(ot_path, 'r', encoding=encoding) as f:
                    primera_linea = f.readline().strip()
                    self.stdout.write(f'  Primera línea: {primera_linea[:100]}...' if len(primera_linea) > 100 else f'  Primera línea: {primera_linea}')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Error leyendo ot.txt: {str(e)}'))

        if ruta_existe:
            self.stdout.write(self.style.WARNING('\n📊 PASO 4: Verificando contenido de ruta_ot.txt'))
            try:
                with open(ruta_path, 'rb') as f:
                    raw_data = f.read(10000)
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']

                with open(ruta_path, 'r', encoding=encoding) as f:
                    lineas_ruta = len(f.readlines())
                    self.stdout.write(f'  ruta_ot.txt contiene {lineas_ruta} líneas')
                    
                # Leer primera línea para verificar formato
                with open(ruta_path, 'r', encoding=encoding) as f:
                    primera_linea = f.readline().strip()
                    self.stdout.write(f'  Primera línea: {primera_linea[:100]}...' if len(primera_linea) > 100 else f'  Primera línea: {primera_linea}')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Error leyendo ruta_ot.txt: {str(e)}'))

        # 4.5. NUEVO: Diagnóstico de comparación BD vs Archivos
        programa_id = options['programa_id']
        if programa_id:
            self.stdout.write(self.style.WARNING('\n🔍 PASO 4.5: Diagnóstico de comparación BD vs Archivos'))
            self.diagnosticar_bd_vs_archivos(programa_id, ot_path, ruta_path, options.get('diagnostico_completo', False))

        # 5. Probar función completa de importación
        self.stdout.write(self.style.WARNING('\n🔄 PASO 5: Probando importación completa'))
        
        fecha_test = options['fecha']
        
        self.stdout.write(f'  Fecha de prueba: {fecha_test}')
        self.stdout.write(f'  Programa ID: {programa_id or "Todos los programas"}')
        
        try:
            resultado = importar_avances_produccion(fecha_test, programa_id)
            
            self.stdout.write(self.style.SUCCESS('\n📊 RESULTADOS DE LA IMPORTACIÓN:'))
            self.stdout.write(f'  ✅ Fecha referencia: {resultado.get("fecha_referencia")}')
            self.stdout.write(f'  ✅ Programa ID: {resultado.get("programa_id")}')
            self.stdout.write(f'  ✅ OTs procesadas: {resultado.get("ots_procesadas", 0)}')
            self.stdout.write(f'  ✅ Items actualizados: {resultado.get("items_actualizados", 0)}')
            self.stdout.write(f'  ✅ Cambios detectados: {len(resultado.get("cambios_detectados", []))}')
            self.stdout.write(f'  ✅ Errores: {len(resultado.get("errores", []))}')
            
            # Mostrar archivos encontrados
            archivos = resultado.get('archivos_encontrados', {})
            self.stdout.write(f'\n📂 Archivos encontrados:')
            for tipo, encontrado in archivos.items():
                self.stdout.write(f'  {tipo}: {"✅" if encontrado else "❌"}')
            
            # Mostrar rutas utilizadas
            rutas = resultado.get('rutas_utilizadas', {})
            self.stdout.write(f'\n📁 Rutas utilizadas:')
            for tipo, ruta in rutas.items():
                self.stdout.write(f'  {tipo}: {ruta}')
            
            # Mostrar errores si los hay
            if resultado.get('errores'):
                self.stdout.write(self.style.WARNING(f'\n⚠️  ERRORES ENCONTRADOS:'))
                for i, error in enumerate(resultado['errores'], 1):
                    self.stdout.write(f'  {i}. {error}')
            
            # Mostrar algunos cambios detectados
            cambios = resultado.get('cambios_detectados', [])
            if cambios:
                self.stdout.write(self.style.SUCCESS(f'\n🔄 PRIMEROS CAMBIOS DETECTADOS (máximo 5):'))
                for i, cambio in enumerate(cambios[:5], 1):
                    self.stdout.write(f'  {i}. OT {cambio.get("codigo_ot")} - Item {cambio.get("item")} - Proceso {cambio.get("codigo_proceso")}')
                    
                    if cambio.get('cambios', {}).get('cantidad_terminado'):
                        ct = cambio['cambios']['cantidad_terminado']
                        self.stdout.write(f'     Cantidad terminado: {ct.get("anterior")} → {ct.get("nueva")} (Δ: {ct.get("diferencia")})')
            
            # Resultado final
            if len(resultado.get('errores', [])) == 0:
                self.stdout.write(self.style.SUCCESS('\n🎉 ¡IMPORTACIÓN EXITOSA!'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠️  IMPORTACIÓN COMPLETADA CON ALGUNOS ERRORES'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ ERROR EN LA IMPORTACIÓN: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'Traceback: {traceback.format_exc()}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Prueba completada'))

    def diagnosticar_bd_vs_archivos(self, programa_id, ot_path, ruta_path, diagnostico_completo=False):
        """Diagnóstica diferencias entre BD y archivos"""
        
        try:
            from JobManagement.models import ProgramaProduccion, ProgramaOrdenTrabajo
            
            # Obtener OTs del programa desde BD
            programa = ProgramaProduccion.objects.get(id=programa_id)
            prog_ots = ProgramaOrdenTrabajo.objects.filter(programa=programa).select_related('orden_trabajo')
            codigos_ot_bd = [str(prog_ot.orden_trabajo.codigo_ot) for prog_ot in prog_ots]
            
            self.stdout.write(f'  📋 Programa: {programa.nombre}')
            self.stdout.write(f'  📊 OTs en programa {programa_id}: {len(codigos_ot_bd)}')
            self.stdout.write(f'  📝 Códigos: {", ".join(codigos_ot_bd[:5])}{"..." if len(codigos_ot_bd) > 5 else ""}')
            
            # Analizar ot.txt
            if ot_path and os.path.exists(ot_path):
                self.analizar_ot_txt(ot_path, codigos_ot_bd, diagnostico_completo)
            
            # Analizar ruta_ot.txt
            if ruta_path and os.path.exists(ruta_path):
                self.analizar_ruta_ot_txt(ruta_path, codigos_ot_bd, diagnostico_completo)
            
            # Análisis detallado si se solicita
            if diagnostico_completo:
                self.analisis_detallado_programa(programa, ot_path, ruta_path)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Error en diagnóstico: {str(e)}'))

    def analizar_ot_txt(self, ot_path, codigos_ot_bd, mostrar_detalles=False):
        """Analiza el archivo ot.txt comparándolo con BD"""
        
        self.stdout.write(f'\n  📄 Analizando ot.txt:')
        codigos_en_archivo_ot = set()
        lineas_con_datos = 0
        
        try:
            # Detectar codificación automáticamente
            import chardet
            with open(ot_path, 'rb') as f:
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']
                
            self.stdout.write(f'    Codificación detectada: {encoding} (confianza: {confidence:.2f})')
            
            # ✅ FORZAR: Separador $ para ot.txt
            separador = '$'
            self.stdout.write(f'    Separador FORZADO: "{separador}"')
            
            with open(ot_path, 'r', encoding=encoding) as f:
                lineas = f.readlines()
                
            for i, linea in enumerate(lineas):
                if i == 0:  # Posible header
                    if linea.strip():
                        self.stdout.write(f'    Header: {linea.strip()[:80]}')
                    continue
                    
                if linea.strip():  # Solo líneas no vacías
                    lineas_con_datos += 1
                    
                    # Usar separador forzado
                    campos = linea.strip().split(separador)
                    if len(campos) > 0:
                        codigo_ot_raw = campos[0].strip()
                        
                        # Limpiar código OT (quitar ceros a la izquierda)
                        if codigo_ot_raw:
                            try:
                                codigo_ot = str(int(codigo_ot_raw))
                                codigos_en_archivo_ot.add(codigo_ot)
                            except ValueError:
                                codigo_ot = codigo_ot_raw.strip()
                                codigos_en_archivo_ot.add(codigo_ot)
                        
                # Mostrar primeras líneas si se solicita
                if mostrar_detalles and i <= 5 and linea.strip():
                    campos = linea.strip().split(separador)
                    codigo_extraido = campos[0].strip() if len(campos) > 0 else "N/A"
                    
                    try:
                        codigo_limpio = str(int(codigo_extraido)) if codigo_extraido != "N/A" else "N/A"
                    except:
                        codigo_limpio = codigo_extraido
                        
                    self.stdout.write(f'    Línea {i}: Raw="{codigo_extraido}" → Limpio="{codigo_limpio}" | {linea.strip()[:60]}...')
            
            self.stdout.write(f'    📊 Total líneas con datos: {lineas_con_datos}')
            self.stdout.write(f'    📊 Total OTs únicas en archivo: {len(codigos_en_archivo_ot)}')
            
            if codigos_en_archivo_ot:
                ejemplos_archivo = list(codigos_en_archivo_ot)[:5]
                self.stdout.write(f'    📝 Ejemplos códigos en archivo (limpios): {", ".join(ejemplos_archivo)}')

            # Comparar con BD
            coincidencias_ot = set(codigos_ot_bd) & codigos_en_archivo_ot
            solo_bd = set(codigos_ot_bd) - codigos_en_archivo_ot
            solo_archivo = codigos_en_archivo_ot - set(codigos_ot_bd)
            
            self.stdout.write(f'    ✅ Coincidencias BD ↔ Archivo: {len(coincidencias_ot)}')
            self.stdout.write(f'    🔵 Solo en BD: {len(solo_bd)}')
            self.stdout.write(f'    🟡 Solo en Archivo: {len(solo_archivo)}')
            
            if coincidencias_ot:
                ejemplos = list(coincidencias_ot)[:3]
                self.stdout.write(f'    📝 Ejemplos coincidencias: {", ".join(ejemplos)}')
            if solo_bd:
                ejemplos = list(solo_bd)[:3]
                self.stdout.write(f'    📝 Ejemplos solo BD: {", ".join(ejemplos)}')
            if solo_archivo:
                ejemplos = list(solo_archivo)[:3]
                self.stdout.write(f'    📝 Ejemplos solo archivo: {", ".join(ejemplos)}')
            
            return coincidencias_ot
                
        except Exception as e:
            self.stdout.write(f'    ❌ Error analizando ot.txt: {str(e)}')
            import traceback
            self.stdout.write(f'    Traceback: {traceback.format_exc()[:300]}')
            return set()

    def analizar_ruta_ot_txt(self, ruta_path, codigos_ot_bd, mostrar_detalles=False):
        """Analiza el archivo ruta_ot.txt comparándolo con BD"""
        
        self.stdout.write(f'\n  📄 Analizando ruta_ot.txt:')
        
        try:
            # Detectar codificación automáticamente
            import chardet
            with open(ruta_path, 'rb') as f:
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                
            self.stdout.write(f'    Codificación detectada: {encoding}')
            
            # ✅ FORZAR: Separador @ para ruta_ot.txt
            separador_ruta = '@'
            self.stdout.write(f'    Separador FORZADO: "{separador_ruta}"')
            
            with open(ruta_path, 'r', encoding=encoding) as f:
                lineas = f.readlines()
                
            codigos_en_ruta = set()
            items_por_ot = {}
            lineas_con_datos = 0
            
            for i, linea in enumerate(lineas):
                # No saltear header automáticamente, analizar todas las líneas
                if linea.strip():  # Solo líneas no vacías
                    lineas_con_datos += 1
                    campos = linea.strip().split(separador_ruta)
                    if len(campos) > 1:
                        codigo_ot_raw = campos[0].strip()
                        
                        # Limpiar código OT (quitar ceros a la izquierda)
                        if codigo_ot_raw:
                            try:
                                codigo_ot = str(int(codigo_ot_raw))
                                codigos_en_ruta.add(codigo_ot)
                                if codigo_ot not in items_por_ot:
                                    items_por_ot[codigo_ot] = 0
                                items_por_ot[codigo_ot] += 1
                            except ValueError:
                                codigo_ot = codigo_ot_raw
                                codigos_en_ruta.add(codigo_ot)
                                if codigo_ot not in items_por_ot:
                                    items_por_ot[codigo_ot] = 0
                                items_por_ot[codigo_ot] += 1
                        
                # Mostrar primeras líneas si se solicita
                if mostrar_detalles and i <= 5 and linea.strip():
                    campos = linea.strip().split(separador_ruta)
                    codigo_raw = campos[0].strip() if len(campos) > 0 else "N/A"
                    try:
                        codigo_limpio = str(int(codigo_raw)) if codigo_raw != "N/A" and codigo_raw.isdigit() else codigo_raw
                    except:
                        codigo_limpio = codigo_raw
                    self.stdout.write(f'    Línea {i}: Raw="{codigo_raw}" → Limpio="{codigo_limpio}" | {linea.strip()[:60]}...')
            
            self.stdout.write(f'    📊 Total líneas con datos: {lineas_con_datos}')
            self.stdout.write(f'    📊 Total OTs en ruta_ot: {len(codigos_en_ruta)}')
            self.stdout.write(f'    📊 Total líneas de procesos: {sum(items_por_ot.values())}')
            
            # Mostrar algunos códigos del archivo para debug
            if codigos_en_ruta:
                ejemplos_archivo = list(codigos_en_ruta)[:5]
                self.stdout.write(f'    📝 Ejemplos códigos en archivo (limpios): {", ".join(ejemplos_archivo)}')
            
            # Mostrar OTs con más procesos
            if items_por_ot:
                ots_mas_procesos = sorted(items_por_ot.items(), key=lambda x: x[1], reverse=True)[:3]
                self.stdout.write(f'    📈 OTs con más procesos: {ots_mas_procesos}')
            
            # Comparar con BD
            coincidencias_ruta = set(codigos_ot_bd) & codigos_en_ruta
            self.stdout.write(f'    ✅ OTs que están en BD Y ruta_ot.txt: {len(coincidencias_ruta)}')
            
            if coincidencias_ruta:
                ejemplos = list(coincidencias_ruta)[:5]
                self.stdout.write(f'    🎯 ESTAS OTs SE PUEDEN PROCESAR: {", ".join(ejemplos)}')
            
            return coincidencias_ruta, items_por_ot
                
        except Exception as e:
            self.stdout.write(f'    ❌ Error analizando ruta_ot.txt: {str(e)}')
            import traceback
            self.stdout.write(f'    Traceback: {traceback.format_exc()[:200]}')
            return set(), {}

    def analisis_detallado_programa(self, programa, ot_path, ruta_path):
        """Análisis detallado usando la MISMA lógica que las funciones de importación"""
        
        self.stdout.write(f'\n  🔍 ANÁLISIS DETALLADO - Programa {programa.id}:')
        
        prog_ots = programa.programaordentrabajo_set.all().select_related('orden_trabajo')

        
        # ✅ ANALIZAR SOLO LA PRIMERA OT PERO CON MÁXIMO DETALLE
        for i, prog_ot in enumerate(prog_ots[:1]):  
            ot = prog_ot.orden_trabajo
            self.stdout.write(f'\n    📋 OT {i+1}: {ot.codigo_ot}')
            self.stdout.write(f'       Descripción: {ot.descripcion_producto_ot[:50]}...')
            self.stdout.write(f'       BD - Cantidad: {ot.cantidad}, Avance BD: {ot.cantidad_avance}')
            
            # Buscar en ot.txt con lógica correcta
            datos_ot_archivo = self.buscar_ot_en_archivo(str(ot.codigo_ot).strip(), ot_path)
            if datos_ot_archivo:
                self.stdout.write(f'       📄 Encontrada en ot.txt')
            else:
                self.stdout.write(f'       ❌ NO encontrada en ot.txt')
            
            # ✅ ANALIZAR ITEMS: Usando lógica de importar_rutas_ot
            if hasattr(ot, 'ruta_ot') and ot.ruta_ot:
                items_bd = ot.ruta_ot.items.all().order_by('item')
                self.stdout.write(f'       🔧 Analizando {items_bd.count()} items:')
                
                for item in items_bd:
                    self.stdout.write(f'\n         🔍 Item {item.item}: Proceso {item.proceso.codigo_proceso}')
                    self.stdout.write(f'            BD - Terminado: {item.cantidad_terminado_proceso}, Perdida: {item.cantidad_perdida_proceso}')
                    
                    datos_item_archivo = self.buscar_item_en_archivo(ot.codigo_ot, item.item, ruta_path)
                    # El diagnóstico se muestra dentro de buscar_item_en_archivo
                        
            else:
                self.stdout.write(f'       ❌ Sin ruta en BD')
        
        if len(prog_ots) > 1:
            self.stdout.write(f'\n    📝 ... y {len(prog_ots) - 1} OTs más en el programa (solo se analizó la primera)')

    def buscar_ot_en_archivo(self, codigo_ot, ot_path):
        """Busca una OT específica en ot.txt usando la MISMA lógica que importar_ordenes_trabajo"""
        try:
            import chardet
            with open(ot_path, 'rb') as f:
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                encoding = result['encoding']
            
            codigo_ot_buscar = int(codigo_ot)
            self.stdout.write(f'       🔍 Buscando OT {codigo_ot_buscar} en {ot_path}')
            self.stdout.write(f'       📄 Codificación: {encoding}')
            
            lineas_procesadas = 0
            lineas_validas = 0
            ots_encontradas = []
            
            with open(ot_path, 'r', encoding=encoding) as file:
                # ✅ USAR: Misma lógica que importar_ordenes_trabajo
                reader = csv.reader(file, delimiter='$')
                next(reader)
                
                for row in reader:
                    lineas_procesadas += 1
                    
                    try:
                        if len(row) != 25 :  # ✅ MISMO: Validación de 24 campos
                            if lineas_procesadas <= 5:  # Solo mostrar primeras líneas problemáticas
                                self.stdout.write(f'       ⚠️  Línea {lineas_procesadas}: {len(row)} campos (esperaba 24)')
                            continue
                        
                        lineas_validas += 1
                        
                        # ✅ MISMO: Código OT (campo 0)
                        codigo_ot_archivo_raw = row[0].strip()
                        codigo_ot_archivo = int(codigo_ot_archivo_raw)
                        
                        # Guardar las primeras 5 OTs encontradas para diagnóstico
                        if len(ots_encontradas) < 5:
                            ots_encontradas.append(codigo_ot_archivo)
                        
                        # ✅ COMPARAR
                        if codigo_ot_archivo == codigo_ot_buscar:
                            # ✅ LEER: Campo 16 (cantidad_avance) como en importar_ordenes_trabajo
                            try:
                                cantidad_avance_str = row[16].strip()
                                puntos = ['', ' ', '.', '. ', ' .']
                                if cantidad_avance_str in puntos:
                                    cantidad_avance = 0.0
                                else:
                                    cantidad_avance = float(cantidad_avance_str)
                            except (ValueError, IndexError):
                                cantidad_avance = 0.0
                            
                            resultado = '$'.join(row)
                            self.stdout.write(f'       ✅ OT ENCONTRADA en línea {lineas_procesadas}!')
                            self.stdout.write(f'       📊 Avance en archivo: {cantidad_avance}')
                            self.stdout.write(f'       📄 Contenido: {resultado[:100]}...')
                            return resultado
                            
                    except (ValueError, IndexError) as e:
                        if lineas_procesadas <= 5:  # Solo mostrar primeros errores
                            self.stdout.write(f'       ❌ Error línea {lineas_procesadas}: {str(e)}')
                        continue
            
            # ✅ DIAGNÓSTICO: Si no se encuentra, mostrar qué sí encontró
            self.stdout.write(f'       ❌ OT {codigo_ot_buscar} NO encontrada')
            self.stdout.write(f'       📊 Líneas procesadas: {lineas_procesadas}')
            self.stdout.write(f'       📊 Líneas válidas (24 campos): {lineas_validas}')
            self.stdout.write(f'       📝 Primeras OTs encontradas: {ots_encontradas}')
            
            # ✅ BUSCAR OTs SIMILARES (errores de tipeo, etc.)
            ots_similares = []
            codigo_str = str(codigo_ot_buscar)
            
            with open(ot_path, 'r', encoding=encoding) as file:
                reader = csv.reader(file, delimiter='$')
                for row in reader:
                    try:
                        if len(row) >= 1:
                            ot_archivo = row[0].strip()
                            # Buscar OTs que contengan parte del código
                            if codigo_str in ot_archivo or ot_archivo in codigo_str:
                                ots_similares.append(ot_archivo)
                                if len(ots_similares) >= 3:
                                    break
                    except:
                        continue
            
            if ots_similares:
                self.stdout.write(f'       🔎 OTs similares encontradas: {ots_similares}')
            
            return None
            
        except Exception as e:
            self.stdout.write(f'       ❌ Error general buscando OT: {str(e)}')
            import traceback
            self.stdout.write(f'       📄 Traceback: {traceback.format_exc()[:200]}')
            return None

    def buscar_item_en_archivo(self, codigo_ot, item, ruta_path):
        """Busca un item específico en ruta_ot.txt usando la MISMA lógica que importar_rutas_ot"""
        try:
            import chardet
            with open(ruta_path, 'rb') as f:
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                encoding = result['encoding']
            
            codigo_ot_str = str(codigo_ot)
            item_buscar = int(item)  # ✅ USAR: Entero para comparar
            
            self.stdout.write(f'           🔍 Buscando OT {codigo_ot_str} con Item {item_buscar}...')
            
            items_encontrados_para_ot = []
            
            with open(ruta_path, 'r', encoding=encoding) as file:
                # ✅ USAR: Misma lógica que importar_rutas_ot
                reader = csv.reader(file, delimiter='@')
                # next(reader)  # ❌ NO saltar header - puede no existir
                
                for idx, row in enumerate(reader):
                    try:
                        if len(row) != 9:  # ✅ MISMO: Validación de 9 campos
                            continue
                        
                        # ✅ MISMO: Código OT (quitar ceros iniciales)
                        codigo_ot_archivo = int(row[0].strip())
                        
                        if codigo_ot_archivo == int(codigo_ot_str):
                            # ✅ MISMO: Item secuencial
                            item_archivo = int(row[1].strip())
                            codigo_proceso = row[2].strip()
                            
                            # ✅ MISMO: Cantidades (campos 6 y 7)
                            try:
                                cantidad_terminado_str = row[6].strip()
                                puntos = ['', ' ', '.', '. ', ' .']
                                if cantidad_terminado_str in puntos:
                                    cantidad_terminado = 0.0
                                else:
                                    cantidad_terminado = float(cantidad_terminado_str)
                            except (ValueError, IndexError):
                                cantidad_terminado = 0.0
                            
                            try:
                                cantidad_perdida_str = row[7].strip()
                                if cantidad_perdida_str in puntos:
                                    cantidad_perdida = 0.0
                                else:
                                    cantidad_perdida = float(cantidad_perdida_str)
                            except (ValueError, IndexError):
                                cantidad_perdida = 0.0
                            
                            items_encontrados_para_ot.append({
                                'item': item_archivo,
                                'proceso': codigo_proceso,
                                'cantidad_terminado': cantidad_terminado,
                                'cantidad_perdida': cantidad_perdida,
                                'linea': idx + 1,
                                'contenido': '@'.join(row)
                            })
                            
                            # Si encontramos el item específico
                            if item_archivo == item_buscar:
                                self.stdout.write(f'           ✅ ENCONTRADO Item {item_archivo} para OT {codigo_ot}!')
                                self.stdout.write(f'           📄 Proceso: {codigo_proceso}, Terminado: {cantidad_terminado}, Perdida: {cantidad_perdida}')
                                return '@'.join(row)
                                
                    except (ValueError, IndexError) as e:
                        continue
            
            # ✅ DIAGNÓSTICO COMPLETO
            if items_encontrados_para_ot:
                self.stdout.write(f'           📊 OT {codigo_ot} encontrada con {len(items_encontrados_para_ot)} items:')
                for info in items_encontrados_para_ot[:5]:
                    self.stdout.write(f'              Item {info["item"]} → Proceso {info["proceso"]} (T:{info["cantidad_terminado"]}, P:{info["cantidad_perdida"]})')
                
                items_disponibles = [str(info['item']) for info in items_encontrados_para_ot]
                self.stdout.write(f'           🎯 Items disponibles: {", ".join(items_disponibles)}')
                self.stdout.write(f'           ❌ Item {item_buscar} NO encontrado')
            else:
                self.stdout.write(f'           ❌ OT {codigo_ot} NO encontrada en archivo')
                
        except Exception as e:
            self.stdout.write(f'           ❌ Error en búsqueda: {str(e)}')
            
        return None
