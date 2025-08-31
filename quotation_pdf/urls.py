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
    path('generate/<int:project_id>/', GenerateQuotationPDFView.as_view(), name='generate_pdf'),
    
    # Preview & Validation
    # path('preview/<int:project_id>/', PreviewQuotationDataView.as_view(), name='preview_data'),
    path('validate/<int:project_id>/', ValidateCustomizationView.as_view(), name='validate_customization'),

    # Customization Management
    path('customization/<int:project_id>/', GetPDFCustomizationView.as_view(), name='get_customization'),
    path('customization/<int:project_id>/save/', SavePDFCustomizationView.as_view(), name='save_customization'),

    # History & Templates
    path('history/<int:project_id>/', QuotationPDFHistoryView.as_view(), name='pdf_history'),
    path('templates/', PDFTemplatesListView.as_view(), name='pdf_templates'),
]


