# quotation_pdf/services.py



from decimal import Decimal

from datetime import datetime, timedelta
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from decimal import Decimal
import os
import uuid
import logging


# Import your existing models
from pricing.models import (
    Project, ProjectLineItem, ProjectLineItemAccessory, ProjectTotals,
    ProjectLightingConfiguration, ProjectLightingItem
)
from catalog.models import ProductVariant
from customers.models import Customer
class QuotationPDFDataCompiler:
    """Compile all project data for PDF generation"""
    
    def __init__(self, project_id, customizations=None):
        self.project_id = project_id
        self.customizations = customizations or {}
        try:
            self.project = Project.objects.select_related(
                'customer', 
                'brand'
            ).prefetch_related(
                'lines__cabinet_type',
                'lines__cabinet_material',
                'lines__door_material',
                'lighting_items',
                'image_groups__images'
            ).get(id=project_id)
        except Project.DoesNotExist:
            raise ValueError(f"Project with ID {project_id} not found")
    
    def compile_complete_data(self):
        """Main method to compile all PDF data"""
        try:
            return {
                'project_info': self.get_project_details(),
                'customer_info': self.get_customer_details(),
                'cabinet_items': self.get_cabinet_breakdown(),
                'door_items': self.get_door_breakdown(),
                'accessories': self.get_accessories_with_images(),
                'lighting_items': self.get_lighting_breakdown(),
                'plan_images': self.get_project_plan_images(),
                'calculations': self.get_pricing_breakdown(),
                'customizations': self.customizations,
                'customer_notes': self.get_customer_notes(),
                'metadata': self.get_pdf_metadata()
            }
        except Exception as e:
            raise ValueError(f"Failed to compile preview data: {str(e)}")
    
    def get_project_details(self):
        """Get basic project information"""
        try:
            # FIXED: Get kitchen_types from customer, not project
            customer_kitchen_types = {}
            if hasattr(self.project.customer, 'kitchen_types') and self.project.customer.kitchen_types:
                if isinstance(self.project.customer.kitchen_types, dict):
                    customer_kitchen_types = self.project.customer.kitchen_types
                elif isinstance(self.project.customer.kitchen_types, list):
                    # Convert list to dict format
                    customer_kitchen_types = {kt.get('type', 'Unknown'): kt.get('count', 1) 
                                            for kt in self.project.customer.kitchen_types}
                else:
                    customer_kitchen_types = {'Standard': 1}
            else:
                customer_kitchen_types = {'Standard': 1}
            
            return {
                'id': str(self.project.id),
                'customer_name': self.project.customer.name,
                'project_type': 'Kitchen Quotation',
                'quotation_number': f'KQ-{str(self.project.id)[:8]}',
                'quotation_date': datetime.now().strftime('%d %B %Y'),
                'quotation_valid_until': (datetime.now() + timedelta(days=30)).strftime('%d %B %Y'),
                'brand': self.project.brand.name if self.project.brand else 'Premium Kitchens',
                'budget_tier': getattr(self.project, 'budget_tier', 'STANDARD'),
                'kitchen_types': customer_kitchen_types,  # FIXED: Get from customer
                'notes': getattr(self.project, 'notes', ''),
                'status': getattr(self.project, 'status', 'DRAFT'),
                'scopes': getattr(self.project, 'scopes', {}),
                'margin_pct': getattr(self.project, 'margin_pct', 0),
                'gst_pct': getattr(self.project, 'gst_pct', 18),
                'currency': getattr(self.project, 'currency', 'INR')
            }
        except Exception as e:
            print(f"Error in get_project_details: {e}")
            # Return basic fallback data
            return {
                'id': str(self.project.id),
                'customer_name': self.project.customer.name,
                'project_type': 'Kitchen Quotation',
                'quotation_number': f'KQ-{str(self.project.id)[:8]}',
                'quotation_date': datetime.now().strftime('%d %B %Y'),
                'quotation_valid_until': (datetime.now() + timedelta(days=30)).strftime('%d %B %Y'),
                'brand': 'Premium Kitchens',
                'budget_tier': 'STANDARD',
                'kitchen_types': {'Standard': 1},
                'notes': '',
                'status': 'DRAFT'
            }
    
    def get_customer_details(self):
        """Get customer information"""
        try:
            customer = self.project.customer
            return {
                'name': customer.name,
                'email': getattr(customer, 'email', ''),
                'phone': getattr(customer, 'contact_number', ''),
                'location': getattr(customer, 'location', ''),
                'address': getattr(customer, 'address', getattr(customer, 'location', '')),
                'city': getattr(customer, 'city', ''),
                'state': getattr(customer, 'state', ''),
                'pincode': getattr(customer, 'pincode', ''),
            }
        except Exception as e:
            print(f"Error in get_customer_details: {e}")
            return {
                'name': self.project.customer.name,
                'email': '',
                'phone': '',
                'address': '',
                'city': '',
                'state': ''
            }
    
    def get_cabinet_breakdown(self):
        """Get cabinet line items breakdown"""
        try:
            if not self.customizations.get('include_cabinet_details', True):
                return []
            
            line_items = self.project.lines.filter(is_active=True).select_related(
                'cabinet_type', 'cabinet_material', 'door_material'
            )
            
            cabinet_items = []
            for item in line_items:
                cabinet_items.append({
                    'id': item.id,
                    'cabinet_type': item.cabinet_type.name if item.cabinet_type else 'Unknown',
                    'cabinet_material': item.cabinet_material.name if item.cabinet_material else 'Unknown',
                    'quantity': item.qty,
                    'dimensions': f"{item.width_mm} × {item.depth_mm} × {item.height_mm} mm",
                    'width_mm': item.width_mm,
                    'depth_mm': item.depth_mm, 
                    'height_mm': item.height_mm,
                    'scope': getattr(item, 'scope', 'OPEN'),
                    'cabinet_sqft': float(getattr(item, 'computed_cabinet_sqft', 0)),
                    'door_sqft': float(getattr(item, 'computed_door_sqft', 0)),
                    'cabinet_price': float(getattr(item, 'cabinet_material_price', 0)),
                    'door_price': float(getattr(item, 'door_price', 0)),
                    'accessory_charge': float(getattr(item, 'standard_accessory_charge', 0)),
                    'total_price': float(getattr(item, 'total_price', 0)),
                })
            
            return cabinet_items
            
        except Exception as e:
            print(f"Error in get_cabinet_breakdown: {e}")
            return []
    
    def get_door_breakdown(self):
        """Get door-specific breakdown"""
        try:
            if not self.customizations.get('include_door_details', True):
                return []
            
            # Group line items by door material for door breakdown
            line_items = self.project.lines.filter(is_active=True).select_related(
                'door_material'
            )
            
            door_materials = {}
            for item in line_items:
                door_mat = item.door_material.name if item.door_material else 'Unknown'
                if door_mat not in door_materials:
                    door_materials[door_mat] = {
                        'material': door_mat,
                        'total_sqft': 0,
                        'total_price': 0,
                        'items': []
                    }
                
                door_materials[door_mat]['total_sqft'] += float(getattr(item, 'computed_door_sqft', 0))
                door_materials[door_mat]['total_price'] += float(getattr(item, 'door_price', 0))
                door_materials[door_mat]['items'].append(item)
            
            return list(door_materials.values())
            
        except Exception as e:
            print(f"Error in get_door_breakdown: {e}")
            return []
    
    def get_accessories_with_images(self):
        """Get accessories with product images if available"""
        try:
            if not self.customizations.get('include_accessories', True):
                return []
            
            accessories = ProjectLineItemAccessory.objects.filter(
                line_item__project=self.project,
                is_active=True
            ).select_related('product_variant__product__brand')
            
            accessory_items = []
            for acc in accessories:
                accessory_data = {
                    'id': acc.id,
                    'name': acc.product_variant.product.name if acc.product_variant else 'Unknown Accessory',
                    'brand': acc.product_variant.product.brand.name if (acc.product_variant and 
                            acc.product_variant.product.brand) else 'Generic',
                    'quantity': acc.quantity,
                    'unit_price': float(acc.unit_price),
                    'total_price': float(acc.total_price),
                    'material_code': getattr(acc.product_variant, 'material_code', ''),
                    'sku_code': getattr(acc.product_variant, 'sku_code', ''),
                }
                
                # Add image if include_accessory_images is enabled
                if self.customizations.get('include_accessory_images', True):
                    if acc.product_variant and hasattr(acc.product_variant, 'image') and acc.product_variant.image:
                        accessory_data['image_url'] = acc.product_variant.image.url
                    else:
                        accessory_data['image_url'] = None
                
                accessory_items.append(accessory_data)
            
            return accessory_items
            
        except Exception as e:
            print(f"Error in get_accessories_with_images: {e}")
            return []
    
    def get_lighting_breakdown(self):
        """Get lighting items breakdown"""
        try:
            if not self.customizations.get('include_lighting', True):
                return []
            
            lighting_items = self.project.lighting_items.filter(
                is_active=True
            ).select_related('cabinet_material', 'cabinet_type', 'lighting_rule')
            
            lighting_breakdown = []
            for item in lighting_items:
                lighting_breakdown.append({
                    'id': item.id,
                    'cabinet_material': item.cabinet_material.name if item.cabinet_material else 'Unknown',
                    'cabinet_type': item.cabinet_type.name if item.cabinet_type else 'All Types',
                    'wall_cabinet_width_mm': item.wall_cabinet_width_mm,
                    'base_cabinet_width_mm': item.base_cabinet_width_mm,
                    'wall_cabinet_count': item.wall_cabinet_count,
                    'under_cabinet_cost': float(getattr(item, 'under_cabinet_cost', 0)),
                    'nosing_led_cost': float(getattr(item, 'nosing_led_cost', 0)),
                    'spot_lights_cost': float(getattr(item, 'spot_lights_cost', 0)),
                    'total_cost': float(getattr(item, 'total_cost', 0)),
                })
            
            # Get lighting configuration totals
            try:
                lighting_config = self.project.lighting_config
                lighting_total = float(lighting_config.grand_total_lighting_cost)
            except:
                lighting_total = sum(item['total_cost'] for item in lighting_breakdown)
            
            return {
                'items': lighting_breakdown,
                'total_cost': lighting_total,
                'total_formatted': f"₹{lighting_total:,.2f}"
            }
            
        except Exception as e:
            print(f"Error in get_lighting_breakdown: {e}")
            return {'items': [], 'total_cost': 0, 'total_formatted': '₹0.00'}
    
    def get_project_plan_images(self):
        """Get project plan images if enabled"""
        try:
            if not self.customizations.get('include_plan_images', True):
                return []
            
            # Get selected plan images or all if none selected
            selected_image_ids = self.customizations.get('selected_plan_images', [])
            
            plan_images = []
            
            # Get images from ProjectPlanImageGroup model if it exists
            if hasattr(self.project, 'image_groups'):
                image_groups = self.project.image_groups.filter(is_active=True)
                
                for group in image_groups:
                    group_images = group.images.filter(is_active=True)
                    
                    # Filter by selected images if specified
                    if selected_image_ids:
                        group_images = group_images.filter(id__in=selected_image_ids)
                    
                    for image in group_images:
                        plan_images.append({
                            'id': image.id,
                            'group_title': group.title,
                            'caption': image.caption or f"{group.title} - Image",
                            'url': image.image.url if image.image else None,
                            'file_size': getattr(image, 'file_size', None),
                            'sort_order': image.sort_order
                        })
            
            # Sort by group and then by sort_order
            plan_images.sort(key=lambda x: (x['group_title'], x['sort_order']))
            
            return plan_images
            
        except Exception as e:
            print(f"Error in get_project_plan_images: {e}")
            return []
    
    def get_pricing_breakdown(self):
        """Get comprehensive pricing breakdown"""
        try:
            # Get project totals if available
            try:
                project_totals = self.project.totals
                base_calculations = {
                    'line_items_total': float(project_totals.subtotal_cabinets + project_totals.subtotal_doors),
                    'accessories_total': float(project_totals.subtotal_accessories),
                    'lighting_total': 0,  # Will be calculated separately
                    'subtotal': float(project_totals.subtotal_before_margin),
                    'margin_amount': float(project_totals.margin_amount),
                    'subtotal_after_margin': float(project_totals.subtotal_after_margin),
                    'gst_amount': float(project_totals.gst_amount),
                    'grand_total': float(project_totals.grand_total)
                }
            except:
                # Fallback calculation from line items
                line_items = self.project.lines.filter(is_active=True)
                accessories = ProjectLineItemAccessory.objects.filter(
                    line_item__project=self.project, is_active=True
                )
                
                line_items_total = sum(float(getattr(item, 'total_price', 0)) for item in line_items)
                accessories_total = sum(float(acc.total_price) for acc in accessories)
                subtotal = line_items_total + accessories_total
                
                margin_pct = float(getattr(self.project, 'margin_pct', 0))
                gst_pct = float(getattr(self.project, 'gst_pct', 18))
                
                margin_amount = subtotal * margin_pct / 100
                subtotal_after_margin = subtotal + margin_amount
                gst_amount = subtotal_after_margin * gst_pct / 100
                grand_total = subtotal_after_margin + gst_amount
                
                base_calculations = {
                    'line_items_total': line_items_total,
                    'accessories_total': accessories_total,
                    'lighting_total': 0,
                    'subtotal': subtotal,
                    'margin_amount': margin_amount,
                    'subtotal_after_margin': subtotal_after_margin,
                    'gst_amount': gst_amount,
                    'grand_total': grand_total
                }
            
            # Add lighting costs
            try:
                lighting_config = self.project.lighting_config
                lighting_total = float(lighting_config.grand_total_lighting_cost)
                base_calculations['lighting_total'] = lighting_total
                base_calculations['grand_total'] += lighting_total
            except:
                base_calculations['lighting_total'] = 0
            
            # Apply discounts from customizations
            discount_percentage = float(self.customizations.get('discount_percentage', 0))
            discount_amount = float(self.customizations.get('discount_amount', 0))
            
            total_before_discount = base_calculations['grand_total']
            
            # Apply percentage discount first, then fixed discount
            if discount_percentage > 0:
                discount_amount += total_before_discount * discount_percentage / 100
            
            final_total = max(0, total_before_discount - discount_amount)
            
            return {
                **base_calculations,
                'total_before_discount': total_before_discount,
                'discount_percentage': discount_percentage,
                'discount_amount': discount_amount,
                'final_total': final_total,
                
                # Formatted strings for display
                'formatted': {
                    'line_items_total': f"₹{base_calculations['line_items_total']:,.2f}",
                    'accessories_total': f"₹{base_calculations['accessories_total']:,.2f}",
                    'lighting_total': f"₹{base_calculations['lighting_total']:,.2f}",
                    'subtotal': f"₹{base_calculations['subtotal']:,.2f}",
                    'margin_amount': f"₹{base_calculations['margin_amount']:,.2f}",
                    'gst_amount': f"₹{base_calculations['gst_amount']:,.2f}",
                    'discount_amount': f"₹{discount_amount:,.2f}",
                    'final_total': f"₹{final_total:,.2f}"
                }
            }
            
        except Exception as e:
            print(f"Error in get_pricing_breakdown: {e}")
            # Return fallback calculations
            return {
                'line_items_total': 0,
                'accessories_total': 0,
                'lighting_total': 0,
                'subtotal': 0,
                'margin_amount': 0,
                'gst_amount': 0,
                'discount_amount': 0,
                'final_total': 0,
                'formatted': {
                    'line_items_total': '₹0.00',
                    'accessories_total': '₹0.00',
                    'lighting_total': '₹0.00',
                    'subtotal': '₹0.00',
                    'margin_amount': '₹0.00',
                    'gst_amount': '₹0.00',
                    'discount_amount': '₹0.00',
                    'final_total': '₹0.00'
                }
            }
    
    def get_customer_notes(self):
        """Get custom customer notes from customizations"""
        return {
            'special_instructions': self.customizations.get('special_instructions', ''),
            'installation_notes': self.customizations.get('installation_notes', ''),
            'timeline_notes': self.customizations.get('timeline_notes', ''),
            'custom_requirements': self.customizations.get('custom_requirements', ''),
            'discount_reason': self.customizations.get('discount_reason', '')
        }
    
    def get_pdf_metadata(self):
        """Get metadata for PDF generation"""
        return {
            'generation_date': datetime.now().isoformat(),
            'template_type': self.customizations.get('template_type', 'DETAILED'),
            'includes_images': self.customizations.get('include_accessory_images', True),
            'includes_plans': self.customizations.get('include_plan_images', True),
            'compiler_version': '1.0',
            'project_id': str(self.project.id)
        }


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