
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging

import time


from ..services.pdf_generator import QuotationPDFGenerator

from ..services.data_compiler import QuotationPDFDataCompiler

from ..models import (
    QuotationPDFHistory
)
from pricing.models import Project

logger = logging.getLogger('quotation_pdf')




@method_decorator(csrf_exempt, name='dispatch')
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







