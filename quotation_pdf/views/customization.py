from django.http import JsonResponse
from django.views import View
import json
import logging



from ..models import (
 QuotationPDFTemplate, 
    QuotationPDFCustomization, QuotationPDFSettings,

)
from pricing.models import Project

logger = logging.getLogger('quotation_pdf')





class GetPDFCustomizationView(View):
    """Get PDF customization settings for a project"""
    
    def get(self, request, project_id):
        try:
            # Try to get existing customization
            try:
                customization = QuotationPDFCustomization.objects.get(project_id=project_id)
                
                settings_data = {
                    'template_type': customization.template.template_type if customization.template else 'DETAILED',
                    'include_cabinet_details': customization.include_cabinet_details,
                    'include_door_details': customization.include_door_details,
                    'include_accessories': customization.include_accessories,
                    'include_accessory_images': customization.include_accessory_images,
                    'include_plan_images': customization.include_plan_images,
                    'include_lighting': customization.include_lighting,
                    'show_item_codes': customization.show_item_codes,
                    'show_dimensions': customization.show_dimensions,
                    'include_warranty_info': customization.include_warranty_info,
                    'include_terms_conditions': customization.include_terms_conditions,
                    'header_logo': customization.header_logo,
                    'footer_contact': customization.footer_contact,
                    'page_numbers': customization.page_numbers,
                    'watermark': customization.watermark,
                    'color_theme': customization.color_theme,
                    'discount_percentage': float(customization.discount_percentage),
                    'discount_amount': float(customization.discount_amount),
                    'discount_reason': customization.discount_reason,
                    'special_instructions': customization.special_instructions,
                    'installation_notes': customization.installation_notes,
                    'timeline_notes': customization.timeline_notes,
                    'custom_requirements': customization.custom_requirements,
                    'selected_plan_images': customization.selected_plan_images
                }
                
            except QuotationPDFCustomization.DoesNotExist:
                # Return default settings
                settings_data = {
                    'template_type': 'DETAILED',
                    'include_cabinet_details': True,
                    'include_door_details': True,
                    'include_accessories': True,
                    'include_accessory_images': True,
                    'include_plan_images': True,
                    'include_lighting': True,
                    'show_item_codes': True,
                    'show_dimensions': True,
                    'include_warranty_info': True,
                    'include_terms_conditions': True,
                    'header_logo': True,
                    'footer_contact': True,
                    'page_numbers': True,
                    'watermark': False,
                    'color_theme': 'default',
                    'discount_percentage': 0,
                    'discount_amount': 0,
                    'discount_reason': '',
                    'special_instructions': '',
                    'installation_notes': '',
                    'timeline_notes': '',
                    'custom_requirements': '',
                    'selected_plan_images': []
                }
            
            return JsonResponse(settings_data)
            
        except Exception as e:
            logger.error(f"Error getting PDF customization: {str(e)}")
            return JsonResponse({
                'error': f'Failed to get customization settings: {str(e)}'
            }, status=500)
        

class SavePDFCustomizationView(View):
    """Save PDF customization settings for a project"""
    
    def post(self, request, project_id):
        try:
            # Parse request data
            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({
                        'error': 'Invalid JSON data'
                    }, status=400)
            else:
                data = dict(request.POST.items())
            
            # Get or create customization record
            customization, created = QuotationPDFCustomization.objects.get_or_create(
                project_id=project_id,
                defaults={'created_by': request.user if request.user.is_authenticated else None}
            )
            
            # Update customization fields
            template_type = data.get('template_type', 'DETAILED')
            if template_type:
                try:
                    template = QuotationPDFTemplate.objects.get(template_type=template_type, is_active=True)
                    customization.template = template
                except QuotationPDFTemplate.DoesNotExist:
                    pass
            
            # Boolean fields
            bool_fields = [
                'include_cabinet_details', 'include_door_details', 'include_accessories',
                'include_accessory_images', 'include_plan_images', 'include_lighting',
                'show_item_codes', 'show_dimensions', 'include_warranty_info',
                'include_terms_conditions', 'header_logo', 'footer_contact',
                'page_numbers', 'watermark'
            ]
            
            for field in bool_fields:
                if field in data:
                    setattr(customization, field, bool(data[field]))
            
            # String fields
            string_fields = [
                'color_theme', 'discount_reason', 'special_instructions',
                'installation_notes', 'timeline_notes', 'custom_requirements'
            ]
            
            for field in string_fields:
                if field in data:
                    setattr(customization, field, str(data[field]))
            
            # Decimal fields
            if 'discount_percentage' in data:
                customization.discount_percentage = float(data['discount_percentage'])
            if 'discount_amount' in data:
                customization.discount_amount = float(data['discount_amount'])
            
            # JSON fields
            if 'selected_plan_images' in data:
                customization.selected_plan_images = data['selected_plan_images']
            
            customization.save()
            
            return JsonResponse({
                'success': True,
                'message': 'PDF customization settings saved successfully',
                'created': created
            })
            
        except Exception as e:
            logger.error(f"Error saving PDF customization: {str(e)}")
            return JsonResponse({
                'error': f'Failed to save customization settings: {str(e)}'
            }, status=500)



