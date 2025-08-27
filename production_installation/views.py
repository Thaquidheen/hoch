from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from .models import ProductionInstallationPhase
from .serializers import ProductionInstallationPhaseSerializer

class ProductionInstallationPhaseListCreateView(ListCreateAPIView):
    serializer_class = ProductionInstallationPhaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter customers in the 'Production' or 'Installation' state
        return ProductionInstallationPhase.objects.filter(customer__state__in=['Production', 'Installation'])

    def perform_create(self, serializer):
        serializer.save()

class ProductionInstallationPhaseDetailUpdateView(RetrieveUpdateDestroyAPIView):
    queryset = ProductionInstallationPhase.objects.all()
    serializer_class = ProductionInstallationPhaseSerializer
    permission_classes = [IsAuthenticated]
