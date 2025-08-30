# quotation_pdf/services.py
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.core.files.storage import default_storage
from decimal import Decimal
import os
import uuid
from datetime import datetime

# Import your existing models
from pricing.models import Project, ProjectLineItem, ProjectLineItemAccessory, ProjectTotals
from catalog.models import ProductVariant

class QuotationPDFDataCompiler:
    """Compile all project data for PDF generation"""
    
    def __init__(self, project_id, customizations=None):
        self.project_id = project_id
        self.customizations = customizations or {}
        self.project = Project.objects.select_related('customer').get(id=project_id)
    
    def compile_complete_data(self):
        """Main method to compile all PDF data"""
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
    
    def get_project_details(self):
        """Get basic project information"""
        return {
            'id': str(self.project.id),
            'customer_name': self.project.customer.name,
            'project_type': 'Kitchen Quotation',
            'quotation_number': f'KQ-{self.project.id}',
            'quotation_date': datetime.now().strftime('%d %B %Y'),
            'brand': self.project.brand.name if hasattr(self.project, 'brand') and self.project.brand else 'Premium Kitchens',
            'budget_tier': getattr(self.project, 'budget_tier', 'STANDARD'),
            'kitchen_types': self.project.kitchen_types,
            'notes': self.project.notes
        }
    
    def get_customer_details(self):
        """Get customer information"""
        customer = self.project.customer
        return {
            'name': customer.name,
            'email': getattr(customer, 'email', ''),
            'phone': getattr(customer, 'phone', ''),
            'address': getattr(customer, 'address', ''),
            'city': getattr(customer, 'city', ''),
            'state': getattr(customer, 'state', ''),
            'pincode': getattr(customer, 'pincode', ''),
        }
    
    def get_cabinet_breakdown(self):
        """Break down cabinet items by category"""
        line_items = ProjectLineItem.objects.filter(project=self.project).select_related(
            'cabinet_type', 'cabinet_material', 'door_material'
        )
        
        # Group by cabinet category
        categories = {}
        for item in line_items:
            category_name = item.cabinet_type.category.name if item.cabinet_type.category else 'OTHER'
            
            if category_name not in categories:
                categories[category_name] = {
                    'name': category_name,
                    'items': [],
                    'subtotal': Decimal('0')
                }
            
            item_data = {
                'id': str(item.id),
                'description': f"{item.cabinet_type.name}",
                'cabinet_material': item.cabinet_material.name,
                'door_material': item.door_material.name,
                'dimensions': f"{item.width_mm} × {item.depth_mm} × {item.height_mm} mm",
                'dimensions_formatted': {
                    'width': item.width_mm,
                    'depth': item.depth_mm,
                    'height': item.height_mm
                },
                'quantity': item.qty,
                'cabinet_sqft': float(item.computed_cabinet_sqft),
                'door_sqft': float(item.computed_door_sqft),
                'cabinet_unit_rate': float(item.cabinet_unit_rate),
                'door_unit_rate': float(item.door_unit_rate),
                'cabinet_material_price': float(item.cabinet_material_price),
                'door_price': float(item.door_price),
                'standard_accessory_charge': float(item.standard_accessory_charge),
                'line_total': float(item.line_total_before_tax),
                'scope': item.scope
            }
            
            categories[category_name]['items'].append(item_data)
            categories[category_name]['subtotal'] += item.line_total_before_tax
        
        # Convert to list and add formatted subtotals
        cabinet_breakdown = []
        for category_name, category_data in categories.items():
            category_data['subtotal'] = float(category_data['subtotal'])
            category_data['subtotal_formatted'] = f"₹{category_data['subtotal']:,.2f}"
            cabinet_breakdown.append(category_data)
        
        return cabinet_breakdown
    
    def get_door_breakdown(self):
        """Get door-specific breakdown"""
        line_items = ProjectLineItem.objects.filter(project=self.project).select_related(
            'door_material'
        )
        
        # Group by door material
        door_materials = {}
        for item in line_items:
            material_name = item.door_material.name
            
            if material_name not in door_materials:
                door_materials[material_name] = {
                    'material_name': material_name,
                    'total_sqft': 0,
                    'total_price': Decimal('0'),
                    'items': []
                }
            
            door_materials[material_name]['total_sqft'] += float(item.computed_door_sqft)
            door_materials[material_name]['total_price'] += item.door_price
            door_materials[material_name]['items'].append({
                'cabinet_type': item.cabinet_type.name,
                'quantity': item.qty,
                'door_sqft': float(item.computed_door_sqft),
                'door_unit_rate': float(item.door_unit_rate),
                'door_price': float(item.door_price)
            })
        
        # Convert to list
        door_breakdown = []
        for material_name, material_data in door_materials.items():
            material_data['total_price'] = float(material_data['total_price'])
            material_data['avg_rate'] = material_data['total_price'] / material_data['total_sqft'] if material_data['total_sqft'] > 0 else 0
            door_breakdown.append(material_data)
        
        return door_breakdown
    
    def get_accessories_with_images(self):
        """Get accessories grouped by line item with product images"""
        accessories = ProjectLineItemAccessory.objects.filter(
            line_item__project=self.project
        ).select_related(
            'line_item', 'product_variant', 'product_variant__product',
            'product_variant__product__brand', 'product_variant__product__category'
        ).prefetch_related('product_variant__images')
        
        # Group by line item
        accessories_by_line_item = {}
        for accessory in accessories:
            line_item_id = str(accessory.line_item.id)
            
            if line_item_id not in accessories_by_line_item:
                accessories_by_line_item[line_item_id] = {
                    'line_item_info': {
                        'id': line_item_id,
                        'cabinet_type': accessory.line_item.cabinet_type.name,
                        'scope': accessory.line_item.scope
                    },
                    'accessories': [],
                    'subtotal': Decimal('0')
                }
            
            # Get product images
            images = []
            if self.customizations.get('include_accessory_images', True):
                for image in accessory.product_variant.images.all()[:2]:  # Limit to 2 images
                    images.append({
                        'url': image.image.url if image.image else None,
                        'alt_text': image.alt_text or accessory.product_variant.product.name
                    })
            
            accessory_data = {
                'id': str(accessory.id),
                'name': accessory.product_variant.product.name,
                'variant_info': {
                    'color': accessory.product_variant.color_name,
                    'material_code': accessory.product_variant.material_code,
                    'sku': accessory.product_variant.sku_code
                },
                'brand': accessory.product_variant.product.brand.name if accessory.product_variant.product.brand else '',
                'category': accessory.product_variant.product.category.name if accessory.product_variant.product.category else '',
                'description': accessory.product_variant.product.description or '',
                'quantity': accessory.qty,
                'unit_price': float(accessory.unit_price),
                'total_price': float(accessory.total_price),
                'installation_notes': accessory.installation_notes,
                'images': images,
                'dimensions': {
                    'width': accessory.product_variant.size_width,
                    'height': accessory.product_variant.size_height,
                    'depth': accessory.product_variant.size_depth
                }
            }
            
            accessories_by_line_item[line_item_id]['accessories'].append(accessory_data)
            accessories_by_line_item[line_item_id]['subtotal'] += accessory.total_price
        
        # Convert to list and format subtotals
        accessories_breakdown = []
        for line_item_id, group_data in accessories_by_line_item.items():
            group_data['subtotal'] = float(group_data['subtotal'])
            group_data['subtotal_formatted'] = f"₹{group_data['subtotal']:,.2f}"
            accessories_breakdown.append(group_data)
        
        return accessories_breakdown
    
    def get_lighting_breakdown(self):
        """Get lighting items if they exist"""
        try:
            from pricing.models import ProjectLightingItem
            lighting_items = ProjectLightingItem.objects.filter(
                project=self.project, is_active=True
            ).select_related('lighting_rule', 'cabinet_material')
            
            lighting_breakdown = []
            total_lighting_cost = Decimal('0')
            
            for item in lighting_items:
                lighting_data = {
                    'rule_name': item.lighting_rule.name,
                    'cabinet_material': item.cabinet_material.name,
                    'cabinet_type': item.cabinet_type.name if item.cabinet_type else 'All Types',
                    'under_cabinet_cost': float(item.under_cabinet_lights_cost),
                    'nosing_led_cost': float(item.nosing_led_cost),
                    'spot_lights_cost': float(item.spot_lights_cost),
                    'total_cost': float(item.total_cost)
                }
                lighting_breakdown.append(lighting_data)
                total_lighting_cost += item.total_cost
            
            return {
                'items': lighting_breakdown,
                'total_cost': float(total_lighting_cost),
                'total_formatted': f"₹{float(total_lighting_cost):,.2f}"
            }
        except ImportError:
            return {'items': [], 'total_cost': 0, 'total_formatted': '₹0.00'}
    
    def get_project_plan_images(self):
        """Get selected plan images"""
        try:
            from pricing.models import ProjectPlanImageGroup, ProjectPlanImage
            
            # Get selected image IDs from customizations
            selected_image_ids = self.customizations.get('selected_plan_images', [])
            
            if selected_image_ids:
                # Get specific selected images
                images = ProjectPlanImage.objects.filter(
                    id__in=selected_image_ids,
                    image_group__project=self.project
                ).select_related('image_group').order_by('image_group__sort_order', 'sort_order')
            else:
                # Get all images if none specifically selected
                images = ProjectPlanImage.objects.filter(
                    image_group__project=self.project
                ).select_related('image_group').order_by('image_group__sort_order', 'sort_order')[:10]  # Limit to 10
            
            plan_images = []
            for image in images:
                plan_images.append({
                    'id': str(image.id),
                    'url': image.image.url if image.image else None,
                    'caption': image.caption or f"{image.image_group.title} - Image",
                    'group_title': image.image_group.title,
                    'file_size': image.file_size or 0
                })
            
            return plan_images
        except ImportError:
            return []
    
    def get_pricing_breakdown(self):
        """Get comprehensive pricing calculations"""
        try:
            project_totals = ProjectTotals.objects.get(project=self.project)
            
            # Base calculations from project totals
            base_calculations = {
                'line_items_total': float(project_totals.line_items_total),
                'accessories_total': float(project_totals.accessories_total),
                'lighting_total': float(project_totals.lighting_total),
                'subtotal': float(project_totals.subtotal),
                'tax_amount': float(project_totals.tax_amount),
                'total_before_discount': float(project_totals.total),
            }
            
            # Apply custom discount
            discount_amount = Decimal('0')
            discount_percentage = self.customizations.get('discount_percentage', 0)
            custom_discount_amount = self.customizations.get('discount_amount', 0)
            
            if discount_percentage > 0:
                discount_amount = (base_calculations['total_before_discount'] * Decimal(str(discount_percentage))) / 100
            elif custom_discount_amount > 0:
                discount_amount = Decimal(str(custom_discount_amount))
            
            final_total = Decimal(str(base_calculations['total_before_discount'])) - discount_amount
            
            return {
                **base_calculations,
                'discount_percentage': discount_percentage,
                'discount_amount': float(discount_amount),
                'discount_reason': self.customizations.get('discount_reason', ''),
                'final_total': float(final_total),
                
                # Formatted strings for display
                'formatted': {
                    'line_items_total': f"₹{base_calculations['line_items_total']:,.2f}",
                    'accessories_total': f"₹{base_calculations['accessories_total']:,.2f}",
                    'lighting_total': f"₹{base_calculations['lighting_total']:,.2f}",
                    'subtotal': f"₹{base_calculations['subtotal']:,.2f}",
                    'tax_amount': f"₹{base_calculations['tax_amount']:,.2f}",
                    'discount_amount': f"₹{float(discount_amount):,.2f}",
                    'final_total': f"₹{float(final_total):,.2f}"
                }
            }
        except ProjectTotals.DoesNotExist:
            # Fallback if no project totals exist
            return {
                'line_items_total': 0,
                'accessories_total': 0,
                'lighting_total': 0,
                'subtotal': 0,
                'tax_amount': 0,
                'discount_amount': 0,
                'final_total': 0,
                'formatted': {
                    'line_items_total': '₹0.00',
                    'accessories_total': '₹0.00',
                    'lighting_total': '₹0.00',
                    'subtotal': '₹0.00',
                    'tax_amount': '₹0.00',
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
            'custom_requirements': self.customizations.get('custom_requirements', '')
        }
    
    def get_pdf_metadata(self):
        """Get metadata for PDF generation"""
        return {
            'generation_date': datetime.now().isoformat(),
            'template_type': self.customizations.get('template_type', 'DETAILED'),
            'includes_images': self.customizations.get('include_accessory_images', True),
            'includes_plans': self.customizations.get('include_plan_images', True)
        }


class QuotationPDFGenerator:
    """Generate PDF from compiled data"""
    
    def __init__(self, project_id, customizations=None):
        self.project_id = project_id
        self.customizations = customizations or {}
        self.compiler = QuotationPDFDataCompiler(project_id, customizations)
    
    def generate_pdf(self):
        """Main PDF generation method"""
        # Compile all data
        pdf_data = self.compiler.compile_complete_data()
        
        # Select template based on customizations
        template_name = self.get_template_name()
        
        # Render HTML
        html_content = render_to_string(template_name, pdf_data)
        
        # Generate PDF (we'll implement this next)
        pdf_bytes = self.render_pdf_from_html(html_content)
        
        # Save PDF history record
        self.save_pdf_history(pdf_data, len(pdf_bytes))
        
        return pdf_bytes
    
    def get_template_name(self):
        """Select appropriate template"""
        template_type = self.customizations.get('template_type', 'DETAILED')
        
        template_mapping = {
            'DETAILED': 'quotation_pdf/detailed_quotation.html',
            'STANDARD': 'quotation_pdf/standard_quotation.html',
            'SIMPLE': 'quotation_pdf/simple_quotation.html'
        }
        
        return template_mapping.get(template_type, 'quotation_pdf/detailed_quotation.html')
    
    def render_pdf_from_html(self, html_content):
        """Convert HTML to PDF - we'll implement this with WeasyPrint"""
        # This will be implemented in the next step
        pass
    
    def render_pdf_from_html(self, html_content):
        """Convert HTML to PDF using WeasyPrint"""
        from .pdf_renderer import PDFRenderer
        
        renderer = PDFRenderer()
        css_files = ['quotation_styles.css']  # Add more CSS files as needed
        
        return renderer.render_pdf(html_content, css_files)

    def save_pdf_history(self, pdf_data, file_size):
        """Save PDF generation history"""
        from .models import QuotationPDFHistory
        
        calculations = pdf_data.get('calculations', {})
        
        QuotationPDFHistory.objects.create(
            project_id=self.project_id,
            filename=f"quotation-{self.project_id}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            file_size=file_size,
            total_amount=calculations.get('total_before_discount', 0),
            discount_applied=calculations.get('discount_amount', 0),
            final_amount=calculations.get('final_total', 0),
            status='GENERATED'
        )