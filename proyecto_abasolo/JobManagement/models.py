import decimal
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import JSONField
from django.utils import timezone
from django.core.exceptions import ValidationError
from Client.models import Cliente
from Product.models import Producto, Pieza, MateriaPrima, MeasurementUnit
from datetime import datetime, time, timedelta, date
import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.db.models import Q




# Create your models here.


class Maquina(models.Model):
    codigo_maquina = models.CharField(max_length=10, null=False, blank=False, unique=False)
    descripcion = models.CharField(max_length=100, null=False, blank=False)
    sigla = models.CharField(max_length=10, null=False, blank=False, default='')
    carga = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    golpes = models.IntegerField(default=0)
    empresa = models.ForeignKey('EmpresaOT', on_delete=models.CASCADE, null=True)

    class Meta:
        unique_together = ('empresa', 'codigo_maquina')

    def __str__(self):
        return f'{self.codigo_maquina} - {self.descripcion}'
    
    def get_disponibilidad_fecha(self, fecha):
        """Obtiene la disponibilidad para una fecha específica"""
        from Machine.models import DisponibilidadMaquina
        return DisponibilidadMaquina.objects.get_or_create(
            maquina=self,
            fecha=fecha
        )[0]
    
    def validar_disponibilidad(self, fecha, cantidad, estandar):
        """Valida si la máquina puede aceptar más carga en una fecha"""
        disponibilidad = self.get_disponibilidad_fecha(fecha)
        estado = self.estado
        
        if not disponibilidad.disponible:
            return False, "Máquina no disponible en esta fecha"
        
        horas_efectivas = disponibilidad.get_horas_efectivas()
        capacidad_dia = estado.get_capacidad_real() * horas_efectivas
        carga_actual = self.calcular_carga_fecha(fecha)
        horas_requeridas = cantidad / estandar
        
        if (carga_actual + horas_requeridas) > capacidad_dia:
            return False, f"Capacidad insuficiente. Disponible: {capacidad_dia - carga_actual} hrs, Requerido: {horas_requeridas} hrs"
            
        return True, "Máquina disponible"
    
    def calcular_carga_fecha(self, fecha):
        """Calcula la carga total para una fecha específica basada en ItemRuta"""
        from datetime import datetime, time
        inicio_dia = datetime.combine(fecha, time.min)
        fin_dia = datetime.combine(fecha, time.max)
        
        # Obtener todos los ItemRuta que usan esta máquina en la fecha
        items_ruta = ItemRuta.objects.filter(
            maquina=self,
            ruta_ot__programa__fecha_inicio__lte=fecha,
            ruta_ot__programa__fecha_fin__gte=fecha
        ).select_related(
            'ruta_ot__programa',
            'ruta_ot__orden_trabajo'
        )

        carga_total = 0
        for item in items_ruta:
            # Validar si el proceso está programado para esta fecha
            if self.proceso_programado_para_fecha(item, fecha):
                # Calcular carga basada en cantidad y estándar
                carga_total += item.cantidad / item.estandar if item.estandar else 0
                
        return carga_total

    def proceso_programado_para_fecha(self, item_ruta, fecha):
        """Determina si un proceso está programado para una fecha específica"""
        programa = item_ruta.ruta_ot.programa
        
        # Si tenemos fechas específicas en el timeline
        timeline = programa.timeline_set.filter(
            item_ruta=item_ruta,
            fecha=fecha
        ).exists()
        
        if timeline:
            return True
            
        # Si no hay timeline específico, usar lógica de programación general
        orden_trabajo = item_ruta.ruta_ot.orden_trabajo
        prioridad = orden_trabajo.programaordentrabajo_set.filter(
            programa=programa
        ).first()
        
        if not prioridad:
            return False
            
        # Aquí podrías implementar la lógica para determinar si,
        # basado en la prioridad y la secuencia de procesos,
        # este proceso debería estar activo en esta fecha
        
        return False  # Por defecto, ser conservador

class Proceso(models.Model):
    codigo_proceso = models.CharField(max_length=10, null=False, blank=False, unique=False)
    sigla = models.CharField(max_length=10, null=True, blank=True)
    descripcion = models.CharField(max_length=100, null=False, blank=False)
    carga = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    empresa = models.ForeignKey('EmpresaOT', on_delete=models.CASCADE, null=True, blank=True)
    # Añadir esta relación
    tipos_maquina_compatibles = models.ManyToManyField('Machine.TipoMaquina', related_name='procesos_compatibles')

    class Meta:
        unique_together = ('empresa', 'codigo_proceso')

    def __str__(self):
        return f'{self.codigo_proceso} - {self.descripcion}'

    def get_maquinas_compatibles(self):
        """Obtiene todas las máquinas compatibles con este proceso"""
        from Machine.models import EstadoMaquina
        
        return Maquina.objects.filter(
            estadomaquina__tipos_maquina__in=self.tipos_maquina_compatibles.all(),
            estadomaquina__estado_operatividad__estado='OP'  # Solo máquinas operativas
        ).distinct()
    
class Ruta(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='rutas')
    nro_etapa = models.PositiveIntegerField()
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE)
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE)
    estandar = models.IntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'nro_etapa', 'proceso', 'maquina')

    def __str__(self):
        return f'{self.producto.codigo_producto} - Etapa {self.nro_etapa} - {self.proceso.codigo_proceso}'
    
class RutaPieza(models.Model):
    pieza = models.ForeignKey(Pieza, on_delete=models.CASCADE, related_name='rutas')
    nro_etapa = models.PositiveIntegerField()
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE)
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE)
    estandar = models.IntegerField(default=0)

    class Meta:
        unique_together = ('pieza', 'nro_etapa', 'proceso', 'maquina')

    def __str__(self):
        return f'{self.pieza.codigo_pieza} - Etapa {self.nro_etapa} - {self.proceso.codigo_proceso}'
    
class TipoOT(models.Model):
    codigo_tipo_ot = models.CharField(max_length=2, unique=True)
    descripcion = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f'{self.codigo_tipo_ot}: {self.descripcion}' or 'Unnamed'
    
class SituacionOT(models.Model):
    codigo_situacion_ot = models.CharField(max_length=2, unique=True)
    descripcion = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f'{self.codigo_situacion_ot}: {self.descripcion}' or 'Unnamed'
    
class EmpresaOT(models.Model):
    nombre = models.CharField(max_length=50, blank=False, null=False)
    apodo = models.CharField(max_length=50, blank=False, null=False, unique=True)
    codigo_empresa = models.CharField(max_length=50, blank=False, null=False, unique=True)

    def __str__(self):
        return f'{self.apodo} - {self.codigo_empresa}'
    
