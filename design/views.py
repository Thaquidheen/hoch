from django.shortcuts import render
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# Create your views here.
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from .models import DesignPhase
from .serializers import DesignPhaseSerializer

class DesignPhaseListCreateView(ListCreateAPIView):
    serializer_class = DesignPhaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DesignPhase.objects.filter(customer__state='Design')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class DesignPhaseDetailUpdateView(RetrieveUpdateDestroyAPIView):
    queryset = DesignPhase.objects.all()
    serializer_class = DesignPhaseSerializer
    permission_classes = [IsAuthenticated]


class UpcomingMeetingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        # For example, show all scheduled meetings that haven't happened yet
        today = timezone.now().date()
        upcoming_meetings = DesignPhase.objects.filter(
            schedule_client_meeting__gte=today  # meeting date >= today
        ).select_related('customer')

        # Transform data into JSON
        data = []
        for phase in upcoming_meetings:
            data.append({
                "customer_id": str(phase.customer.customer_id),
                "customer_name": phase.customer.name,
                "meeting_date": str(phase.schedule_client_meeting),
            })

        return Response(data)