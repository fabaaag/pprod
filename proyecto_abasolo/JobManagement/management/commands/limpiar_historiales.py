from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import datetime
from JobManagement.models import (
    HistorialPlanificacion,
    TareaFragmentada,
    ReporteDiarioPrograma
)

class Command(BaseCommand):
    help = 'Limpia los historiales duplicados y restaura el estado de las tareas'

    def add_arguments(self, parser):
        parser.add_argument('programa_id', type=int, help='ID del programa')
        parser.add_argument('fecha', type=str, help='Fecha en formato YYYY-MM-DD')

    def handle(self, *args, **options):
        programa_id = options['programa_id']
        fecha = datetime.strptime(options['fecha'], '%Y-%m-%d').date()

        try:
            with transaction.atomic():
                # 1. Encontrar todos los historiales para esta fecha y programa
                historiales = HistorialPlanificacion.objects.filter(
                    programa_id=programa_id,
                    fecha_referencia=fecha,
                    tipo_reajuste='DIARIO'
                ).order_by('fecha_reajuste')

                if not historiales.exists():
                    self.stdout.write(self.style.WARNING('No se encontraron historiales para esta fecha'))
                    return

                self.stdout.write(f'Se encontraron {historiales.count()} historiales')

                # 2. Mantener solo el primer historial si existe y eliminar los demás
                if historiales.count() > 1:
                    historiales_a_eliminar = historiales[1:]
                    for historial in historiales_a_eliminar:
                        self.stdout.write(f'Eliminando historial ID: {historial.id}')
                        historial.delete()

                # 3. Restaurar el estado de las tareas
                tareas = TareaFragmentada.objects.filter(
                    programa_id=programa_id,
                    fecha=fecha
                )

                for tarea in tareas:
                    # Restaurar estado original de la tarea
                    tarea.estado = 'PENDIENTE'
                    if tarea.cantidad_completada > 0:
                        tarea.estado = 'EN_PROCESO'
                    tarea.save()

                # 4. Restaurar el estado del reporte diario
                reporte = ReporteDiarioPrograma.objects.filter(
                    programa_id=programa_id,
                    fecha=fecha
                ).first()

                if reporte:
                    reporte.estado = 'ABIERTO'
                    reporte.fecha_cierre = None
                    reporte.cerrado_por = None
                    reporte.save()
                    self.stdout.write(f'Reporte del día restaurado a estado ABIERTO')

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Proceso completado exitosamente:\n'
                        f'- Historiales eliminados: {historiales.count() - 1}\n'
                        f'- Tareas restauradas: {tareas.count()}\n'
                        f'- Reporte diario restaurado'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error durante la limpieza: {str(e)}')
            )
            raise