class ItemRuta(models.Model):
    item = models.PositiveIntegerField()
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE)
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE)
    estandar = models.IntegerField(default=0)
    cantidad_pedido = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    cantidad_terminado_proceso = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    cantidad_perdida_proceso = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    terminado_sin_actualizar = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    ruta = models.ForeignKey('RutaOT', on_delete=models.CASCADE, related_name='items')

    # ============= NUEVOS CAMPOS PARA PROGRESO DIRECTO =============
    # Control de progreso tiempo real
    permite_progreso_directo = models.BooleanField(default=True)
    cantidad_en_proceso = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    porcentaje_completado = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Tracking temporal
    fecha_inicio_real = models.DateTimeField(null=True, blank=True)
    fecha_fin_real = models.DateTimeField(null=True, blank=True)
    ultima_actualizacion_progreso = models.DateTimeField(null=True, blank=True)
    
    # Estado del proceso
    estado_proceso = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE', 'Pendiente'),
            ('EN_PROCESO', 'En Proceso'),
            ('COMPLETADO', 'Completado'),
            ('PAUSADO', 'Pausado'),
            ('CANCELADO', 'Cancelado')
        ],
        default='PENDIENTE'
    )
    
    # Personal y observaciones
    operador_actual = models.ForeignKey(
        'Operator.Operador', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='items_en_proceso'
    )
    observaciones_progreso = models.TextField(blank=True)
    
    # Tracking de cambios
    historial_progreso = JSONField(default=list, help_text='Historial de actualizaciones de progreso')
    
    class Meta:
        unique_together = ('ruta', 'item', 'maquina', 'proceso')

    def __str__(self):
        return f'Item {self.item} de Ruta de Orden:'
    
    # ============= NUEVOS MÉTODOS PARA PROGRESO DIRECTO =============
    @property
    def cantidad_pendiente(self):
        """Cantidad que falta por completar"""
        from decimal import Decimal
        # Asegurar que ambos valores son Decimal
        pedido = self.cantidad_pedido if isinstance(self.cantidad_pedido, Decimal) else Decimal(str(self.cantidad_pedido or 0))
        terminado = self.cantidad_terminado_proceso if isinstance(self.cantidad_terminado_proceso, Decimal) else Decimal(str(self.cantidad_terminado_proceso or 0))
        return max(Decimal('0'), pedido - terminado)
    
    @property
    def es_ultimo_proceso_ot(self):
        """Verifica si este es el último proceso de la OT"""
        ultimo_item = self.ruta.items.order_by('item').last()
        return ultimo_item and ultimo_item.id == self.id
    
    def iniciar_proceso(self, operador=None, observaciones=''):
        """Inicia el proceso"""
        if self.estado_proceso != 'PENDIENTE':
            raise ValidationError("El proceso ya ha sido iniciado")
        
        self.estado_proceso = 'EN_PROCESO'
        self.fecha_inicio_real = timezone.now()
        self.operador_actual = operador
        self.observaciones_progreso = observaciones
        self.registrar_cambio_progreso('INICIO_PROCESO', {
            'operador': operador.id if operador else None,
            'observaciones': observaciones
        })
        self.save()
    
    def actualizar_progreso(self, cantidad_completada_nueva, operador=None, observaciones='', usuario=None):
        """Actualiza el progreso del ItemRuta"""
        from django.utils import timezone
        from decimal import Decimal  # ✅ AGREGAR ESTA IMPORTACIÓN
        
        # Validaciones
        if cantidad_completada_nueva < 0:
            raise ValidationError("La cantidad completada no puede ser negativa")
        
        # Guardar valores anteriores
        cantidad_anterior = self.cantidad_terminado_proceso
        porcentaje_anterior = self.porcentaje_completado
        
        # ✅ CONVERTIR A DECIMAL ANTES DE USAR
        cantidad_completada_decimal = Decimal(str(cantidad_completada_nueva))
        
        # Actualizar valores
        self.cantidad_terminado_proceso = cantidad_completada_decimal
        self.porcentaje_completado = (cantidad_completada_decimal / self.cantidad_pedido * 100) if self.cantidad_pedido > 0 else 0
        self.ultima_actualizacion_progreso = timezone.now()
        
        if operador:
            self.operador_actual = operador
        
        if observaciones:
            self.observaciones_progreso = observaciones
        
        # Actualizar estado
        if cantidad_completada_decimal >= self.cantidad_pedido:
            self.estado_proceso = 'COMPLETADO'
            self.fecha_fin_real = timezone.now()
        elif cantidad_completada_decimal > 0 and self.estado_proceso == 'PENDIENTE':
            self.estado_proceso = 'EN_PROCESO'
            if not self.fecha_inicio_real:
                self.fecha_inicio_real = timezone.now()
        
        # Registrar cambio
        self.registrar_cambio_progreso('ACTUALIZACION_PROGRESO', {
            'cantidad_anterior': float(cantidad_anterior),
            'cantidad_nueva': float(cantidad_completada_decimal),  # ✅ USAR LA VERSIÓN DECIMAL
            'porcentaje_anterior': float(porcentaje_anterior),
            'porcentaje_nuevo': float(self.porcentaje_completado),
            'operador': operador.id if operador else None,
            'observaciones': observaciones,
            'usuario': usuario.id if usuario else None
        })
        
        self.save()
        
        # Si es el último proceso y está completado, actualizar la OT
        if self.es_ultimo_proceso_ot and self.estado_proceso == 'COMPLETADO':
            self.actualizar_progreso_ot()
        
        return self
    
    def actualizar_progreso_ot(self):
        """Actualiza el progreso de la OT basado en el progreso de todos sus ItemRuta"""
        if not self.ruta.orden_trabajo:
            return
        
        # Calcular progreso total de la OT
        items = self.ruta.items.all()
        total_cantidad_pedida = sum(item.cantidad_pedido for item in items)
        total_cantidad_completada = sum(item.cantidad_terminado_proceso for item in items)
        
        if total_cantidad_pedida > 0:
            porcentaje_ot = (total_cantidad_completada / total_cantidad_pedida) * 100
            
            # Actualizar cantidad_avance en OrdenTrabajo
            self.ruta.orden_trabajo.cantidad_avance = total_cantidad_completada
            self.ruta.orden_trabajo.save()
            
            # Registrar en historial
            self.registrar_cambio_progreso('ACTUALIZACION_OT', {
                'porcentaje_ot': porcentaje_ot,
                'cantidad_avance': float(total_cantidad_completada)
            })
    
    def registrar_cambio_progreso(self, tipo_cambio, datos):
        """Registra un cambio en el historial de progreso"""
        cambio = {
            'fecha': timezone.now().isoformat(),
            'tipo': tipo_cambio,
            'datos': datos
        }
        
        if not isinstance(self.historial_progreso, list):
            self.historial_progreso = []
        
        self.historial_progreso.append(cambio)
        
        # Mantener solo los últimos 50 cambios
        if len(self.historial_progreso) > 50:
            self.historial_progreso = self.historial_progreso[-50:]

    # ✅ NUEVOS CAMPOS (agregar al final)
    permite_salto_proceso = models.BooleanField(
        default=False,
        help_text="Permite que este proceso avance independientemente del anterior"
    )
    
    tipo_dependencia = models.CharField(
        max_length=20,
        choices=[
            ('ESTRICTA', 'Dependencia Estricta'),
            ('PARCIAL', 'Dependencia Parcial'),
            ('INDEPENDIENTE', 'Independiente'),
        ],
        default='ESTRICTA'
    )
    
    porcentaje_minimo_anterior = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text="% mínimo que debe completar el proceso anterior"
    )

    justificacion_salto = models.TextField(
        blank=True,
        help_text="Justificación cuando se permite salto de proceso"
    )

