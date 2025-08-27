from django.urls import path
from .views import ArchitectListCreateView, ArchitectDetailView

urlpatterns = [
    path('architectlist/', ArchitectListCreateView.as_view(), name='architect-list'),
    path('<uuid:architect_id>/', ArchitectDetailView.as_view(), name='architect-detail'),
]