class PDFTemplatesListView(View):
    """Get available PDF templates"""
    
    def get(self, request):
        try:
            templates_qs = QuotationPDFTemplate.objects.filter(is_active=True).order_by('template_type', 'name')
            
            templates_data = []
            for template in templates_qs:
                templates_data.append({
                    'id': str(template.id),
                    'name': template.name,
                    'template_type': template.template_type,
                    'description': template.description,
                    'is_active': template.is_active,
                    'is_default': template.is_default,
                    'created_at': template.created_at.isoformat(),
                    # Add mock data for frontend compatibility
                    'features': self._get_template_features(template.template_type),
                    'estimated_pages': self._get_estimated_pages(template.template_type),
                    'best_for': self._get_best_for(template.template_type),
                    'category': self._get_category(template.template_type)
                })
            
            return JsonResponse(templates_data, safe=False)
            
        except Exception as e:
            logger.error(f"Error fetching templates: {str(e)}")
            return JsonResponse({
                'error': f'Failed to fetch templates: {str(e)}'
            }, status=500)
    
    def _get_template_features(self, template_type):
        """Get features for template type"""
        features_map = {
            'DETAILED': ['Product Images', 'Floor Plans', 'Detailed Specs', 'Warranty Info', 'Terms & Conditions'],
            'STANDARD': ['Line Items', 'Basic Images', 'Pricing Summary', 'Contact Info'],
            'SIMPLE': ['Line Items', 'Total Amount', 'Basic Contact']
        }
        return features_map.get(template_type, [])
    
    def _get_estimated_pages(self, template_type):
        """Get estimated pages for template type"""
        pages_map = {
            'DETAILED': '6-8 pages',
            'STANDARD': '3-4 pages',
            'SIMPLE': '1-2 pages'
        }
        return pages_map.get(template_type, '3-4 pages')
    
    def _get_best_for(self, template_type):
        """Get best use case for template type"""
        best_for_map = {
            'DETAILED': 'High-value projects, detailed presentations',
            'STANDARD': 'Most projects, balanced detail',
            'SIMPLE': 'Quick quotes, simple projects'
        }
        return best_for_map.get(template_type, 'General use')
    
    def _get_category(self, template_type):
        """Get category for template type"""
        category_map = {
            'DETAILED': 'premium',
            'STANDARD': 'standard',
            'SIMPLE': 'basic'
        }
        return category_map.get(template_type, 'standard')


