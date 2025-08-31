from datetime import datetime, timedelta
import logging  # <-- Kept only one import here

# Add logging setup
logger = logging.getLogger('quotation_pdf')

# Import your existing models
from pricing.models import (
    Project, ProjectLineItemAccessory
)

from django.utils import timezone

class QuotationPDFDataCompiler:
    def __init__(self, project_id, customizations=None):
        self.project_id = project_id
        self.customizations = customizations or {}
        
        # 🔧 FIX: Load the actual Project object with your correct model
        try:
            from pricing.models import Project  # Using your actual Project model
            
            self.project = Project.objects.select_related(
                'customer',  # Your Project has customer FK
                'brand',     # Your Project has brand FK
                'totals'     # For pricing calculations
            ).prefetch_related(
                'lines__cabinet_type',                    # ProjectLineItem -> CabinetTypes
                'lines__cabinet_material',                # ProjectLineItem -> Materials
                'lines__door_material',                   # ProjectLineItem -> Materials
                'lines__extra_accessories__product_variant__product__brand',  # Accessories
                'lighting_items__lighting_rule',          # ProjectLightingItem
                'lighting_items__cabinet_material',       # Lighting materials
                'image_groups__images'                     # Floor plans and images
            ).get(id=project_id)
            
            logger.info(f"✅ Loaded project {project_id} for customer: {self.project.customer.name}")
            
        except Exception as e:
            logger.error(f"❌ Error loading project {project_id}: {e}")
            raise PDFGenerationError(f"Could not load project {project_id}: {str(e)}")

    def compile_complete_data(self):
        """Enhanced version using your actual models"""
        try:
            logger.info("Starting comprehensive PDF data compilation with your models")
            
            # 🆕 Enhanced data compilation using your actual model structure
            enhanced_data = {
                'project_info': self.get_enhanced_project_details(),
                'customer_info': self.get_customer_details(),
                'calculations': self.get_pricing_calculations(),
                'customer_notes': self.get_enhanced_customer_notes(),
                
                # 🆕 NEW ENHANCED SECTIONS using your models
                'cabinet_breakdown': self.get_detailed_cabinet_breakdown(),
                'accessories_detailed': self.get_detailed_accessories_list(),
                'lighting_specifications': self.get_lighting_specifications(),
                'terms_conditions': self.get_terms_and_conditions(),
                'warranty_information': self.get_warranty_information(),
                'installation_timeline': self.get_installation_timeline(),
                'project_floor_plans': self.get_project_floor_plans(),
                'brand_information': self.get_brand_information(),
                
                # Metadata
                'metadata': {
                    'template_type': self.customizations.get('template_type', 'DETAILED'),
                    'generated_at': timezone.now().isoformat(),
                    'generated_by': 'Thaquidheen',
                    'pdf_version': '2.0-Enhanced',
                    'current_utc': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'current_ist': (timezone.now() + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
                    'customization_options': self.customizations
                }
            }
            
            logger.info("✅ Enhanced PDF data compilation completed successfully")
            return enhanced_data
            
        except Exception as e:
            logger.error(f"❌ Error compiling PDF data: {str(e)}")
            # Fallback to basic data if enhancement fails
            return self.get_fallback_data()

    def get_enhanced_project_details(self):
        """Enhanced project details with correct timezone using your Project model"""
        try:
            # Get current UTC time and convert to IST
            current_utc = timezone.now()
            ist_time = current_utc + timedelta(hours=5, minutes=30)
            
            return {
                'id': str(self.project.id),
                'customer_name': self.project.customer.name,
                'project_type': 'Kitchen Quotation',
                'quotation_number': f'SPK-{str(self.project.id).zfill(6)}',  # Speisekamer prefix
                'quotation_date': ist_time.strftime('%d %B %Y'),
                'quotation_time': ist_time.strftime('%H:%M'),
                'quotation_timezone': 'IST',
                'quotation_valid_until': (ist_time + timedelta(days=30)).strftime('%d %B %Y'),
                'brand': self.project.brand.name,  # Your Project.brand FK
                'generated_by': 'Thaquidheen',
                'generated_at_utc': current_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'generated_at_local': ist_time.strftime('%Y-%m-%d %H:%M:%S IST'),
                'status': self.project.status,  # Your Project.status field
                'currency': self.project.currency,  # Your Project.currency field
                'budget_tier': self.project.budget_tier,  # Your Project.budget_tier field
                'margin_pct': float(self.project.margin_pct),
                'gst_pct': float(self.project.gst_pct),
                'notes': self.project.notes,
                'scopes': self.project.scopes  # Your Project.scopes JSONField
            }
        except Exception as e:
            logger.error(f"Error getting enhanced project details: {e}")
            # Fallback with manual IST calculation
            current_utc = timezone.now()
            ist_time = current_utc + timedelta(hours=5, minutes=30)
            
            return {
                'id': str(self.project.id),
                'customer_name': self.project.customer.name,
                'quotation_number': f'SPK-{str(self.project.id).zfill(6)}',
                'quotation_date': ist_time.strftime('%d %B %Y'),
                'quotation_time': ist_time.strftime('%H:%M'),
                'quotation_timezone': 'IST',
                'brand': self.project.brand.name,
                'generated_by': 'Thaquidheen'
            }

    def get_customer_details(self):
        """Get customer details from your Customer model"""
        try:
            customer = self.project.customer
            return {
                'name': customer.name,
                'email': '',
                'phone': customer.contact_number,
                'address': customer.location,  # Use location instead of address
                'contact_number': customer.contact_number,  # Also include the actual field
                'location': customer.location,  # Also include the actual field
                'company': '',
                'gst_number': '',
                'customer_id': customer.id
            }
        except Exception as e:
            logger.error(f"Error getting customer details: {e}")
            return {
                'name': 'Unknown Customer',
                'email': '',
                'phone': '',
                'address': '',
                'company': '',
                'gst_number': ''
            }

    def get_pricing_calculations(self):
        """Get pricing calculations from your ProjectTotals model"""
        try:
            if hasattr(self.project, 'totals') and self.project.totals:
                totals = self.project.totals
                
                return {
                    # Raw amounts
                    'subtotal_cabinets': float(totals.subtotal_cabinets),
                    'subtotal_doors': float(totals.subtotal_doors),
                    'subtotal_accessories': float(totals.subtotal_accessories),
                    'subtotal_tops': float(totals.subtotal_tops),
                    'margin_amount': float(totals.margin_amount),
                    'taxable_amount': float(totals.taxable_amount),
                    'gst_amount': float(totals.gst_amount),
                    'grand_total': float(totals.grand_total),
                    
                    # Formatted amounts
                    'formatted': {
                        'line_items_total': f"₹{totals.subtotal_cabinets:,.2f}",
                        'doors_total': f"₹{totals.subtotal_doors:,.2f}",
                        'accessories_total': f"₹{totals.subtotal_accessories:,.2f}",
                        'tops_total': f"₹{totals.subtotal_tops:,.2f}",
                        'subtotal': f"₹{totals.taxable_amount:,.2f}",
                        'margin_amount': f"₹{totals.margin_amount:,.2f}",
                        'gst_amount': f"₹{totals.gst_amount:,.2f}",
                        'final_total': f"₹{totals.grand_total:,.2f}"
                    },
                    
                    # Add lighting if available
                    'lighting_total': self._get_lighting_total(),
                    
                    # Discount information (if provided in customizations)
                    'discount_percentage': self.customizations.get('discount_percentage', 0),
                    'discount_amount': self._calculate_discount_amount(),
                    'discount_reason': self.customizations.get('discount_reason', '')
                }
            else:
                # Fallback calculation from line items
                return self._calculate_totals_from_line_items()
                
        except Exception as e:
            logger.error(f"Error getting pricing calculations: {e}")
            return self._get_default_calculations()

    def get_detailed_cabinet_breakdown(self):
        """Get detailed cabinet information from your ProjectLineItem model"""
        try:
            if not self.customizations.get('include_cabinet_details', True):
                return []
                
            line_items = self.project.lines.filter(is_active=True).select_related(
                'cabinet_type',
                'cabinet_material',
                'door_material'
            )
            
            cabinet_breakdown = []
            for item in line_items:
                try:
                    cabinet_data = {
                        'id': item.id,
                        'name': item.cabinet_type.name,  # CabinetTypes.name
                        'category': item.cabinet_type.category.name if item.cabinet_type.category else 'Cabinet',
                        'brand': self.project.brand.name,  # From project
                        'scope': item.scope,  # OPEN/WORKING
                        'specifications': {
                            'quantity': item.qty,
                            'cabinet_unit_rate': float(item.cabinet_unit_rate),
                            'door_unit_rate': float(item.door_unit_rate),
                            'cabinet_material_price': float(item.cabinet_material_price),
                            'door_price': float(item.door_price),
                            'top_price': float(item.top_price),
                            'standard_accessory_charge': float(item.standard_accessory_charge),
                            'line_total_before_tax': float(item.line_total_before_tax)
                        },
                        'dimensions': {
                            'width': item.width_mm,
                            'height': item.height_mm,
                            'depth': item.depth_mm,
                            'unit': 'mm',
                            'cabinet_sqft': float(item.computed_cabinet_sqft),
                            'door_sqft': float(item.computed_door_sqft)
                        },
                        'materials': {
                            'cabinet_material': item.cabinet_material.name,
                            'cabinet_material_role': item.cabinet_material.role,
                            'door_material': item.door_material.name,
                            'door_material_role': item.door_material.role
                        },
                        'features': self._get_cabinet_features(item),
                        'accessories_count': item.extra_accessories.filter(is_active=True).count(),
                        'remarks': item.remarks
                    }
                    cabinet_breakdown.append(cabinet_data)
                except Exception as item_error:
                    logger.warning(f"Error processing cabinet item {item.id}: {item_error}")
                    continue
            
            return sorted(cabinet_breakdown, key=lambda x: (x['scope'], x['category'], x['name']))
            
        except Exception as e:
            logger.error(f"Error getting cabinet breakdown: {e}")
            return []

    def get_detailed_accessories_list(self):
        """Get detailed accessories from your ProjectLineItemAccessory model"""
        try:
            if not self.customizations.get('include_accessories', True):
                return []
                
            accessories = []
            
            # Get accessories from all line items
            for line_item in self.project.lines.filter(is_active=True):
                for acc in line_item.extra_accessories.filter(is_active=True).select_related(
                    'product_variant__product__brand'
                ):
                    try:
                        accessory_data = {
                            'id': acc.id,
                            'name': acc.accessory_name,  # Your property method
                            'line_item_cabinet': line_item.cabinet_type.name,
                            'category': getattr(acc.product_variant.product, 'category', 'Accessory'),
                            'brand': acc.product_variant.product.brand.name if acc.product_variant.product.brand else self.project.brand.name,
                            'material_code': acc.material_code,  # Your property method
                            'specifications': {
                                'quantity': acc.qty,
                                'unit_price': float(acc.unit_price),
                                'total_price': float(acc.total_price),
                                'tax_rate': float(acc.tax_rate_snapshot),
                                'installation_notes': acc.installation_notes
                            },
                            'dimensions': acc.dimensions,  # Your property method
                            'image_url': acc.accessory_image,  # Your property method
                            'product_details': {
                                'product_name': acc.product_variant.product.name,
                                'variant_color': acc.product_variant.color_name,
                                'variant_size': getattr(acc.product_variant, 'size', ''),
                                'material': getattr(acc.product_variant, 'material', '')
                            }
                        }
                        accessories.append(accessory_data)
                    except Exception as acc_error:
                        logger.warning(f"Error processing accessory {acc.id}: {acc_error}")
                        continue
                        
            return sorted(accessories, key=lambda x: (x['line_item_cabinet'], x['category'], x['name']))
            
        except Exception as e:
            logger.error(f"Error getting accessories: {e}")
            return []

    def get_project_floor_plans(self):
        try:
            if not self.customizations.get('include_plan_images', True):
                return []
            
            floor_plans = []
            
            # Move import outside loop for performance
            from django.conf import settings
            
            # Get image groups with images
            for image_group in self.project.image_groups.filter(is_active=True).prefetch_related(
                'images'
            ).order_by('sort_order', 'created_at'):
                
                group_data = {
                    'group_id': image_group.id,
                    'title': image_group.title,
                    'description': image_group.description,
                    'sort_order': image_group.sort_order,
                    'image_count': image_group.images.filter(is_active=True).count(),
                    'first_image_url': None,
                    'images': []
                }
                
                # Get images for this group
                images = image_group.images.filter(is_active=True).order_by('sort_order', 'created_at')
                
                for image in images:
                    # Build full URL for image
                    image_url = None
                    if image.image:
                        try:
                            # Try to get full URL
                            if hasattr(image.image, 'url'):
                                # For development/testing, you might need to add domain
                                image_url = image.image.url
                                if not image_url.startswith('http'):
                                    image_url = f"http://127.0.0.1:8000{image_url}"
                        except Exception as img_error:
                            logger.warning(f"Error getting image URL for {image.id}: {img_error}")
                    
                    image_data = {
                        'id': image.id,
                        'image_url': image_url,
                        'thumbnail_url': image_url,  # Use same URL for now
                        'caption': image.caption or f"Floor Plan {image.id}",
                        'sort_order': image.sort_order,
                        'file_size': image.file_size,
                        'file_size_display': image.file_size_display if hasattr(image, 'file_size_display') else 'Unknown',
                        'file_type': image.file_type or 'Image',
                        'created_at': image.created_at.isoformat() if hasattr(image, 'created_at') else None
                    }
                    
                    # Set first image URL for group thumbnail
                    if not group_data['first_image_url'] and image_url:
                        group_data['first_image_url'] = image_url
                    
                    group_data['images'].append(image_data)
                
                # Only add groups that have images or are important
                if group_data['images'] or image_group.title:
                    floor_plans.append(group_data)
            
            # If no real floor plans exist, create sample data for testing
            if not floor_plans:
                logger.info("No floor plan images found, creating sample data")
                floor_plans = [
                    {
                        'group_id': 1,
                        'title': 'Kitchen Layout Plans',
                        'description': 'Comprehensive layout designs showing cabinet placement and dimensions',
                        'sort_order': 0,
                        'image_count': 3,
                        'first_image_url': None,
                        'images': [
                            {
                                'id': 1,
                                'image_url': None,  # Will show placeholder
                                'caption': 'Main Kitchen Layout - Plan View',
                                'sort_order': 0,
                                'file_size_display': 'Coming Soon',  # <-- Fixed typo
                                'file_type': 'PDF'
                            },
                            {
                                'id': 2,
                                'image_url': None,
                                'caption': 'Cabinet Elevation Details',
                                'sort_order': 1,
                                'file_size_display': 'Coming Soon',  # <-- Fixed typo
                                'file_type': 'PDF'
                            },
                            {
                                'id': 3,
                                'image_url': None,
                                'caption': 'Lighting & Electrical Layout',
                                'sort_order': 2,
                                'file_size_display': 'Coming Soon',  # <-- Fixed typo
                                'file_type': 'PDF'
                            }
                        ]
                    },
                    {
                        'group_id': 2,
                        'title': '3D Renderings',
                        'description': 'Photorealistic visualizations of your kitchen design',
                        'sort_order': 1,
                        'image_count': 2,
                        'first_image_url': None,
                        'images': [
                            {
                                'id': 4,
                                'image_url': None,
                                'caption': 'Kitchen Overview - 3D Render',
                                'sort_order': 0,
                                'file_size_display': 'Coming Soon',  # <-- Fixed typo
                                'file_type': 'JPG'
                            },
                            {
                                'id': 5,
                                'image_url': None,
                                'caption': 'Detail View - Coming Soon',  # <-- Fixed typo
                                'sort_order': 1,
                                'file_size_display': 'Coming Soon',  # <-- Fixed typo
                                'file_type': 'JPG'
                            }
                        ]
                    }
                ]
            
            logger.info(f"✅ Found {len(floor_plans)} floor plan groups with images")
            return sorted(floor_plans, key=lambda x: x['sort_order'])
            
        except Exception as e:
            logger.error(f"❌ Error getting floor plans: {e}")
            return []

    def get_lighting_specifications(self):
        """Get lighting specifications from your ProjectLightingItem model"""
        try:
            if not self.customizations.get('include_lighting', True):
                return {}
                
            # Get lighting configuration
            lighting_config = getattr(self.project, 'lighting_config', None)
            lighting_items = self.project.lighting_items.filter(is_active=True).select_related(
                'lighting_rule',
                'cabinet_material',
                'cabinet_type'
            )
            
            if not lighting_items.exists() and not lighting_config:
                return {}
                
            lighting_specs = {
                'overview': {
                    'total_fixtures': lighting_items.count(),
                    'total_cost': float(lighting_config.grand_total_lighting_cost) if lighting_config else 0,
                    'estimated_power_consumption': self._calculate_power_consumption_from_lighting(lighting_items),
                    'lighting_zones': self._get_lighting_zones_from_items(lighting_items),
                    'total_wall_cabinet_width': lighting_config.total_wall_cabinet_width_mm if lighting_config else 0,
                    'work_top_length': lighting_config.work_top_length_mm if lighting_config else 0
                },
                'lighting_breakdown': [],
                'installation_requirements': {
                    'electrical_points_needed': lighting_items.count(),
                    'special_wiring': False,
                    'work_top_length_required': lighting_config.work_top_length_mm if lighting_config else 0
                }
            }
            
            # Add detailed breakdown
            for item in lighting_items:
                breakdown = {
                    'material': item.cabinet_material.name,
                    'cabinet_type': item.cabinet_type.name if item.cabinet_type else 'All Types',
                    'rule_name': item.lighting_rule.name,
                    'specifications': {
                        'led_specification': item.lighting_rule.led_specification,
                        'spot_light_specification': item.lighting_rule.spot_light_specification,
                        'led_rate_per_mm': float(item.lighting_rule.led_strip_rate_per_mm),
                        'spot_rate_per_cabinet': float(item.lighting_rule.spot_light_rate_per_cabinet)
                    },
                    'dimensions': {
                        'wall_cabinet_width_mm': item.wall_cabinet_width_mm,
                        'base_cabinet_width_mm': item.base_cabinet_width_mm,
                        'wall_cabinet_count': item.wall_cabinet_count,
                        'work_top_length_mm': item.work_top_length_mm
                    },
                    'cost_breakdown': {
                        'led_under_wall_cost': float(item.led_under_wall_cost),
                        'led_work_top_cost': float(item.led_work_top_cost),
                        'led_skirting_cost': float(item.led_skirting_cost),
                        'spot_lights_cost': float(item.spot_lights_cost),
                        'total_cost': float(item.total_cost)
                    },
                    'applicability': {
                        'applies_to_wall_cabinets': item.lighting_rule.applies_to_wall_cabinets,
                        'applies_to_base_cabinets': item.lighting_rule.applies_to_base_cabinets
                    }
                }
                lighting_specs['lighting_breakdown'].append(breakdown)
            
            return lighting_specs
            
        except Exception as e:
            logger.error(f"Error getting lighting specifications: {e}")
            return {}

    def get_brand_information(self):
        """Get brand information from your Brand model"""
        try:
            brand = self.project.brand
            return {
                'name': brand.name,
                'tagline': 'Crafting Premium Kitchen Experiences',
                'established': '2020',
                'specialization': f"{self.project.budget_tier.title()} Kitchen Solutions",
                'contact_info': {
                    'phone': '+91-9876-543210',
                    'email': f'info@{brand.name.lower().replace(" ", "")}.com',
                    'website': f'www.{brand.name.lower().replace(" ", "")}.com',
                    'address': 'Mumbai, Maharashtra, India'
                },
                'certifications': ['ISO 9001:2015', 'FSC Certified', 'Green Building Approved'],
                'brand_id': brand.id
            }
        except Exception as e:
            logger.error(f"Error getting brand information: {e}")
            return {
                'name': 'Speisekamer',
                'tagline': 'Crafting Premium Kitchen Experiences',
                'contact_info': {'phone': '+91-9876-543210', 'email': 'info@speisekamer.com'}
            }

    # Helper methods
    def _get_lighting_total(self):
        """Calculate total lighting cost"""
        try:
            if hasattr(self.project, 'lighting_config') and self.project.lighting_config:
                return {
                    'raw_amount': float(self.project.lighting_config.grand_total_lighting_cost),
                    'formatted': f"₹{self.project.lighting_config.grand_total_lighting_cost:,.2f}"
                }
        except:
            pass
        return {'raw_amount': 0, 'formatted': '₹0.00'}

    def _calculate_discount_amount(self):
        """Calculate discount amount if percentage is provided"""
        discount_pct = self.customizations.get('discount_percentage', 0)
        if discount_pct and hasattr(self.project, 'totals'):
            subtotal = float(self.project.totals.taxable_amount)
            discount_amount = subtotal * (float(discount_pct) / 100)
            return {
                'raw_amount': discount_amount,
                'formatted': f"₹{discount_amount:,.2f}"
            }
        return {'raw_amount': 0, 'formatted': '₹0.00'}

    def _calculate_power_consumption_from_lighting(self, lighting_items):
        """Calculate estimated power consumption"""
        total_led_length = sum(
            item.wall_cabinet_width_mm + item.work_top_length_mm + item.base_cabinet_width_mm 
            for item in lighting_items
        )
        total_spots = sum(item.wall_cabinet_count for item in lighting_items)
        
        # Estimate: 10W per meter LED + 5W per spot light
        estimated_watts = (total_led_length / 1000) * 10 + total_spots * 5
        monthly_kwh = (estimated_watts * 8 * 30) / 1000  # 8 hours/day, 30 days
        
        return f"{estimated_watts:.0f}W total, ~{monthly_kwh:.1f} kWh/month"

    def _get_lighting_zones_from_items(self, lighting_items):
        """Get lighting zones from items"""
        zones = []
        for item in lighting_items:
            if item.lighting_rule.applies_to_wall_cabinets:
                zones.extend(['Under Cabinet', 'Work Top'])
            if item.lighting_rule.applies_to_base_cabinets:
                zones.append('Skirting')
        return list(set(zones))

    def _get_cabinet_features(self, line_item):
        """Get cabinet features based on line item"""
        features = []
        try:
            # Add features based on materials and specifications
            if 'plywood' in line_item.cabinet_material.name.lower():
                features.append('Premium Plywood Construction')
            if 'mdf' in line_item.cabinet_material.name.lower():
                features.append('High-Grade MDF')
            
            features.extend([
                'Soft-close hinges',
                'Adjustable shelves',
                'Premium hardware',
                f'{line_item.door_material.name} doors'
            ])
            
            if line_item.standard_accessory_charge > 0:
                features.append('Standard accessories included')
                
        except:
            features = ['Premium construction', 'Quality hardware']
        
        return features

    def get_enhanced_customer_notes(self):
        """Get all customer notes and instructions"""
        notes = {}
        try:
            # From API customizations
            notes['special_instructions'] = self.customizations.get('special_instructions', '')
            notes['installation_notes'] = self.customizations.get('installation_notes', '')
            notes['timeline_notes'] = self.customizations.get('timeline_notes', '')
            notes['discount_reason'] = self.customizations.get('discount_reason', '')
            
            # From project model
            if self.project.notes:
                notes['project_notes'] = self.project.notes
                
            # From project scopes (JSONField)
            if self.project.scopes:
                scope_notes = []
                for scope, enabled in self.project.scopes.items():
                    if enabled:
                        scope_notes.append(f"{scope.title()} kitchen included")
                if scope_notes:
                    notes['scope_information'] = '; '.join(scope_notes)
                    
        except Exception as e:
            logger.error(f"Error getting customer notes: {e}")
            
        return notes

    def get_terms_and_conditions(self):
        """Get terms and conditions based on project tier"""
        budget_tier = self.project.budget_tier
        
        base_terms = {
            'payment_terms': {
                'advance_payment': '40% advance with order confirmation',
                'progress_payment': '40% during installation',
                'final_payment': '20% upon completion',
                'payment_methods': ['Bank Transfer', 'Cheque', 'Online Payment', 'UPI'],
                'payment_timeline': 'Net 30 days for corporate clients'
            },
            'delivery_terms': {
                'standard_delivery': '4-6 weeks from order confirmation' if budget_tier == 'ECONOMY' else '3-5 weeks from order confirmation',
                'express_delivery': '2-3 weeks (additional charges apply)',
                'delivery_scope': 'Free delivery within 25 km radius',
                'installation_included': True,
                'site_preparation': 'Customer responsibility'
            }
        }
        
        if budget_tier == 'LUXURY':
            base_terms['premium_services'] = {
                'design_consultation': 'Complimentary 3D design service',
                'material_samples': 'Free material samples at home',
                'priority_support': '24/7 premium customer support',
                'extended_warranty': 'Extended warranty on premium components'
            }
        
        return base_terms

    def get_warranty_information(self):
        """Get warranty based on budget tier"""
        budget_tier = self.project.budget_tier
        
        if budget_tier == 'LUXURY':
            return {
                'coverage_summary': {
                    'cabinet_structure': '3 years comprehensive warranty',
                    'premium_hardware': '2 years replacement warranty',
                    'door_panels': '3 years against warping/cracking',
                    'lighting_systems': '3 years electrical warranty',
                    'installation_work': '2 years workmanship warranty'
                },
                'premium_benefits': [
                    'Annual maintenance visit included',
                    'Priority service response',
                    'Premium replacement parts',
                    'Extended coverage on electrical components'
                ]
            }
        else:
            return {
                'coverage_summary': {
                    'cabinet_structure': '2 years comprehensive warranty',
                    'hardware_fittings': '1 year replacement warranty',
                    'door_panels': '2 years against warping/cracking',
                    'lighting_systems': '2 years electrical warranty',
                    'installation_work': '1 year workmanship warranty'
                }
            }

    def get_installation_timeline(self):
        """Get timeline based on project complexity"""
        line_item_count = self.project.lines.filter(is_active=True).count()
        has_lighting = self.project.lighting_items.filter(is_active=True).exists()
        budget_tier = self.project.budget_tier
        
        # Calculate production time based on complexity
        base_production = 15
        if line_item_count > 20:
            base_production += 7
        if has_lighting:
            base_production += 3
        if budget_tier == 'LUXURY':
            base_production += 5  # More detailed work
            
        return {
            'project_phases': [
                {
                    'phase': 'Design Finalization',
                    'duration': '2-3 days' if budget_tier == 'LUXURY' else '3-5 days',
                    'description': 'Final design approval and material confirmation',
                    'deliverables': ['Final 3D design', 'Material specifications', 'Installation plan']
                },
                {
                    'phase': 'Production',
                    'duration': f'{base_production}-{base_production + 7} days',
                    'description': 'Manufacturing of cabinets and components',
                    'deliverables': ['Manufactured cabinets', 'Quality certificates', 'Hardware kits']
                },
                {
                    'phase': 'Installation',
                    'duration': f'{max(3, line_item_count // 8)}-{max(5, line_item_count // 5)} days',
                    'description': 'On-site installation and setup',
                    'deliverables': ['Installed cabinets', 'Lighting setup' if has_lighting else 'Hardware fitting', 'Final inspection']
                }
            ],
            'total_timeline': f'{base_production + 8}-{base_production + 17} working days',
            'project_complexity': {
                'line_items': line_item_count,
                'has_lighting': has_lighting,
                'budget_tier': budget_tier,
                'estimated_complexity': 'High' if line_item_count > 15 or budget_tier == 'LUXURY' else 'Standard'
            }
        }

    def get_fallback_data(self):
        """Fallback data if compilation fails"""
        current_utc = timezone.now()
        ist_time = current_utc + timedelta(hours=5, minutes=30)
        
        return {
            'project_info': {
                'customer_name': self.project.customer.name,
                'quotation_number': f'SPK-{str(self.project.id).zfill(6)}',
                'quotation_date': ist_time.strftime('%d %B %Y'),
                'quotation_time': ist_time.strftime('%H:%M'),
                'brand': self.project.brand.name,
                'generated_by': 'Thaquidheen'
            },
            'customer_info': {'name': self.project.customer.name},
            'calculations': {'formatted': {'final_total': '₹0.00'}}
        }

    def _calculate_totals_from_line_items(self):
        """Calculate totals from line items if ProjectTotals doesn't exist"""
        try:
            line_items = self.project.lines.filter(is_active=True)
            
            subtotal_cabinets = sum(float(item.cabinet_material_price) for item in line_items)
            subtotal_doors = sum(float(item.door_price) for item in line_items)
            subtotal_accessories = sum(float(item.standard_accessory_charge) for item in line_items)
            subtotal_tops = sum(float(item.top_price) for item in line_items)
            
            subtotal = subtotal_cabinets + subtotal_doors + subtotal_accessories + subtotal_tops
            gst_amount = subtotal * (float(self.project.gst_pct) / 100)
            grand_total = subtotal + gst_amount
            
            return {
                'subtotal_cabinets': subtotal_cabinets,
                'subtotal_doors': subtotal_doors,
                'subtotal_accessories': subtotal_accessories,
                'subtotal_tops': subtotal_tops,
                'gst_amount': gst_amount,
                'grand_total': grand_total,
                'formatted': {
                    'line_items_total': f"₹{subtotal_cabinets:,.2f}",
                    'doors_total': f"₹{subtotal_doors:,.2f}",
                    'accessories_total': f"₹{subtotal_accessories:,.2f}",
                    'tops_total': f"₹{subtotal_tops:,.2f}",
                    'subtotal': f"₹{subtotal:,.2f}",
                    'gst_amount': f"₹{gst_amount:,.2f}",
                    'final_total': f"₹{grand_total:,.2f}"
                }
            }
        except Exception as e:
            logger.error(f"Error calculating totals from line items: {e}")
            return self._get_default_calculations()

    def _get_default_calculations(self):
        """Default calculations"""
        return {
            'subtotal_cabinets': 0,
            'grand_total': 0,
            'formatted': {
                'line_items_total': '₹0.00',
                'final_total': '₹0.00'
            }
        }