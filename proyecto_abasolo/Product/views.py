from rest_framework import generics
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from JobManagement.models import Proceso, Ruta, RutaPieza, Maquina

from .models import Producto, Pieza, FamiliaProducto, SubfamiliaProducto
from .serializers import (
    ProductoSerializer, PiezaSerializer, 
    FamiliaProductoSerializer, SubfamiliaProductoSerializer
)
from .filters import ProductoFilter, PiezaFilter
from .pagination import ProductoPagination, PiezaPagination

# Vistas de Productos
class ProductoListView(generics.ListAPIView):
    serializer_class = ProductoSerializer
    pagination_class = ProductoPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductoFilter
    search_fields = ['codigo_producto', 'descripcion']
    ordering_fields = ['codigo_producto', 'descripcion']
    ordering = ['codigo_producto']

    def get_queryset(self):
        return Producto.objects.all().select_related(
            'familia_producto',
            'subfamilia_producto',
            'ficha_tecnica',
            'und_medida'
        ).prefetch_related('rutas')

class ProductoDetailView(generics.RetrieveAPIView):
    serializer_class = ProductoSerializer
    lookup_field = 'id'
    queryset = Producto.objects.all().select_related(
        'familia_producto',
        'subfamilia_producto',
        'ficha_tecnica',
        'und_medida'
    ).prefetch_related('rutas')

# Vistas de Piezas
class PiezaListView(generics.ListAPIView):
    serializer_class = PiezaSerializer
    pagination_class = PiezaPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PiezaFilter
    search_fields = ['codigo_pieza', 'descripcion']
    ordering_fields = ['codigo_pieza', 'descripcion']
    ordering = ['codigo_pieza']

    def get_queryset(self):
        return Pieza.objects.all().select_related(
            'familia_producto',
            'subfamilia_producto',
            'ficha_tecnica',
            'und_medida'
        ).prefetch_related('rutas')

class PiezaDetailView(generics.RetrieveAPIView):
    serializer_class = PiezaSerializer
    lookup_field = 'id'
    queryset = Pieza.objects.all().select_related(
        'familia_producto',
        'subfamilia_producto',
        'ficha_tecnica',
        'und_medida'
    ).prefetch_related('rutas')

# Vistas comunes para Familias y Subfamilias
class FamiliaProductoView(generics.ListAPIView):
    serializer_class = FamiliaProductoSerializer
    ordering = ['codigo_familia']

    def get_queryset(self):
        tipo = self.request.query_params.get('tipo', 'ambos')
        queryset = FamiliaProducto.objects.all()
        
        if tipo == 'productos':
            queryset = queryset.filter(producto__isnull=False)
        elif tipo == 'piezas':
            queryset = queryset.filter(pieza__isnull=False)
        
        return queryset.distinct().order_by('codigo_familia')

class SubfamiliaProductoView(generics.ListAPIView):
    serializer_class = SubfamiliaProductoSerializer
    ordering = ['codigo_subfamilia']

    def get_queryset(self):
        familia_codigo = self.request.query_params.get('familia_codigo')
        tipo = self.request.query_params.get('tipo', 'ambos')
        
        queryset = SubfamiliaProducto.objects.all()
        
        if familia_codigo:
            queryset = queryset.filter(familia_producto__codigo_familia=familia_codigo)
        
        if tipo == 'productos':
            queryset = queryset.filter(producto__isnull=False)
        elif tipo == 'piezas':
            queryset = queryset.filter(pieza__isnull=False)
            
        return queryset.distinct().order_by('codigo_subfamilia')
    

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from JobManagement.models import Proceso, Ruta, RutaPieza

