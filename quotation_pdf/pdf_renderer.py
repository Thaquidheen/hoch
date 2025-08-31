# quotation_pdf/pdf_renderer.py

import os
import logging
from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse
from datetime import datetime
import sys

logger = logging.getLogger('quotation_pdf')

# Try importing WeasyPrint with proper error handling
WEASYPRINT_AVAILABLE = False
WEASYPRINT_ERROR = None

try:
    # Check if we're on Windows and warn about potential issues
    if sys.platform.startswith('win'):
        logger.warning("Running on Windows - WeasyPrint may require GTK+ libraries")
    
    import weasyprint
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint successfully imported")
except ImportError as e:
    WEASYPRINT_ERROR = str(e)
    logger.warning(f"WeasyPrint not available: {e}")
except OSError as e:
    # This catches the gobject-2.0-0 error on Windows
    WEASYPRINT_ERROR = str(e)
    logger.warning(f"WeasyPrint dependencies not available: {e}")
    if sys.platform.startswith('win'):
        logger.info("For Windows users: Consider using xhtml2pdf or ReportLab as alternatives")

# Try importing ReportLab as fallback
REPORTLAB_AVAILABLE = False
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
    logger.info("ReportLab available as PDF fallback")
except ImportError as e:
    logger.warning(f"ReportLab not available: {e}")

# Try importing xhtml2pdf as another fallback
XHTML2PDF_AVAILABLE = False
try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
    logger.info("xhtml2pdf available as PDF fallback")
except ImportError as e:
    logger.warning(f"xhtml2pdf not available: {e}")


class PDFGenerationError(Exception):
    """Custom exception for PDF generation errors"""
    pass


