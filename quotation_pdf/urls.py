from django.urls import path
from django.http import JsonResponse

# Import from the new organized view modules
from .views.generation import (
    GenerateQuotationPDFView,
    PreviewQuotationPDFView, 
    PDFDataPreviewView,
    PDFBatchGenerationView,
    RegeneratePDFView
)
from .views.management import (
    DownloadQuotationPDFView,
    QuotationPDFHistoryView,
    DeletePDFView,
    PDFAnalyticsView
)
from .views.customization import (
    GetPDFCustomizationView,
    SavePDFCustomizationView,
    PDFTemplatesListView,
    ValidateCustomizationView,
    PDFSettingsView
)
from .views.sharing import (
    EmailQuotationPDFView,
    CreatePDFShareLinkView,
    SharedPDFView
)

app_name = 'quotation_pdf'

urlpatterns = [
    # =============================================================================
    # PDF GENERATION ENDPOINTS
    # =============================================================================
      path('generate/<int:project_id>/', GenerateQuotationPDFView.as_view(), name='generate_pdf'),
    path('preview/<uuid:project_id>/', PreviewQuotationPDFView.as_view(), name='preview_pdf'),
    path('data-preview/<uuid:project_id>/', PDFDataPreviewView.as_view(), name='data_preview'),
    path('batch-generate/', PDFBatchGenerationView.as_view(), name='batch_generate'),
    path('regenerate/<uuid:pdf_id>/', RegeneratePDFView.as_view(), name='regenerate_pdf'),
    
    # =============================================================================
    # PDF MANAGEMENT ENDPOINTS  
    # =============================================================================
    path('download/<uuid:pdf_id>/', DownloadQuotationPDFView.as_view(), name='download_pdf'),
    path('history/<uuid:project_id>/', QuotationPDFHistoryView.as_view(), name='pdf_history'),
    path('delete/<uuid:pdf_id>/', DeletePDFView.as_view(), name='delete_pdf'),
    path('analytics/', PDFAnalyticsView.as_view(), name='pdf_analytics'),
    
    # =============================================================================
    # CUSTOMIZATION & SETTINGS ENDPOINTS
    # =============================================================================
    path('customization/<uuid:project_id>/', GetPDFCustomizationView.as_view(), name='get_customization'),
    path('customization/<uuid:project_id>/save/', SavePDFCustomizationView.as_view(), name='save_customization'),
    path('validate/<uuid:project_id>/', ValidateCustomizationView.as_view(), name='validate_customization'),
    path('templates/', PDFTemplatesListView.as_view(), name='pdf_templates'),
    path('settings/', PDFSettingsView.as_view(), name='pdf_settings'),
    
    # =============================================================================
    # SHARING & COMMUNICATION ENDPOINTS
    # =============================================================================
    path('email/<uuid:pdf_id>/', EmailQuotationPDFView.as_view(), name='email_pdf'),
    path('share/<uuid:pdf_id>/', CreatePDFShareLinkView.as_view(), name='create_share_link'),
    path('shared/<str:token>/', SharedPDFView.as_view(), name='shared_pdf'),
    
    # =============================================================================
    # UTILITY ENDPOINTS
    # =============================================================================
    path('health/', lambda request: JsonResponse({
        'status': 'ok', 
        'service': 'quotation_pdf',
        'timestamp': '2025-08-31T02:05:57Z',
        'version': '1.0'
    }), name='health'),
]