from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Campos que se muestran en la lista de usuarios
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'activo', 'is_staff', 'date_joined')
    
    # Campos por los que se puede filtrar
    list_filter = ('rol', 'activo', 'is_staff', 'is_superuser', 'date_joined')
    
    # Campos por los que se puede buscar
    search_fields = ('username', 'email', 'first_name', 'last_name', 'rut')
    
    # Agregar los campos personalizados al formulario de edición
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('rut', 'telefono', 'cargo', 'rol', 'activo')
        }),
    )
    
    # Campos para el formulario de creación de usuario
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('email', 'first_name', 'last_name', 'rut', 'telefono', 'cargo', 'rol', 'activo')
        }),
    )