from django.urls import path
from .views_files import (
    program_views,
    machine_views,
    order_views,
    import_views,
    supervisor_views,
    optimization_views,
    metrics_views,
    executive_views,
    test_views
)
#Urls para Programas
urlpatterns = [
    #Imports
    path('importar_ots/', import_views.importar_ots_from_file, name='importar_ot'),
    path('importar_ruta_ot/', import_views.importar_rutaot_file),
        
    #Ordenes
    path('api/v1/ordenes/', order_views.OTView.as_view(), name='ordenes-list'),
    path('api/v1/ordenes/search/', order_views.search_orders, name='search-orders'),
    path('api/v1/ordenes/no_asignadas/', order_views.get_unassigned_ots, name='ordenes-unassigned'),

    #Programa
    path('api/v1/programas/crear_programa/', program_views.ProgramCreateView.as_view(), name='crear_programa'),
    path('api/v1/programas/', program_views.ProgramListView.as_view(), name='programas-list'),
    path('api/v1/programas/<int:pk>/', program_views.ProgramDetailView.as_view(), name='get-program'),
    path('api/v1/programas/<int:pk>/update-prio/', program_views.ProgramDetailView.as_view(), name='program-detail'),
    #path('api/v1/programas/<int:pk>/delete-orders/', program_views.UpdatePriorityView.as_view(), name='delete_orders'),
    path('api/v1/programas/<int:pk>/delete/', program_views.ProgramListView.as_view(), name='delete_program'),
    path('api/v1/programas/<int:pk>/generar_pdf/', program_views.GenerateProgramPDF.as_view(), name='generar_pdf'),
    path('api/v1/programas/<int:pk>/check-status/', program_views.ProgramDetailView.as_view(), name='check_status'),
    path('api/v1/programas/<int:pk>/add-orders/', program_views.AddOrdersToProgram.as_view(), name='add-orders-to-program'),
    path('api/v1/programas/<int:pk>/reajustar/', program_views.ReajustarProgramaView.as_view(), name='reajustar-programa'),
    path('api/v1/programas/<int:pk>/historial/', program_views.ProgramHistoryView.as_view(), name='programa-historial'),
    path('api/v1/programas/<int:pk>/historial/<int:historial_id>/', program_views.ProgramHistoryView.as_view(), name='programa-historial-delete'),
    path('api/v1/programas/<int:pk>/timeline-planificacion/', program_views.TimelinePlanningView.as_view(), name='timeline-planificacion'),
    path('api/v1/programas/<int:pk>/update-product-standard/', program_views.UpdateProductStandardView.as_view(), name='update-product-standard'),
    path('api/v1/maquinas-compatibles/<int:pk>/', program_views.UpdateProductStandardView.as_view(), name='maquinas-compatibles'),

    #Maquinas
    path('api/v1/programas/<int:pk>/maquinas/', machine_views.MaquinasView.as_view(), name='maquinas-list'),
    path('api/v1/maquinas/', machine_views.MaquinaListView.as_view(), name='maquinas-get-list'),
    path('api/v1/empresas/', program_views.EmpresaListView.as_view(), name='empresas-get-list'),

    #Reporte
    path('api/v1/programas/<int:pk>/supervisor-report/', supervisor_views.SupervisorReportView.as_view(), name='supervisor-report'),
    path('api/v1/programas/<int:programa_id>/resumen-diario/<str:fecha>/', supervisor_views.ResumenDiarioView.as_view(), name='resumen-diario'),
    path('api/v1/programas/<int:pk>/supervisor-report/update-priority/', supervisor_views.SupervisorReportView.as_view(), name='supervisor-report'),
    path('api/v1/programas/<int:programa_id>/finalizar-dia/<str:fecha_str>/', supervisor_views.FinalizarDiaView.as_view(), name='finalizar_dia'),
    path('api/v1/reportes-supervisor/', supervisor_views.ReporteSupervisorListView.as_view(), name='reportes-supervisor-list'),
    path('api/v1/programas/<int:pk>/timeline-ejecucion/', supervisor_views.TimelineEjecucionView.as_view(), name='timeline-ejecucion'),
    path('api/supervisor/task/<int:task_id>/details/', supervisor_views.get_task_production_details, name='task_production_details'),
    # En urls.py
    path('api/v1/programas/<int:programa_id>/regenerar-tareas/', supervisor_views.regenerar_tareas_programa, name='regenerar-tareas'),

     # ========================================================================
    # URLS PARA PROGRESO DIRECTO DE ITEMRUTA
    # ========================================================================
    path('api/v1/tareas/<int:tarea_id>/tiempo-real/', program_views.TareaTimeRealtimeUpdateView.as_view(), name='tarea-tiempo-real'),
    path('api/v1/programas/<int:programa_id>/timeline-tiempo-real/', program_views.ProgramaTimelineRealtimeView.as_view(), name='programa-timeline-tiempo-real'),
    path('api/v1/item-ruta/<int:item_ruta_id>/estado/', program_views.ItemRutaEstadoView.as_view(), name='item-ruta-estado'),
    path('api/v1/item-ruta/<int:item_ruta_id>/progreso/', program_views.ItemRutaProgressView.as_view(), name='item-ruta-progress'),
    path('api/v1/item-ruta/<int:item_ruta_id>/iniciar/', program_views.ItemRutaIniciarProcesoView.as_view(), name='item-ruta-iniciar'),
    path('api/v1/programas/<int:programa_id>/items-progress/', program_views.ProgramaItemsProgressView.as_view(), name='programa-items-progress'),

    # Finalizar día y regenerar planificación
    path('api/v1/programas/<int:programa_id>/finalizar-dia/', program_views.FinalizarDiaView.as_view(), name='finalizar-dia'),
    path('api/v1/programas/<int:programa_id>/timeline-actual/', program_views.ObtenerTimelineActualView.as_view(), name='obtener-timeline-actual'),
    path('api/v1/programas/<int:programa_id>/validar-dia/', program_views.ValidarDiaFinalizadoView.as_view(), name='validar-dia-finalizado'),

    path('api/v1/programas/<int:programa_id>/ots-inconsistencias/', 
         program_views.ListarOTsConInconsistenciasView.as_view(), 
         name='listar-ots-inconsistencias'),
    path('api/v1/programas/<int:programa_id>/analizar-avances/<int:ot_id>/', 
         program_views.AnalizarAvancesOTView.as_view(), 
         name='analizar-avances-ot'),
    path('api/v1/programas/<int:programa_id>/aplicar-reconciliacion/<int:ot_id>/', 
         program_views.AplicarReconciliacionAvancesView.as_view(), 
         name='aplicar-reconciliacion-avances'),

     path('api/v1/programas/<int:programa_id>/update-estandar-from-start/', program_views.get_estandar_from_producto, name='update-estandar-from-start'),
    # ========================================================================
    # URLS PARA OPTIMIZACIÓN
    # ========================================================================
    path('api/v1/programas/<int:programa_id>/optimizar/', 
         optimization_views.OptimizarProgramaView.as_view(), 
         name='optimizar-programa'),
    path('api/v1/programas/<int:programa_id>/sugerir-operadores/', 
         optimization_views.SugerirOperadoresView.as_view(), 
         name='sugerir-operadores'),
    path('api/v1/programas/<int:programa_id>/analisis-capacidad/', 
         optimization_views.AnalisisCapacidadView.as_view(), 
         name='analisis-capacidad'),
    path('api/v1/programas/<int:programa_id>/simular-cambios/', 
         optimization_views.SimularCambiosView.as_view(), 
         name='simular-cambios'),

    # ========================================================================
    # URLS PARA MÉTRICAS Y DASHBOARD
    # ========================================================================
    path('api/v1/programas/<int:programa_id>/kpis/', 
         metrics_views.ProgramaKPIsView.as_view(), 
         name='programa-kpis'),
    path('api/v1/programas/<int:programa_id>/dashboard/', 
         metrics_views.DashboardPrincipalView.as_view(), 
         name='dashboard-principal'),
    path('api/v1/programas/<int:programa_id>/metricas-diarias/', 
         metrics_views.MetricasDiariasView.as_view(), 
         name='metricas-diarias'),
    path('api/v1/programas/<int:programa_id>/tendencias/', 
         metrics_views.TendenciasView.as_view(), 
         name='tendencias'),
    path('api/v1/programas/<int:programa_id>/comparar-periodos/', 
         metrics_views.ComparacionPeriodosView.as_view(), 
         name='comparar-periodos'),
    path('api/v1/programas/<int:programa_id>/exportar-metricas/', 
         metrics_views.ExportarMetricasView.as_view(), 
         name='exportar-metricas'),
    path('api/v1/programas/<int:programa_id>/alertas/', 
         metrics_views.AlertasMetricasView.as_view(), 
         name='alertas-metricas'),
     path('api/v1/programas/<int:program_id>/update-item-states/', 
         program_views.update_item_ruta_states, 
         name='update_item_ruta_states'),
    
    # ========================================================================
    # URLS PARA MÉTRICAS EJECUTIVAS (NUEVO DASHBOARD GERENCIAL)
    # ========================================================================
    path('api/jobmanagement/executive/dashboard/<int:programa_id>/', 
         executive_views.dashboard_ejecutivo_completo, 
         name='dashboard_ejecutivo_completo'),
    path('api/jobmanagement/executive/produccion/<int:programa_id>/', 
         executive_views.resumen_produccion_fisica, 
         name='resumen_produccion_fisica'),
    path('api/jobmanagement/executive/eficiencia/<int:programa_id>/', 
         executive_views.eficiencia_operacional, 
         name='eficiencia_operacional_ejecutivo'),
    path('api/jobmanagement/executive/entregas/<int:programa_id>/', 
         executive_views.cumplimiento_entregas, 
         name='cumplimiento_entregas'),
    path('api/jobmanagement/executive/costos/<int:programa_id>/', 
         executive_views.costos_estimados, 
         name='costos_estimados'),
    path('api/jobmanagement/executive/comparativas/<int:programa_id>/', 
         executive_views.comparativas_historicas, 
         name='comparativas_historicas'),
    path('api/jobmanagement/executive/alertas/<int:programa_id>/', 
         executive_views.alertas_ejecutivas, 
         name='alertas_ejecutivas'),
    path('api/jobmanagement/executive/proyecciones/<int:programa_id>/', 
         executive_views.proyecciones_programa, 
         name='proyecciones_programa'),
    path('api/jobmanagement/executive/pdf/<int:programa_id>/', 
         executive_views.resumen_ejecutivo_pdf, 
         name='resumen_ejecutivo_pdf'),
    path('api/jobmanagement/executive/consolidado/', 
         executive_views.kpis_ejecutivos_todos_programas, 
         name='kpis_ejecutivos_todos_programas'),
    path('api/jobmanagement/executive/configurar-costos/', 
         executive_views.configurar_parametros_costos, 
         name='configurar_parametros_costos'),
    path('api/jobmanagement/executive/tiempo-real/<int:programa_id>/', 
         executive_views.metricas_tiempo_real, 
         name='metricas_tiempo_real'),

    # ========================================================================
    # URLS DE PRUEBA (TEMPORAL)
    # ========================================================================
    path('api/test/connectivity/', 
         test_views.test_api_connectivity, 
         name='test_api_connectivity'),
    path('api/test/dashboard/<int:programa_id>/', 
         test_views.test_dashboard_base, 
         name='test_dashboard_base'),
]


from .views_files.program_views import (
    ListarOperadoresAPIView, DashboardOperadorAPIView, IngresarProduccionAPIView,
    FallasDisponiblesAPIView
)

# URLs para ingreso de producción (APIs REST)
urlpatterns += [
    # Core functionality
    path('api/produccion/operadores/', ListarOperadoresAPIView.as_view(), name='api_listar_operadores'),
    path('api/produccion/operador/<int:operador_id>/dashboard/', DashboardOperadorAPIView.as_view(), name='api_dashboard_operador'),
    path('api/produccion/operador/<int:operador_id>/ingresar/', IngresarProduccionAPIView.as_view(), name='api_ingresar_produccion'),
    
    # Datos auxiliares
    path('api/produccion/fallas/', FallasDisponiblesAPIView.as_view(), name='api_fallas_disponibles'),

]