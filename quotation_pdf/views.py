from django.http import JsonResponse, HttpResponse, Http404
from django.views import View
from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.mail import EmailMessage
from django.urls import reverse
import json
import os
import logging
from datetime import datetime, timedelta
import time
import secrets

from .services import QuotationPDFGenerator, QuotationPDFDataCompiler, PDFManager
from .models import *;
from pricing.models import Project

logger = logging.getLogger('quotation_pdf')


class GenerateQuotationPDFView(View):
    """Generate PDF quotation with heavy dependencies"""
    
    def post(self, request, project_id):
        start_time = time.time()
        
        try:
            logger.info(f"PDF generation request for project {project_id}")
            
            # Validate project exists
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Project with ID {project_id} not found'
                }, status=404)
            
            # Parse customizations from request
            customizations = {}
            if request.content_type == 'application/json':
                try:
                    body = json.loads(request.body)
                    customizations = body
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in request body: {e}")
                    pass
            else:
                customizations = dict(request.POST.items())
            
            logger.info(f"PDF customizations: {customizations}")
            
            # Generate PDF using the heavy dependencies
            generator = QuotationPDFGenerator(project_id, customizations)
            result = generator.generate_pdf()
            
            generation_time = time.time() - start_time
            logger.info(f"PDF generation completed in {generation_time:.2f} seconds")
            
            if result['success']:
                # Return success response with download info
                response_data = {
                    'success': True,
                    'message': 'PDF generated successfully',
                    'filename': result['filename'],
                    'file_size': result['file_size'],
                    'file_size_formatted': self._format_file_size(result['file_size']),
                    'download_url': result['download_url'],
                    'generation_time': round(generation_time, 2),
                    'template_type': customizations.get('template_type', 'DETAILED'),
                    'project_id': str(project_id),
                    'history_id': str(result.get('history_id')) if result.get('history_id') else None
                }
                
                # Update history record with generation time
                if result.get('history_id'):
                    try:
                        history_record = QuotationPDFHistory.objects.get(id=result['history_id'])
                        history_record.generation_time_seconds = generation_time
                        history_record.save()
                    except QuotationPDFHistory.DoesNotExist:
                        pass
                
                return JsonResponse(response_data, status=200)
            else:
                # Return error response
                return JsonResponse({
                    'success': False,
                    'error': result['error'],
                    'generation_time': round(generation_time, 2)
                }, status=500)
                
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Unexpected error in PDF generation: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'generation_time': round(generation_time, 2)
            }, status=500)
    
    def _format_file_size(self, bytes_size):
        """Format file size in human readable format"""
        if not bytes_size:
            return 'N/A'
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"


