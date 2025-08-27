from django.urls import path
from .views import DesignPhaseListCreateView, DesignPhaseDetailUpdateView,UpcomingMeetingsView

urlpatterns = [
    path('designphases/', DesignPhaseListCreateView.as_view(), name='designphase-list-create'),
    path('designphases/<uuid:pk>/', DesignPhaseDetailUpdateView.as_view(), name='designphase-detail-update'),
    path('designphases/upcoming-meetings/', UpcomingMeetingsView.as_view(), name='upcoming-meeting-view'),

    
]
