# quotation_pdf/pdf_renderer.py

import os
import logging
from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse
from datetime import datetime

logger = logging.getLogger('quotation_pdf')

try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint successfully imported")
except ImportError as e:
    WEASYPRINT_AVAILABLE = False
    logger.error(f"WeasyPrint not available: {e}")

class PDFRenderer:
    """Handle PDF generation with WeasyPrint"""
    
    def __init__(self):
        self.weasyprint_available = WEASYPRINT_AVAILABLE
        
    def render_pdf(self, html_content, css_files=None, base_url=None):
        """
        Render HTML content to PDF using WeasyPrint
        
        Args:
            html_content (str): HTML content to render
            css_files (list): List of CSS file paths
            base_url (str): Base URL for resolving relative paths
            
        Returns:
            bytes: PDF content as bytes
        """
        if not self.weasyprint_available:
            raise ImportError("WeasyPrint is not available. Install it with: pip install weasyprint")
        
        try:
            logger.info("Starting PDF generation with WeasyPrint")
            
            # Prepare CSS stylesheets
            stylesheets = []
            if css_files:
                for css_file in css_files:
                    if os.path.exists(css_file):
                        stylesheets.append(weasyprint.CSS(filename=css_file))
                        logger.info(f"Loaded CSS file: {css_file}")
                    else:
                        logger.warning(f"CSS file not found: {css_file}")
            
            # Configure WeasyPrint
            config = self._get_weasyprint_config()
            
            # Generate PDF
            html_doc = weasyprint.HTML(
                string=html_content,
                base_url=base_url,
                encoding='utf-8'
            )
            
            pdf_bytes = html_doc.write_pdf(
                stylesheets=stylesheets,
                font_config=config['font_config'],
                optimize_size=('fonts', 'images')
            )
            
            logger.info(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            raise PDFGenerationError(f"Failed to generate PDF: {str(e)}")
    
    def _get_weasyprint_config(self):
        """Get WeasyPrint configuration"""
        font_config = weasyprint.fonts.FontConfiguration()
        
        # Add custom font paths if configured
        font_paths = getattr(settings, 'WEASYPRINT_FONT_PATHS', [])
        for font_path in font_paths:
            if os.path.exists(font_path):
                font_config.add_font_directory(font_path)
                logger.info(f"Added font directory: {font_path}")
        
        return {
            'font_config': font_config,
        }
    
    def render_pdf_response(self, html_content, filename, css_files=None):
        """
        Render PDF and return Django HttpResponse
        
        Args:
            html_content (str): HTML content
            filename (str): PDF filename
            css_files (list): CSS files
            
        Returns:
            HttpResponse: PDF response
        """
        try:
            pdf_bytes = self.render_pdf(html_content, css_files)
            
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(pdf_bytes)
            
            return response
            
        except Exception as e:
            logger.error(f"PDF response generation failed: {str(e)}")
            raise


class PDFGenerationError(Exception):
    """Custom exception for PDF generation errors"""
    pass


# Alternative renderer using ReportLab (lighter dependency)
class ReportLabRenderer:
    """Alternative PDF renderer using ReportLab"""
    
    def __init__(self):
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            self.reportlab_available = True
            self.canvas = canvas
            self.A4 = A4
            self.SimpleDocTemplate = SimpleDocTemplate
            self.Paragraph = Paragraph
            self.Spacer = Spacer
            self.getSampleStyleSheet = getSampleStyleSheet
        except ImportError:
            self.reportlab_available = False
    
    def render_simple_pdf(self, project_data, filename):
        """
        Render a simple PDF using ReportLab (fallback option)
        """
        if not self.reportlab_available:
            raise ImportError("ReportLab is not available")
        
        buffer = BytesIO()
        doc = self.SimpleDocTemplate(buffer, pagesize=self.A4)
        styles = self.getSampleStyleSheet()
        
        # Build PDF content
        story = []
        
        # Title
        title = self.Paragraph(f"Kitchen Quotation - {project_data.get('customer_name', 'Unknown')}", 
                              styles['Title'])
        story.append(title)
        story.append(self.Spacer(1, 20))
        
        # Project details
        details = f"""
        <b>Project ID:</b> {project_data.get('project_id', 'N/A')}<br/>
        <b>Date:</b> {datetime.now().strftime('%d %B %Y')}<br/>
        <b>Customer:</b> {project_data.get('customer_name', 'Unknown')}<br/>
        <b>Total Amount:</b> {project_data.get('total_amount', '₹0.00')}
        """
        
        details_para = self.Paragraph(details, styles['Normal'])
        story.append(details_para)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()


# Factory function to get appropriate renderer
def get_pdf_renderer(prefer_weasyprint=True):
    """
    Get the best available PDF renderer
    
    Args:
        prefer_weasyprint (bool): Prefer WeasyPrint if available
        
    Returns:
        PDFRenderer or ReportLabRenderer
    """
    if prefer_weasyprint and WEASYPRINT_AVAILABLE:
        return PDFRenderer()
    else:
        return ReportLabRenderer()