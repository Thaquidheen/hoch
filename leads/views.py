from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from .serializers import PipelineSerializer
from .models import Pipeline
from customers.models import Customer
# Create your views here.
class PipelineDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PipelineSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"
    def get_queryset(self):
        return Pipeline.objects.select_related('customer').filter(customer__state='Pipeline')
    
class PipelineListView(generics.ListAPIView):
    serializer_class = PipelineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Pipeline.objects.select_related('customer').filter(customer__state='Pipeline')