class DownloadQuotationPDFView(View):
    """Download generated PDF"""
    
    def get(self, request, pdf_id):
        try:
            # Get PDF history record
            pdf_record = get_object_or_404(QuotationPDFHistory, id=pdf_id)
            
            # Check if file exists
            file_path = pdf_record.file_path
            if not default_storage.exists(file_path):
                return JsonResponse({
                    'error': 'PDF file not found'
                }, status=404)
            
            # Get file content
            try:
                file_obj = default_storage.open(file_path, 'rb')
                file_content = file_obj.read()
                file_obj.close()
            except Exception as e:
                logger.error(f"Error reading PDF file {file_path}: {str(e)}")
                return JsonResponse({
                    'error': 'Failed to read PDF file'
                }, status=500)
            
            # Update download count
            pdf_record.download_count += 1
            pdf_record.save()
            
            # Return PDF response
            response = HttpResponse(file_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{pdf_record.filename}"'
            response['Content-Length'] = len(file_content)
            
            logger.info(f"PDF downloaded: {pdf_record.filename}")
            return response
            
        except Exception as e:
            logger.error(f"Error in PDF download: {str(e)}")
            return JsonResponse({
                'error': f'Download failed: {str(e)}'
            }, status=500)


class PreviewQuotationPDFView(View):
    """Preview PDF in browser"""
    
    def post(self, request, project_id):
        try:
            # Parse customizations
            customizations = {}
            if request.content_type == 'application/json':
                try:
                    body = json.loads(request.body)
                    customizations = body
                except json.JSONDecodeError:
                    pass
            
            # Generate PDF preview
            generator = QuotationPDFGenerator(project_id, customizations)
            result = generator.generate_pdf()
            
            if result['success']:
                # Return PDF for preview
                response = HttpResponse(result['pdf_bytes'], content_type='application/pdf')
                response['Content-Disposition'] = f'inline; filename="preview_{result["filename"]}"'
                return response
            else:
                return JsonResponse({
                    'error': result['error']
                }, status=500)
                
        except Exception as e:
            return JsonResponse({
                'error': f'Preview generation failed: {str(e)}'
            }, status=500)


class QuotationPDFHistoryView(View):
    """Get PDF history for a project"""
    
    def get(self, request, project_id):
        try:
            # Get PDF history for the project
            history_qs = QuotationPDFHistory.objects.filter(
                project_id=project_id
            ).order_by('-created_at')
            
            # Apply filters if provided
            status_filter = request.GET.get('status')
            if status_filter:
                history_qs = history_qs.filter(status=status_filter)
            
            limit = request.GET.get('limit')
            if limit:
                try:
                    limit = int(limit)
                    history_qs = history_qs[:limit]
                except ValueError:
                    pass
            
            # Serialize history data
            history_data = []
            for record in history_qs:
                history_data.append({
                    'id': str(record.id),
                    'project_id': str(record.project_id),
                    'project_name': record.project_name,
                    'customer_name': record.customer_name,
                    'filename': record.filename,
                    'file_path': record.file_path,
                    'file_size': record.file_size,
                    'file_size_formatted': record.file_size_formatted,
                    'template_type': record.template_type,
                    'total_amount': float(record.total_amount),
                    'discount_applied': float(record.discount_applied),
                    'final_amount': float(record.final_amount),
                    'currency': record.currency,
                    'status': record.status,
                    'generation_time_seconds': record.generation_time_seconds,
                    'error_message': record.error_message,
                    'email_sent_count': record.email_sent_count,
                    'download_count': record.download_count,
                    'view_count': record.view_count,
                    'created_at': record.created_at.isoformat(),
                    'updated_at': record.updated_at.isoformat(),
                    'customizations': record.customizations
                })
            
            return JsonResponse(history_data, safe=False)
            
        except Exception as e:
            logger.error(f"Error fetching PDF history: {str(e)}")
            return JsonResponse({
                'error': f'Failed to fetch PDF history: {str(e)}'
            }, status=500)


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


class EmailQuotationPDFView(View):
    """Email quotation PDF to customer"""
    
    def post(self, request, pdf_id):
        try:
            # Get PDF record
            pdf_record = get_object_or_404(QuotationPDFHistory, id=pdf_id)
            
            # Parse request data
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            
            recipient_email = data.get('recipient_email')
            subject = data.get('subject', f'Kitchen Quotation - {pdf_record.project_name}')
            message = data.get('message', 'Please find attached your kitchen quotation.')
            
            if not recipient_email:
                return JsonResponse({
                    'error': 'Recipient email is required'
                }, status=400)
            
            # Check if file exists
            if not default_storage.exists(pdf_record.file_path):
                return JsonResponse({
                    'error': 'PDF file not found'
                }, status=404)
            
            # Get file content
            file_obj = default_storage.open(pdf_record.file_path, 'rb')
            file_content = file_obj.read()
            file_obj.close()
            
            # Create email
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email]
            )
            
            # Attach PDF
            email.attach(pdf_record.filename, file_content, 'application/pdf')
            
            # Send email
            email.send()
            
            # Update email count
            pdf_record.email_sent_count += 1
            pdf_record.last_emailed_at = timezone.now()
            pdf_record.save()
            
            logger.info(f"PDF emailed successfully: {pdf_record.filename} to {recipient_email}")
            
            return JsonResponse({
                'success': True,
                'message': 'Email sent successfully'
            })
            
        except Exception as e:
            logger.error(f"Error emailing PDF: {str(e)}")
            return JsonResponse({
                'error': f'Failed to send email: {str(e)}'
            }, status=500)


class CreatePDFShareLinkView(View):
    """Create shareable link for PDF"""
    
    def post(self, request, pdf_id):
        try:
            # Get PDF record
            pdf_record = get_object_or_404(QuotationPDFHistory, id=pdf_id)
            
            # Parse request data
            data = json.loads(request.body) if request.content_type == 'application/json' else {}
            
            # Create share link
            share_link = QuotationPDFShareLink.objects.create(
                pdf_history=pdf_record,
                share_token=secrets.token_urlsafe(32),
                expires_at=timezone.now() + timedelta(days=data.get('expires_days', 30)),
                max_downloads=data.get('max_downloads', 10),
                max_views=data.get('max_views', 50),
                created_by=request.user if request.user.is_authenticated else None
            )
            
            # Generate share URL
            share_url = request.build_absolute_uri(
                reverse('quotation_pdf:shared_pdf', kwargs={'token': share_link.share_token})
            )
            
            return JsonResponse({
                'success': True,
                'share_url': share_url,
                'share_token': share_link.share_token,
                'expires_at': share_link.expires_at.isoformat(),
                'max_downloads': share_link.max_downloads,
                'max_views': share_link.max_views
            })
            
        except Exception as e:
            logger.error(f"Error creating share link: {str(e)}")
            return JsonResponse({
                'error': f'Failed to create share link: {str(e)}'
            }, status=500)