class WeasyPrintRenderer:
    """Handle PDF generation with WeasyPrint"""
    
    def __init__(self):
        if not WEASYPRINT_AVAILABLE:
            raise PDFGenerationError(f"WeasyPrint is not available: {WEASYPRINT_ERROR}")
        self.weasyprint = weasyprint
        
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
        try:
            logger.info("Starting PDF generation with WeasyPrint")
            
            # Prepare CSS stylesheets
            stylesheets = []
            if css_files:
                for css_file in css_files:
                    if os.path.exists(css_file):
                        stylesheets.append(self.weasyprint.CSS(filename=css_file))
                        logger.info(f"Loaded CSS file: {css_file}")
                    else:
                        logger.warning(f"CSS file not found: {css_file}")
            
            # Configure WeasyPrint
            config = self._get_weasyprint_config()
            
            # Generate PDF
            html_doc = self.weasyprint.HTML(
                string=html_content,
                base_url=base_url,
                encoding='utf-8'
            )
            
            pdf_bytes = html_doc.write_pdf(
                stylesheets=stylesheets,
                font_config=config['font_config'],
                optimize_size=('fonts', 'images')
            )
            
            logger.info(f"PDF generated successfully with WeasyPrint, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"WeasyPrint PDF generation failed: {str(e)}")
            raise PDFGenerationError(f"WeasyPrint failed: {str(e)}")
    
    def _get_weasyprint_config(self):
        """Get WeasyPrint configuration"""
        font_config = self.weasyprint.fonts.FontConfiguration()
        
        # Add custom font paths if configured
        font_paths = getattr(settings, 'WEASYPRINT_FONT_PATHS', [])
        for font_path in font_paths:
            if os.path.exists(font_path):
                font_config.add_font_directory(font_path)
                logger.info(f"Added font directory: {font_path}")
        
        return {
            'font_config': font_config,
        }


class XHTMLToPDFRenderer:
    """PDF renderer using xhtml2pdf"""
    
    def __init__(self):
        if not XHTML2PDF_AVAILABLE:
            raise PDFGenerationError("xhtml2pdf is not available")
    
    def render_pdf(self, html_content, css_files=None, base_url=None):
        """
        Render HTML content to PDF using xhtml2pdf
        
        Args:
            html_content (str): HTML content to render
            css_files (list): List of CSS file paths (embedded in HTML)
            base_url (str): Base URL for resolving relative paths
            
        Returns:
            bytes: PDF content as bytes
        """
        try:
            logger.info("Starting PDF generation with xhtml2pdf")
            
            # Embed CSS in HTML if provided
            if css_files:
                css_content = ""
                for css_file in css_files:
                    if os.path.exists(css_file):
                        with open(css_file, 'r', encoding='utf-8') as f:
                            css_content += f.read()
                        logger.info(f"Loaded CSS file: {css_file}")
                
                if css_content:
                    # Embed CSS in HTML
                    html_content = f"""
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <style type="text/css">
                        {css_content}
                        </style>
                    </head>
                    <body>
                    {html_content}
                    </body>
                    </html>
                    """
            
            # Generate PDF
            result = BytesIO()
            pdf_status = pisa.CreatePDF(
                html_content,
                dest=result,
                encoding='utf-8'
            )
            
            if pdf_status.err:
                raise PDFGenerationError(f"xhtml2pdf generation failed with errors")
            
            pdf_bytes = result.getvalue()
            result.close()
            
            logger.info(f"PDF generated successfully with xhtml2pdf, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"xhtml2pdf PDF generation failed: {str(e)}")
            raise PDFGenerationError(f"xhtml2pdf failed: {str(e)}")


class ReportLabRenderer:
    """Fallback PDF renderer using ReportLab"""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise PDFGenerationError("ReportLab is not available")
        
        self.canvas = canvas
        self.A4 = A4
        self.SimpleDocTemplate = SimpleDocTemplate
        self.Paragraph = Paragraph
        self.Spacer = Spacer
        self.Table = Table
        self.TableStyle = TableStyle
        self.getSampleStyleSheet = getSampleStyleSheet
        self.ParagraphStyle = ParagraphStyle
        self.colors = colors
        self.inch = inch
    
    def render_pdf(self, html_content, css_files=None, base_url=None):
        """
        Render basic PDF using ReportLab (simplified version)
        This doesn't parse HTML but creates a structured PDF
        """
        logger.info("Starting PDF generation with ReportLab (simplified)")
        
        buffer = BytesIO()
        doc = self.SimpleDocTemplate(buffer, pagesize=self.A4)
        styles = self.getSampleStyleSheet()
        story = []
        
        # Add custom styles
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=20,
            textColor=self.colors.darkblue
        ))
        
        styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=self.colors.darkblue
        ))
        
        # Title
        title = self.Paragraph("Kitchen Quotation", styles['CustomTitle'])
        story.append(title)
        story.append(self.Spacer(1, 20))
        
        # Add a simple message about the PDF generation method
        message = self.Paragraph(
            "This PDF was generated using ReportLab as a fallback. "
            "For full HTML rendering capabilities, please install WeasyPrint with its dependencies.",
            styles['Normal']
        )
        story.append(message)
        story.append(self.Spacer(1, 20))
        
        # Basic project information (you can extract this from HTML or pass separately)
        info_text = f"""
        <b>Generated:</b> {datetime.now().strftime('%d %B %Y at %H:%M')}<br/>
        <b>Status:</b> PDF Generated Successfully<br/>
        <b>Method:</b> ReportLab Fallback Renderer
        """
        
        info_para = self.Paragraph(info_text, styles['Normal'])
        story.append(info_para)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"PDF generated successfully with ReportLab, size: {len(pdf_bytes)} bytes")
        return pdf_bytes


