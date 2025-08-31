
from django.core.files.storage import default_storage


# Add logging setup
import logging
logger = logging.getLogger('quotation_pdf')
import logging









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