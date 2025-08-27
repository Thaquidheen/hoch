from rest_framework import generics, permissions
from .models import Architect
from .serializers import ArchitectSerializer

# List all Architects & Create a new Architect
class ArchitectListCreateView(generics.ListCreateAPIView):
    queryset = Architect.objects.all()
    serializer_class = ArchitectSerializer
    permission_classes = [permissions.IsAuthenticated]

# Retrieve, Update, Delete an Architect
class ArchitectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Architect.objects.all()
    serializer_class = ArchitectSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'architect_id'  # Using UUID for lookups