class SharedPDFView(View):
    """Access PDF via share link"""
    
    def get(self, request, token):
        try:
            # Get share link
            share_link = get_object_or_404(QuotationPDFShareLink, share_token=token)
            
            # Check if link is still valid
            if not share_link.can_access():
                return JsonResponse({
                    'error': 'Share link has expired or reached access limits'
                }, status=403)
            
            # Get PDF record
            pdf_record = share_link.pdf_history
            
            # Check if file exists
            if not default_storage.exists(pdf_record.file_path):
                return JsonResponse({
                    'error': 'PDF file not found'
                }, status=404)
            
            # Determine action (view or download)
            action = request.GET.get('action', 'view')
            
            # Log access
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            share_link.log_access(client_ip, action)
            
            # Get file content
            file_obj = default_storage.open(pdf_record.file_path, 'rb')
            file_content = file_obj.read()
            file_obj.close()
            
            # Return PDF response
            response = HttpResponse(file_content, content_type='application/pdf')
            
            if action == 'download':
                response['Content-Disposition'] = f'attachment; filename="{pdf_record.filename}"'
            else:
                response['Content-Disposition'] = f'inline; filename="{pdf_record.filename}"'
            
            response['Content-Length'] = len(file_content)
            
            return response
            
        except Exception as e:
            logger.error(f"Error accessing shared PDF: {str(e)}")
            return JsonResponse({
                'error': f'Access failed: {str(e)}'
            }, status=500)