class RutaOT(models.Model):
    
    orden_trabajo = models.OneToOneField('OrdenTrabajo', on_delete=models.CASCADE, related_name='ruta_ot', null=True, blank=True)

    def __str__(self):
        if hasattr(self, 'orden_trabajo') and self.orden_trabajo:
            return f'Ruta asociada a la Orden de Trabajo: {self.orden_trabajo.codigo_ot}'
        return 'Ruta sin Orden de Trabajo asociada'
    
class OrdenTrabajo(models.Model):

    codigo_ot = models.IntegerField(unique=True)
    tipo_ot = models.ForeignKey(TipoOT, on_delete=models.PROTECT)
    situacion_ot = models.ForeignKey(SituacionOT, on_delete=models.PROTECT)
    fecha_emision = models.DateField(null=True, blank=True)
    fecha_proc = models.DateField(null=True, blank=True)
    fecha_termino = models.DateField(null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, null=True, blank=True)
    nro_nota_venta_ot = models.CharField(max_length=12, null=True, blank=True)
    item_nota_venta = models.IntegerField()
    referencia_nota_venta = models.IntegerField(null=True, blank=True)
    codigo_producto_inicial = models.CharField(max_length=12, null=True, blank=True)
    codigo_producto_salida = models.CharField(max_length=12, null=True, blank=True)
    descripcion_producto_ot = models.CharField(max_length=255, null=True, blank=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    unidad_medida = models.ForeignKey(MeasurementUnit, on_delete=models.PROTECT, null=True, blank=True)
    cantidad_avance = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    peso_unitario = models.DecimalField(max_digits=19, decimal_places=5, default=0.00000)
    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.PROTECT, null=True, blank=True)
    cantidad_mprima = models.DecimalField(max_digits=14, decimal_places=2, default=0.00000)
    unidad_medida_mprima = models.ForeignKey(MeasurementUnit, related_name='unidad_of_medida_materia_prima', on_delete=models.PROTECT, null=True, blank=True) #column 19
    observacion_ot = models.CharField(max_length=150, null=True, blank=True)
    empresa = models.ForeignKey(EmpresaOT, on_delete=models.PROTECT, null=True, blank=True)
    multa = models.BooleanField(default=False)
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)

    def __str__(self):
        return f'{self.codigo_ot}'

    def update_item_rutas(self, items_data):
        print("Items data:", items_data)
        # Si recibes el listado de máquinas en el frontend, sería ideal cargar estas previamente
        maquinas_dict = {maquina.id: maquina for maquina in Maquina.objects.all()}
        
        for item_data in items_data:
            try:
                # Intenta obtener el ítem de la ruta correspondiente
                item = self.ruta_ot.items.get(item=item_data['item'])
                print("Item instance:", item)

                # Validar y actualizar la máquina si se proporciona
                if 'maquina' in item_data:
                    maquina = maquinas_dict.get(item_data['maquina'])
                    if maquina:
                        item.maquina = maquina
                    else:
                        print(f"Máquina con ID {item_data['maquina']} no encontrada.")
                
                # Actualizar el estándar de producción si se proporciona
                if 'estandar' in item_data:
                    item.estandar = item_data['estandar']
                
                item.save()  # Guardar los cambios en el ítem

            except ItemRuta.DoesNotExist:
                print(f"Ítem con el número {item_data['item']} no encontrado en la ruta.")
            except Exception as e:
                print(f"Error al actualizar ItemRuta: {e}")

class ProgramaProduccion(models.Model):
    nombre = models.CharField(max_length=100, unique=True, blank=True)
    #Fecha de inicio será determinada por la fecha de la ot en primera posición, y la fecha de fin se determinará por el cálculo de cuando termine el último proceso de la ultima ot
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='programas_creados'
    )
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='programas_modificados'
    )

    class Meta:
        verbose_name = "Programa Producción"
        verbose_name_plural = "Programas Producción"

    def __str__(self):
        return self.nombre
    
    def save(self, *args, **kwargs):
        if not self.nombre:
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            random_string = uuid.uuid4().hex[:6]
            self.nombre = f"Programa_{timestamp}_{random_string}"

        #Si es un programa nuevo y no tiene fecha_fin, usamos fecha_inicio + 30 dias como valor predeterminado
        if not self.pk and not self.fecha_fin:
            self.fecha_fin = self.fecha_inicio + timezone.timedelta(days=30)

        #Guardamos el objecto con los valores iniciales
        super().save(*args, **kwargs)

        #Si ya tiene OTs asociadas, calculamos la fecha_fin (para actualizaciones)
        if self.pk and ProgramaOrdenTrabajo.objects.filter(programa=self).exists():
            self.actualizar_fecha_fin()

    def actualizar_fecha_fin(self):
        """Método legacy manenido para compatibilidad"""
        pass
            
    @property
    def dias_programa(self):
        return (self.fecha_fin - self.fecha_inicio).days + 1

    #Crear métodos para disponibilidad de operadores y maquinas
    #Disponibilidad horaria más adelante

class ProgramaOrdenTrabajo(models.Model):
    programa =  models.ForeignKey(ProgramaProduccion, on_delete=models.CASCADE)
    orden_trabajo = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE)
    prioridad = models.PositiveIntegerField()

    class Meta:
        unique_together = ('programa', 'orden_trabajo')

    def save(self, *args, **kwargs):
        if not self.id:
            if self.orden_trabajo.situacion_ot.codigo_situacion_ot not in ['P', 'S']:
                raise ValidationError("La OT debe estar en situación 'Pendiente' o 'Sin imprimir'")
        super(ProgramaOrdenTrabajo, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.programa.nombre} - {self.orden_trabajo.codigo_ot} - Prioridad: {self.prioridad}'

class IntervaloDisponibilidad(models.Model):
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    

    TIPO_CHOICES = [
        ('MAQUINA', 'Maquina'),
        ('OPERADOR', 'Operador')
    ]
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    class Meta:
        abstract = True

    def clean(self):
        if self.fecha_inicio > self.fecha_fin:
            raise ValidationError("La fecha de inicio debe ser anterior a la fecha de fin")

        # Validar que esté dentro del horario (7:45 - 17:45)
        hora_laboral_inicio = time(7, 45)
        hora_laboral_fin = time(17, 45)

        #Verificar cada día del intervalo
        fecha_actual = self.fecha_inicio
        while fecha_actual <= self.fecha_fin:
            #Solo verificar días laborales(L-V)
            if fecha_actual.weekyday() < 5: #0-4 son Lunes a Viernes
                hora_inicio = fecha_actual.time()
                hora_fin = min(fecha_actual.replace(hour=17, minute=45).time(), self.fecha_fin.time() if fecha_actual.date() == self.fecha_fin.date() else hora_laboral_fin)

                if hora_inicio < hora_laboral_inicio or hora_fin > hora_laboral_fin:
                    raise ValidationError(f"El intervalo del día {fecha_actual.date()} debe estar dentro del horario laboral (7:45 - 17:45)")
                
            fecha_actual += timedelta(days=1)

    def tiene_conflicto(self, fecha_inicio, fecha_fin):
        """Verfifica si hay conflicto con otro intervalo de tiempo"""
        return not(fecha_fin <= self.fecha_inicio or fecha_inicio >= self.fecha_fin)
    
