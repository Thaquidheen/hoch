

from datetime import datetime
from django.template.loader import render_to_string
from django.conf import settings

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

import os
import time


# from .quotation_pdf.services.data_compiler import QuotationPDFDataCompiler
from .data_compiler import QuotationPDFDataCompiler

from ..pdf_renderer import get_pdf_renderer, PDFGenerationError

# Add logging setup
import logging
logger = logging.getLogger('quotation_pdf')
import logging








class QuotationPDFGenerator:
    """Generate PDF from compiled data with heavy dependencies"""
    
    def __init__(self, project_id=None, customizations=None):
        # ✅ Make parameters optional with defaults
        self.project_id = project_id
        self.customizations = customizations or {}
        
        # Only initialize compiler if project_id is provided
        if self.project_id:
            self.compiler = QuotationPDFDataCompiler(project_id, customizations)
        else:
            self.compiler = None
            
        # Initialize PDF renderer
        self.pdf_renderer = get_pdf_renderer(prefer_weasyprint=True)
        self.project_id = project_id
        self.customizations = customizations or {}
        self.compiler = QuotationPDFDataCompiler(project_id, customizations)
        self.pdf_renderer = get_pdf_renderer(prefer_weasyprint=True)
        
    def generate_pdf(self, project_id=None, customizations=None):
        """Main PDF generation method with flexible parameter handling"""
        try:
            # ✅ Allow parameters to be passed here if not set in constructor
            if project_id:
                self.project_id = project_id
            if customizations:
                self.customizations = customizations
                
            # Validate we have required data
            if not self.project_id:
                raise PDFGenerationError("Project ID is required for PDF generation")
                
            # Initialize compiler if not already done
            if not self.compiler:
                self.compiler = QuotationPDFDataCompiler(self.project_id, self.customizations)
            
            logger.info(f"Starting PDF generation for project {self.project_id}")
            
            # Compile all data
            pdf_data = self.compiler.compile_complete_data()
            
            # Select template based on customizations
            template_name = self.get_template_name()
            logger.info(f"Using template: {template_name}")
            
            # Render HTML
            html_content = render_to_string(template_name, pdf_data)
            logger.info("HTML content rendered successfully")
            
            # Generate PDF with enhanced HTML rendering
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
                'file_size_formatted': self._format_file_size(len(pdf_bytes)),
                'history_id': history_record.id if history_record else None,
                'download_url': self.get_download_url(pdf_filename),
                'generation_time': time.time() - time.time(),  # You can add timing here
                'template_type': self.customizations.get('template_type', 'DETAILED'),
                'renderer_used': 'Enhanced HTML Professional',
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
    
    def _format_file_size(self, bytes_size):
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
        
    
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
            pdf_data = self.compiler.compile_complete_data()
            # Use WeasyPrint renderer
            if hasattr(self.pdf_renderer, 'render_pdf'):
                pdf_bytes = self.pdf_renderer.render_pdf(
                    html_content=html_content,
                    css_files=css_files,
                    base_url=settings.BASE_DIR,
                    pdf_data=pdf_data
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
            from ..models import QuotationPDFHistory
            
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
