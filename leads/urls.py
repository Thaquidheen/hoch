from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    PipelineDetailView,PipelineListView
)

urlpatterns = [
    path('api/pipelines/', PipelineListView.as_view(), name='pipeline_list'),
    path('pipelines/<uuid:pk>/', PipelineDetailView.as_view(), name='pipeline_detail'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)