class IntervaloMaquina(IntervaloDisponibilidad):
    maquina = models.ForeignKey('Maquina', on_delete=models.CASCADE)
    motivo = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar DisponibilidadMaquina cuando se crea un intervalo
        from Machine.models import DisponibilidadMaquina, BloqueoMaquina
        
        # Crear o actualizar DisponibilidadMaquina para cada día del intervalo
        fecha_actual = self.fecha_inicio.date()
        while fecha_actual <= self.fecha_fin.date():
            disponibilidad, _ = DisponibilidadMaquina.objects.get_or_create(
                maquina=self.maquina,
                fecha=fecha_actual
            )
            
            # Crear BloqueoMaquina correspondiente
            if fecha_actual == self.fecha_inicio.date():
                hora_inicio = self.fecha_inicio.time()
            else:
                hora_inicio = time(7, 45)  # Hora inicio normal
                
            if fecha_actual == self.fecha_fin.date():
                hora_fin = self.fecha_fin.time()
            else:
                hora_fin = time(17, 45)  # Hora fin normal
                
            BloqueoMaquina.objects.create(
                disponibilidad=disponibilidad,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                motivo=f"Intervalo: {self.motivo}"
            )
            
            fecha_actual += timedelta(days=1)

    def __str__(self):
        return f"Intervalo {self.maquina.codigo_maquina} - {self.fecha_inicio.strftime('%Y-%m-%d %H:%M')} a {self.fecha_fin.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['maquina', 'fecha_inicio'],
                name='unique_maquina_intervalo'
            )
        ]

    @classmethod
    def validar_disponibilidad(cls, maquina, fecha_inicio, fecha_fin):
        """
        Verifica si una máquina está disponible en un intervalo de tiempo específico
        Retorna bool, str : (está_disponible, mensaje)
        """
        intervalos = cls.objects.filter(
            maquina=maquina,
            fecha_fin__gte=fecha_inicio,
            fecha_inicio__lte=fecha_fin
        )

        for intervalo in intervalos:
            if intervalo.tiene_conflicto(fecha_inicio, fecha_fin):
                return False, f"Maquina no disponible del {intervalo.fecha_inicio.strf.time('%Y-%m-%d %H:%M')} al {intervalo.fecha_fin.strftime('%Y-%m-%d H:%M')}"
            
        return True, "Disponible"
    

class IntervaloOperador(IntervaloDisponibilidad):
    operador = models.ForeignKey('Operator.Operador', on_delete=models.CASCADE)
    motivo = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Intervalo {self.operador.nombre} - ({self.fecha_inicio.strftime('%Y-%m-%d %H:%M')} a {self.hora_fin.strftime('%Y-%m-%d %H:%M')})"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['operador', 'fecha_inicio'],
                name='unique_operador_intervalo'
            )
        ]

    @classmethod
    def validar_disponibilidad(cls, operador, fecha, fecha_inicio, fecha_fin):
        """
        Verifica si un operador está disponible en un intervalo de tiempo específico
        Retorna (bool, str): (está_disponible, mensaje)
        """
        intervalos = cls.objects.filter(
            operador=operador,
            fecha_fin__gte=fecha_inicio,
            fecha_inicio__lte=fecha_fin
        )

        for intervalo in intervalos:
            if intervalo.tiene_conflicto(fecha, fecha_inicio, fecha_fin):
                return False, f"Operador no disponible de {intervalo.fecha_inicio.strftime('%Y-%m-%d %H:%M')} a {intervalo.fecha_fin.strftime('%Y-%m-%d %H:%M')}"
            
        return True, "Disponible"

    @classmethod
    def encontrar_siguiente_disponibilidad(cls, operador, fecha_inicio, duracion_horas):
        """
        Encuentra el siguiente intervalo disponible para un operador
        """

        #Obtener todos los intervalos futuros del operador
        intervalos = cls.objects.filter(
            operador=operador,
            fecha_fin__gte=fecha_inicio
        ).order_by('fecha_inicio')

        fecha_propuesta = fecha_inicio
        duracion = timedelta(hours=duracion_horas)

        for intervalo in intervalos:
            fecha_fin_propuesta = fecha_propuesta + duracion

            #Si no hay conflicto, hemos encontrado un espacio
            if not intervalo.tiene_conflicto(fecha_propuesta, fecha_fin_propuesta):
                return fecha_propuesta

            #Si hay conflicto, intentar después del intervalo actual
            fecha_propuesta = intervalo.fecha_fin

        #Si no encontramos conflictos o no hay más intervalos, usar la última fecha propuesta
        return fecha_propuesta

