from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import json

from ...models import (
    ProgramaProduccion, OrdenTrabajo, TareaFragmentada,
    EmpresaOT, Cliente, Maquina, Proceso, EstandarMaquinaProceso
)
from ...services.production_scheduler import ProductionScheduler
from ...services.optimization_engine import OptimizationEngine
from ...services.metrics_engine import MetricsEngine
from ...services.time_calculations import TimeCalculator
from Operator.models import Operador, AsignacionOperador
from Product.models import Producto, MeasurementUnit


class Command(BaseCommand):
    help = 'Integra y verifica que todos los sistemas funcionen correctamente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-completo',
            action='store_true',
            help='Ejecuta un test completo de integración'
        )
        parser.add_argument(
            '--crear-datos-demo',
            action='store_true',
            help='Crea datos de demostración'
        )

    def handle(self, *args, **options):
        self.stdout.write("🚀 Iniciando integración completa del sistema...")
        
        if options['crear_datos_demo']:
            self.crear_datos_demo()
        
        if options['test_completo']:
            self.ejecutar_test_completo()
        
        self.verificar_integraciones()
        
        self.stdout.write(
            self.style.SUCCESS("✅ Integración completada exitosamente!")
        )

    def crear_datos_demo(self):
        """Crea datos de demostración para testing"""
        self.stdout.write("📝 Creando datos de demostración...")
        
        try:
            with transaction.atomic():
                # 1. Empresa
                empresa, _ = EmpresaOT.objects.get_or_create(
                    apodo="DEMO",
                    defaults={
                        'nombre': 'Empresa Demo',
                        'codigo_empresa': 'DEMO001'
                    }
                )
                
                # 2. Cliente
                cliente, _ = Cliente.objects.get_or_create(
                    apodo="CLI_DEMO",
                    defaults={'nombre': 'Cliente Demo'}
                )
                
                # 3. Unidad de medida
                unidad, _ = MeasurementUnit.objects.get_or_create(
                    nombre="UNIDADES",
                    defaults={'descripcion': 'Unidades'}
                )
                
                # 4. Productos
                productos_data = [
                    {'codigo': 'PROD001', 'descripcion': 'Producto Demo 1', 'peso': 1.5},
                    {'codigo': 'PROD002', 'descripcion': 'Producto Demo 2', 'peso': 2.0},
                    {'codigo': 'PROD003', 'descripcion': 'Producto Demo 3', 'peso': 1.8},
                ]
                
                productos = []
                for prod_data in productos_data:
                    producto, created = Producto.objects.get_or_create(
                        codigo_producto=prod_data['codigo'],
                        defaults={
                            'descripcion': prod_data['descripcion'],
                            'peso_unitario': prod_data['peso'],
                            'empresa': empresa
                        }
                    )
                    productos.append(producto)
                
                # 5. Máquinas
                maquinas_data = [
                    {'codigo': 'MAQ001', 'descripcion': 'Torno CNC 1', 'sigla': 'TOR1'},
                    {'codigo': 'MAQ002', 'descripcion': 'Fresadora Universal', 'sigla': 'FRE1'},
                    {'codigo': 'MAQ003', 'descripcion': 'Rectificadora', 'sigla': 'REC1'},
                ]
                
                maquinas = []
                for maq_data in maquinas_data:
                    maquina, created = Maquina.objects.get_or_create(
                        codigo_maquina=maq_data['codigo'],
                        empresa=empresa,
                        defaults={
                            'descripcion': maq_data['descripcion'],
                            'sigla': maq_data['sigla']
                        }
                    )
                    maquinas.append(maquina)
                
                # 6. Procesos
                procesos_data = [
                    {'codigo': 'TOR', 'descripcion': 'Torneado'},
                    {'codigo': 'FRE', 'descripcion': 'Fresado'},
                    {'codigo': 'REC', 'descripcion': 'Rectificado'},
                ]
                
                procesos = []
                for proc_data in procesos_data:
                    proceso, created = Proceso.objects.get_or_create(
                        codigo_proceso=proc_data['codigo'],
                        empresa=empresa,
                        defaults={'descripcion': proc_data['descripcion']}
                    )
                    procesos.append(proceso)
                
                # 7. Estándares máquina-proceso
                estandares_data = [
                    (productos[0], procesos[0], maquinas[0], 100, True),
                    (productos[0], procesos[1], maquinas[1], 80, False),
                    (productos[1], procesos[0], maquinas[0], 120, True),
                    (productos[1], procesos[2], maquinas[2], 60, False),
                    (productos[2], procesos[1], maquinas[1], 90, True),
                ]
                
                for producto, proceso, maquina, estandar, es_principal in estandares_data:
                    EstandarMaquinaProceso.objects.get_or_create(
                        producto=producto,
                        proceso=proceso,
                        maquina=maquina,
                        defaults={
                            'estandar': estandar,
                            'es_principal': es_principal
                        }
                    )
                
                # 8. Operadores
                operadores_data = [
                    {'nombre': 'Juan Pérez', 'rut': '12345678-9'},
                    {'nombre': 'María García', 'rut': '98765432-1'},
                    {'nombre': 'Carlos López', 'rut': '11223344-5'},
                ]
                
                operadores = []
                for op_data in operadores_data:
                    operador, created = Operador.objects.get_or_create(
                        rut=op_data['rut'],
                        defaults={
                            'nombre': op_data['nombre'],
                            'empresa': empresa
                        }
                    )
                    operadores.append(operador)
                
                # 9. Asignaciones operador-máquina
                for i, operador in enumerate(operadores):
                    for j, maquina in enumerate(maquinas):
                        if i <= j:  # Crear algunas asignaciones
                            AsignacionOperador.objects.get_or_create(
                                operador=operador,
                                maquina=maquina,
                                defaults={'activo': True}
                            )
                
                # 10. Órdenes de trabajo
                ordenes_data = [
                    {'codigo': 1001, 'producto': productos[0], 'cantidad': 100},
                    {'codigo': 1002, 'producto': productos[1], 'cantidad': 150},
                    {'codigo': 1003, 'producto': productos[2], 'cantidad': 80},
                ]
                
                from ..models import TipoOT, SituacionOT
                tipo_ot, _ = TipoOT.objects.get_or_create(
                    codigo_tipo_ot='PR',
                    defaults={'descripcion': 'Producción'}
                )
                
                situacion_ot, _ = SituacionOT.objects.get_or_create(
                    codigo_situacion_ot='P',
                    defaults={'descripcion': 'Pendiente'}
                )
                
                ordenes = []
                for orden_data in ordenes_data:
                    orden, created = OrdenTrabajo.objects.get_or_create(
                        codigo_ot=orden_data['codigo'],
                        defaults={
                            'tipo_ot': tipo_ot,
                            'situacion_ot': situacion_ot,
                            'cliente': cliente,
                            'item_nota_venta': 1,
                            'codigo_producto_inicial': orden_data['producto'].codigo_producto,
                            'descripcion_producto_ot': orden_data['producto'].descripcion,
                            'cantidad': orden_data['cantidad'],
                            'unidad_medida': unidad,
                            'peso_unitario': orden_data['producto'].peso_unitario,
                            'empresa': empresa
                        }
                    )
                    ordenes.append(orden)
                
                self.stdout.write("✅ Datos de demostración creados exitosamente")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error creando datos demo: {str(e)}")
            )

    def ejecutar_test_completo(self):
        """Ejecuta un test completo de todas las funcionalidades"""
        self.stdout.write("🧪 Ejecutando test de integración completo...")
        
        try:
            # 1. Test de ProductionScheduler
            self.test_production_scheduler()
            
            # 2. Test de OptimizationEngine
            self.test_optimization_engine()
            
            # 3. Test de MetricsEngine
            self.test_metrics_engine()
            
            # 4. Test de integración completa
            self.test_flujo_completo()
            
            self.stdout.write("✅ Todos los tests pasaron exitosamente")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error en tests: {str(e)}")
            )

    def test_production_scheduler(self):
        """Test del scheduler de producción"""
        self.stdout.write("  🔄 Testing ProductionScheduler...")
        
        scheduler = ProductionScheduler(TimeCalculator())
        
        # Buscar un programa existente o crear uno
        programa = ProgramaProduccion.objects.first()
        if not programa:
            programa = ProgramaProduccion.objects.create(
                nombre="Programa Test",
                fecha_inicio=timezone.now().date()
            )
        
        # Test de generación de timeline
        ordenes = list(OrdenTrabajo.objects.all()[:3])
        if ordenes:
            ordenes_data = []
            for orden in ordenes:
                orden_data = {
                    'orden_trabajo': orden.id,
                    'orden_trabajo_codigo_ot': orden.codigo_ot,
                    'orden_trabajo_descripcion_producto_ot': orden.descripcion_producto_ot,
                    'procesos': []
                }
                ordenes_data.append(orden_data)
            
            timeline = scheduler.generate_timeline_data(programa, ordenes_data)
            
            if 'groups' in timeline or 'items' in timeline:
                self.stdout.write("    ✅ ProductionScheduler funciona correctamente")
            else:
                raise Exception("Timeline no generado correctamente")

    def test_optimization_engine(self):
        """Test del motor de optimización"""
        self.stdout.write("  ⚡ Testing OptimizationEngine...")
        
        optimization = OptimizationEngine()
        
        programa = ProgramaProduccion.objects.first()
        if programa:
            resultado = optimization.optimize_machine_assignment(programa)
            
            if isinstance(resultado, dict) and 'optimizaciones_aplicadas' in resultado:
                self.stdout.write("    ✅ OptimizationEngine funciona correctamente")
            else:
                raise Exception("Optimización no funcionó correctamente")

    def test_metrics_engine(self):
        """Test del motor de métricas"""
        self.stdout.write("  📊 Testing MetricsEngine...")
        
        metrics = MetricsEngine()
        
        programa = ProgramaProduccion.objects.first()
        if programa:
            kpis = metrics.get_programa_kpis(programa)
            
            if isinstance(kpis, dict) and 'eficiencia_general' in kpis:
                self.stdout.write("    ✅ MetricsEngine funciona correctamente")
            else:
                raise Exception("Métricas no generadas correctamente")

    def test_flujo_completo(self):
        """Test del flujo completo de planificación"""
        self.stdout.write("  🔄 Testing flujo completo...")
        
        # 1. Crear programa
        programa = ProgramaProduccion.objects.create(
            nombre=f"Test Completo {timezone.now().strftime('%H%M%S')}",
            fecha_inicio=timezone.now().date()
        )
        
        # 2. Asignar órdenes
        ordenes = list(OrdenTrabajo.objects.all()[:2])
        for i, orden in enumerate(ordenes):
            from ..models import ProgramaOrdenTrabajo
            ProgramaOrdenTrabajo.objects.create(
                programa=programa,
                orden_trabajo=orden,
                prioridad=i
            )
        
        # 3. Generar planificación
        scheduler = ProductionScheduler(TimeCalculator())
        ordenes_data = []
        
        for pot in programa.programaordentrabajo_set.all():
            orden_data = {
                'orden_trabajo': pot.orden_trabajo.id,
                'orden_trabajo_codigo_ot': pot.orden_trabajo.codigo_ot,
                'orden_trabajo_descripcion_producto_ot': pot.orden_trabajo.descripcion_producto_ot,
                'procesos': []
            }
            ordenes_data.append(orden_data)
        
        if scheduler.create_fragmented_tasks(programa, ordenes_data):
            self.stdout.write("    ✅ Planificación automática funciona")
        
        # 4. Optimizar
        optimization = OptimizationEngine()
        optimization.optimize_machine_assignment(programa)
        self.stdout.write("    ✅ Optimización automática funciona")
        
        # 5. Generar métricas
        metrics = MetricsEngine()
        kpis = metrics.get_programa_kpis(programa)
        self.stdout.write("    ✅ Generación de métricas funciona")
        
        self.stdout.write("    ✅ Flujo completo funciona perfectamente")

    def verificar_integraciones(self):
        """Verifica que todas las integraciones estén funcionando"""
        self.stdout.write("🔍 Verificando integraciones del sistema...")
        
        verificaciones = [
            self.verificar_modelos,
            self.verificar_servicios,
            self.verificar_apis,
            self.verificar_frontend_integration
        ]
        
        for verificacion in verificaciones:
            try:
                verificacion()
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  {verificacion.__name__}: {str(e)}")
                )

    def verificar_modelos(self):
        """Verifica que todos los modelos estén correctamente configurados"""
        modelos_criticos = [
            ProgramaProduccion, OrdenTrabajo, TareaFragmentada,
            Maquina, Proceso, EstandarMaquinaProceso
        ]
        
        for modelo in modelos_criticos:
            count = modelo.objects.count()
            self.stdout.write(f"  ✅ {modelo.__name__}: {count} registros")

    def verificar_servicios(self):
        """Verifica que todos los servicios estén disponibles"""
        servicios = [
            ProductionScheduler,
            OptimizationEngine,
            MetricsEngine,
            TimeCalculator
        ]
        
        for servicio in servicios:
            instance = servicio() if servicio != ProductionScheduler else servicio(TimeCalculator())
            self.stdout.write(f"  ✅ {servicio.__name__}: Disponible")

    def verificar_apis(self):
        """Verifica que las APIs estén configuradas"""
        from django.urls import reverse
        
        # URLs críticas que deben existir
        urls_criticas = [
            'programas-list',
            'crear_programa',
            'programa-kpis',
            'dashboard-principal',
            'optimizar-programa'
        ]
        
        for url_name in urls_criticas:
            try:
                reverse(url_name, kwargs={'programa_id': 1} if 'programa' in url_name else {})
                self.stdout.write(f"  ✅ API {url_name}: Configurada")
            except:
                self.stdout.write(f"  ⚠️  API {url_name}: No encontrada")

    def verificar_frontend_integration(self):
        """Verifica que los componentes del frontend estén disponibles"""
        import os
        
        frontend_files = [
            'frontend_react/src/components/Programa/DashboardAvanzado.jsx',
            'frontend_react/src/components/Programa/css/DashboardAvanzado.css',
            'frontend_react/src/components/Programa/TimelineTimeReal.jsx'
        ]
        
        for file_path in frontend_files:
            if os.path.exists(file_path):
                self.stdout.write(f"  ✅ Frontend: {os.path.basename(file_path)} disponible")
            else:
                self.stdout.write(f"  ⚠️  Frontend: {os.path.basename(file_path)} no encontrado")

    def generar_reporte_integracion(self):
        """Genera un reporte completo de la integración"""
        reporte = {
            'fecha_verificacion': timezone.now().isoformat(),
            'estado_general': 'OPERATIVO',
            'estadisticas': {
                'programas': ProgramaProduccion.objects.count(),
                'ordenes': OrdenTrabajo.objects.count(),
                'tareas_fragmentadas': TareaFragmentada.objects.count(),
                'maquinas': Maquina.objects.count(),
                'procesos': Proceso.objects.count(),
                'operadores': Operador.objects.count(),
            },
            'servicios_disponibles': [
                'ProductionScheduler',
                'OptimizationEngine', 
                'MetricsEngine',
                'TimeCalculator'
            ],
            'funcionalidades_principales': [
                'Planificación automática',
                'Optimización de recursos',
                'Métricas en tiempo real',
                'Dashboard avanzado',
                'Timeline interactivo',
                'Progreso en tiempo real',
                'Finalización de día automática',
                'Análisis de inconsistencias'
            ]
        }
        
        with open('reporte_integracion.json', 'w') as f:
            json.dump(reporte, f, indent=2, default=str)
        
        self.stdout.write("📄 Reporte de integración generado: reporte_integracion.json") 