class ValidateCustomizationView(View):
    """Validate PDF customization before generation"""
    
    def post(self, request, project_id):
        try:
            # Parse customizations
            customizations = {}
            if request.content_type == 'application/json':
                try:
                    body = json.loads(request.body)
                    customizations = body
                except json.JSONDecodeError:
                    return JsonResponse({
                        'error': 'Invalid JSON data'
                    }, status=400)
            
            # Validation logic
            errors = []
            warnings = []
            
            # Validate discount values
            discount_pct = float(customizations.get('discount_percentage', 0))
            discount_amt = float(customizations.get('discount_amount', 0))
            
            if discount_pct < 0 or discount_pct > 100:
                errors.append('Discount percentage must be between 0 and 100')
            
            if discount_amt < 0:
                errors.append('Discount amount cannot be negative')
            
            if discount_pct > 0 and discount_amt > 0:
                warnings.append('Both percentage and fixed discount are set. Only one will be applied.')
            
            if (discount_pct > 0 or discount_amt > 0) and not customizations.get('discount_reason'):
                warnings.append('Consider adding a discount reason for transparency')
            
            # Validate template type
            template_type = customizations.get('template_type', 'DETAILED')
            if template_type not in ['DETAILED', 'STANDARD', 'SIMPLE']:
                errors.append('Invalid template type selected')
            
            # Validate project exists
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                errors.append(f'Project with ID {project_id} not found')
            
            # Check if project has required data
            if 'project' in locals():
                if not project.customer:
                    warnings.append('Project has no customer assigned')
                
                # Check for line items if include details is enabled
                if customizations.get('include_cabinet_details', True):
                    line_items_count = project.projectlineitem_set.count()
                    if line_items_count == 0:
                        warnings.append('No line items found for cabinet details')
            
            # Validate selected plan images
            selected_images = customizations.get('selected_plan_images', [])
            if customizations.get('include_plan_images', True) and len(selected_images) == 0:
                warnings.append('No plan images selected but plan images are enabled')
            
            return JsonResponse({
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'suggestions': self._get_suggestions(customizations)
            })
            
        except Exception as e:
            logger.error(f"Error validating customization: {str(e)}")
            return JsonResponse({
                'error': f'Validation failed: {str(e)}'
            }, status=500)
    
    def _get_suggestions(self, customizations):
        """Get suggestions based on customizations"""
        suggestions = []
        
        template_type = customizations.get('template_type', 'DETAILED')
        
        if template_type == 'SIMPLE':
            suggestions.append('Simple template is best for quick quotes with minimal details')
        elif template_type == 'DETAILED':
            suggestions.append('Detailed template provides comprehensive project information')
        
        if not customizations.get('include_warranty_info', True):
            suggestions.append('Consider including warranty information for customer confidence')
        
        if not customizations.get('include_terms_conditions', True):
            suggestions.append('Including terms and conditions helps protect your business')
        
        return suggestions



class PDFSettingsView(View):
    """Manage global PDF settings"""
    
    def get(self, request):
        try:
            # Get or create global settings
            settings_obj, created = QuotationPDFSettings.objects.get_or_create(
                pk=1,
                defaults={
                    'default_template_type': 'DETAILED',
                    'max_file_size_mb': 50,
                    'pdf_storage_days': 365,
                    'watermark_text': '',
                    'company_logo_url': '',
                    'default_color_theme': 'default'
                }
            )
            
            settings_data = {
                'default_template_type': settings_obj.default_template_type,
                'max_file_size_mb': settings_obj.max_file_size_mb,
                'pdf_storage_days': settings_obj.pdf_storage_days,
                'watermark_text': settings_obj.watermark_text,
                'company_logo_url': settings_obj.company_logo_url,
                'default_color_theme': settings_obj.default_color_theme,
                'auto_cleanup_enabled': settings_obj.auto_cleanup_enabled,
                'email_notifications_enabled': settings_obj.email_notifications_enabled
            }
            
            return JsonResponse(settings_data)
            
        except Exception as e:
            logger.error(f"Error fetching PDF settings: {str(e)}")
            return JsonResponse({
                'error': f'Failed to fetch settings: {str(e)}'
            }, status=500)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            # Get or create settings
            settings_obj, created = QuotationPDFSettings.objects.get_or_create(pk=1)
            
            # Update settings fields
            updatable_fields = [
                'default_template_type', 'max_file_size_mb', 'pdf_storage_days',
                'watermark_text', 'company_logo_url', 'default_color_theme',
                'auto_cleanup_enabled', 'email_notifications_enabled'
            ]
            
            for field in updatable_fields:
                if field in data:
                    setattr(settings_obj, field, data[field])
            
            settings_obj.save()
            
            return JsonResponse({
                'success': True,
                'message': 'PDF settings updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error updating PDF settings: {str(e)}")
            return JsonResponse({
                'error': f'Failed to update settings: {str(e)}'
            }, status=500)




