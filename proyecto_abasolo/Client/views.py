from .serializers import ClienteSerializer
from .models import Cliente
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# Create your views here.
class ClienteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        clientes = Cliente.objects.all()
        serializers = ClienteSerializer(clientes, many=True)
        return Response(serializers.data)
    
    def get_client(self, pk):
        try:
            cliente = Cliente.objects.get(pk=pk)
            if not cliente:
                return Response({
                    "error": "Cliente no encontrado"
                }, status=status.HTTP_404_NOT_FOUND)
            return cliente
        except Cliente.DoesNotExist:
            return Response({
                "error": "Cliente no encontrado"
            }, status=status.HTTP_404_NOT_FOUND)