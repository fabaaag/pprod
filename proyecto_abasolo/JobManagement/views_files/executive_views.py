from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import json

from ..models import ProgramaProduccion, TareaFragmentada
from ..services.executive_metrics import ExecutiveMetricsEngine


@api_view(['GET'])
def dashboard_ejecutivo_completo(request, programa_id):
    """
    Dashboard ejecutivo completo con todas las métricas solicitadas
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        # Obtener todas las métricas ejecutivas
        datos_completos = engine.get_resumen_ejecutivo_completo(programa)
        
        return Response({
            'success': True,
            'programa': {
                'id': programa.id,
                'nombre': programa.nombre,
                'fecha_inicio': programa.fecha_inicio,
                'fecha_fin': programa.fecha_fin,
                'estado': 'ACTIVO'  # Calcular estado real
            },
            'metricas': datos_completos,
            'timestamp': timezone.now()
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def resumen_produccion_fisica(request, programa_id):
    """
    Específicamente para métricas de producción física (kilos, unidades)
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        datos_produccion = engine.get_metricas_produccion_fisica(programa)
        
        return Response({
            'success': True,
            'produccion_fisica': datos_produccion
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def eficiencia_operacional(request, programa_id):
    """
    Métricas de eficiencia operacional detallada
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        datos_eficiencia = engine.get_eficiencia_operacional(programa)
        
        return Response({
            'success': True,
            'eficiencia': datos_eficiencia
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def cumplimiento_entregas(request, programa_id):
    """
    Análisis de cumplimiento de entregas por cliente y producto
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        datos_cumplimiento = engine.get_cumplimiento_entregas(programa)
        
        return Response({
            'success': True,
            'cumplimiento': datos_cumplimiento
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def costos_estimados(request, programa_id):
    """
    Estructura de costos preparada para cuando tengan datos de precios
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        datos_costos = engine.get_costos_estimados(programa)
        
        return Response({
            'success': True,
            'costos': datos_costos,
            'nota': 'Estructura preparada para configurar precios y costos'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def comparativas_historicas(request, programa_id):
    """
    Comparativas con programas anteriores
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        datos_comparativas = engine.get_comparativas_historicas(programa)
        
        return Response({
            'success': True,
            'comparativas': datos_comparativas
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def alertas_ejecutivas(request, programa_id):
    """
    Alertas específicas para nivel ejecutivo
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        alertas = engine.get_alertas_ejecutivas(programa)
        
        return Response({
            'success': True,
            'alertas': alertas,
            'total_alertas': len(alertas),
            'alertas_criticas': len([a for a in alertas if a['prioridad'] == 'CRITICA'])
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def proyecciones_programa(request, programa_id):
    """
    Proyecciones basadas en tendencias actuales
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        proyecciones = engine.get_proyecciones(programa)
        
        return Response({
            'success': True,
            'proyecciones': proyecciones
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def resumen_ejecutivo_pdf(request, programa_id):
    """
    Endpoint para generar reporte ejecutivo en PDF
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        # Obtener todos los datos
        datos_completos = engine.get_resumen_ejecutivo_completo(programa)
        
        # Preparar datos para PDF
        datos_pdf = {
            'programa_info': {
                'nombre': programa.nombre,
                'fecha_inicio': programa.fecha_inicio.strftime('%d/%m/%Y'),
                'fecha_fin': programa.fecha_fin.strftime('%d/%m/%Y') if programa.fecha_fin else 'Sin definir',
                'fecha_reporte': timezone.now().strftime('%d/%m/%Y %H:%M')
            },
            'resumen_ejecutivo': {
                'kilos_planificados': datos_completos['produccion_fisica']['resumen_general']['kilos_planificados'],
                'kilos_fabricados': datos_completos['produccion_fisica']['resumen_general']['kilos_fabricados'],
                'porcentaje_completado': datos_completos['produccion_fisica']['resumen_general']['porcentaje_completado_kilos'],
                'eficiencia_promedio': datos_completos['eficiencia_operacional']['resumen_eficiencia']['eficiencia_promedio_programa']
            },
            'alertas_criticas': [a for a in datos_completos['alertas_ejecutivas'] if a['prioridad'] == 'CRITICA'],
            'proyecciones': datos_completos['proyecciones']
        }
        
        return Response({
            'success': True,
            'datos_pdf': datos_pdf,
            'nota': 'Integrar con generador de PDF según necesidades'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def kpis_ejecutivos_todos_programas(request):
    """
    KPIs ejecutivos consolidados de todos los programas activos
    """
    try:
        # Obtener programas activos (simplificado)
        programas_activos = ProgramaProduccion.objects.filter(
            fecha_fin__gte=timezone.now().date()
        )
        
        engine = ExecutiveMetricsEngine()
        
        consolidado = {
            'total_programas_activos': programas_activos.count(),
            'kilos_planificados_total': 0,
            'kilos_fabricados_total': 0,
            'eficiencia_promedio_empresa': 0,
            'programas_detalle': []
        }
        
        eficiencias = []
        
        for programa in programas_activos:
            metricas = engine.get_metricas_produccion_fisica(programa)
            eficiencia_op = engine.get_eficiencia_operacional(programa)
            
            kilos_plan = metricas['resumen_general']['kilos_planificados']
            kilos_fab = metricas['resumen_general']['kilos_fabricados']
            eficiencia = eficiencia_op['resumen_eficiencia']['eficiencia_promedio_programa']
            
            consolidado['kilos_planificados_total'] += kilos_plan
            consolidado['kilos_fabricados_total'] += kilos_fab
            eficiencias.append(eficiencia)
            
            consolidado['programas_detalle'].append({
                'id': programa.id,
                'nombre': programa.nombre,
                'kilos_planificados': kilos_plan,
                'kilos_fabricados': kilos_fab,
                'porcentaje_completado': metricas['resumen_general']['porcentaje_completado_kilos'],
                'eficiencia': eficiencia
            })
        
        if eficiencias:
            consolidado['eficiencia_promedio_empresa'] = sum(eficiencias) / len(eficiencias)
        
        consolidado['porcentaje_completado_empresa'] = (
            (consolidado['kilos_fabricados_total'] / consolidado['kilos_planificados_total'] * 100) 
            if consolidado['kilos_planificados_total'] > 0 else 0
        )
        
        return Response({
            'success': True,
            'consolidado': consolidado,
            'timestamp': timezone.now()
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def configurar_parametros_costos(request):
    """
    Endpoint para configurar parámetros de costos cuando estén disponibles
    """
    try:
        parametros = request.data.get('parametros', {})
        
        # Guardar en configuración (por implementar)
        # Por ahora solo devolvemos la estructura
        
        return Response({
            'success': True,
            'message': 'Parámetros de costos configurados',
            'parametros_guardados': parametros,
            'nota': 'Implementar persistencia de configuración'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def metricas_tiempo_real(request, programa_id):
    """
    Métricas en tiempo real con auto-refresh
    """
    try:
        programa = get_object_or_404(ProgramaProduccion, id=programa_id)
        engine = ExecutiveMetricsEngine()
        
        # Solo las métricas más importantes para tiempo real
        metricas_rapidas = {
            'produccion_hoy': {},  # Implementar producción del día actual
            'alertas_activas': engine.get_alertas_ejecutivas(programa),
            'eficiencia_actual': 0,  # Implementar cálculo rápido
            'maquinas_activas': 0,  # Implementar conteo de máquinas activas
            'operadores_activos': 0  # Implementar conteo de operadores activos
        }
        
        return Response({
            'success': True,
            'metricas_tiempo_real': metricas_rapidas,
            'timestamp': timezone.now(),
            'refresh_recomendado': 30  # segundos
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 