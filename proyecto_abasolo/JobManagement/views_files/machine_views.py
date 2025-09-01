from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..models import Maquina, Proceso, ProgramaProduccion, Ruta, RutaPieza
from ..serializers import MaquinaSerializer
from Product.models import Producto, Pieza

class MaquinasView(APIView):
    def get(self, request, pk=None):
        try:
            programa = ProgramaProduccion.objects.get(pk=pk)
            proceso_codigo = request.query_params.get('proceso_codigo')
            #print(f"Buscando máquinas para proceso: {proceso_codigo}")

            maquinas = Maquina.objects.filter(
                Q(empresa__isnull=False)
            ).distinct()
            #print(f"Máquinas iniciales: {maquinas.count()}")

            if proceso_codigo: 
                try:
                    proceso = Proceso.objects.get(codigo_proceso=proceso_codigo)
                    #print(f"Proceso encontrado: {proceso}")
                    #print(f"Tipos de máquina compatibles: {list(proceso.tipos_maquina_compatibles.all())}")
                    
                    maquinas_compatibles = proceso.get_maquinas_compatibles()
                    #print(f"Máquinas compatibles encontradas: {maquinas_compatibles.count()}")
                    
                    maquinas = maquinas_compatibles.filter(id__in=maquinas)
                    #print(f"Máquinas finales después del filtro: {maquinas.count()}")
                except Proceso.DoesNotExist:
                    print(f"Proceso no encontrado: {proceso_codigo}")
                    pass
                except Exception as e:
                    print(f"Error al obtener máquinas compatibles: {str(e)}")
                    raise

            maquinas = maquinas.order_by('codigo_maquina')
            serializer = MaquinaSerializer(maquinas, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error en MaquinasView: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class MaquinaListView(APIView):
    def get(self, request):
        maquinas = Maquina.objects.all()
        serializer = MaquinaSerializer(maquinas, many=True)
        return Response(serializer.data)
    

class MaquinasCompatiblesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, proceso_id, tipo, objeto_id):
        try:
            proceso = get_object_or_404(Proceso, id=proceso_id)
            maquinas = proceso.get_maquinas_compatibles()

            if tipo == "producto":
                obj = get_object_or_404(Producto, id=objeto_id)
                rutas = Ruta.objects.filter(producto=obj, proceso=proceso)
                estandares = {r.maquina_id: r.estandar for r in rutas}
            elif tipo == "pieza":
                obj = get_object_or_404(Pieza, id=objeto_id)
                rutas = RutaPieza.objects.filter(pieza=obj, proceso=proceso)
                estandares= {r.maquina_id: r.estandar for r in rutas}

            datos_maquinas = [{
                'id': m.id,
                'codigo': m.codigo_maquina,
                'descripcion': m.descripcion,
                'estandar': estandares.get(m.id, 0)
            } for m in maquinas]

            return Response(datos_maquinas)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        