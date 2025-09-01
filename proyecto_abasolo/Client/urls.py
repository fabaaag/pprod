from django.urls import path, include

from Client import views



urlpatterns = [
    path("api/v1/clientes/", views.ClienteView.as_view(), name='clientes'),
    path("api/v1/clientes/<int:pk>/", views.ClienteView.as_view(), name='cliente'),
]
