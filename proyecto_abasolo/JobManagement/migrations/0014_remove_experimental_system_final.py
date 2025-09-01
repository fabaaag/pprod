# Migración para eliminar sistema experimental usando SeparateDatabaseAndState
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('JobManagement', '0013_remove_experimental_system'),
        ('Operator', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Operaciones en la base de datos
            database_operations=[
                # Eliminar las tablas experimentales si existen
                migrations.RunSQL(
                    sql=[
                        "DROP TABLE IF EXISTS experimental_punto_control;",
                        "DROP TABLE IF EXISTS experimental_sesion;", 
                        "DROP TABLE IF EXISTS experimental_ventana_trabajo;",
                        "DROP TABLE IF EXISTS experimental_configuracion;",
                    ],
                    reverse_sql=[]
                ),
            ],
            # Operaciones en el estado de Django
            state_operations=[
                # Remover los modelos del estado de Django
                migrations.DeleteModel(name='PuntoControl'),
                migrations.DeleteModel(name='SesionExperimental'),
                migrations.DeleteModel(name='VentanaTrabajo'),
                migrations.DeleteModel(name='ConfiguracionExperimental'),
            ]
        ),
    ] 