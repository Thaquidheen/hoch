# quotation_pdf/services.py (Updated with PDF rendering)

from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from decimal import Decimal
import os
import uuid
import logging
from datetime import datetime, timedelta

# Import your existing models
from pricing.models import (
    Project, ProjectLineItem, ProjectLineItemAccessory, ProjectTotals,
    ProjectLightingConfiguration, ProjectLightingItem
)
from catalog.models import ProductVariant
from customers.models import Customer

# Import PDF renderer
from .pdf_renderer import get_pdf_renderer, PDFGenerationError

logger = logging.getLogger('quotation_pdf')

# ... (keep all your existing QuotationPDFDataCompiler code from previous version) ...

class QuotationPDFGenerator:
    """Generate PDF from compiled data with heavy dependencies"""
    
    def __init__(self, project_id, customizations=None):
        self.project_id = project_id
        self.customizations = customizations or {}
        self.compiler = QuotationPDFDataCompiler(project_id, customizations)
        self.pdf_renderer = get_pdf_renderer(prefer_weasyprint=True)
        
    def generate_pdf(self):
        """Main PDF generation method with actual PDF rendering"""
        try:
            logger.info(f"Starting PDF generation for project {self.project_id}")
            
            # Compile all data
            pdf_data = self.compiler.compile_complete_data()
            
            # Select template based on customizations
            template_name = self.get_template_name()
            logger.info(f"Using template: {template_name}")
            
            # Render HTML
            html_content = render_to_string(template_name, pdf_data)
            logger.info("HTML content rendered successfully")
            
            # Generate PDF with WeasyPrint
            css_files = self.get_css_files()
            pdf_bytes = self.render_pdf_from_html(html_content, css_files)
            
            if not pdf_bytes:
                raise PDFGenerationError("PDF rendering returned empty content")
            
            # Save PDF to storage
            pdf_filename = self.save_pdf_to_storage(pdf_bytes, pdf_data)
            
            # Save PDF history record
            history_record = self.save_pdf_history(pdf_data, len(pdf_bytes), pdf_filename)
            
            logger.info(f"PDF generation completed: {pdf_filename}")
            
            return {
                'success': True,
                'pdf_bytes': pdf_bytes,
                'filename': pdf_filename,
                'file_size': len(pdf_bytes),
                'history_id': history_record.id if history_record else None,
                'download_url': self.get_download_url(pdf_filename),
                'data': pdf_data
            }
            
        except PDFGenerationError as e:
            logger.error(f"PDF generation error: {str(e)}")
            return {
                'success': False,
                'error': f'PDF Generation Error: {str(e)}',
                'pdf_bytes': None,
                'filename': None
            }
        except Exception as e:
            logger.error(f"Unexpected error in PDF generation: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'pdf_bytes': None,
                'filename': None
            }
    
    def get_template_name(self):
        """Select appropriate template"""
        template_type = self.customizations.get('template_type', 'DETAILED')
        
        template_mapping = {
            'DETAILED': 'quotation_pdf/detailed_quotation.html',
            'STANDARD': 'quotation_pdf/standard_quotation.html',
            'SIMPLE': 'quotation_pdf/simple_quotation.html'
        }
        
        return template_mapping.get(template_type, 'quotation_pdf/detailed_quotation.html')
    
    def get_css_files(self):
        """Get CSS files for PDF styling"""
        css_files = []
        
        # Main quotation styles
        main_css = os.path.join(
            settings.BASE_DIR, 
            'quotation_pdf', 
            'static', 
            'css', 
            'quotation_styles.css'
        )
        if os.path.exists(main_css):
            css_files.append(main_css)
        
        # Add any additional CSS files from settings
        additional_css = getattr(settings, 'WEASYPRINT_CSS_PATHS', [])
        css_files.extend(additional_css)
        
        return css_files
    
    def render_pdf_from_html(self, html_content, css_files=None):
        """Convert HTML to PDF using WeasyPrint or fallback"""
        try:
            logger.info("Starting PDF rendering")
            
            # Use WeasyPrint renderer
            if hasattr(self.pdf_renderer, 'render_pdf'):
                pdf_bytes = self.pdf_renderer.render_pdf(
                    html_content=html_content,
                    css_files=css_files,
                    base_url=settings.BASE_DIR
                )
                return pdf_bytes
            
            # Fallback to ReportLab for simple PDF
            elif hasattr(self.pdf_renderer, 'render_simple_pdf'):
                project_data = {
                    'project_id': self.project_id,
                    'customer_name': self.compiler.project.customer.name,
                    'total_amount': '₹0.00'  # You can calculate this from pdf_data
                }
                return self.pdf_renderer.render_simple_pdf(project_data, 'temp.pdf')
            
            else:
                raise PDFGenerationError("No PDF renderer available")
                
        except Exception as e:
            logger.error(f"PDF rendering failed: {str(e)}")
            raise PDFGenerationError(f"Failed to render PDF: {str(e)}")
    
    def save_pdf_to_storage(self, pdf_bytes, pdf_data):
        """Save PDF file to Django storage"""
        try:
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            customer_name = pdf_data['customer_info']['name']
            safe_customer_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_customer_name = safe_customer_name.replace(' ', '_')
            
            pdf_filename = f"quotation_{safe_customer_name}_{self.project_id}_{timestamp}.pdf"
            
            # Save to media storage
            file_path = f"quotation_pdfs/{pdf_filename}"
            
            # Use Django's default storage
            file_obj = ContentFile(pdf_bytes)
            saved_path = default_storage.save(file_path, file_obj)
            
            logger.info(f"PDF saved to storage: {saved_path}")
            return pdf_filename
            
        except Exception as e:
            logger.error(f"Failed to save PDF to storage: {str(e)}")
            raise PDFGenerationError(f"Failed to save PDF: {str(e)}")
    
    def get_download_url(self, filename):
        """Get download URL for the PDF"""
        if filename:
            return f"{settings.MEDIA_URL}quotation_pdfs/{filename}"
        return None
    
    def save_pdf_history(self, pdf_data, file_size, filename):
        """Save PDF generation history"""
        try:
            from .models import QuotationPDFHistory
            
            calculations = pdf_data.get('calculations', {})
            project_info = pdf_data.get('project_info', {})
            
            history_record = QuotationPDFHistory.objects.create(
                project_id=self.project_id,
                filename=filename,
                file_path=f"quotation_pdfs/{filename}",
                file_size=file_size,
                template_type=self.customizations.get('template_type', 'DETAILED'),
                total_amount=calculations.get('total_before_discount', 0),
                discount_applied=calculations.get('discount_amount', 0),
                final_amount=calculations.get('final_total', 0),
                status='GENERATED',
                customizations=self.customizations,
                generated_by_id=1,  # You should get this from request.user
                project_name=project_info.get('customer_name', 'Unknown Project'),
                customer_name=pdf_data['customer_info']['name']
            )
            
            logger.info(f"PDF history record created: {history_record.id}")
            return history_record
            
        except Exception as e:
            logger.error(f"Error saving PDF history: {str(e)}")
            return None


# Utility functions for PDF management
class PDFManager:
    """Manage PDF files and operations"""
    
    @staticmethod
    def get_pdf_file_path(filename):
        """Get full file path for a PDF"""
        return default_storage.path(f"quotation_pdfs/{filename}")
    
    @staticmethod
    def delete_pdf_file(filename):
        """Delete PDF file from storage"""
        try:
            file_path = f"quotation_pdfs/{filename}"
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
                logger.info(f"PDF file deleted: {filename}")
                return True
            else:
                logger.warning(f"PDF file not found for deletion: {filename}")
                return False
        except Exception as e:
            logger.error(f"Error deleting PDF file {filename}: {str(e)}")
            return False
    
    @staticmethod
    def get_pdf_file_size(filename):
        """Get PDF file size"""
        try:
            file_path = f"quotation_pdfs/{filename}"
            if default_storage.exists(file_path):
                return default_storage.size(file_path)
            return 0
        except Exception as e:
            logger.error(f"Error getting PDF file size {filename}: {str(e)}")
            return 0