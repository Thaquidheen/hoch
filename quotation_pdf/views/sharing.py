
from django.http import JsonResponse, HttpResponse
from django.views import View

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.mail import EmailMessage
from django.urls import reverse

import json

import logging
from datetime import timedelta

import secrets


from ..models import (
    QuotationPDFHistory,

    QuotationPDFShare  # Use this instead of QuotationPDFShareLink
)
from pricing.models import Project

logger = logging.getLogger('quotation_pdf')



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
            share_link = QuotationPDFShare.objects.create(
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
            share_link = get_object_or_404(QuotationPDFShare, share_token=token)
            
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