class PDFDataPreviewView(View):
    """Preview PDF data without generating actual PDF"""
    
    def post(self, request, project_id):
        try:
            # Parse customizations
            customizations = {}
            if request.content_type == 'application/json':
                try:
                    body = json.loads(request.body)
                    customizations = body
                except json.JSONDecodeError:
                    pass
            
            # Compile PDF data using data compiler
            compiler = QuotationPDFDataCompiler(project_id, customizations)
            pdf_data = compiler.compile_complete_data()
            
            # Return data preview
            preview_data = {
                'project_info': pdf_data.get('project_info', {}),
                'customer_info': pdf_data.get('customer_info', {}),
                'calculations': pdf_data.get('calculations', {}),
                'sections_summary': {
                    'cabinet_sections_count': len(pdf_data.get('cabinet_sections', [])),
                    'accessories_count': len(pdf_data.get('accessories', [])),
                    'lighting_items_count': len(pdf_data.get('lighting_items', [])),
                    'plan_images_count': len(pdf_data.get('plan_images', [])),
                    'total_line_items': len(pdf_data.get('line_items', []))
                },
                'template_info': {
                    'template_type': customizations.get('template_type', 'DETAILED'),
                    'estimated_pages': self._estimate_pages(pdf_data, customizations)
                }
            }
            
            return JsonResponse(preview_data)
            
        except Exception as e:
            logger.error(f"Error generating PDF data preview: {str(e)}")
            return JsonResponse({
                'error': f'Preview failed: {str(e)}'
            }, status=500)
    
    def _estimate_pages(self, pdf_data, customizations):
        """Estimate number of pages for PDF"""
        base_pages = 1  # Cover page
        
        template_type = customizations.get('template_type', 'DETAILED')
        
        if template_type == 'SIMPLE':
            return base_pages + 1  # Just summary page
        
        # Add pages based on content
        if customizations.get('include_cabinet_details', True):
            cabinet_sections = len(pdf_data.get('cabinet_sections', []))
            base_pages += max(1, cabinet_sections // 3)  # ~3 sections per page
        
        if customizations.get('include_accessories', True):
            accessories_count = len(pdf_data.get('accessories', []))
            base_pages += max(1, accessories_count // 6)  # ~6 accessories per page
        
        if customizations.get('include_plan_images', True):
            images_count = len(pdf_data.get('plan_images', []))
            base_pages += max(1, images_count // 2)  # ~2 images per page
        
        if customizations.get('include_lighting', True):
            lighting_count = len(pdf_data.get('lighting_items', []))
            if lighting_count > 0:
                base_pages += 1
        
        if customizations.get('include_terms_conditions', True):
            base_pages += 1
        
        return min(base_pages, 12)  # Cap at 12 pages


class PDFBatchGenerationView(View):
    """Generate PDFs for multiple projects"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            project_ids = data.get('project_ids', [])
            batch_customizations = data.get('customizations', {})
            
            if not project_ids:
                return JsonResponse({
                    'error': 'No project IDs provided'
                }, status=400)
            
            results = []
            
            for project_id in project_ids:
                try:
                    # Generate PDF for each project
                    generator = QuotationPDFGenerator(project_id, batch_customizations)
                    result = generator.generate_pdf()
                    
                    results.append({
                        'project_id': str(project_id),
                        'success': result['success'],
                        'filename': result.get('filename'),
                        'error': result.get('error')
                    })
                    
                except Exception as e:
                    results.append({
                        'project_id': str(project_id),
                        'success': False,
                        'error': str(e)
                    })
            
            # Summary statistics
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful
            
            return JsonResponse({
                'success': True,
                'total_processed': len(results),
                'successful': successful,
                'failed': failed,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error in batch PDF generation: {str(e)}")
            return JsonResponse({
                'error': f'Batch generation failed: {str(e)}'
            }, status=500)


class PDFAnalyticsView(View):
    """Get PDF analytics and statistics"""
    
    def get(self, request):
        try:
            # Date range filters
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            
            queryset = QuotationPDFHistory.objects.all()
            
            if start_date:
                queryset = queryset.filter(created_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(created_at__lte=end_date)
            
            # Basic statistics
            total_pdfs = queryset.count()
            successful_pdfs = queryset.filter(status='COMPLETED').count()
            failed_pdfs = queryset.filter(status='FAILED').count()
            
            # Template usage statistics
            template_stats = {}
            for record in queryset:
                template_type = record.template_type
                if template_type not in template_stats:
                    template_stats[template_type] = 0
                template_stats[template_type] += 1
            
            # Download statistics
            total_downloads = sum(record.download_count for record in queryset)
            avg_downloads = total_downloads / total_pdfs if total_pdfs > 0 else 0
            
            # Generation time statistics
            generation_times = [
                record.generation_time_seconds 
                for record in queryset 
                if record.generation_time_seconds is not None
            ]
            
            avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0
            
            # File size statistics
            file_sizes = [record.file_size for record in queryset if record.file_size > 0]
            avg_file_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
            
            analytics_data = {
                'summary': {
                    'total_pdfs': total_pdfs,
                    'successful_pdfs': successful_pdfs,
                    'failed_pdfs': failed_pdfs,
                    'success_rate': (successful_pdfs / total_pdfs * 100) if total_pdfs > 0 else 0
                },
                'template_usage': template_stats,
                'download_stats': {
                    'total_downloads': total_downloads,
                    'average_downloads_per_pdf': round(avg_downloads, 2)
                },
                'performance': {
                    'average_generation_time': round(avg_generation_time, 2),
                    'average_file_size': round(avg_file_size, 2)
                },
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
            
            return JsonResponse(analytics_data)
            
        except Exception as e:
            logger.error(f"Error fetching PDF analytics: {str(e)}")
            return JsonResponse({
                'error': f'Failed to fetch analytics: {str(e)}'
            }, status=500)


class DeletePDFView(View):
    """Delete PDF and its history record"""
    
    def delete(self, request, pdf_id):
        try:
            # Get PDF record
            pdf_record = get_object_or_404(QuotationPDFHistory, id=pdf_id)
            
            # Delete file from storage
            if pdf_record.file_path and default_storage.exists(pdf_record.file_path):
                try:
                    default_storage.delete(pdf_record.file_path)
                    logger.info(f"Deleted PDF file: {pdf_record.file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete PDF file: {str(e)}")
            
            # Delete history record
            pdf_record.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'PDF deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deleting PDF: {str(e)}")
            return JsonResponse({
                'error': f'Failed to delete PDF: {str(e)}'
            }, status=500)


class RegeneratePDFView(View):
    """Regenerate PDF with same or updated customizations"""
    
    def post(self, request, pdf_id):
        try:
            # Get original PDF record
            original_pdf = get_object_or_404(QuotationPDFHistory, id=pdf_id)
            
            # Parse new customizations (optional)
            new_customizations = {}
            if request.content_type == 'application/json':
                try:
                    body = json.loads(request.body)
                    new_customizations = body.get('customizations', {})
                except json.JSONDecodeError:
                    pass
            
            # Use original customizations if no new ones provided
            customizations = new_customizations if new_customizations else original_pdf.customizations
            
            # Generate new PDF
            generator = QuotationPDFGenerator(original_pdf.project_id, customizations)
            result = generator.generate_pdf()
            
            if result['success']:
                # Mark old PDF as replaced
                original_pdf.status = 'REPLACED'
                original_pdf.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'PDF regenerated successfully',
                    'new_pdf_id': str(result.get('history_id')),
                    'filename': result['filename'],
                    'download_url': result['download_url']
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                }, status=500)
            
        except Exception as e:
            logger.error(f"Error regenerating PDF: {str(e)}")
            return JsonResponse({
                'error': f'Failed to regenerate PDF: {str(e)}'
            }, status=500)


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