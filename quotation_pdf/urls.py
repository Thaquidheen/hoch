# quotation_pdf/urls.py
from django.urls import path
from .views import (
    GenerateQuotationPDFView,

    QuotationPDFHistoryView,
    SavePDFCustomizationView,
    GetPDFCustomizationView,
    PDFTemplatesListView,
    ValidateCustomizationView
)

app_name = 'quotation_pdf'

urlpatterns = [
    # PDF Generation
    path('generate/<uuid:project_id>/', GenerateQuotationPDFView.as_view(), name='generate_pdf'),
    
    # Preview & Validation
    # path('preview/<uuid:project_id>/', PreviewQuotationDataView.as_view(), name='preview_data'),
    path('validate/<uuid:project_id>/', ValidateCustomizationView.as_view(), name='validate_customization'),
    
    # Customization Management
    path('customization/<uuid:project_id>/', GetPDFCustomizationView.as_view(), name='get_customization'),
    path('customization/<uuid:project_id>/save/', SavePDFCustomizationView.as_view(), name='save_customization'),
    
    # History & Templates
    path('history/<uuid:project_id>/', QuotationPDFHistoryView.as_view(), name='pdf_history'),
    path('templates/', PDFTemplatesListView.as_view(), name='pdf_templates'),
]