class TareaFragmentada(models.Model):
    # Relaciones principales (mantenemos y añadimos)
    tarea_original = models.ForeignKey('ItemRuta', on_delete=models.CASCADE, related_name='fragmentos')
    tarea_padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='continuaciones')
    programa = models.ForeignKey('ProgramaProduccion', on_delete=models.CASCADE)
    operador = models.ForeignKey('Operator.Operador', on_delete=models.SET_NULL, null=True, blank=True)

    # Campos temporales (mantenemos y mejoramos)
    fecha = models.DateField()
    fecha_planificada_inicio = models.DateTimeField(null=True, blank=True)
    fecha_planificada_fin = models.DateTimeField(null=True, blank=True)
    fecha_real_inicio = models.DateTimeField(null=True, blank=True)
    fecha_real_fin = models.DateTimeField(null=True, blank=True)

    # Campos de cantidades (unificamos conceptos)
    cantidad_asignada = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_pendiente_anterior = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cantidad_completada = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    kilos_fabricados = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unidades_fabricadas = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Control de estado y fragmentación (mantenemos)
    estado = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE', 'Pendiente'),
            ('EN_PROCESO', 'En Proceso'),
            ('COMPLETADO', 'Completado'),
            ('CONTINUADO', 'Continuado al siguiente día'),
            ('DETENIDO', 'Detenido')
        ],
        default='PENDIENTE'
    )
    es_continuacion = models.BooleanField(default=False)
    nivel_fragmentacion = models.IntegerField(default=0)

    # Campos adicionales
    observaciones = models.TextField(blank=True)
    motivo_detencion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Campos para tracking de cambios
    version_planificacion = models.IntegerField(default=1)
    fecha_ultima_modificacion = models.DateTimeField(auto_now=True)
    motivo_modificacion = models.CharField(
        max_length=50, 
        choices=[
            ('BASE', 'Planificación Base'),
            ('AJUSTE_DIA', 'Ajuste por Fin de Día'),
            ('AJUSTE_MANUAL', 'Ajuste Manual'),
            ('CONFLICTO_MAQUINA', 'Ajuste por Conflicto de Máquina'),
            ('CONTINUACION', 'Continuación de Tarea'),
        ],
        null=True,
        blank=True
    )
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='tareas_modificadas'
    )

    # Campos para tracking de timeline
    fecha_planificada_inicio_original = models.DateTimeField(null=True, blank=True)
    fecha_planificada_fin_original = models.DateTimeField(null=True, blank=True)

    # Nuevos campos para mejor tracking
    historial_cambios = JSONField(default=list)  # [
        # {
        #   fecha: datetime,
        #   tipo_cambio: str,
        #   datos_anteriores: dict,
        #   datos_nuevos: dict,
        #   usuario: int,
        #   motivo: str
        # }
    #]
    
    # Campos para manejo de continuaciones
    continuaciones_futuras = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='tareas_anteriores'
    )
    
    # Campos para tracking de cantidades
    cantidad_total_original = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,  # Permitimos null inicialmente
        blank=True,  # Permitimos que esté vacío en formularios
        help_text="Cantidad original asignada a la tarea"
    )
    
    # Campos para validación
    ultima_validacion = models.DateTimeField(null=True, blank=True)
    estado_validacion = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE', 'Pendiente de Validación'),
            ('VALIDADO', 'Validado'),
            ('ERROR', 'Error en Validación')
        ],
        default='PENDIENTE'
    )

    # ============= NUEVOS CAMPOS PARA TIEMPO REAL (AGREGAR) =============
    modo_actualizacion = models.CharField(
        max_length=20,
        choices=[
            ('MANUAL', 'Actualización Manual'),
            ('TIEMPO_REAL', 'Tiempo Real'),
            ('HIBRIDO', 'Híbrido')
        ],
        default='MANUAL'
    )
    
    ultima_actualizacion_tiempo_real = models.DateTimeField(null=True, blank=True)
    progreso_tiempo_real = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    velocidad_actual = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    permite_edicion_rapida = models.BooleanField(default=True)
    bloqueo_edicion = models.BooleanField(default=False)

    # ============= MÉTODOS EXISTENTES (MANTENER) + NUEVOS =============
    # Mantenemos los métodos existentes
    @property
    def cantidad_total_dia(self):
        return self.cantidad_asignada + self.cantidad_pendiente_anterior

    @property
    def cantidad_pendiente(self):
        return self.cantidad_total_dia - self.cantidad_completada

    @property
    def porcentaje_cumplimiento(self):
        if self.cantidad_total_dia > 0:
            return (self.cantidad_completada / self.cantidad_total_dia) * 100
        return 0

    def acumular_pendiente(self, cantidad):
        # Mantenemos el método existente
        siguiente_fragmento = TareaFragmentada.objects.filter(
            tarea_original=self.tarea_original,
            fecha__gt=self.fecha
        ).order_by('fecha').first()

        if siguiente_fragmento:
            siguiente_fragmento.cantidad_pendiente_anterior += cantidad
            siguiente_fragmento.save()
            return True
        return False

    def crear_continuacion(self, cantidad_pendiente, nueva_fecha):
        """
        Crea una nueva tarea como continuación de la actual y actualiza todas las referencias
        necesarias para mantener la consistencia.
        """
        # 1. Crear la continuación con referencias adecuadas
        continuacion = TareaFragmentada.objects.create(
            tarea_original=self.tarea_original,
            tarea_padre=self,
            programa=self.programa,
            fecha=nueva_fecha,
            cantidad_asignada=cantidad_pendiente,
            cantidad_pendiente_anterior=Decimal('0'),
            es_continuacion=True,
            nivel_fragmentacion=self.nivel_fragmentacion + 1,
            version_planificacion=self.version_planificacion + 1,
            motivo_modificacion='CONTINUACION',
            estado='PENDIENTE',  # Siempre inicia como pendiente
            # Heredar operador si existe
            operador=self.operador,
            # Calcular nuevas fechas planificadas
            fecha_planificada_inicio=datetime.combine(nueva_fecha, time(7, 45)),
            fecha_planificada_fin=None  # Se calculará después
        )
        
        # 2. Calcular fechas de planificación realistas
        if self.tarea_original.estandar and cantidad_pendiente:
            from .services.time_calculations import TimeCalculator
            calculator = TimeCalculator()
            calculo = calculator.calculate_working_days(
                continuacion.fecha_planificada_inicio,
                float(cantidad_pendiente),
                float(self.tarea_original.estandar)
            )
            if 'error' not in calculo:
                continuacion.fecha_planificada_fin = calculo['next_available_time']
        
        continuacion.save(update_fields=['fecha_planificada_fin'])
        
        # 3. Actualizar el estado de la tarea actual a "CONTINUADO"
        self.estado = 'CONTINUADO'
        self.save(update_fields=['estado'])
        
        # 4. Agregar a continuaciones_futuras para referencia bidireccional
        self.continuaciones_futuras.add(continuacion)
        
        # 5. Registrar en historial de cambios
        cambio = {
            'fecha': timezone.now().isoformat(),
            'tipo_cambio': 'CONTINUACION',
            'datos_anteriores': {
                'estado': 'PENDIENTE' if self.estado != 'CONTINUADO' else self.estado,
                'cantidad_completada': str(self.cantidad_completada),
                'cantidad_pendiente': str(self.cantidad_total_dia - self.cantidad_completada)
            },
            'datos_nuevos': {
                'estado': 'CONTINUADO',
                'continuacion_id': continuacion.id,
                'continuacion_fecha': nueva_fecha.isoformat(),
                'cantidad_continuada': str(cantidad_pendiente)
            }
        }
        
        if not self.historial_cambios:
            self.historial_cambios = []
        self.historial_cambios.append(cambio)
        self.save(update_fields=['historial_cambios'])
        
        # 6. Propagar cambios a tareas dependientes
        self._propagar_ajustes_continuacion(continuacion)
        
        return continuacion

    def _propagar_ajustes_continuacion(self, continuacion):
        """
        Propaga los ajustes necesarios a las tareas dependientes
        cuando se crea una continuación.
        """
        # Buscar procesos posteriores en la misma OT
        if not self.tarea_original or not self.tarea_original.ruta:
            return
        
        # Encontrar tareas que dependen de esta (procesos posteriores en la misma OT)
        siguiente_item_ruta = ItemRuta.objects.filter(
            ruta=self.tarea_original.ruta,
            item__gt=self.tarea_original.item
        ).order_by('item').first()
        
        if not siguiente_item_ruta:
            return  # No hay procesos posteriores
        
        # Buscar tareas fragmentadas para el siguiente proceso
        tareas_dependientes = TareaFragmentada.objects.filter(
            programa=self.programa,
            tarea_original=siguiente_item_ruta,
            fecha__gte=self.fecha  # Solo afectar a las que están programadas desde esta fecha en adelante
        )
        
        # Si no hay tareas dependientes, no hay nada que propagar
        if not tareas_dependientes.exists():
            return
        
        # Fecha desde la que inicia la primera tarea dependiente
        primera_tarea = tareas_dependientes.order_by('fecha').first()
        
        # Si la fecha de inicio de la tarea dependiente es anterior a la fecha
        # de la continuación, necesitamos reajustarla
        if primera_tarea and primera_tarea.fecha < continuacion.fecha:
            # Ajustar esta tarea para que empiece después de la continuación
            primera_tarea.fecha = continuacion.fecha
            primera_tarea.fecha_planificada_inicio = continuacion.fecha_planificada_inicio
            
            # Recalcular fecha de fin
            if primera_tarea.tarea_original.estandar:
                from .services.time_calculations import TimeCalculator
                calculator = TimeCalculator()
                calculo = calculator.calculate_working_days(
                    primera_tarea.fecha_planificada_inicio,
                    float(primera_tarea.cantidad_asignada),
                    float(primera_tarea.tarea_original.estandar)
                )
                if 'error' not in calculo:
                    primera_tarea.fecha_planificada_fin = calculo['next_available_time']
            
            primera_tarea.save()
            
            # También propagar a las tareas siguientes
            primera_tarea._propagar_ajustes_continuacion(primera_tarea)

    def registrar_produccion(self, kilos_fabricados, cantidad_completada):
        """Registra la producción y actualiza los campos relacionados"""
        try:
            # Convertir todos los valores a Decimal en lugar de float
            self.kilos_fabricados = Decimal(str(kilos_fabricados))
            self.cantidad_completada = Decimal(str(cantidad_completada))
            
            self.save()
        except Exception as e:
            print(f"Error en registrar_produccion: {str(e)}")
            raise e

    def clean(self):
        super().clean()
        
        # Validar cantidades
        if self.cantidad_completada > self.cantidad_total_dia:
            self.cantidad_completada = self.cantidad_total_dia
            self.cantidad_pendiente = 0
        
        # Validar estado según cantidades
        if self.cantidad_completada >= self.cantidad_total_dia:
            if self.estado != 'COMPLETADO':
                self.estado = 'COMPLETADO'
                # Si era una continuación, verificar y limpiar continuaciones futuras
                if self.es_continuacion:
                    self._limpiar_continuaciones_futuras()

    def _limpiar_continuaciones_futuras(self):
        """Elimina o cancela las continuaciones futuras cuando una tarea se completa"""
        continuaciones_futuras = TareaFragmentada.objects.filter(
            tarea_original=self.tarea_original,
            fecha__gt=self.fecha,
            es_continuacion=True
        )
        
        for continuacion in continuaciones_futuras:
            continuacion.delete()  # O marcarla como cancelada según necesites

    def registrar_cambio(self, tipo_cambio, datos_anteriores, datos_nuevos, usuario, motivo=None):
        """Registra un cambio en el historial de la tarea"""
        cambio = {
            'fecha': timezone.now(),
            'tipo_cambio': tipo_cambio,
            'datos_anteriores': datos_anteriores,
            'datos_nuevos': datos_nuevos,
            'usuario': usuario.id if usuario else None,
            'motivo': motivo
        }
        self.historial_cambios.append(cambio)
        self.save()
    
    def validar_cantidades(self):
        """Valida la consistencia de las cantidades"""
        total = self.cantidad_asignada
        completada = self.cantidad_completada
        pendiente = self.cantidad_pendiente
        
        if total < (completada + pendiente):
            return False, "La suma de cantidades completadas y pendientes excede el total"
        
        return True, "Cantidades válidas"

    # NUEVO método para tiempo real
    def actualizar_tiempo_real(self, cantidad_completada, usuario=None):
        """Actualiza la tarea en tiempo real"""
        from django.utils import timezone
        
        # Guardar estado anterior
        datos_anteriores = {
            'cantidad_completada': str(self.cantidad_completada),
            'estado': self.estado,
            'porcentaje': str(self.porcentaje_cumplimiento)
        }
        
        # Aplicar cambios
        self.cantidad_completada = cantidad_completada
        self.ultima_actualizacion_tiempo_real = timezone.now()
        self.progreso_tiempo_real = (cantidad_completada / self.cantidad_total_dia) * 100
        
        # Auto-cambiar estado
        if self.progreso_tiempo_real >= 100:
            self.estado = 'COMPLETADO'
        elif self.progreso_tiempo_real > 0:
            self.estado = 'EN_PROCESO'
        
        # Registrar en historial_cambios (campo existente)
        if usuario:
            cambio = {
                'fecha': timezone.now().isoformat(),
                'tipo_cambio': 'ACTUALIZACION_TIEMPO_REAL',
                'datos_anteriores': datos_anteriores,
                'datos_nuevos': {
                    'cantidad_completada': str(cantidad_completada),
                    'estado': self.estado,
                    'porcentaje': str(self.progreso_tiempo_real)
                },
                'usuario': usuario.id,
                'motivo': 'Actualización desde timeline tiempo real'
            }
            
            if not self.historial_cambios:
                self.historial_cambios = []
            self.historial_cambios.append(cambio)
        
        self.save()
        return True

