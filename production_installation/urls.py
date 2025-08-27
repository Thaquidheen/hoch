from django.urls import path
from .views import ProductionInstallationPhaseListCreateView, ProductionInstallationPhaseDetailUpdateView

urlpatterns = [
    path("production-installation-phases/", ProductionInstallationPhaseListCreateView.as_view(), name="production-installation-phase-list-create"),
    path("production-installation-phases/<uuid:pk>/", ProductionInstallationPhaseDetailUpdateView.as_view(), name="production-installation-phase-detail-update"),
]
