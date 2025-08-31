# quotation_pdf/pdf_renderer.py (Improved with better error handling)

import os
import logging
from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse
from datetime import datetime
import sys
import re

logger = logging.getLogger('quotation_pdf')

# Try importing WeasyPrint with proper error handling
WEASYPRINT_AVAILABLE = False
WEASYPRINT_ERROR = None

try:
    if sys.platform.startswith('win'):
        logger.warning("Running on Windows - WeasyPrint may require GTK+ libraries")
    
    import weasyprint
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint successfully imported")
except ImportError as e:
    WEASYPRINT_ERROR = str(e)
    logger.warning(f"WeasyPrint not available: {e}")
except OSError as e:
    WEASYPRINT_ERROR = str(e)
    logger.warning(f"WeasyPrint dependencies not available: {e}")

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
        """Render HTML content to PDF using WeasyPrint"""
        try:
            logger.info("Starting PDF generation with WeasyPrint")
            
            stylesheets = []
            if css_files:
                for css_file in css_files:
                    if os.path.exists(css_file):
                        stylesheets.append(self.weasyprint.CSS(filename=css_file))
                        logger.info(f"Loaded CSS file: {css_file}")
            
            config = self._get_weasyprint_config()
            
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
        return {'font_config': font_config}


class XHTMLToPDFRenderer:
    """PDF renderer using xhtml2pdf with improved error handling"""
    
    def __init__(self):
        if not XHTML2PDF_AVAILABLE:
            raise PDFGenerationError("xhtml2pdf is not available")
    
    def render_pdf(self, html_content, css_files=None, base_url=None):
        """Render HTML content to PDF using xhtml2pdf with better error handling"""
        try:
            logger.info("Starting PDF generation with xhtml2pdf")
            
            # Clean HTML content for xhtml2pdf compatibility
            cleaned_html = self._clean_html_for_xhtml2pdf(html_content)
            
            # Embed CSS in HTML if provided
            if css_files:
                css_content = ""
                for css_file in css_files:
                    if os.path.exists(css_file):
                        with open(css_file, 'r', encoding='utf-8') as f:
                            css_content += f.read()
                        logger.info(f"Loaded CSS file: {css_file}")
                
                # Clean CSS for xhtml2pdf
                css_content = self._clean_css_for_xhtml2pdf(css_content)
                
                if css_content:
                    cleaned_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <style type="text/css">
                        {css_content}
                        </style>
                    </head>
                    <body>
                    {cleaned_html}
                    </body>
                    </html>
                    """
            
            # Generate PDF with error handling
            result = BytesIO()
            
            # Use CreatePDF with better error handling
            pdf_status = pisa.CreatePDF(
                cleaned_html,
                dest=result,
                encoding='utf-8',
                show_error_as_pdf=True  # Show errors in PDF instead of crashing
            )
            
            if pdf_status.err:
                logger.warning(f"xhtml2pdf reported errors but continued: {pdf_status.err}")
                # Don't fail completely, just log the warning
            
            pdf_bytes = result.getvalue()
            result.close()
            
            if len(pdf_bytes) == 0:
                raise PDFGenerationError("xhtml2pdf generated empty PDF")
            
            logger.info(f"PDF generated successfully with xhtml2pdf, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"xhtml2pdf PDF generation failed: {str(e)}")
            raise PDFGenerationError(f"xhtml2pdf failed: {str(e)}")
    
    def _clean_html_for_xhtml2pdf(self, html_content):
        """Clean HTML to make it more compatible with xhtml2pdf"""
        # Remove problematic HTML5 elements and attributes
        html_content = re.sub(r'<(section|article|header|footer|nav|aside)', r'<div', html_content)
        html_content = re.sub(r'</(section|article|header|footer|nav|aside)>', r'</div>', html_content)
        
        # Remove data attributes that might cause issues
        html_content = re.sub(r'\s+data-[^=]*="[^"]*"', '', html_content)
        
        # Remove CSS Grid and Flexbox properties that xhtml2pdf doesn't support
        html_content = re.sub(r'display:\s*grid[^;]*;?', '', html_content)
        html_content = re.sub(r'display:\s*flex[^;]*;?', '', html_content)
        html_content = re.sub(r'grid-[^:]*:[^;]*;?', '', html_content)
        html_content = re.sub(r'flex-[^:]*:[^;]*;?', '', html_content)
        
        return html_content
    
    def _clean_css_for_xhtml2pdf(self, css_content):
        """Clean CSS to make it more compatible with xhtml2pdf"""
        # Remove CSS Grid and Flexbox
        css_content = re.sub(r'display:\s*(grid|flex)[^;]*;?', 'display: block;', css_content)
        css_content = re.sub(r'grid-[^:]*:[^;]*;?', '', css_content)
        css_content = re.sub(r'flex-[^:]*:[^;]*;?', '', css_content)
        
        # Remove modern CSS that xhtml2pdf doesn't support
        css_content = re.sub(r'transform:[^;]*;?', '', css_content)
        css_content = re.sub(r'box-shadow:[^;]*;?', '', css_content)
        css_content = re.sub(r'border-radius:[^;]*;?', '', css_content)
        
        # Remove CSS variables
        css_content = re.sub(r'--[^:]*:[^;]*;?', '', css_content)
        css_content = re.sub(r'var\([^)]*\)', '0', css_content)
        
        return css_content


class ReportLabRenderer:
    """Enhanced ReportLab renderer with actual project data"""
    
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
    
    def render_pdf(self, html_content, css_files=None, base_url=None, pdf_data=None):
        """Enhanced ReportLab PDF generation with project data"""
        logger.info("Starting PDF generation with ReportLab")
        
        buffer = BytesIO()
        doc = self.SimpleDocTemplate(buffer, pagesize=self.A4)
        styles = self.getSampleStyleSheet()
        story = []
        
        # Custom styles
        styles.add(self.ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=20,
            spaceAfter=20,
            textColor=self.colors.darkblue,
            alignment=1  # Center
        ))
        
        styles.add(self.ParagraphStyle(
            name='CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=self.colors.darkblue
        ))
        
        # Header
        title = self.Paragraph("Kitchen Quotation", styles['CustomTitle'])
        story.append(title)
        story.append(self.Spacer(1, 20))
        
        # Add project data if available
        if pdf_data:
            project_info = pdf_data.get('project_info', {})
            customer_info = pdf_data.get('customer_info', {})
            calculations = pdf_data.get('calculations', {})
            
            # Customer details
            if customer_info.get('name'):
                customer_text = f"""
                <b>Customer:</b> {customer_info.get('name', 'Unknown')}<br/>
                <b>Project:</b> {project_info.get('quotation_number', 'N/A')}<br/>
                <b>Date:</b> {project_info.get('quotation_date', datetime.now().strftime('%d %B %Y'))}<br/>
                <b>Brand:</b> {project_info.get('brand', 'Speisekamer')}
                """
                customer_para = self.Paragraph(customer_text, styles['Normal'])
                story.append(customer_para)
                story.append(self.Spacer(1, 20))
            
            # Pricing summary
            if calculations:
                pricing_heading = self.Paragraph("Pricing Summary", styles['CustomHeading'])
                story.append(pricing_heading)
                
                pricing_data = [
                    ['Description', 'Amount'],
                    ['Line Items Total', calculations.get('formatted', {}).get('line_items_total', '₹0.00')],
                    ['Accessories Total', calculations.get('formatted', {}).get('accessories_total', '₹0.00')],
                    ['Lighting Total', calculations.get('formatted', {}).get('lighting_total', '₹0.00')],
                    ['Discount', f"-{calculations.get('formatted', {}).get('discount_amount', '₹0.00')}"],
                    ['Final Total', calculations.get('formatted', {}).get('final_total', '₹0.00')]
                ]
                
                pricing_table = self.Table(pricing_data, colWidths=[3*self.inch, 2*self.inch])
                pricing_table.setStyle(self.TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), self.colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), self.colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, self.colors.black),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, -1), (-1, -1), self.colors.lightgrey),
                ]))
                story.append(pricing_table)
                story.append(self.Spacer(1, 20))
        
        # Footer note
        footer_text = f"""
        <i>Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}</i><br/>
        <b>Note:</b> This PDF was generated using ReportLab. 
        For enhanced formatting, please install WeasyPrint or ensure xhtml2pdf works properly.
        """
        footer_para = self.Paragraph(footer_text, styles['Normal'])
        story.append(self.Spacer(1, 30))
        story.append(footer_para)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"PDF generated successfully with ReportLab, size: {len(pdf_bytes)} bytes")
        return pdf_bytes


class PDFRendererProxy:
    """Enhanced proxy with better fallback logic"""
    
    def __init__(self, prefer_weasyprint=True):
        self.renderer = None
        self.renderer_name = None
        self.attempted_renderers = []
        
        # Try renderers in order
        if prefer_weasyprint and WEASYPRINT_AVAILABLE:
            try:
                self.renderer = WeasyPrintRenderer()
                self.renderer_name = "WeasyPrint"
                logger.info("Using WeasyPrint renderer")
                return
            except Exception as e:
                self.attempted_renderers.append(f"WeasyPrint: {str(e)}")
                logger.warning(f"WeasyPrint initialization failed: {e}")
        
        # Try ReportLab first as it's most reliable
        if REPORTLAB_AVAILABLE:
            try:
                self.renderer = ReportLabRenderer()
                self.renderer_name = "ReportLab"
                logger.info("Using ReportLab renderer (reliable fallback)")
                return
            except Exception as e:
                self.attempted_renderers.append(f"ReportLab: {str(e)}")
                logger.warning(f"ReportLab initialization failed: {e}")
        
        # Finally try xhtml2pdf
        if XHTML2PDF_AVAILABLE:
            try:
                self.renderer = XHTMLToPDFRenderer()
                self.renderer_name = "xhtml2pdf"
                logger.info("Using xhtml2pdf renderer")
                return
            except Exception as e:
                self.attempted_renderers.append(f"xhtml2pdf: {str(e)}")
                logger.warning(f"xhtml2pdf initialization failed: {e}")
        
        # No renderer available
        error_msg = f"No PDF rendering libraries available. Attempted: {'; '.join(self.attempted_renderers)}"
        raise PDFGenerationError(error_msg)
    
    def render_pdf(self, html_content, css_files=None, base_url=None, pdf_data=None):
        """Render PDF with enhanced error handling"""
        if not self.renderer:
            raise PDFGenerationError("No PDF renderer available")
        
        logger.info(f"Rendering PDF with {self.renderer_name}")
        
        try:
            # ReportLab renderer accepts pdf_data parameter
            if self.renderer_name == "ReportLab":
                return self.renderer.render_pdf(html_content, css_files, base_url, pdf_data)
            else:
                return self.renderer.render_pdf(html_content, css_files, base_url)
                
        except Exception as e:
            logger.error(f"Primary renderer {self.renderer_name} failed: {str(e)}")
            
            # Try fallback to ReportLab if we weren't already using it
            if self.renderer_name != "ReportLab" and REPORTLAB_AVAILABLE:
                logger.info("Attempting fallback to ReportLab")
                try:
                    fallback_renderer = ReportLabRenderer()
                    return fallback_renderer.render_pdf(html_content, css_files, base_url, pdf_data)
                except Exception as fallback_error:
                    logger.error(f"Fallback renderer also failed: {str(fallback_error)}")
            
            raise PDFGenerationError(f"All renderers failed. Primary: {str(e)}")
    
    def get_renderer_info(self):
        """Get information about the active renderer"""
        return {
            'name': self.renderer_name,
            'weasyprint_available': WEASYPRINT_AVAILABLE,
            'xhtml2pdf_available': XHTML2PDF_AVAILABLE,
            'reportlab_available': REPORTLAB_AVAILABLE,
            'attempted_renderers': self.attempted_renderers,
            'weasyprint_error': WEASYPRINT_ERROR
        }


# Factory function
def get_pdf_renderer(prefer_weasyprint=True):
    """Get the best available PDF renderer"""
    return PDFRendererProxy(prefer_weasyprint=prefer_weasyprint)


# Utility functions
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