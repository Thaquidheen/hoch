from django.shortcuts import render
from rest_framework import generics, status
from .models import *
from .serializers import CustomerSerializer,CustomerStateSerializer,RequirementSerializer
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from workflow.models import WorkflowHistory
from rest_framework import viewsets
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
# Create your views here.
class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'customer_id'


class CustomerStateUpdateView(APIView):
    def patch(self, request, customer_id):
        customer = get_object_or_404(Customer, customer_id=customer_id)
        serializer = CustomerStateSerializer(customer, data=request.data, partial=True)

        if serializer.is_valid():
            previous_state = customer.state  # Capture the current state before the update
            new_state = serializer.validated_data['state']
            user = request.user
            serializer.save()
            WorkflowHistory.objects.create(
                customer=customer,
                previous_state=previous_state,
                new_state=new_state,
                changed_by=user,
            )

            return Response(
                {"message": "Customer state updated successfully!", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )





class RequirementListCreateView(ListCreateAPIView):
    serializer_class = RequirementSerializer

    def get_queryset(self):
        # Filter requirements by customer_id
        customer_id = self.kwargs['customer_id']
        return Requirement.objects.filter(customer__customer_id=customer_id)

    def perform_create(self, serializer):
        # Ensure the customer exists
        customer = get_object_or_404(Customer, customer_id=self.kwargs['customer_id'])
        serializer.save(customer=customer)

    def get_queryset(self):
        customer_id = self.kwargs['customer_id']
        return Requirement.objects.filter(customer__customer_id=customer_id)

    def perform_create(self, serializer):
        customer_id = self.kwargs['customer_id']
        serializer.save(customer_id=customer_id)





class RequirementDetailUpdateView(RetrieveUpdateDestroyAPIView):
    serializer_class = RequirementSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        customer_id = self.kwargs['customer_id']
        customer = get_object_or_404(Customer, customer_id=customer_id)
        requirement, _ = Requirement.objects.get_or_create(customer=customer)
        return requirement

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        # Handle file uploads only if provided
        if 'documents' in request.FILES:
            files = request.FILES.getlist('documents')
            # Get the list of document names (which should be sent as an array)
            document_names = request.data.getlist('documentNames[]')
            for index, file in enumerate(files):
                # Use the corresponding name, defaulting to a fallback (e.g., the first choice) if missing
                name_value = document_names[index] if index < len(document_names) else "site_photos_and_measurements"
                document = Document.objects.create(file=file, name=name_value)
                instance.documents.add(document)

        # Exclude the 'documents' and 'documentNames[]' keys before saving the rest of the data
        request_data = request.data.copy()
        request_data.pop('documents', None)
        request_data.pop('documentNames[]', None)

        serializer = self.get_serializer(instance, data=request_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        if 'documents' in request.FILES:
            files = request.FILES.getlist('documents')
            document_names = request.data.getlist('documentNames[]')
            for index, file in enumerate(files):
                name_value = document_names[index] if index < len(document_names) else "site_photos_and_measurements"
                document = Document.objects.create(file=file, name=name_value)
                instance.documents.add(document)
                
        request_data = request.data.copy()
        request_data.pop('documents', None)
        request_data.pop('documentNames[]', None)

        serializer = self.get_serializer(instance, data=request_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

class DocumentDeleteView(APIView):
    """
    API endpoint for deleting a document.
    """

    def delete(self, request, document_id, format=None):
        # Look up the document using its primary key
        document = get_object_or_404(Document, id=document_id)
        document.delete()
        # Return a 204 (No Content) response after successful deletion
        return Response(status=status.HTTP_204_NO_CONTENT)
    



