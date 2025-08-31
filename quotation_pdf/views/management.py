from django.http import JsonResponse, HttpResponse
from django.views import View
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
import logging




from ..models import (
    QuotationPDFHistory
)


logger = logging.getLogger('quotation_pdf')




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








