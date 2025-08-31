# quotation_pdf/services/pdf_generator.py - UPDATED with data mapping

import os
import time
import logging
from datetime import datetime
from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .data_compiler import QuotationPDFDataCompiler
from .template_data_mapper import TemplateDataMapper
from ..pdf_renderer import get_pdf_renderer, PDFGenerationError

logger = logging.getLogger('quotation_pdf')

class QuotationPDFGenerator:
    """Generate PDF from compiled data with proper template mapping"""
    
    def __init__(self, project_id=None, customizations=None):
        self.project_id = project_id
        self.customizations = customizations or {}
        
        if self.project_id:
            self.compiler = QuotationPDFDataCompiler(project_id, customizations)
        else:
            self.compiler = None
            
        # Initialize PDF renderer with compatibility preference
        self.pdf_renderer = get_pdf_renderer(prefer_weasyprint=True)
        
    def generate_pdf(self, project_id=None, customizations=None):
        """Main PDF generation method with template data mapping"""
        try:
            # Allow parameters to be passed here if not set in constructor
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
            logger.info(f"Active renderer: {self.pdf_renderer.renderer_name}")
            
            # STEP 1: Compile raw data from your models
            raw_pdf_data = self.compiler.compile_complete_data()
            logger.info("Raw PDF data compiled successfully")
            
            # STEP 2: Map data to template-expected structure
            mapper = TemplateDataMapper(raw_pdf_data)
            template_data = mapper.map_to_template_structure()
            logger.info("Data successfully mapped to template structure")
            
            # STEP 3: Select appropriate template based on renderer capability
            template_name = self.get_compatible_template_name()
            logger.info(f"Using template: {template_name}")
            
            # STEP 4: Render HTML content from Django template with mapped data
            html_content = render_to_string(template_name, template_data)
            logger.info(f"HTML content rendered successfully, length: {len(html_content)} characters")
            
            # STEP 5: Generate PDF with appropriate CSS handling
            css_files = self.get_compatible_css_files()
            pdf_bytes = self.render_pdf_with_compatibility(html_content, css_files, raw_pdf_data)
            
            if not pdf_bytes:
                raise PDFGenerationError("PDF rendering returned empty content")
            
            # STEP 6: Save PDF to storage
            pdf_filename = self.save_pdf_to_storage(pdf_bytes, template_data)
            
            # STEP 7: Save PDF history record
            history_record = self.save_pdf_history(template_data, len(pdf_bytes), pdf_filename)
            
            logger.info(f"PDF generation completed successfully: {pdf_filename}")
            
            return {
                'success': True,
                'pdf_bytes': pdf_bytes,
                'filename': pdf_filename,
                'file_size': len(pdf_bytes),
                'file_size_formatted': self._format_file_size(len(pdf_bytes)),
                'history_id': history_record.id if history_record else None,
                'download_url': self.get_download_url(pdf_filename),
                'template_type': self.customizations.get('template_type', 'DETAILED'),
                'renderer_used': self.pdf_renderer.renderer_name,
                'generation_method': 'HTML_TO_PDF_COMPATIBLE',
                'data': template_data  # Return mapped data for debugging
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
    
    def get_compatible_template_name(self):
        """Select template based on renderer capabilities"""
        template_type = self.customizations.get('template_type', 'DETAILED')
        
        # If using xhtml2pdf, use compatible templates
        if 'xhtml2pdf' in self.pdf_renderer.renderer_name.lower():
            logger.info("Using xhtml2pdf-compatible template")
            return 'quotation_pdf/simple_quotation_compatible.html'
        
        # Otherwise use the standard templates
        template_mapping = {
            'DETAILED': 'quotation_pdf/detailed_quotation.html',
            'STANDARD': 'quotation_pdf/standard_quotation.html',
            'SIMPLE': 'quotation_pdf/simple_quotation.html'
        }
        
        selected_template = template_mapping.get(template_type, 'quotation_pdf/detailed_quotation.html')
        logger.info(f"Using standard template: {selected_template}")
        return selected_template
    
    def get_compatible_css_files(self):
        """Get CSS files appropriate for the active renderer"""
        css_files = []
        
        # For xhtml2pdf, we embed CSS in template, so don't load external files
        if 'xhtml2pdf' in self.pdf_renderer.renderer_name.lower():
            logger.info("xhtml2pdf renderer - CSS embedded in template")
            return css_files
        
        # For WeasyPrint and other renderers, load external CSS
        main_css = os.path.join(
            settings.BASE_DIR, 
            'quotation_pdf', 
            'static', 
            'css', 
            'quotation_styles.css'
        )
        if os.path.exists(main_css):
            css_files.append(main_css)
            logger.info(f"Loaded CSS file: {main_css}")
        else:
            logger.warning(f"CSS file not found: {main_css}")
        
        # Add any additional CSS files from settings
        additional_css = getattr(settings, 'WEASYPRINT_CSS_PATHS', [])
        css_files.extend(additional_css)
        
        logger.info(f"Total CSS files loaded: {len(css_files)}")
        return css_files
    
    def render_pdf_with_compatibility(self, html_content, css_files, pdf_data):
        """Render PDF with compatibility handling and fallback"""
        try:
            logger.info(f"Starting PDF rendering with {self.pdf_renderer.renderer_name}")
            
            # First attempt with current renderer
            pdf_bytes = self.pdf_renderer.render_pdf(
                html_content=html_content,
                css_files=css_files,
                base_url=settings.BASE_DIR,
                pdf_data=pdf_data
            )
            
            logger.info(f"PDF rendering successful with {self.pdf_renderer.renderer_name}")
            return pdf_bytes
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Primary PDF rendering failed: {error_msg}")
            
            # Handle specific xhtml2pdf compatibility issues
            if 'NotImplementedType' in error_msg or 'object is not iterable' in error_msg:
                logger.info("Detected xhtml2pdf compatibility issue - attempting with simplified template")
                return self._attempt_simplified_rendering(pdf_data)
            
            # Re-raise the original error if we can't handle it
            raise PDFGenerationError(f"PDF rendering failed: {error_msg}")
    
    def _attempt_simplified_rendering(self, pdf_data):
        """Attempt rendering with ultra-simplified template as fallback"""
        try:
            # Create a very basic template content
            simplified_html = self._create_emergency_fallback_template(pdf_data)
            
            # Try rendering with no CSS files
            pdf_bytes = self.pdf_renderer.render_pdf(
                html_content=simplified_html,
                css_files=[],  # No external CSS
                base_url=settings.BASE_DIR,
                pdf_data=pdf_data
            )
            
            logger.info("Simplified fallback rendering successful")
            return pdf_bytes
            
        except Exception as fallback_error:
            logger.error(f"Even simplified rendering failed: {str(fallback_error)}")
            raise PDFGenerationError(f"All rendering attempts failed. Last error: {str(fallback_error)}")
    
    def _create_emergency_fallback_template(self, pdf_data):
        """Create emergency fallback HTML template with actual data"""
        
        # Extract basic information from mapped data
        customer_name = pdf_data.get('customer_info', {}).get('name', 'Customer')
        project_name = pdf_data.get('project_info', {}).get('project_name', 'Kitchen Project')
        total_amount = pdf_data.get('pricing_summary', {}).get('total', '0.00')
        quotation_number = pdf_data.get('quotation_info', {}).get('quotation_number', 'SPK-000001')
        
        # Create minimal HTML with actual data
        fallback_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Quotation PDF</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ text-align: center; color: #333; border-bottom: 2px solid #000; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .total {{ font-weight: bold; background-color: #e6e6e6; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>QUOTATION</h1>
                <p><strong>Quotation Number:</strong> {quotation_number}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%d %B %Y')}</p>
            </div>
            
            <h2>Project Information</h2>
            <table>
                <tr><th>Customer Name</th><td>{customer_name}</td></tr>
                <tr><th>Project Name</th><td>{project_name}</td></tr>
                <tr><th>Project Type</th><td>Kitchen Design & Installation</td></tr>
            </table>
            
            <h2>Price Summary</h2>
            <table>
                <tr><th>Description</th><th>Amount</th></tr>
                <tr><td>Kitchen Components</td><td>₹{pdf_data.get('pricing_summary', {}).get('kitchen_total', '0.00')}</td></tr>
                <tr><td>Doors</td><td>₹{pdf_data.get('pricing_summary', {}).get('doors_total', '0.00')}</td></tr>
                <tr><td>Accessories</td><td>₹{pdf_data.get('pricing_summary', {}).get('accessories_total', '0.00')}</td></tr>
                <tr><td>Lighting</td><td>₹{pdf_data.get('pricing_summary', {}).get('lighting_total', '0.00')}</td></tr>
                <tr class="total"><th>TOTAL AMOUNT</th><td><strong>₹{total_amount}</strong></td></tr>
            </table>
            
            <div style="margin-top: 40px;">
                <h3>Terms and Conditions</h3>
                <ul>
                    <li>This quotation is valid for 30 days from the date of issue.</li>
                    <li>50% advance payment required to commence work.</li>
                    <li>Balance payment due upon project completion.</li>
                    <li>All materials are covered under manufacturer warranty.</li>
                </ul>
            </div>
            
            <div style="margin-top: 40px; text-align: center; border-top: 1px solid #ddd; padding-top: 20px;">
                <p><strong>Speisekamer - Premium Kitchen Solutions</strong><br>
                Phone: +91-9876-543210 | Email: info@speisekamer.com</p>
                <p><em>Thank you for choosing Speisekamer for your kitchen needs!</em></p>
            </div>
        </body>
        </html>
        """
        
        logger.info("Created emergency fallback template with actual project data")
        return fallback_html
    
    def _format_file_size(self, bytes_size):
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"

    def save_pdf_to_storage(self, pdf_bytes, template_data):
        """Save PDF file to Django storage"""
        try:
            # Generate filename using mapped data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            customer_name = template_data.get('customer_info', {}).get('name', 'Customer')
            safe_customer_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_customer_name = safe_customer_name.replace(' ', '_')
            
            pdf_filename = f"quotation_{safe_customer_name}_{self.project_id}_{timestamp}.pdf"
            
            # Save to media storage
            file_path = f"quotation_pdfs/{pdf_filename}"
            
            # Use Django storage
            content_file = ContentFile(pdf_bytes)
            saved_path = default_storage.save(file_path, content_file)
            
            logger.info(f"PDF saved to storage: {saved_path}")
            return pdf_filename
            
        except Exception as e:
            logger.error(f"Failed to save PDF to storage: {str(e)}")
            raise PDFGenerationError(f"Storage save failed: {str(e)}")

    def save_pdf_history(self, template_data, file_size, pdf_filename):
        """Save PDF generation history"""
        try:
            # Import here to avoid circular imports
            from ..models import QuotationPDFHistory
            
            history_record = QuotationPDFHistory.objects.create(
                project_id=self.project_id,
                pdf_filename=pdf_filename,
                file_size=file_size,
                template_type=self.customizations.get('template_type', 'DETAILED'),
                customizations=self.customizations,
                generation_method='HTML_TO_PDF_COMPATIBLE',
                renderer_used=self.pdf_renderer.renderer_name
            )
            
            logger.info(f"PDF history saved: {history_record.id}")
            return history_record
            
        except Exception as e:
            logger.warning(f"Failed to save PDF history: {str(e)}")
            return None

    def get_download_url(self, pdf_filename):
        """Generate download URL"""
        try:
            return f"/media/quotation_pdfs/{pdf_filename}"
        except Exception:
            return None

    def debug_template_data(self):
        """Debug method to inspect template data structure"""
        try:
            if not self.compiler:
                self.compiler = QuotationPDFDataCompiler(self.project_id, self.customizations)
            
            # Get raw data
            raw_data = self.compiler.compile_complete_data()
            
            # Map to template format
            mapper = TemplateDataMapper(raw_data)
            template_data = mapper.map_to_template_structure()
            
            debug_info = {
                'raw_data_keys': list(raw_data.keys()),
                'template_data_keys': list(template_data.keys()),
                'customer_name': template_data.get('customer_info', {}).get('name'),
                'project_name': template_data.get('project_info', {}).get('project_name'),
                'kitchen_items_count': len(template_data.get('kitchen_items', [])),
                'doors_items_count': len(template_data.get('doors_items', [])),
                'accessories_count': len(template_data.get('accessories_items', [])),
                'lighting_count': len(template_data.get('lighting_items', [])),
                'total_amount': template_data.get('pricing_summary', {}).get('total'),
                'quotation_number': template_data.get('quotation_info', {}).get('quotation_number')
            }
            
            logger.info(f"Template data debug info: {debug_info}")
            return {
                'raw_data': raw_data,
                'template_data': template_data,
                'debug_info': debug_info
            }
            
        except Exception as e:
            logger.error(f"Debug template data failed: {str(e)}")
            return {'error': str(e)}