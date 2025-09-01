from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone


@api_view(['GET'])
def test_api_connectivity(request):
    """
    Vista simple para probar conectividad de API
    """
    return Response({
        'success': True,
        'message': 'API funcionando correctamente',
        'timestamp': timezone.now(),
        'server_status': 'OK'
    })


@api_view(['GET'])
def test_dashboard_base(request, programa_id=None):
    """
    Vista de prueba para dashboard ejecutivo
    """
    return Response({
        'success': True,
        'programa': {
            'id': programa_id or 1,
            'nombre': 'Programa de Prueba',
            'fecha_inicio': '2024-01-01',
            'fecha_fin': '2024-01-31'
        },
        'metricas': {
            'produccion_fisica': {
                'resumen_general': {
                    'kilos_planificados': 10000,
                    'kilos_fabricados': 7500,
                    'kilos_pendientes': 2500,
                    'porcentaje_completado_kilos': 75.0
                }
            },
            'eficiencia_operacional': {
                'resumen_eficiencia': {
                    'eficiencia_promedio_programa': 85.0
                }
            },
            'alertas_ejecutivas': [
                {
                    'titulo': 'Producción por debajo del objetivo',
                    'descripcion': 'La producción está 5% por debajo del objetivo diario',
                    'prioridad': 'MEDIA',
                    'impacto_ejecutivo': 'Posible retraso en entregas',
                    'accion_recomendada': 'Revisar asignación de operadores'
                }
            ],
            'proyecciones': {
                'finalizacion': {
                    'fecha_proyectada': '2024-01-28',
                    'retraso_dias': 3,
                    'probabilidad_cumplimiento': 78
                }
            }
        },
        'timestamp': timezone.now()
    }) 