class EjecucionTarea(models.Model):
    """
    Modelo para registrar la ejecución real de las tareas.
    Permite mantener un historial detallado de la producción.
    """
    tarea = models.ForeignKey(
        TareaFragmentada, 
        on_delete=models.CASCADE,
        related_name='ejecuciones'
    )
    fecha_hora_inicio = models.DateTimeField()
    fecha_hora_fin = models.DateTimeField()
    cantidad_producida = models.DecimalField(max_digits=10, decimal_places=2)
    operador = models.ForeignKey(
        'Operator.Operador', 
        on_delete=models.SET_NULL, 
        null=True
    )
    estado = models.CharField(
        max_length=20,
        choices=[
            ('EN_PROCESO', 'En Proceso'),
            ('PAUSADO', 'Pausado'),
            ('COMPLETADO', 'Completado')
        ]
    )
    motivo_pausa = models.CharField(max_length=255, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_hora_inicio']

class ReporteDiarioPrograma(models.Model):
    """
    Modelo para manejar el estado general del programa por día.
    Permite controlar el cierre de día y mantener estadísticas.
    """
    programa = models.ForeignKey('ProgramaProduccion', on_delete=models.CASCADE)
    fecha = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=[
            ('ABIERTO', 'Abierto'),
            ('CERRADO', 'Cerrado'),
            ('EN_REVISION', 'En Revisión')
        ],
        default='ABIERTO'
    )
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reportes_cerrados'
    )
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    observaciones_cierre = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['programa', 'fecha']

