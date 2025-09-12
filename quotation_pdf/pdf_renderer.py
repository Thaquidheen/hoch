# quotation_pdf/pdf_renderer.py - FIXED to always use template

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
            
            logger.info(f"✅ WeasyPrint PDF generation successful, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"❌ WeasyPrint HTML-to-PDF failed: {str(e)}")
            raise PDFGenerationError(f"WeasyPrint HTML rendering failed: {str(e)}")


class XHTMLToPDFRenderer:
    """HTML-to-PDF renderer using xhtml2pdf with compatibility fixes"""
    
    def __init__(self):
        if not XHTML2PDF_AVAILABLE:
            raise PDFGenerationError("xhtml2pdf is not available")
    
    def render_pdf(self, html_content, css_files=None, base_url=None, pdf_data=None):
        """Render HTML content to PDF using xhtml2pdf with compatibility fixes"""
        try:
            logger.info("Starting HTML-to-PDF generation with xhtml2pdf (compatibility mode)")
            
            # Clean HTML content for xhtml2pdf compatibility
            cleaned_html = self._clean_html_for_compatibility(html_content)
            
            # Prepare CSS with compatibility fixes
            css_content = self._prepare_compatible_css(css_files)
            
            # Create complete HTML with embedded CSS
            complete_html = self._build_complete_html(cleaned_html, css_content)
            
            # Generate PDF with xhtml2pdf
            result_buffer = BytesIO()
            
            # Configure xhtml2pdf with error handling
            pisa_status = pisa.CreatePDF(
                src=complete_html,
                dest=result_buffer,
                encoding='utf-8',
                link_callback=self._safe_link_callback,
                show_error_as_pdf=False
            )
            
            # Check for errors
            if pisa_status.err:
                error_details = f"xhtml2pdf reported {len(pisa_status.err)} errors"
                logger.warning(f"xhtml2pdf generation had warnings: {error_details}")
                # Continue - warnings are usually non-critical
            
            pdf_bytes = result_buffer.getvalue()
            result_buffer.close()
            
            if not pdf_bytes or len(pdf_bytes) < 100:
                raise PDFGenerationError("xhtml2pdf generated empty or invalid PDF")
            
            logger.info(f"✅ xhtml2pdf PDF generation successful, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"❌ xhtml2pdf HTML-to-PDF failed: {str(e)}")
            raise PDFGenerationError(f"xhtml2pdf HTML rendering failed: {str(e)}")
    
    def _clean_html_for_compatibility(self, html_content):
        """Clean HTML content to be compatible with xhtml2pdf"""
        
        # Remove problematic CSS properties from inline styles
        problematic_patterns = [
            (r'display\s*:\s*grid[^;]*;?', 'display: block;'),
            (r'display\s*:\s*flex[^;]*;?', 'display: block;'),
            (r'grid-[^;]*:[^;]*;?', ''),
            (r'flex-[^;]*:[^;]*;?', ''),
            (r'align-items[^;]*:[^;]*;?', ''),
            (r'justify-content[^;]*:[^;]*;?', ''),
            (r'transform[^;]*:[^;]*;?', ''),
            (r'transition[^;]*:[^;]*;?', ''),
            (r'animation[^;]*:[^;]*;?', ''),
            (r'box-shadow[^;]*:[^;]*;?', ''),
            (r'border-radius[^;]*:[^;]*;?', ''),
            (r'background-image[^;]*:linear-gradient[^;]*;?', ''),
            (r'::before', ''),
            (r'::after', ''),
            (r'style\s*=\s*["\']["\']', ''),
            (r'style\s*=\s*["\'][\s;]*["\']', ''),
        ]
        
        cleaned_html = html_content
        for pattern, replacement in problematic_patterns:
            cleaned_html = re.sub(pattern, replacement, cleaned_html, flags=re.IGNORECASE | re.MULTILINE)
        
        return cleaned_html
    
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
        
        return self._clean_css_for_xhtml2pdf(css_content)
    
    def _clean_css_for_xhtml2pdf(self, css_content):
        """Remove CSS properties that xhtml2pdf can't handle"""
        
        unsupported_patterns = [
            r'display\s*:\s*grid[^;]*;?',
            r'display\s*:\s*flex[^;]*;?',
            r'grid-[^:]*:[^;]*;?',
            r'flex-[^:]*:[^;]*;?',
            r'align-items[^:]*:[^;]*;?',
            r'justify-content[^:]*:[^;]*;?',
            r'transform[^:]*:[^;]*;?',
            r'transition[^:]*:[^;]*;?',
            r'animation[^:]*:[^;]*;?',
            r'box-shadow[^:]*:[^;]*;?',
            r'border-radius[^:]*:[^;]*;?',
            r'background-image\s*:\s*linear-gradient[^;]*;?',
            r'background-image\s*:\s*radial-gradient[^;]*;?',
            r'[^{]*::before[^{]*{[^}]*}',
            r'[^{]*::after[^{]*{[^}]*}',
            r'[^{]*:hover[^{]*{[^}]*}',
            r'@media[^{]*{[^{}]*{[^}]*}[^}]*}',
            r'position\s*:\s*sticky[^;]*;?',
            r'z-index[^:]*:[^;]*;?',
        ]
        
        cleaned_css = css_content
        for pattern in unsupported_patterns:
            cleaned_css = re.sub(pattern, '', cleaned_css, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        # Add basic compatible styles
        compatible_css = """
        body {
            font-family: Arial, sans-serif;
            font-size: 11px;
            line-height: 1.4;
            margin: 15px;
            color: #000;
        }
        h1, h2, h3 { color: #333; font-weight: bold; margin-bottom: 10px; }
        h1 { font-size: 20px; }
        h2 { font-size: 16px; }
        h3 { font-size: 14px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
        table td, table th { border: 1px solid #ddd; padding: 6px; text-align: left; vertical-align: top; }
        table th { background-color: #f5f5f5; font-weight: bold; }
        .text-right { text-align: right; }
        .text-center { text-align: center; }
        .font-bold { font-weight: bold; }
        """ + cleaned_css
        
        return compatible_css
    
    def _build_complete_html(self, html_content, css_content):
        """Build complete HTML document with embedded CSS"""
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Kitchen Quotation PDF</title>
    <style type="text/css">{css_content}</style>
</head>
<body>{html_content}</body>
</html>'''
    
    def _safe_link_callback(self, uri, rel):
        """Safe link callback for handling file paths"""
        try:
            if uri.startswith('http'):
                return uri
            
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
        
        return uri


class HTMLOnlyPDFRenderer:
    """✅ FIXED: Always use proper templates, never generate fallback HTML"""
    
    def __init__(self, prefer_weasyprint=True):
        self.renderer = None
        self.renderer_name = None
        self.attempted_renderers = []
        
        # Try renderers in order of preference
        renderers_to_try = []
        
        if prefer_weasyprint and WEASYPRINT_AVAILABLE:
            renderers_to_try.append(('WeasyPrint', WeasyPrintRenderer))
        
        if XHTML2PDF_AVAILABLE:
            renderers_to_try.append(('xhtml2pdf-compatible', XHTMLToPDFRenderer))
        
        if not prefer_weasyprint and WEASYPRINT_AVAILABLE:
            renderers_to_try.append(('WeasyPrint', WeasyPrintRenderer))
        
        # Initialize the first working renderer
        for renderer_name, renderer_class in renderers_to_try:
            try:
                self.renderer = renderer_class()
                self.renderer_name = renderer_name
                logger.info(f"✅ Successfully initialized {renderer_name} for HTML-to-PDF")
                return
            except Exception as e:
                error_msg = f"{renderer_name}: {str(e)}"
                self.attempted_renderers.append(error_msg)
                logger.warning(f"❌ {renderer_name} initialization failed: {e}")
        
        # No HTML renderer available
        error_msg = f"No compatible HTML-to-PDF renderers available. Attempted: {'; '.join(self.attempted_renderers)}"
        raise PDFGenerationError(error_msg)
    
    def render_pdf(self, html_content, css_files=None, base_url=None, pdf_data=None):
        """✅ FIXED: Render PDF using only proper templates"""
        if not self.renderer:
            raise PDFGenerationError("No HTML-to-PDF renderer available")
        
        logger.info(f"🎨 Rendering HTML-to-PDF with {self.renderer_name}")
        
        try:
            # ✅ First attempt: Use the provided HTML template (your detailed template)
            pdf_bytes = self.renderer.render_pdf(html_content, css_files, base_url, pdf_data)
            logger.info(f"✅ Primary template rendered successfully with {self.renderer_name}")
            return pdf_bytes
                
        except Exception as e:
            logger.error(f"❌ Primary template rendering failed with {self.renderer_name}: {str(e)}")
            
            # ✅ Fallback: Load the compatible template instead of generating HTML
            try:
                logger.info("🔄 Attempting fallback to compatible template...")
                fallback_html = self._load_compatible_template(pdf_data)
                pdf_bytes = self.renderer.render_pdf(fallback_html, None, base_url, pdf_data)
                logger.info(f"✅ Compatible template rendered successfully with {self.renderer_name}")
                return pdf_bytes
                
            except Exception as fallback_error:
                logger.error(f"❌ Compatible template also failed: {fallback_error}")
                # ❌ NO MORE FALLBACKS - Let the error bubble up
                raise PDFGenerationError(f"Both primary and compatible templates failed. Primary: {str(e)}. Fallback: {str(fallback_error)}")
    
    def _load_compatible_template(self, pdf_data):
        """✅ Load the simple compatible template for xhtml2pdf"""
        try:
            template_name = 'quotation_pdf/simple_quotation_compatible.html'
            html_content = render_to_string(template_name, pdf_data or {})
            logger.info(f"✅ Loaded compatible template: {template_name}")
            return html_content
            
        except Exception as e:
            logger.error(f"❌ Failed to load compatible template: {e}")
            # Try alternative template names
            alternative_templates = [
                'quotation_pdf/simple_quotation.html',
                'quotation_pdf/basic_quotation.html'
            ]
            
            for template_name in alternative_templates:
                try:
                    html_content = render_to_string(template_name, pdf_data or {})
                    logger.info(f"✅ Loaded alternative template: {template_name}")
                    return html_content
                except:
                    continue
            
            # If no template works, raise the original error
            raise PDFGenerationError(f"Could not load any compatible template. Original error: {e}")
    
    def get_renderer_info(self):
        """Get information about the active renderer"""
        return {
            'name': self.renderer_name,
            'type': 'HTML_TO_PDF_TEMPLATE_ONLY',
            'weasyprint_available': WEASYPRINT_AVAILABLE,
            'xhtml2pdf_available': XHTML2PDF_AVAILABLE,
            'attempted_renderers': self.attempted_renderers,
            'weasyprint_error': WEASYPRINT_ERROR,
            'current_time_utc': '2025-08-31 06:53:32',
            'current_user': 'Thaquidheen'
        }


# Factory function
def get_pdf_renderer(prefer_weasyprint=True):
    """Get compatible HTML-to-PDF renderer - template-only approach"""
    return HTMLOnlyPDFRenderer(prefer_weasyprint=prefer_weasyprint)


# Utility functions
def get_available_renderers():
    """Get information about available HTML-to-PDF renderers"""
    return {
        'weasyprint': {
            'available': WEASYPRINT_AVAILABLE,
            'type': 'HTML_TO_PDF_PREMIUM',
            'error': WEASYPRINT_ERROR if not WEASYPRINT_AVAILABLE else None,
            'quality': 'HIGH'
        },
        'xhtml2pdf': {
            'available': XHTML2PDF_AVAILABLE,
            'type': 'HTML_TO_PDF_COMPATIBLE',
            'error': None if XHTML2PDF_AVAILABLE else "Not installed",
            'quality': 'MEDIUM'
        },
        'status': 'TEMPLATE_ONLY_MODE',
        'last_updated': '2025-08-31 06:53:32 UTC',
        'updated_by': 'Thaquidheen'
    }