from django.urls import path
from . import views

urlpatterns = [
    # Endpoints de Productos
    path('productos/', views.ProductoListView.as_view(), name='producto-list'),
    path('productos/<int:id>/', views.ProductoDetailView.as_view(), name='producto-detail'),
    
    # Endpoints de Piezas
    path('piezas/', views.PiezaListView.as_view(), name='pieza-list'),
    path('piezas/<int:id>/', views.PiezaDetailView.as_view(), name='pieza-detail'),
    
    # Endpoints comunes
    path('familias/', views.FamiliaProductoView.as_view(), name='familia-list'),
    path('subfamilias/', views.SubfamiliaProductoView.as_view(), name='subfamilia-list'),

    path('rutas-proceso/<int:objeto_id>/', views.RutaProcesoView.as_view(), name='rutas-proceso'),
    path('actualizar-estandar-ruta/<int:ruta_id>/', views.ActualizarEstandarRutaView.as_view(), name='actualizar-estandar-ruta'),

    path('estandares-proceso/<int:proceso_id>/', views.EstandarMaquinaProcesoView.as_view(), name='estandares-proceso'),
    path('estandares-proceso/', views.EstandarMaquinaProcesoView.as_view(), name='crear-estandar-proceso'),
    path('estandares-proceso/<int:estandar_id>/eliminar/', views.EstandarMaquinaProcesoView.as_view(), name='eliminar-estandar-proceso'),
]