class ReporteSupervisor(models.Model):
    """Modelo para gestionar el reporte global de un supervisor para un programa"""
    programa = models.OneToOneField(
        ProgramaProduccion,
        on_delete=models.CASCADE,
        related_name='reporte_supervisor'
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='programas_supervisados'
    )
    estado = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVO', 'Activo'),
            ('FINALIZADO', 'Finalizado'),
            ('PAUSADO', 'Pausado')
        ],
        default='ACTIVO'
    )
    notas = models.TextField(blank=True, null=True)
    porcentaje_completado = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    #Campos para el bloqueo de edición
    editor_actual = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reportes_editando'
    )
    bloqueo_hasta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Reporte de Supervisor'
        verbose_name_plural = 'Reportes de Supervisor'

    def __str__(self):
        return f'Reporte Supervisor: {self.programa.nombre}'
    
    def calcular_porcentaje_completado(self):
        """Calcular porcentaje de tareas completadas del programa"""
        tareas = TareaFragmentada.objects.filter(programa=self.programa)
        if not tareas.exists():
            return 0
        
        total_tareas = tareas.count()
        tareas_completadas = tareas.filter(estado='COMPLETADO').count()

        porcentaje = (tareas_completadas / total_tareas) * 100 if total_tareas > 0 else 0
        self.porcentaje_completado = round(porcentaje, 2)
        self.save(update_fields=['porcentaje_completado'])
        return self.porcentaje_completado
    

    #Métodos para gestonar el bloqueo
    def esta_bloqueado(self):
        return (self.editor_actual is not None and
                self.bloqueo_hasta is not None and
                self.bloqueo_hasta > timezone.now())
    
    def puede_editar(self, usuario):
        if not self.esta_bloqueado():
            return True
        return self.editor_actual == usuario
    
    def adquirir_bloqueo(self, usuario, duracion_minutos=30):
        if self.esta_bloqueado() and self.editor_actual != usuario:
            return False
        self.editor_actual = usuario
        self.bloqueo_hasta = timezone.now() + timedelta(minutes=duracion_minutos)
        self.save(update_fields=['editor_actual', 'bloqueo_hasta'])
        return True
    
    def liberar_bloqueo(self, usuario):
        if self.editor_actual == usuario:
            self.editor_actual = None
            self.bloqueo_hasta = None
            self.save(update_fields=['editor_actual', 'bloqueo_hasta'])
            return True
        return False
    
    @receiver(post_save, sender=ProgramaProduccion)
    def crear_reporte_supervisor(sender, instance, created, **kwargs):
        """Crea automáticamente un ReporteSupervisor cuando se crea un ProgramaProduccion"""
        if created:
            # Buscar un supervisor adecuado
            User = get_user_model()
            default_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            
            supervisor = None
            if hasattr(instance, 'creado_por') and instance.creado_por:
                supervisor = instance.creado_por
            elif hasattr(instance, 'modificado_por') and instance.modificado_por:
                supervisor = instance.modificado_por
            else:
                supervisor = default_user
                
            if supervisor:
                ReporteSupervisor.objects.create(
                    programa=instance,
                    supervisor=supervisor,
                    estado='ACTIVO'
                )


class HistorialPlanificacion(models.Model):
    programa = models.ForeignKey(ProgramaProduccion, on_delete=models.CASCADE)
    fecha_reajuste = models.DateTimeField(auto_now_add=True)
    fecha_referencia = models.DateField()
    tipo_reajuste = models.CharField(
        max_length=20,
        choices=[
            ('INICIAL', 'Planificación Inicial'),
            ('DIARIO', 'Reajuste Diario'),
            ('MANUAL', 'Reajuste Manual'),
            ('CONTINUACION', 'Continuación de Tareas'),
            ('AJUSTE_AUTOMATICO', 'Ajuste Automático')
        ]
    )
    
    # Referencia al reporte diario
    reporte_diario = models.ForeignKey('ReporteDiarioPrograma', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Estructura mejorada del timeline
    timeline_data = JSONField(default=dict)  # {
        # grupos: {
        #   id: str,
        #   orden_trabajo: int,
        #   items: [int],  # IDs de items
        #   metadata: dict  # Información adicional del grupo
        # }
        # items: {
        #   id: int,
        #   tarea_id: int,
        #   fecha_inicio: datetime,
        #   fecha_fin: datetime,
        #   cantidad_asignada: decimal,
        #   cantidad_completada: decimal,
        #   estado: str,
        #   metadata: dict
        # }
        # relaciones: {
        #   dependencias: [],
        #   continuaciones: []
        # }
    #}
    
    # Tracking detallado de cambios
    tareas_modificadas = JSONField(default=list)  # [
        # {
        #   tarea_id: int,
        #   tipo_cambio: str,
        #   datos_anteriores: dict,
        #   datos_nuevos: dict,
        #   motivo: str
        # }
    #]
    
    # Estados completos
    timeline_original = JSONField(default=dict)
    timeline_actualizada = JSONField(default=dict)
    
    # Campos de auditoría
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='historiales_creados'
    )
    observaciones = models.TextField(blank=True)
    
    def guardar_timeline(self, grupos, items, cambios, metadata=None):
        self.timeline_data = {
            'grupos': grupos,
            'items': items,
            'cambios': cambios,
            'metadata': metadata or {}
        }
        self.save()
    
    def registrar_cambio_tarea(self, tarea_id, tipo_cambio, datos_anteriores, datos_nuevos):
        if not self.tareas_modificadas:
            self.tareas_modificadas = []
        
        self.tareas_modificadas.append({
            'tarea_id': tarea_id,
            'tipo_cambio': tipo_cambio,
            'anterior': datos_anteriores,
            'nuevo': datos_nuevos,
            'fecha_cambio': timezone.now().isoformat()
        })
        self.save()
    
    def guardar_estados(self, estado_original, estado_actualizado):
        """Guarda los estados original y actualizado del timeline"""
        try:
            self.timeline_original = {
                'groups': estado_original.get('groups', []),  # Usar 'groups' en lugar de 'grupos'
                'items': estado_original.get('items', []),
                'metadata': {
                    'fecha_referencia': self.fecha_referencia.isoformat(),
                    'tipo_reajuste': self.tipo_reajuste
                }
            }
            
            self.timeline_actualizada = {
                'groups': estado_actualizado.get('groups', []),  # Usar 'groups' en lugar de 'grupos'
                'items': estado_actualizado.get('items', []),
                'metadata': {
                    'fecha_referencia': self.fecha_referencia.isoformat(),
                    'tipo_reajuste': self.tipo_reajuste
                }
            }
            
            self.save()
            return True
        except Exception as e:
            print(f"Error guardando estados: {str(e)}")
            return False
    
    def _calcular_cambios(self, original, actualizada):
        """Calcula los cambios entre los dos estados"""
        cambios = []
        items_originales = {item['id']: item for item in original['items']}
        items_actualizados = {item['id']: item for item in actualizada['items']}
        
        for item_id, item_original in items_originales.items():
            if item_id in items_actualizados:
                item_actual = items_actualizados[item_id]
                if self._hay_cambios(item_original, item_actual):
                    cambios.append({
                        'tipo': 'MODIFICADO',
                        'item_id': item_id,
                        'cambios': self._detectar_cambios(item_original, item_actual)
                    })
            else:
                cambios.append({
                    'tipo': 'ELIMINADO',
                    'item_id': item_id,
                    'datos_originales': item_original
                })
        
        # Identificar nuevos items
        for item_id, item_actual in items_actualizados.items():
            if item_id not in items_originales:
                cambios.append({
                    'tipo': 'NUEVO',
                    'item_id': item_id,
                    'datos_nuevos': item_actual
                })
        
        return cambios
    
    class Meta:
        ordering = ['-fecha_reajuste']
        indexes = [
            models.Index(fields=['programa', 'fecha_referencia']),
            models.Index(fields=['fecha_reajuste'])
        ]

