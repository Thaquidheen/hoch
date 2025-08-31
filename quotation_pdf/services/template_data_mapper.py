# quotation_pdf/services/template_data_mapper.py
# Maps your data structure to template-expected structure

import logging
from decimal import Decimal

logger = logging.getLogger('quotation_pdf')

class TemplateDataMapper:
    """Maps compiled PDF data to template-expected structure"""
    
    def __init__(self, compiled_data):
        self.compiled_data = compiled_data
        
    def map_to_template_structure(self):
        """Map your data structure to what templates expect"""
        try:
            logger.info("Mapping compiled data to template structure")
            
            # Base template structure
            template_data = {
                # Company information
                'company_info': self._map_company_info(),
                
                # Project information
                'project_info': self._map_project_info(),
                
                # Customer information
                'customer_info': self._map_customer_info(),
                
                # Quotation metadata
                'quotation_info': self._map_quotation_info(),
                
                # Items for template
                'kitchen_items': self._map_kitchen_items(),
                'doors_items': self._map_doors_items(),
                'accessories_items': self._map_accessories_items(),
                'lighting_items': self._map_lighting_items(),
                
                # Pricing summary
                'pricing_summary': self._map_pricing_summary(),
                
                # Timeline information
                'timeline_info': self._map_timeline_info(),
                
                # Additional sections
                'warranty_info': self._map_warranty_info(),
                'special_instructions': self._map_special_instructions(),
            }
            
            logger.info("Template data mapping completed successfully")
            return template_data
            
        except Exception as e:
            logger.error(f"Error mapping template data: {str(e)}")
            return self._create_fallback_data()
    
    def _map_company_info(self):
        """Map company/brand information"""
        brand_info = self.compiled_data.get('brand_information', {})
        
        return {
            'name': brand_info.get('name', 'Speisekamer'),
            'tagline': brand_info.get('tagline', 'Premium Kitchen Solutions'),
            'phone': brand_info.get('contact_info', {}).get('phone', '+91-9876-543210'),
            'email': brand_info.get('contact_info', {}).get('email', 'info@speisekamer.com'),
            'website': brand_info.get('contact_info', {}).get('website', 'www.speisekamer.com'),
            'address': 'Kochi, Kerala, India',  # Add your company address
            'signatory': 'Thaquidheen'
        }
    
    def _map_project_info(self):
        """Map project information"""
        project_data = self.compiled_data.get('project_info', {})
        
        return {
            'project_name': f"Kitchen Project - {project_data.get('customer_name', 'Customer')}",
            'project_type': 'Kitchen Design & Installation',
            'location': project_data.get('location', 'Not specified'),
            'dimensions': project_data.get('dimensions', 'To be measured'),
            'budget_tier': project_data.get('budget_tier', 'Standard').title(),
            'status': project_data.get('status', 'DRAFT'),
            'scopes': project_data.get('scopes', [])
        }
    
    def _map_customer_info(self):
        """Map customer information"""
        customer_data = self.compiled_data.get('customer_info', {})
        
        return {
            'name': customer_data.get('name', 'Customer Name'),
            'email': customer_data.get('email', 'customer@email.com'),
            'phone': customer_data.get('phone', '+91-XXXXXXXXXX'),
            'address': customer_data.get('address', 'Customer Address'),
            'company': customer_data.get('company', ''),
            'gst_number': customer_data.get('gst_number', '')
        }
    
    def _map_quotation_info(self):
        """Map quotation metadata"""
        project_data = self.compiled_data.get('project_info', {})
        
        return {
            'quotation_number': project_data.get('quotation_number', 'SPK-000001'),
            'date': project_data.get('quotation_date', '2024-01-01'),
            'time': project_data.get('quotation_time', '12:00'),
            'timezone': project_data.get('quotation_timezone', 'IST'),
            'valid_until': project_data.get('quotation_valid_until', '30 days'),
            'generated_by': project_data.get('generated_by', 'System')
        }
    
    def _map_kitchen_items(self):
        """Map cabinet breakdown to kitchen items"""
        cabinet_data = self.compiled_data.get('cabinet_breakdown', [])
        kitchen_items = []
        
        for cabinet in cabinet_data:
            try:
                item = {
                    'name': cabinet.get('name', 'Kitchen Cabinet'),
                    'description': f"{cabinet.get('category', 'Cabinet')} - {cabinet.get('materials', {}).get('cabinet_material', 'Standard Material')}",
                    'dimensions': f"{cabinet.get('dimensions', {}).get('width', 0)}mm × {cabinet.get('dimensions', {}).get('height', 0)}mm × {cabinet.get('dimensions', {}).get('depth', 0)}mm",
                    'material': cabinet.get('materials', {}).get('cabinet_material', 'Standard'),
                    'quantity': cabinet.get('specifications', {}).get('quantity', 1),
                    'unit_price': f"{cabinet.get('specifications', {}).get('cabinet_unit_rate', 0):.2f}",
                    'amount': f"{cabinet.get('specifications', {}).get('cabinet_material_price', 0):.2f}",
                    'total': f"{cabinet.get('specifications', {}).get('line_total_before_tax', 0):.2f}"
                }
                kitchen_items.append(item)
            except Exception as e:
                logger.warning(f"Error mapping cabinet item: {e}")
                continue
        
        return kitchen_items
    
    def _map_doors_items(self):
        """Map door information from cabinet breakdown"""
        cabinet_data = self.compiled_data.get('cabinet_breakdown', [])
        doors_items = []
        
        for cabinet in cabinet_data:
            try:
                # Only include if door price > 0
                door_price = cabinet.get('specifications', {}).get('door_price', 0)
                if door_price > 0:
                    item = {
                        'name': f"{cabinet.get('name', 'Cabinet')} Door",
                        'style': cabinet.get('materials', {}).get('door_material', 'Standard'),
                        'dimensions': f"{cabinet.get('dimensions', {}).get('width', 0)}mm × {cabinet.get('dimensions', {}).get('height', 0)}mm",
                        'finish': cabinet.get('materials', {}).get('door_material', 'Standard Finish'),
                        'quantity': cabinet.get('specifications', {}).get('quantity', 1),
                        'unit_price': f"{cabinet.get('specifications', {}).get('door_unit_rate', 0):.2f}",
                        'total': f"{door_price:.2f}"
                    }
                    doors_items.append(item)
            except Exception as e:
                logger.warning(f"Error mapping door item: {e}")
                continue
        
        return doors_items
    
    def _map_accessories_items(self):
        """Map accessories to template format"""
        accessories_data = self.compiled_data.get('accessories_detailed', [])
        accessories_items = []
        
        for accessory in accessories_data:
            try:
                item = {
                    'name': accessory.get('name', 'Accessory'),
                    'description': f"{accessory.get('category', 'Hardware')} for {accessory.get('line_item_cabinet', 'Cabinet')}",
                    'brand': accessory.get('brand', 'Standard'),
                    'quantity': accessory.get('specifications', {}).get('quantity', 1),
                    'unit_price': f"{accessory.get('specifications', {}).get('unit_price', 0):.2f}",
                    'total': f"{accessory.get('specifications', {}).get('total_price', 0):.2f}"
                }
                accessories_items.append(item)
            except Exception as e:
                logger.warning(f"Error mapping accessory item: {e}")
                continue
        
        return accessories_items
    
    def _map_lighting_items(self):
        """Map lighting information"""
        lighting_data = self.compiled_data.get('lighting_specifications', {})
        lighting_breakdown = lighting_data.get('lighting_breakdown', [])
        lighting_items = []
        
        for light in lighting_breakdown:
            try:
                item = {
                    'name': f"LED Lighting - {light.get('material', 'Standard')}",
                    'type': 'Under Cabinet & Work Top Lighting',
                    'wattage': light.get('specifications', {}).get('led_specification', 'Standard LED'),
                    'color_temperature': '3000K Warm White',
                    'quantity': 1,
                    'unit_price': f"{light.get('cost_breakdown', {}).get('total_cost', 0):.2f}",
                    'total': f"{light.get('cost_breakdown', {}).get('total_cost', 0):.2f}"
                }
                lighting_items.append(item)
            except Exception as e:
                logger.warning(f"Error mapping lighting item: {e}")
                continue
        
        return lighting_items
    
    def _map_pricing_summary(self):
        """Map pricing calculations to template format"""
        calculations = self.compiled_data.get('calculations', {})
        
        # Get formatted values or calculate them
        kitchen_total = calculations.get('subtotal_cabinets', 0)
        doors_total = calculations.get('subtotal_doors', 0) 
        accessories_total = calculations.get('subtotal_accessories', 0)
        lighting_total = calculations.get('lighting_total', 0)
        
        subtotal = kitchen_total + doors_total + accessories_total + lighting_total
        
        # Get discount info
        discount_percentage = calculations.get('discount_percentage', 0)
        discount_amount = calculations.get('discount_amount', 0)
        
        # Tax calculation
        tax_amount = calculations.get('gst_amount', 0)
        
        # Final total
        final_total = calculations.get('grand_total', subtotal + tax_amount - discount_amount)
        
        return {
            'kitchen_total': f"{kitchen_total:.2f}",
            'doors_total': f"{doors_total:.2f}",
            'accessories_total': f"{accessories_total:.2f}",
            'lighting_total': f"{lighting_total:.2f}",
            'subtotal': f"{subtotal:.2f}",
            'discount_percentage': discount_percentage,
            'discount_amount': f"{discount_amount:.2f}",
            'discount_reason': calculations.get('discount_reason', ''),
            'tax_percentage': '18',  # GST rate
            'tax_amount': f"{tax_amount:.2f}",
            'total': f"{final_total:.2f}"
        }
    
    def _map_timeline_info(self):
        """Create timeline information"""
        return [
            {
                'name': 'Design Finalization',
                'duration': '3-5 days',
                'description': 'Final design approval and material selection'
            },
            {
                'name': 'Manufacturing',
                'duration': '15-20 days',
                'description': 'Custom manufacturing of kitchen components'
            },
            {
                'name': 'Installation',
                'duration': '3-5 days',
                'description': 'Professional installation and finishing'
            }
        ]
    
    def _map_warranty_info(self):
        """Create warranty information"""
        return {
            'description': '2 years comprehensive warranty on manufacturing defects. 1 year warranty on hardware and accessories.'
        }
    
    def _map_special_instructions(self):
        """Map special instructions"""
        project_data = self.compiled_data.get('project_info', {})
        customer_notes = self.compiled_data.get('customer_notes', {})
        
        instructions = []
        
        if project_data.get('notes'):
            instructions.append(f"Project Notes: {project_data['notes']}")
        
        if customer_notes.get('delivery_instructions'):
            instructions.append(f"Delivery: {customer_notes['delivery_instructions']}")
        
        if customer_notes.get('installation_requirements'):
            instructions.append(f"Installation: {customer_notes['installation_requirements']}")
        
        return '. '.join(instructions) if instructions else ''
    
    def _create_fallback_data(self):
        """Create minimal fallback data if mapping fails"""
        logger.warning("Creating fallback template data due to mapping errors")
        
        return {
            'company_info': {
                'name': 'Speisekamer',
                'tagline': 'Premium Kitchen Solutions',
                'phone': '+91-9876-543210',
                'email': 'info@speisekamer.com'
            },
            'project_info': {
                'project_name': 'Kitchen Project',
                'project_type': 'Kitchen Design'
            },
            'customer_info': {
                'name': 'Customer',
                'email': 'customer@email.com',
                'phone': '+91-XXXXXXXXXX'
            },
            'quotation_info': {
                'quotation_number': 'SPK-000001',
                'date': '2024-01-01'
            },
            'kitchen_items': [],
            'doors_items': [],
            'accessories_items': [],
            'lighting_items': [],
            'pricing_summary': {
                'subtotal': '0.00',
                'total': '0.00'
            },
            'timeline_info': [],
            'warranty_info': {'description': 'Standard warranty terms apply.'},
            'special_instructions': ''
        }