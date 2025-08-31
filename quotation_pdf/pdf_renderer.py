# quotation_pdf/pdf_renderer.py - FIXED for xhtml2pdf compatibility

import os
import logging
from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string
import sys
import re

logger = logging.getLogger('quotation_pdf')

# Import checks
WEASYPRINT_AVAILABLE = False
WEASYPRINT_ERROR = None
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint successfully imported")
except ImportError as e:
    WEASYPRINT_ERROR = f"ImportError: {str(e)}"
    logger.warning(f"WeasyPrint not available: {e}")
except OSError as e:
    WEASYPRINT_ERROR = f"OSError: {str(e)}"
    logger.warning(f"WeasyPrint dependencies not available: {e}")

XHTML2PDF_AVAILABLE = False
try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
    logger.info("xhtml2pdf available")
except ImportError as e:
    logger.warning(f"xhtml2pdf not available: {e}")

REPORTLAB_AVAILABLE = False
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
    logger.info("ReportLab available")
except ImportError as e:
    logger.warning(f"ReportLab not available: {e}")


class PDFGenerationError(Exception):
    """Custom exception for PDF generation errors"""
    pass


class WeasyPrintRenderer:
    """HTML-to-PDF renderer using WeasyPrint - Best quality"""
    
    def __init__(self):
        if not WEASYPRINT_AVAILABLE:
            raise PDFGenerationError(f"WeasyPrint is not available: {WEASYPRINT_ERROR}")
        self.weasyprint = weasyprint
        
    def render_pdf(self, html_content, css_files=None, base_url=None, pdf_data=None):
        """Render HTML content to PDF using WeasyPrint"""
        try:
            logger.info("Starting HTML-to-PDF generation with WeasyPrint")
            
            # Prepare stylesheets
            stylesheets = []
            if css_files:
                for css_file in css_files:
                    if os.path.exists(css_file):
                        stylesheets.append(self.weasyprint.CSS(filename=css_file))
                        logger.info(f"Loaded CSS file: {css_file}")
            
            # WeasyPrint configuration
            font_config = self.weasyprint.fonts.FontConfiguration()
            
            # Create HTML document
            html_doc = self.weasyprint.HTML(
                string=html_content,
                base_url=base_url or settings.BASE_DIR,
                encoding='utf-8'
            )
            
            # Generate PDF
            pdf_bytes = html_doc.write_pdf(
                stylesheets=stylesheets,
                font_config=font_config,
                optimize_size=('fonts', 'images')
            )
            
            logger.info(f"WeasyPrint PDF generation successful, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"WeasyPrint HTML-to-PDF failed: {str(e)}")
            raise PDFGenerationError(f"WeasyPrint HTML rendering failed: {str(e)}")


class XHTMLToPDFRenderer:
    """FIXED HTML-to-PDF renderer using xhtml2pdf with compatibility layer"""
    
    def __init__(self):
        if not XHTML2PDF_AVAILABLE:
            raise PDFGenerationError("xhtml2pdf is not available")
    
    def render_pdf(self, html_content, css_files=None, base_url=None, pdf_data=None):
        """Render HTML content to PDF using xhtml2pdf with compatibility fixes"""
        try:
            logger.info("Starting HTML-to-PDF generation with xhtml2pdf (compatibility mode)")
            
            # STEP 1: Clean HTML content for xhtml2pdf compatibility
            cleaned_html = self._clean_html_for_compatibility(html_content)
            
            # STEP 2: Prepare CSS with compatibility fixes
            css_content = self._prepare_compatible_css(css_files)
            
            # STEP 3: Create complete HTML with embedded CSS
            complete_html = self._build_complete_html(cleaned_html, css_content)
            
            # STEP 4: Generate PDF with xhtml2pdf
            result_buffer = BytesIO()
            
            # Configure xhtml2pdf with error handling
            pisa_status = pisa.CreatePDF(
                src=complete_html,
                dest=result_buffer,
                encoding='utf-8',
                link_callback=self._safe_link_callback,
                show_error_as_pdf=False  # Don't show errors in PDF
            )
            
            # Check for errors
            if pisa_status.err:
                error_details = f"xhtml2pdf reported {len(pisa_status.err)} errors"
                logger.warning(f"xhtml2pdf generation had errors: {error_details}")
                # Continue anyway - sometimes warnings are non-critical
            
            pdf_bytes = result_buffer.getvalue()
            result_buffer.close()
            
            if not pdf_bytes or len(pdf_bytes) < 100:
                raise PDFGenerationError("xhtml2pdf generated empty or invalid PDF")
            
            logger.info(f"xhtml2pdf PDF generation successful, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"xhtml2pdf HTML-to-PDF failed: {str(e)}")
            raise PDFGenerationError(f"xhtml2pdf HTML rendering failed: {str(e)}")
    
    def _clean_html_for_compatibility(self, html_content):
        """Clean HTML content to be compatible with xhtml2pdf"""
        
        # Remove problematic HTML5 elements and attributes
        problematic_patterns = [
            # Remove CSS Grid and Flexbox from inline styles
            (r'display\s*:\s*grid[^;]*;?', ''),
            (r'display\s*:\s*flex[^;]*;?', ''),
            (r'grid-[^;]*:[^;]*;?', ''),
            (r'flex-[^;]*:[^;]*;?', ''),
            (r'align-items[^;]*:[^;]*;?', ''),
            (r'justify-content[^;]*:[^;]*;?', ''),
            
            # Remove transforms and animations
            (r'transform[^;]*:[^;]*;?', ''),
            (r'transition[^;]*:[^;]*;?', ''),
            (r'animation[^;]*:[^;]*;?', ''),
            
            # Remove modern CSS properties
            (r'box-shadow[^;]*:[^;]*;?', ''),
            (r'border-radius[^;]*:[^;]*;?', ''),
            (r'background-image[^;]*:linear-gradient[^;]*;?', ''),
            
            # Remove complex selectors
            (r'::before', ''),
            (r'::after', ''),
            (r':hover[^{]*{[^}]*}', ''),
            
            # Clean up empty style attributes
            (r'style\s*=\s*["\']["\']', ''),
            (r'style\s*=\s*["\'][\s;]*["\']', ''),
        ]
        
        cleaned_html = html_content
        for pattern, replacement in problematic_patterns:
            cleaned_html = re.sub(pattern, replacement, cleaned_html, flags=re.IGNORECASE | re.MULTILINE)
        
        # Replace complex div structures with tables for better compatibility
        cleaned_html = self._convert_complex_layouts_to_tables(cleaned_html)
        
        return cleaned_html
    
    def _convert_complex_layouts_to_tables(self, html_content):
        """Convert complex div layouts to table-based layouts for xhtml2pdf"""
        
        # Convert grid-like structures to tables
        # This is a simplified conversion - you may need to customize based on your templates
        
        # Convert project-info grid to table
        grid_pattern = r'<div class="project-info">(.*?)</div>'
        def replace_grid(match):
            content = match.group(1)
            # Convert info cards to table rows
            return f'''
            <table width="100%" cellpadding="10" cellspacing="0" border="0">
                <tr>
                    <td width="50%" valign="top">{content}</td>
                </tr>
            </table>
            '''
        
        html_content = re.sub(grid_pattern, replace_grid, html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert pricing sections to proper tables
        pricing_pattern = r'<div class="pricing-section">(.*?)</div>'
        def replace_pricing(match):
            return f'<table width="100%" cellpadding="5" cellspacing="0" border="1">{match.group(1)}</table>'
        
        html_content = re.sub(pricing_pattern, replace_pricing, html_content, flags=re.DOTALL | re.IGNORECASE)
        
        return html_content
    
    def _prepare_compatible_css(self, css_files):
        """Prepare CSS that's compatible with xhtml2pdf"""
        
        css_content = ""
        
        if css_files:
            for css_file in css_files:
                if os.path.exists(css_file):
                    try:
                        with open(css_file, 'r', encoding='utf-8') as f:
                            css_content += f.read() + "\n"
                        logger.info(f"Loaded CSS file: {css_file}")
                    except Exception as e:
                        logger.warning(f"Failed to read CSS file {css_file}: {e}")
        
        # Clean CSS for xhtml2pdf compatibility
        return self._clean_css_for_xhtml2pdf(css_content)
    
    def _clean_css_for_xhtml2pdf(self, css_content):
        """Remove CSS properties that xhtml2pdf can't handle"""
        
        # List of CSS properties/patterns that cause issues with xhtml2pdf
        unsupported_patterns = [
            # Layout properties
            r'display\s*:\s*grid[^;]*;?',
            r'display\s*:\s*flex[^;]*;?',
            r'grid-[^:]*:[^;]*;?',
            r'flex-[^:]*:[^;]*;?',
            r'align-items[^:]*:[^;]*;?',
            r'justify-content[^:]*:[^;]*;?',
            r'align-self[^:]*:[^;]*;?',
            r'justify-self[^:]*:[^;]*;?',
            
            # Visual effects
            r'transform[^:]*:[^;]*;?',
            r'transition[^:]*:[^;]*;?',
            r'animation[^:]*:[^;]*;?',
            r'box-shadow[^:]*:[^;]*;?',
            r'border-radius[^:]*:[^;]*;?',
            r'backdrop-filter[^:]*:[^;]*;?',
            r'filter[^:]*:[^;]*;?',
            
            # Modern background properties
            r'background-image\s*:\s*linear-gradient[^;]*;?',
            r'background-image\s*:\s*radial-gradient[^;]*;?',
            r'background-clip[^:]*:[^;]*;?',
            r'background-origin[^:]*:[^;]*;?',
            
            # Pseudo-elements and advanced selectors
            r'[^{]*::before[^{]*{[^}]*}',
            r'[^{]*::after[^{]*{[^}]*}',
            r'[^{]*:hover[^{]*{[^}]*}',
            r'[^{]*:focus[^{]*{[^}]*}',
            r'[^{]*:nth-child[^{]*{[^}]*}',
            r'[^{]*:first-child[^{]*{[^}]*}',
            r'[^{]*:last-child[^{]*{[^}]*}',
            
            # Media queries
            r'@media[^{]*{[^{}]*{[^}]*}[^}]*}',
            
            # Advanced positioning
            r'position\s*:\s*sticky[^;]*;?',
            r'z-index[^:]*:[^;]*;?',
            
            # Text effects
            r'text-shadow[^:]*:[^;]*;?',
            r'letter-spacing[^:]*:[^;]*;?',
            
            # Other problematic properties
            r'overflow[^:]*:[^;]*;?',
            r'clip-path[^:]*:[^;]*;?',
            r'mask[^:]*:[^;]*;?',
        ]
        
        cleaned_css = css_content
        for pattern in unsupported_patterns:
            cleaned_css = re.sub(pattern, '', cleaned_css, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        # Add basic xhtml2pdf compatible styles
        compatible_css = """
        /* xhtml2pdf Compatible Styles */
        body {
            font-family: Arial, Helvetica, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            margin: 20px;
            color: #000;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #333;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        h1 { font-size: 24px; }
        h2 { font-size: 20px; }
        h3 { font-size: 16px; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        table td, table th {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            vertical-align: top;
        }
        
        table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #000;
            padding-bottom: 20px;
        }
        
        .section {
            margin-bottom: 30px;
        }
        
        .total {
            font-weight: bold;
            background-color: #f0f0f0;
        }
        
        .text-right {
            text-align: right;
        }
        
        .text-center {
            text-align: center;
        }
        
        """ + cleaned_css
        
        return compatible_css
    
    def _build_complete_html(self, html_content, css_content):
        """Build complete HTML document with embedded CSS"""
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Quotation PDF</title>
    <style type="text/css">
    {css_content}
    </style>
</head>
<body>
{html_content}
</body>
</html>'''
    
    def _safe_link_callback(self, uri, rel):
        """Safe link callback that handles errors gracefully"""
        try:
            if uri.startswith('http'):
                return uri
            
            # Handle local file paths
            if uri.startswith('/static/'):
                path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR, uri.lstrip('/'))
            elif uri.startswith('/media/'):
                path = os.path.join(settings.MEDIA_ROOT or settings.BASE_DIR, uri.lstrip('/'))
            else:
                path = os.path.join(settings.BASE_DIR, uri.lstrip('/'))
            
            if os.path.exists(path):
                return path
                
        except Exception as e:
            logger.debug(f"Link callback warning for {uri}: {e}")
        
        # Return original URI if we can't resolve it
        return uri


class HTMLOnlyPDFRenderer:
    """Enhanced proxy that prioritizes working HTML-to-PDF renderers"""
    
    def __init__(self, prefer_weasyprint=True):
        self.renderer = None
        self.renderer_name = None
        self.attempted_renderers = []
        
        # Try renderers in order of capability
        renderers_to_try = []
        
        if prefer_weasyprint and WEASYPRINT_AVAILABLE:
            renderers_to_try.append(('WeasyPrint', WeasyPrintRenderer))
        
        # Always try xhtml2pdf with our compatibility fixes
        if XHTML2PDF_AVAILABLE:
            renderers_to_try.append(('xhtml2pdf-compatible', XHTMLToPDFRenderer))
        
        # Add WeasyPrint at end if not preferred but available
        if not prefer_weasyprint and WEASYPRINT_AVAILABLE:
            renderers_to_try.append(('WeasyPrint', WeasyPrintRenderer))
        
        # Try each renderer
        for renderer_name, renderer_class in renderers_to_try:
            try:
                self.renderer = renderer_class()
                self.renderer_name = renderer_name
                logger.info(f"Successfully initialized {renderer_name} for HTML-to-PDF")
                return
            except Exception as e:
                error_msg = f"{renderer_name}: {str(e)}"
                self.attempted_renderers.append(error_msg)
                logger.warning(f"{renderer_name} initialization failed: {e}")
        
        # No HTML renderer available
        error_msg = f"No compatible HTML-to-PDF renderers available. Attempted: {'; '.join(self.attempted_renderers)}"
        raise PDFGenerationError(error_msg)
    
    def render_pdf(self, html_content, css_files=None, base_url=None, pdf_data=None):
        """Render PDF using HTML-only approach with error recovery"""
        if not self.renderer:
            raise PDFGenerationError("No HTML-to-PDF renderer available")
        
        logger.info(f"Rendering HTML-to-PDF with {self.renderer_name}")
        
        try:
            return self.renderer.render_pdf(html_content, css_files, base_url, pdf_data)
                
        except Exception as e:
            logger.error(f"HTML-to-PDF rendering with {self.renderer_name} failed: {str(e)}")
            
            # If xhtml2pdf failed due to compatibility issues, try with a simpler template
            if 'xhtml2pdf' in self.renderer_name and 'NotImplementedType' in str(e):
                logger.info("Attempting fallback with simplified template...")
                try:
                    simplified_html = self._create_simplified_fallback_html(html_content, pdf_data)
                    return self.renderer.render_pdf(simplified_html, None, base_url, pdf_data)
                except Exception as fallback_error:
                    logger.error(f"Simplified fallback also failed: {fallback_error}")
            
            raise PDFGenerationError(f"HTML-to-PDF rendering failed with {self.renderer_name}: {str(e)}")
    
    def _create_simplified_fallback_html(self, original_html, pdf_data):
        """Create a very simple HTML fallback when complex rendering fails"""
        
        # Extract basic text content
        import re
        text_content = re.sub(r'<[^>]+>', ' ', original_html)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Create minimal HTML structure
        fallback_html = f"""
        <html>
        <head>
            <title>Quotation PDF</title>
        </head>
        <body>
            <h1 style="text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px;">
                QUOTATION
            </h1>
            
            <div style="margin: 20px 0;">
                <strong>Project Information:</strong><br>
                {text_content[:500]}...
            </div>
            
            <p style="margin-top: 40px; font-style: italic; color: #666;">
                Note: This is a simplified version due to rendering compatibility issues.
                Please contact support for the full formatted version.
            </p>
        </body>
        </html>
        """
        
        logger.info("Created simplified fallback HTML")
        return fallback_html
    
    def get_renderer_info(self):
        """Get information about the active renderer"""
        return {
            'name': self.renderer_name,
            'type': 'HTML_TO_PDF_COMPATIBLE',
            'weasyprint_available': WEASYPRINT_AVAILABLE,
            'xhtml2pdf_available': XHTML2PDF_AVAILABLE,
            'attempted_renderers': self.attempted_renderers,
            'weasyprint_error': WEASYPRINT_ERROR
        }


# Factory function
def get_pdf_renderer(prefer_weasyprint=True):
    """Get compatible HTML-to-PDF renderer"""
    return HTMLOnlyPDFRenderer(prefer_weasyprint=prefer_weasyprint)


# Utility functions
def get_available_renderers():
    """Get information about available HTML-to-PDF renderers"""
    return {
        'weasyprint': {
            'available': WEASYPRINT_AVAILABLE,
            'type': 'HTML_TO_PDF_PREMIUM',
            'error': WEASYPRINT_ERROR if not WEASYPRINT_AVAILABLE else None
        },
        'xhtml2pdf': {
            'available': XHTML2PDF_AVAILABLE,
            'type': 'HTML_TO_PDF_COMPATIBLE',
            'error': None if XHTML2PDF_AVAILABLE else "Not installed"
        },
        'reportlab': {
            'available': REPORTLAB_AVAILABLE,
            'type': 'PROGRAMMATIC_PDF',
            'error': None if REPORTLAB_AVAILABLE else "Not installed"
        }
    }