class EstandarMaquinaProceso(models.Model):
    #Relaciones principales
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True, related_name="estandares_maquina")
    pieza = models.ForeignKey(Pieza, on_delete=models.CASCADE, null=True, blank=True, related_name="estandares_maquina")

    #Relaciones obligatorias
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE)
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE)
    
    #Valor del estándar
    estandar = models.IntegerField(default=0)

    #Campo para indicar si es la máquina principal para este proceso
    es_principal = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ('producto', 'proceso', 'maquina'),
            ('pieza', 'proceso', 'maquina')
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(producto__isnull=False) | models.Q(pieza__isnull=False),
                name='producto_or_pieza_required'
            )
        ]

    def clean(self):
        if self.producto and self.pieza:
            raise ValidationError("No puede asociarse a un producto y una pieza simultáneamente")
        if not self.producto and not self.pieza:
            raise ValidationError("Debe asociarse a un producto o una pieza")

    def __str__(self):
        objeto = self.producto.codigo_producto if self.producto else self.pieza.codigo_pieza
        return f'{objeto} - {self.proceso.descripcion} - {self.maquina.descripcion} - {self.estandar}'

    @classmethod
    def get_mejor_maquina(cls, producto=None, pieza=None, proceso=None):
        """Obtiene la mejor máquina (más eficiente) para un producto/pieza y proceso"""
        if producto:
            return cls.objects.filter(
                producto=producto,
                proceso=proceso,
                es_principal=True
            ).first()
        elif pieza:
            return cls.objects.filter(
                pieza=pieza,
                proceso=proceso,
                es_principal=True
            ).first()
        return None



class IngresoProduccion(models.Model):
    from Operator.models import Operador, AsignacionOperador
    from Machine.models import FallasMaquina
    asignacion = models.ForeignKey(AsignacionOperador, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fallas = models.ForeignKey(FallasMaquina, on_delete=models.SET_NULL, null=True, blank=True)
    operador = models.ForeignKey(Operador, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.operador} - {self.cantidad} (Ingreso {self.id})"


# Los modelos de AsignacionOperador están en Operator/models.py

# ============= MODELO PARA CONFIGURACIÓN DE COSTOS Y PRECIOS =============
class ConfiguracionCostos(models.Model):
    """
    Modelo para configurar parámetros de costos que permitirán cálculos financieros
    """
    empresa = models.ForeignKey(EmpresaOT, on_delete=models.CASCADE)
    
    # Costos de mano de obra
    costo_hora_operador_base = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Costo promedio por hora de operador"
    )
    
    costo_hora_supervisor = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Costo por hora de supervisor"
    )
    
    # Costos de máquinas
    costo_hora_maquina_base = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Costo promedio por hora de máquina (depreciación, energía, mantenimiento)"
    )
    
    # Costos indirectos
    porcentaje_costos_indirectos = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=15.00,
        help_text="Porcentaje de costos indirectos sobre costos directos"
    )
    
    # Precios y márgenes
    margen_beneficio_objetivo = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=20.00,
        help_text="Margen de beneficio objetivo en %"
    )
    
    # Configuración por material
    costo_kg_materia_prima_promedio = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Costo promedio por kg de materia prima"
    )
    
    # Configuración temporal
    activa = models.BooleanField(default=True)
    fecha_vigencia_desde = models.DateField(default=date.today)
    fecha_vigencia_hasta = models.DateField(null=True, blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='configuraciones_costos_creadas'
    )
    
    class Meta:
        verbose_name = "Configuración de Costos"
        verbose_name_plural = "Configuraciones de Costos"
        unique_together = ['empresa', 'fecha_vigencia_desde']
        ordering = ['-fecha_vigencia_desde']
    
    def __str__(self):
        return f"Configuración Costos {self.empresa.apodo} - {self.fecha_vigencia_desde}"
    
    @classmethod
    def get_configuracion_activa(cls, empresa):
        """Obtiene la configuración de costos activa para una empresa"""
        return cls.objects.filter(
            empresa=empresa,
            activa=True,
            fecha_vigencia_desde__lte=timezone.now().date()
        ).filter(
            Q(fecha_vigencia_hasta__isnull=True) | 
            Q(fecha_vigencia_hasta__gte=timezone.now().date())
        ).first()
    
    def calcular_costo_total_programa(self, programa):
        """Calcula el costo total estimado de un programa"""
        # Implementar cálculo basado en:
        # - Horas de mano de obra planificadas
        # - Horas de máquina planificadas  
        # - Cantidad de materiales
        # - Costos indirectos
        return {
            'costo_mano_obra': 0,
            'costo_maquinas': 0,
            'costo_materiales': 0,
            'costos_indirectos': 0,
            'costo_total': 0
        }


class PrecioProducto(models.Model):
    """
    Modelo para almacenar precios específicos por producto/cliente
    """
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='precios'
    )
    pieza = models.ForeignKey(
        Pieza, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='precios'
    )
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Precio específico para cliente. Si es null, es precio general"
    )
    
    # Precios
    precio_por_unidad = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        help_text="Precio por unidad"
    )
    precio_por_kg = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        null=True,
        blank=True,
        help_text="Precio por kilogramo (opcional)"
    )
    
    # Validez
    fecha_vigencia_desde = models.DateField(default=date.today)
    fecha_vigencia_hasta = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        verbose_name = "Precio de Producto"
        verbose_name_plural = "Precios de Productos"
        unique_together = [
            ['producto', 'cliente', 'fecha_vigencia_desde'],
            ['pieza', 'cliente', 'fecha_vigencia_desde']
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(producto__isnull=False) | models.Q(pieza__isnull=False),
                name='precio_producto_or_pieza_required'
            )
        ]
        ordering = ['-fecha_vigencia_desde']
    
    def __str__(self):
        item = self.producto.codigo_producto if self.producto else self.pieza.codigo_pieza
        cliente_str = f" - {self.cliente.nombre}" if self.cliente else " - General"
        return f"Precio {item}{cliente_str}: ${self.precio_por_unidad}"
    
    def clean(self):
        if self.producto and self.pieza:
            raise ValidationError("No puede asociarse a un producto y una pieza simultáneamente")
        if not self.producto and not self.pieza:
            raise ValidationError("Debe asociarse a un producto o una pieza")
    
    @classmethod
    def get_precio_vigente(cls, producto=None, pieza=None, cliente=None, fecha=None):
        """Obtiene el precio vigente para un producto/pieza y cliente en una fecha"""
        if not fecha:
            fecha = timezone.now().date()
        
        # Buscar precio específico del cliente primero
        filtros = {
            'activo': True,
            'fecha_vigencia_desde__lte': fecha
        }
        
        if producto:
            filtros['producto'] = producto
        elif pieza:
            filtros['pieza'] = pieza
        else:
            return None
        
        # Intentar precio específico del cliente
        if cliente:
            precio_especifico = cls.objects.filter(
                cliente=cliente,
                **filtros
            ).filter(
                Q(fecha_vigencia_hasta__isnull=True) | 
                Q(fecha_vigencia_hasta__gte=fecha)
            ).first()
            
            if precio_especifico:
                return precio_especifico
        
        # Precio general (cliente=null)
        precio_general = cls.objects.filter(
            cliente__isnull=True,
            **filtros
        ).filter(
            Q(fecha_vigencia_hasta__isnull=True) | 
            Q(fecha_vigencia_hasta__gte=fecha)
        ).first()
        
        return precio_general