class PDFRendererProxy:
    """Proxy class that chooses the best available PDF renderer"""
    
    def __init__(self, prefer_weasyprint=True):
        self.renderer = None
        self.renderer_name = None
        
        # Try to initialize the best available renderer
        if prefer_weasyprint and WEASYPRINT_AVAILABLE:
            try:
                self.renderer = WeasyPrintRenderer()
                self.renderer_name = "WeasyPrint"
                logger.info("Using WeasyPrint renderer")
            except Exception as e:
                logger.warning(f"WeasyPrint initialization failed: {e}")
        
        # Fallback to xhtml2pdf
        if not self.renderer and XHTML2PDF_AVAILABLE:
            try:
                self.renderer = XHTMLToPDFRenderer()
                self.renderer_name = "xhtml2pdf"
                logger.info("Using xhtml2pdf renderer")
            except Exception as e:
                logger.warning(f"xhtml2pdf initialization failed: {e}")
        
        # Final fallback to ReportLab
        if not self.renderer and REPORTLAB_AVAILABLE:
            try:
                self.renderer = ReportLabRenderer()
                self.renderer_name = "ReportLab"
                logger.info("Using ReportLab renderer (simplified)")
            except Exception as e:
                logger.warning(f"ReportLab initialization failed: {e}")
        
        if not self.renderer:
            available_libs = []
            if WEASYPRINT_AVAILABLE:
                available_libs.append("WeasyPrint")
            if XHTML2PDF_AVAILABLE:
                available_libs.append("xhtml2pdf")
            if REPORTLAB_AVAILABLE:
                available_libs.append("ReportLab")
            
            error_msg = f"No PDF rendering libraries available. Install one of: {', '.join(['WeasyPrint', 'xhtml2pdf', 'ReportLab'])}"
            if available_libs:
                error_msg += f" (Found but failed to initialize: {', '.join(available_libs)})"
            
            raise PDFGenerationError(error_msg)
    
    def render_pdf(self, html_content, css_files=None, base_url=None):
        """Render PDF using the available renderer"""
        if not self.renderer:
            raise PDFGenerationError("No PDF renderer available")
        
        logger.info(f"Rendering PDF with {self.renderer_name}")
        return self.renderer.render_pdf(html_content, css_files, base_url)
    
    def get_renderer_info(self):
        """Get information about the active renderer"""
        return {
            'name': self.renderer_name,
            'weasyprint_available': WEASYPRINT_AVAILABLE,
            'xhtml2pdf_available': XHTML2PDF_AVAILABLE,
            'reportlab_available': REPORTLAB_AVAILABLE,
            'weasyprint_error': WEASYPRINT_ERROR
        }


# Factory function to get appropriate renderer
def get_pdf_renderer(prefer_weasyprint=True):
    """
    Get the best available PDF renderer
    
    Args:
        prefer_weasyprint (bool): Prefer WeasyPrint if available
        
    Returns:
        PDFRendererProxy: Configured PDF renderer
    """
    return PDFRendererProxy(prefer_weasyprint=prefer_weasyprint)


# Utility function to check available renderers
def get_available_renderers():
    """Get information about available PDF renderers"""
    return {
        'weasyprint': {
            'available': WEASYPRINT_AVAILABLE,
            'error': WEASYPRINT_ERROR if not WEASYPRINT_AVAILABLE else None
        },
        'xhtml2pdf': {
            'available': XHTML2PDF_AVAILABLE,
            'error': None if XHTML2PDF_AVAILABLE else "Not installed"
        },
        'reportlab': {
            'available': REPORTLAB_AVAILABLE,
            'error': None if REPORTLAB_AVAILABLE else "Not installed"
        }
    }


# Helper function for quick installation instructions
def get_installation_instructions():
    """Get installation instructions for PDF libraries"""
    instructions = {
        'windows': {
            'weasyprint': [
                "Option 1: Install GTK+ for Windows from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer",
                "Then: pip install weasyprint",
                "",
                "Option 2 (easier): Use alternative renderers:",
                "pip install xhtml2pdf reportlab"
            ],
            'xhtml2pdf': ["pip install xhtml2pdf"],
            'reportlab': ["pip install reportlab"]
        },
        'linux': {
            'weasyprint': [
                "sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info",
                "pip install weasyprint"
            ],
            'xhtml2pdf': ["pip install xhtml2pdf"],
            'reportlab': ["pip install reportlab"]
        },
        'macos': {
            'weasyprint': [
                "brew install cairo pango gdk-pixbuf libffi",
                "pip install weasyprint"
            ],
            'xhtml2pdf': ["pip install xhtml2pdf"],
            'reportlab': ["pip install reportlab"]
        }
    }
    
    platform = 'windows' if sys.platform.startswith('win') else ('darwin' if sys.platform == 'darwin' else 'linux')
    return instructions.get(platform, instructions['linux'])