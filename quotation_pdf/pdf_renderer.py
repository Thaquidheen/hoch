import weasyprint
from django.conf import settings
from django.template.loader import render_to_string
from io import BytesIO
import os

class PDFRenderer:
    """Render HTML to PDF using WeasyPrint"""
    
    def __init__(self):
        # Configure WeasyPrint settings
        self.css_base_path = os.path.join(settings.BASE_DIR, 'quotation_pdf', 'static', 'css')
    
    def render_pdf(self, html_content, css_files=None):
        """Convert HTML content to PDF bytes"""
        try:
            # Create HTML document
            html_doc = weasyprint.HTML(
                string=html_content,
                base_url=settings.MEDIA_URL  # For resolving relative URLs in HTML
            )
            
            # Load CSS files
            css_stylesheets = []
            if css_files:
                for css_file in css_files:
                    css_path = os.path.join(self.css_base_path, css_file)
                    if os.path.exists(css_path):
                        css_stylesheets.append(weasyprint.CSS(filename=css_path))
            
            # Default CSS for quotations
            default_css_path = os.path.join(self.css_base_path, 'quotation_styles.css')
            if os.path.exists(default_css_path):
                css_stylesheets.append(weasyprint.CSS(filename=default_css_path))
            
            # Generate PDF
            pdf_buffer = BytesIO()
            html_doc.write_pdf(
                target=pdf_buffer,
                stylesheets=css_stylesheets,
                optimize_images=True  # Optimize images for smaller file size
            )
            
            return pdf_buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"PDF generation failed: {str(e)}")