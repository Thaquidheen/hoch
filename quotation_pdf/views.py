
# quotation_pdf/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
import json
import logging

from pricing.models import Project
from .services import QuotationPDFGenerator, QuotationPDFDataCompiler
from .serializers import QuotationPDFCustomizationSerializer, QuotationPDFTemplateSerializer

logger = logging.getLogger(__name__)

class GenerateQuotationPDFView(APIView):
    """Generate PDF for a project quotation"""
    permission_classes = [IsAuthenticated]
    
    def validate_customizations(self, customizations):
        errors = {}
        if not isinstance(customizations, dict):
            return {'customizations': 'Must be an object'}
        
        # Validate numeric fields
        if 'discount_percentage' in customizations:
            try:
                value = float(customizations['discount_percentage'])
                if value < 0 or value > 100:
                    errors['discount_percentage'] = 'Must be between 0 and 100'
            except (TypeError, ValueError):
                errors['discount_percentage'] = 'Must be a number'
        if 'discount_amount' in customizations:
            try:
                float(customizations['discount_amount'])
            except (TypeError, ValueError):
                errors['discount_amount'] = 'Must be a number'
        
        # Validate boolean fields
        bool_fields = [
            'include_cabinet_details', 'include_door_details', 'include_accessories',
            'include_accessory_images', 'include_plan_images', 'include_lighting',
            'show_item_codes', 'show_dimensions', 'include_warranty_info',
            'include_terms_conditions'
        ]
        for field in bool_fields:
            if field in customizations and not isinstance(customizations[field], bool):
                errors[field] = 'Must be a boolean'
        
        # Validate list fields
        if 'selected_plan_images' in customizations and not isinstance(customizations['selected_plan_images'], list):
            errors['selected_plan_images'] = 'Must be a list'
        
        return errors
    
    def post(self, request, project_id):
        try:
            # Verify project exists and user has access
            project = get_object_or_404(Project, id=project_id)
            
            # Extract customizations from request
            customizations = request.data.get('customizations', {})
            
            # Validate customizations
            validation_errors = self.validate_customizations(customizations)
            if validation_errors:
                return Response({
                    'error': 'Invalid customization parameters',
                    'errors': validation_errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate PDF
            generator = QuotationPDFGenerator(project_id, customizations)
            pdf_bytes = generator.generate_pdf()
            
            # Return PDF as response
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="quotation-{project_id}.pdf"'
            response['Content-Length'] = len(pdf_bytes)
            
            return response
            
        except Http404:
            return Response({
                'error': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to compile preview data',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class QuotationPDFHistoryView(APIView):
    """Get PDF generation history for a project"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, project_id):
        try:
            from .models import QuotationPDFHistory
            
            project = get_object_or_404(Project, id=project_id)
            
            history = QuotationPDFHistory.objects.filter(
                project=project
            ).order_by('-generated_at')[:10]  # Last 10 PDFs
            
            history_data = []
            for record in history:
                history_data.append({
                    'id': str(record.id),
                    'filename': record.filename,
                    'generated_at': record.generated_at,
                    'total_amount': record.total_amount,
                    'discount_applied': record.discount_applied,
                    'final_amount': record.final_amount,
                    'status': record.status,
                    'file_size': record.file_size,
                    'generated_by': record.generated_by.username if record.generated_by else None
                })
            
            return Response({
                'history': history_data
            }, status=status.HTTP_200_OK)
            
        except Project.DoesNotExist:
            return Response({
                'error': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)

class SavePDFCustomizationView(APIView):
    """Save PDF customization settings for future use"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, project_id):
        try:
            from .models import QuotationPDFCustomization, QuotationPDFTemplate
            
            project = get_object_or_404(Project, id=project_id)
            customizations = request.data.get('customizations', {})
            template_id = request.data.get('template_id')
            
            # Get or create template
            if template_id:
                template = get_object_or_404(QuotationPDFTemplate, id=template_id)
            else:
                template, _ = QuotationPDFTemplate.objects.get_or_create(
                    name='Standard Template',
                    defaults={'template_type': 'DETAILED'}
                )
            
            # Save or update customization
            pdf_customization, created = QuotationPDFCustomization.objects.update_or_create(
                project=project,
                template=template,
                defaults={
                    'include_cabinet_details': customizations.get('include_cabinet_details', True),
                    'include_door_details': customizations.get('include_door_details', True),
                    'include_accessories': customizations.get('include_accessories', True),
                    'include_accessory_images': customizations.get('include_accessory_images', True),
                    'include_plan_images': customizations.get('include_plan_images', True),
                    'include_lighting': customizations.get('include_lighting', True),
                    'discount_percentage': customizations.get('discount_percentage', 0),
                    'discount_amount': customizations.get('discount_amount', 0),
                    'discount_reason': customizations.get('discount_reason', ''),
                    'special_instructions': customizations.get('special_instructions', ''),
                    'installation_notes': customizations.get('installation_notes', ''),
                    'timeline_notes': customizations.get('timeline_notes', ''),
                    'custom_requirements': customizations.get('custom_requirements', ''),
                    'selected_plan_images': customizations.get('selected_plan_images', []),
                    'show_item_codes': customizations.get('show_item_codes', True),
                    'show_dimensions': customizations.get('show_dimensions', True),
                    'include_warranty_info': customizations.get('include_warranty_info', True),
                    'include_terms_conditions': customizations.get('include_terms_conditions', True),
                    'created_by': request.user
                }
            )
            
            return Response({
                'message': 'Customization saved successfully',
                'customization_id': str(pdf_customization.id),
                'created': created
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        except Project.DoesNotExist:
            return Response({
                'error': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)

class GetPDFCustomizationView(APIView):
    """Get saved PDF customization for a project"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, project_id):
        try:
            from .models import QuotationPDFCustomization
            
            project = get_object_or_404(Project, id=project_id)
            
            try:
                customization = QuotationPDFCustomization.objects.get(project=project)
                serializer = QuotationPDFCustomizationSerializer(customization)
                return Response({
                    'customization': serializer.data
                }, status=status.HTTP_200_OK)
                
            except QuotationPDFCustomization.DoesNotExist:
                # Return default customization
                return Response({
                    'customization': {
                        'include_cabinet_details': True,
                        'include_door_details': True,
                        'include_accessories': True,
                        'include_accessory_images': True,
                        'include_plan_images': True,
                        'include_lighting': True,
                        'discount_percentage': 0,
                        'discount_amount': 0,
                        'discount_reason': '',
                        'special_instructions': '',
                        'installation_notes': '',
                        'timeline_notes': '',
                        'custom_requirements': '',
                        'selected_plan_images': [],
                        'show_item_codes': True,
                        'show_dimensions': True,
                        'include_warranty_info': True,
                        'include_terms_conditions': True
                    }
                }, status=status.HTTP_200_OK)
            
        except Project.DoesNotExist:
            return Response({
                'error': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)


class PDFTemplatesListView(APIView):
    """List available PDF templates"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            from .models import QuotationPDFTemplate
            
            templates = QuotationPDFTemplate.objects.filter(
                is_active=True
            ).order_by('name')
            
            serializer = QuotationPDFTemplateSerializer(templates, many=True)
            
            return Response({
                'templates': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Templates list error: {str(e)}")
            return Response({
                'error': 'Failed to retrieve templates',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ValidateCustomizationView(APIView):
    """Validate customization data without saving"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, project_id):
        try:
            project = get_object_or_404(Project, id=project_id)
            customizations = request.data.get('customizations', {})
            
            # Create temporary generator to validate
            generator = GenerateQuotationPDFView()
            validation_errors = generator.validate_customizations(customizations)
            
            if validation_errors:
                return Response({
                    'valid': False,
                    'errors': validation_errors
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'valid': True,
                    'message': 'Customization data is valid'
                }, status=status.HTTP_200_OK)
                
        except Project.DoesNotExist:
            return Response({
                'error': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({
                'valid': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)