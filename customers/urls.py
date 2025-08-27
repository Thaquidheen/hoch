from django.urls import path
from .views import CustomerDetailView ,CustomerListCreateView ,CustomerStateUpdateView,RequirementListCreateView,RequirementDetailUpdateView,DocumentDeleteView

urlpatterns = [
    path('', CustomerListCreateView.as_view(), name='customer_list_create'),
    path('<uuid:customer_id>/', CustomerDetailView.as_view(), name='customer_detail'),
    path('<uuid:customer_id>/update-state/', CustomerStateUpdateView.as_view(), name='customer_state_update'),
    path('<uuid:customer_id>/requirements/', RequirementListCreateView.as_view(), name='requirement-list-create'),
    path('<uuid:customer_id>/requirements/detail/', RequirementDetailUpdateView.as_view(), name='requirement-detail-update'),
path('<int:document_id>/delete/', DocumentDeleteView.as_view(), name='document-delete'),



]