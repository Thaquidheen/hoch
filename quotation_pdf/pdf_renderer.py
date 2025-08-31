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
    """Fixed ReportLab renderer without comparison errors"""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise PDFGenerationError("ReportLab is not available")
    
    def render_pdf(self, html_content, css_files=None, base_url=None, pdf_data=None):
        """Generate comprehensive professional PDF with fixed comparisons"""
        logger.info("Starting comprehensive PDF generation with ReportLab")
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from django.utils import timezone
        from datetime import timedelta
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               topMargin=0.75*inch, bottomMargin=0.75*inch,
                               leftMargin=0.75*inch, rightMargin=0.75*inch)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Enhanced styles
        styles.add(ParagraphStyle(
            name='CustomTitle', parent=styles['Title'], fontSize=24, spaceAfter=20,
            textColor=colors.darkblue, alignment=1, fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='SectionHeading', parent=styles['Heading2'], fontSize=16, spaceAfter=12,
            spaceBefore=20, textColor=colors.darkblue, fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='SubHeading', parent=styles['Heading3'], fontSize=12, spaceAfter=8,
            spaceBefore=15, textColor=colors.darkred, fontName='Helvetica-Bold'
        ))
        
        # Current time
        current_utc = timezone.now()
        ist_time = current_utc + timedelta(hours=5, minutes=30)
        
        if not pdf_data:
            logger.warning("No PDF data provided, generating basic PDF")
            story.extend(self._generate_basic_pdf(ist_time, current_utc, styles))
        else:
            try:
                # PAGE 1: Header and Project Overview
                story.extend(self._generate_header_section(pdf_data, styles, ist_time, current_utc))
                
                # PAGE 2: Cabinet Breakdown
                cabinet_breakdown = pdf_data.get('cabinet_breakdown', [])
                if cabinet_breakdown and len(cabinet_breakdown) > 0:
                    story.append(PageBreak())
                    story.extend(self._generate_cabinet_section(cabinet_breakdown, styles))
                
                # PAGE 3: Accessories & Lighting
                accessories = pdf_data.get('accessories_detailed', [])
                lighting = pdf_data.get('lighting_specifications', {})
                if (accessories and len(accessories) > 0) or (lighting and len(lighting) > 0):
                    story.append(PageBreak())
                    story.extend(self._generate_accessories_lighting_section(accessories, lighting, styles))
                
                # PAGE 4: Timeline & Terms
                story.append(PageBreak())
                story.extend(self._generate_timeline_terms_section(pdf_data, styles))
                
                # PAGE 5: Warranty & Contact
                story.append(PageBreak())
                story.extend(self._generate_warranty_contact_section(pdf_data, styles, ist_time, current_utc))
                
            except Exception as section_error:
                logger.error(f"Error generating PDF sections: {section_error}")
                # Fallback to basic PDF if sections fail
                story = []
                story.extend(self._generate_basic_pdf(ist_time, current_utc, styles))
        
        # Build PDF
        try:
            doc.build(story)
            buffer.seek(0)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            logger.info(f"Comprehensive PDF generated successfully, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as build_error:
            logger.error(f"Error building PDF: {build_error}")
            buffer.close()
            raise PDFGenerationError(f"Failed to build PDF: {build_error}")

    def _generate_header_section(self, pdf_data, styles, ist_time, current_utc):
        """Generate comprehensive header and overview section with safe data access"""
        story = []
        
        # Safe data extraction with fallbacks
        project_info = pdf_data.get('project_info', {})
        customer_info = pdf_data.get('customer_info', {})
        calculations = pdf_data.get('calculations', {})
        brand_info = pdf_data.get('brand_information', {})
        
        # Title
        brand_name = brand_info.get('name', 'Speisekamer') if isinstance(brand_info, dict) else 'Speisekamer'
        story.append(Paragraph("Kitchen Quotation", styles['CustomTitle']))
        story.append(Paragraph(f"by {brand_name}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Project & Customer Information Table
        info_data = [
            ['Project Information', 'Customer Information'],
            [
                f"Quotation No: {project_info.get('quotation_number', 'N/A')}",
                f"Name: {customer_info.get('name', 'Unknown')}"
            ],
            [
                f"Date: {project_info.get('quotation_date', 'N/A')}",
                f"Email: {customer_info.get('email', 'N/A')}"
            ],
            [
                f"Time: {project_info.get('quotation_time', 'N/A')} {project_info.get('quotation_timezone', 'IST')}",
                f"Phone: {customer_info.get('phone', 'N/A')}"
            ],
            [
                f"Valid Until: {project_info.get('quotation_valid_until', 'N/A')}",
                f"Budget Tier: {project_info.get('budget_tier', 'Standard').title()}"
            ],
            [
                f"Generated by: {project_info.get('generated_by', 'System')}",
                f"Project Status: {project_info.get('status', 'DRAFT')}"
            ]
        ]
        
        info_table = Table(info_data, colWidths=[3*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 30))
        
        # Pricing Summary with safe access
        if isinstance(calculations, dict) and calculations:
            story.append(Paragraph("Pricing Summary", styles['SectionHeading']))
            
            formatted_calcs = calculations.get('formatted', {})
            pricing_data = [
                ['Description', 'Amount (₹)'],
                ['Cabinet Items Total', formatted_calcs.get('line_items_total', '₹0.00')],
                ['Doors Total', formatted_calcs.get('doors_total', '₹0.00')],
                ['Accessories Total', formatted_calcs.get('accessories_total', '₹0.00')],
                ['Lighting Total', formatted_calcs.get('lighting_total', '₹0.00')],
                ['Subtotal', formatted_calcs.get('subtotal', '₹0.00')],
            ]
            
            # Add discount if present
            discount_amount = calculations.get('discount_amount', {})
            if isinstance(discount_amount, dict) and discount_amount.get('raw_amount', 0) > 0:
                discount_pct = calculations.get('discount_percentage', 0)
                discount_text = f"Discount Applied ({discount_pct}%)" if discount_pct else "Discount Applied"
                pricing_data.append([discount_text, f"-{discount_amount.get('formatted', '₹0.00')}"])
            
            pricing_data.extend([
                ['GST (18%)', formatted_calcs.get('gst_amount', '₹0.00')],
                ['Final Total', formatted_calcs.get('final_total', '₹0.00')]
            ])
            
            pricing_table = Table(pricing_data, colWidths=[4*inch, 2*inch])
            pricing_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, -2), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(pricing_table)
        
        # Customer Notes
        customer_notes = pdf_data.get('customer_notes', {})
        if isinstance(customer_notes, dict) and any(customer_notes.values()):
            story.append(Spacer(1, 20))
            story.append(Paragraph("Special Instructions", styles['SectionHeading']))
            
            for note_type, note_content in customer_notes.items():
                if note_content and str(note_content).strip():
                    note_title = str(note_type).replace('_', ' ').title()
                    story.append(Paragraph(f"<b>{note_title}:</b> {note_content}", styles['Normal']))
                    story.append(Spacer(1, 8))
        
        return story

    def _generate_cabinet_section(self, cabinet_breakdown, styles):
        """Generate detailed cabinet breakdown section with safe data handling"""
        story = []
        
        story.append(Paragraph("Cabinet Breakdown & Specifications", styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        if not cabinet_breakdown or len(cabinet_breakdown) == 0:
            story.append(Paragraph("No detailed cabinet information available.", styles['Normal']))
            return story
        
        # 🔧 FIX: Safe grouping without comparison issues
        categories = {}
        for cabinet in cabinet_breakdown:
            if not isinstance(cabinet, dict):
                continue
                
            category = str(cabinet.get('category', 'General'))  # Convert to string
            if category not in categories:
                categories[category] = []
            categories[category].append(cabinet)
        
        # 🔧 FIX: Sort categories by name (string comparison)
        for category in sorted(categories.keys()):
            cabinets = categories[category]
            
            story.append(Paragraph(f"{category} Cabinets", styles['SectionHeading']))
            
            # Create table for this category
            cabinet_data = [['Item', 'Specifications', 'Qty', 'Price (₹)']]
            
            for cabinet in cabinets:
                if not isinstance(cabinet, dict):
                    continue
                    
                specs = cabinet.get('specifications', {})
                dimensions = cabinet.get('dimensions', {})
                materials = cabinet.get('materials', {})
                
                # Safe data extraction
                width = dimensions.get('width', 0) if isinstance(dimensions, dict) else 0
                height = dimensions.get('height', 0) if isinstance(dimensions, dict) else 0
                depth = dimensions.get('depth', 0) if isinstance(dimensions, dict) else 0
                
                cabinet_material = materials.get('cabinet_material', 'N/A') if isinstance(materials, dict) else 'N/A'
                door_material = materials.get('door_material', 'N/A') if isinstance(materials, dict) else 'N/A'
                
                quantity = specs.get('quantity', 1) if isinstance(specs, dict) else 1
                total_price = specs.get('line_total_before_tax', 0) if isinstance(specs, dict) else 0
                
                spec_text = f"""
                <b>Brand:</b> {cabinet.get('brand', 'N/A')}<br/>
                <b>Cabinet Material:</b> {cabinet_material}<br/>
                <b>Door Material:</b> {door_material}<br/>
                <b>Dimensions:</b> {width}×{height}×{depth} mm<br/>
                <b>Scope:</b> {cabinet.get('scope', 'N/A')}
                """
                
                cabinet_data.append([
                    str(cabinet.get('name', 'Unknown')),
                    spec_text,
                    str(quantity),
                    f"₹{total_price:,.2f}"
                ])
            
            if len(cabinet_data) > 1:  # Has data beyond header
                cabinet_table = Table(cabinet_data, colWidths=[1.5*inch, 3*inch, 0.8*inch, 1.2*inch])
                cabinet_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                    ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(cabinet_table)
                story.append(Spacer(1, 15))
        
        return story

    def _generate_accessories_lighting_section(self, accessories, lighting, styles):
        """Generate accessories and lighting section with safe data handling"""
        story = []
        
        story.append(Paragraph("Accessories & Lighting Systems", styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Accessories Section
        if accessories and len(accessories) > 0:
            story.append(Paragraph("Detailed Accessories List", styles['SectionHeading']))
            
            acc_data = [['Accessory', 'Cabinet', 'Brand', 'Qty', 'Price (₹)']]
            for acc in accessories:
                if not isinstance(acc, dict):
                    continue
                    
                specs = acc.get('specifications', {})
                quantity = specs.get('quantity', 1) if isinstance(specs, dict) else 1
                total_price = specs.get('total_price', 0) if isinstance(specs, dict) else 0
                
                acc_data.append([
                    str(acc.get('name', 'Unknown')),
                    str(acc.get('line_item_cabinet', 'N/A')),
                    str(acc.get('brand', 'Generic')),
                    str(quantity),
                    f"₹{total_price:,.2f}"
                ])
            
            if len(acc_data) > 1:  # Has data beyond header
                acc_table = Table(acc_data, colWidths=[2*inch, 1.5*inch, 1*inch, 0.8*inch, 1.2*inch])
                acc_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkorange),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                    ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(acc_table)
                story.append(Spacer(1, 20))
        
        # Lighting Section
        if isinstance(lighting, dict) and lighting:
            story.append(Paragraph("Lighting Specifications", styles['SectionHeading']))
            
            overview = lighting.get('overview', {})
            if isinstance(overview, dict):
                overview_text = f"""
                <b>Total Cost:</b> ₹{overview.get('total_cost', 0):,.2f}<br/>
                <b>Power Consumption:</b> {overview.get('estimated_power_consumption', 'N/A')}<br/>
                <b>Zones:</b> {', '.join(overview.get('lighting_zones', []))}
                """
                story.append(Paragraph(overview_text, styles['Normal']))
                story.append(Spacer(1, 15))
            
            # Lighting breakdown
            breakdown = lighting.get('lighting_breakdown', [])
            if breakdown and len(breakdown) > 0:
                lighting_data = [['Material', 'Type', 'Dimensions', 'Total Cost (₹)']]
                
                for item in breakdown:
                    if not isinstance(item, dict):
                        continue
                        
                    dimensions = item.get('dimensions', {})
                    cost_breakdown = item.get('cost_breakdown', {})
                    
                    if isinstance(dimensions, dict) and isinstance(cost_breakdown, dict):
                        dim_text = f"""
                        Wall: {dimensions.get('wall_cabinet_width_mm', 0)}mm<br/>
                        Base: {dimensions.get('base_cabinet_width_mm', 0)}mm<br/>
                        Count: {dimensions.get('wall_cabinet_count', 0)}
                        """
                        
                        lighting_data.append([
                            str(item.get('material', 'N/A')),
                            str(item.get('cabinet_type', 'All')),
                            dim_text,
                            f"₹{cost_breakdown.get('total_cost', 0):,.2f}"
                        ])
                
                if len(lighting_data) > 1:  # Has data beyond header
                    lighting_table = Table(lighting_data, colWidths=[1.5*inch, 1.5*inch, 2*inch, 1.5*inch])
                    lighting_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.purple),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.lavender),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(lighting_table)
        
        return story

    def _generate_timeline_terms_section(self, pdf_data, styles):
        """Generate timeline and terms section"""
        story = []
        
        timeline = pdf_data.get('installation_timeline', {})
        terms = pdf_data.get('terms_conditions', {})
        
        story.append(Paragraph("Installation Timeline & Terms", styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Installation Timeline
        if isinstance(timeline, dict) and timeline:
            story.append(Paragraph("Project Timeline", styles['SectionHeading']))
            
            phases = timeline.get('project_phases', [])
            if phases and len(phases) > 0:
                phase_data = [['Phase', 'Duration', 'Description']]
                for phase in phases:
                    if isinstance(phase, dict):
                        phase_data.append([
                            str(phase.get('phase', 'Unknown')),
                            str(phase.get('duration', 'TBD')),
                            str(phase.get('description', ''))
                        ])
                
                if len(phase_data) > 1:  # Has data beyond header
                    phase_table = Table(phase_data, colWidths=[1.5*inch, 1*inch, 4*inch])
                    phase_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.lightpink),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(phase_table)
                    story.append(Spacer(1, 15))
            
            total_timeline = timeline.get('total_timeline', 'TBD')
            story.append(Paragraph(f"<b>Total Project Timeline:</b> {total_timeline}", styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Payment Terms
        if isinstance(terms, dict) and terms:
            payment_terms = terms.get('payment_terms', {})
            if isinstance(payment_terms, dict) and payment_terms:
                story.append(Paragraph("Payment Terms", styles['SectionHeading']))
                payment_text = f"""
                <b>Advance Payment:</b> {payment_terms.get('advance_payment', 'TBD')}<br/>
                <b>Progress Payment:</b> {payment_terms.get('progress_payment', 'TBD')}<br/>
                <b>Final Payment:</b> {payment_terms.get('final_payment', 'TBD')}<br/>
                <b>Payment Methods:</b> {', '.join(payment_terms.get('payment_methods', []))}<br/>
                <b>Timeline:</b> {payment_terms.get('payment_timeline', 'As per agreement')}
                """
                story.append(Paragraph(payment_text, styles['Normal']))
                story.append(Spacer(1, 15))
        
        return story

    def _generate_warranty_contact_section(self, pdf_data, styles, ist_time, current_utc):
        """Generate warranty and contact information section"""
        story = []
        
        warranty = pdf_data.get('warranty_information', {})
        brand_info = pdf_data.get('brand_information', {})
        
        story.append(Paragraph("Warranty & Contact Information", styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Warranty Information
        if isinstance(warranty, dict) and warranty:
            story.append(Paragraph("Warranty Coverage", styles['SectionHeading']))
            
            coverage = warranty.get('coverage_summary', {})
            if isinstance(coverage, dict) and coverage:
                warranty_data = [['Component', 'Warranty Period']]
                for component, period in coverage.items():
                    warranty_data.append([
                        str(component).replace('_', ' ').title(),
                        str(period)
                    ])
                
                if len(warranty_data) > 1:  # Has data beyond header
                    warranty_table = Table(warranty_data, colWidths=[3*inch, 2.5*inch])
                    warranty_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    story.append(warranty_table)
                    story.append(Spacer(1, 20))
        
        # Contact Information
        story.append(Paragraph("Contact Information", styles['SectionHeading']))
        
        if isinstance(brand_info, dict):
            contact_info = brand_info.get('contact_info', {})
            brand_name = brand_info.get('name', 'Speisekamer')
        else:
            contact_info = {}
            brand_name = 'Speisekamer'
        
        if isinstance(contact_info, dict):
            contact_text = f"""
            <b>Company:</b> {brand_name}<br/>
            <b>Phone:</b> {contact_info.get('phone', '+91-XXXX-XXXXXX')}<br/>
            <b>Email:</b> {contact_info.get('email', 'info@speisekamer.com')}<br/>
            <b>Website:</b> {contact_info.get('website', 'www.speisekamer.com')}<br/>
            <b>Address:</b> {contact_info.get('address', 'Mumbai, Maharashtra, India')}<br/>
            """
        else:
            contact_text = f"""
            <b>Company:</b> {brand_name}<br/>
            <b>Phone:</b> +91-XXXX-XXXXXX<br/>
            <b>Email:</b> info@speisekamer.com<br/>
            """
        
        story.append(Paragraph(contact_text, styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Footer
        footer_text = f"""
        <b>Generated Information:</b><br/>
        Generated on: {ist_time.strftime('%d %B %Y at %H:%M IST')} by Thaquidheen<br/>
        UTC Time: {current_utc.strftime('%d %B %Y at %H:%M UTC')}<br/>
        Template: Enhanced ReportLab Professional v2.0<br/>
        <br/>
        <i>This quotation is valid for 30 days from the date of generation.</i><br/>
        <b>Thank you for choosing {brand_name}!</b>
        """
        story.append(Paragraph(footer_text, styles['Normal']))
        
        return story

    def _generate_basic_pdf(self, ist_time, current_utc, styles):
        """Generate basic PDF when no data is available"""
        story = []
        
        story.append(Paragraph("Kitchen Quotation", styles['CustomTitle']))
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Generated on: {ist_time.strftime('%d %B %Y at %H:%M IST')}", styles['Normal']))
        story.append(Paragraph(f"UTC Time: {current_utc.strftime('%d %B %Y at %H:%M UTC')}", styles['Normal']))
        story.append(Paragraph("PDF data compilation successful. Content loading in progress...", styles['Normal']))
        
        return story


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