class RutaProcesoView(APIView):
    def get(self, request, objeto_id):
        tipo = request.query_params.get('tipo', 'producto')
        
        try:
            # Obtener todas las rutas del objeto (producto o pieza)
            if tipo == 'producto':
                rutas = Ruta.objects.filter(producto_id=objeto_id)
            else:
                rutas = RutaPieza.objects.filter(pieza_id=objeto_id)
            
            # Agrupar por proceso
            procesos_data = {}
            for ruta in rutas:
                proceso_id = ruta.proceso.id
                if proceso_id not in procesos_data:
                    # Obtener todas las máquinas compatibles para este proceso
                    maquinas_compatibles = ruta.proceso.get_maquinas_compatibles()
                    
                    procesos_data[proceso_id] = {
                        'proceso': {
                            'id': ruta.proceso.id,
                            'codigo': ruta.proceso.codigo_proceso,
                            'descripcion': ruta.proceso.descripcion,
                        },
                        'maquinas_disponibles': [{
                            'id': maquina.id,
                            'codigo': maquina.codigo_maquina,
                            'descripcion': maquina.descripcion,
                            'en_uso': False,
                            'estandar': 0
                        } for maquina in maquinas_compatibles],
                        'nro_etapa': ruta.nro_etapa
                    }
                
                # Marcar la máquina actual como en uso y agregar su estándar
                for maquina in procesos_data[proceso_id]['maquinas_disponibles']:
                    if maquina['id'] == ruta.maquina.id:
                        maquina['en_uso'] = True
                        maquina['estandar'] = ruta.estandar
                        break
            
            # Convertir a lista y ordenar por nro_etapa
            procesos_list = list(procesos_data.values())
            procesos_list.sort(key=lambda x: x['nro_etapa'])
            
            return Response({
                'procesos': procesos_list
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ActualizarEstandarRutaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ruta_id):
        try:
            #Verificar parámetros necesarios
            maquina_id = request.data.get('maquina_id')
            estandar = request.data.get('estandar')
            es_principal = request.data.get('es_principal', False)

            if estandar is None:
                return Response(
                    {"error": "Se requiere el estándar"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                estandar = int(estandar)
                if estandar < 0:
                    return Response(
                        {"error": "El estándar debe ser mayor o igual a cero"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {"error": "El estándar debe ser un número"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            #Determinar si es una ruta de producto o pieza
            ruta = None
            tipo = None
            producto = None
            pieza = None

            try:
                ruta = Ruta.objects.get(id=ruta_id)
                tipo = "producto"
                producto = ruta.producto
            except Ruta.DoesNotExist:
                try:
                    ruta = RutaPieza.objects.get(id=ruta_id)
                    tipo = "pieza"
                    pieza = ruta.pieza
                except RutaPieza.DoesNotExist:
                    return Response(
                        {"error": f"No se encontró la ruta con ID {ruta_id}"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
            #Si se proporcionó un maquina_id, cambiar la máquina
            maquina = None
            if maquina_id:
                try:
                    maquina = Maquina.objects.get(id=maquina_id)

                    #Si la máquina seleccionada es diferente a la actual y no se indica 
                    # explícitamente que es principal, entonces no es principal
                    if maquina.id != ruta.maquina.id and not es_principal:
                        es_principal = False
                    else:
                        #Si es la misma máquina que ya estaba en la ruta, sí es principal
                        es_principal = True

                    ruta.maquina = maquina

                except Maquina.DoesNotExist:
                    return Response(
                        {"error": f"No se encontró la máquina con ID {maquina_id}"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            else:
                maquina = ruta.maquina
            
            #Actualizar el estándar
            ruta.estandar = estandar
            ruta.save()

            # Actualizar o crear el registro en EstandarMaquinaProceso
            from JobManagement.models import EstandarMaquinaProceso
            if tipo == 'producto' and producto:
                EstandarMaquinaProceso.objects.update_or_create(
                    producto=producto,
                    proceso=ruta.proceso,
                    maquina=maquina,
                    defaults={
                        'estandar': estandar,
                        'es_principal': es_principal #La máquina en la ruta siempre es la principal
                    }
                )
            elif tipo == 'pieza' and pieza:
                EstandarMaquinaProceso.objects.update_or_create(
                    pieza=pieza,
                    proceso=ruta.proceso,
                    maquina=maquina,
                    defaults={
                        'estandar': estandar,
                        'es_principal': es_principal 
                    }
                )
        
            return Response({
                "message": f"Estándar de {tipo} actualizado correctamente"
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error al actualizar el estándar: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR 
            )

from JobManagement.models import EstandarMaquinaProceso
from JobManagement.serializers import EstandarMaquinaProcesoSerializer

class EstandarMaquinaProcesoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, proceso_id):
        """Obtiene todos los estándares para un proceso específico"""
        try:
            #Obtener parámetros
            producto_id = request.query_params.get('producto_id')
            pieza_id = request.query_params.get('pieza_id')

            # Validar que se proporcione producto o pieza
            if not producto_id and not pieza_id:
                return Response(
                    {"error": "Debe especificar producto_id o pieza_id"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Filtrar estándares
            estandares = EstandarMaquinaProceso.objects.filter(
                proceso_id=proceso_id, 
                producto_id=producto_id if producto_id else None, 
                pieza_id=pieza_id if pieza_id else None
            ).select_related('maquina', 'proceso')

            serializer = EstandarMaquinaProcesoSerializer(estandares, many=True)

            #Debug: imprimir datos serializados
            print(f"Estándares encontrados para proceso {proceso_id}:", serializer.data)

            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Crea o actualiza un estándar para una máquina y proceso"""
        try:
            serializer = EstandarMaquinaProcesoSerializer(data=request.data)
            if serializer.is_valid():
                #Intentar encontrar un estándar existente
                filters = {
                    'proceso_id': serializer.validated_data['proceso_id'],
                    'maquina_id': serializer.validated_data['maquina_id'],
                }

                if 'producto' in serializer.validated_data and serializer.validated_data['producto']:
                    filters['producto_id'] = serializer.validated_data['producto']
                elif 'pieza' in serializer.validated_data and serializer.validated_data['pieza']:
                    filters['pieza_id'] = serializer.validated_data['pieza']
                
                estandar, created = EstandarMaquinaProceso.objects.update_or_create(
                    **filters,
                    defaults={
                        'estandar': serializer.validated_data['estandar'],
                        'es_principal': serializer.validated_data.get('es_principal', False)
                    }
                )

                response_serializer = EstandarMaquinaProcesoSerializer(estandar)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
                )
            
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return Response()

    
    def delete(self, request, estandar_id):
        """Elimina un estándar específico"""
        try:
            estandar = get_object_or_404(EstandarMaquinaProceso, id=estandar_id)
            estandar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
