# Migración manual para eliminar sistema experimental
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('JobManagement', '0012_itemruta_justificacion_salto'),
    ]

    operations = [
        # Eliminar directamente las tablas experimentales usando SQL crudo
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS experimental_punto_control;",
                "DROP TABLE IF EXISTS experimental_sesion;", 
                "DROP TABLE IF EXISTS experimental_ventana_trabajo;",
                "DROP TABLE IF EXISTS experimental_configuracion;",
            ],
            reverse_sql=[
                # No proporcionamos SQL reverso ya que no queremos poder revertir esta migración
            ]
        ),
        
        # Actualizar el constraint de EstandarMaquinaProceso si es necesario
        migrations.RemoveConstraint(
            model_name='estandarmaquinaproceso',
            name='producto_or_pieza_required',
        ),
        migrations.AddConstraint(
            model_name='estandarmaquinaproceso',
            constraint=models.CheckConstraint(
                check=models.Q(('producto__isnull', False), ('pieza__isnull', False), _connector='OR'), 
                name='producto_or_pieza_required_estandar'
            ),
        ),
    ] 