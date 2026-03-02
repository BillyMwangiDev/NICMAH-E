"""
Document generation utilities for inventory management.
"""

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import qrcode
from PIL import Image
import io

# Import document models from inventory app
from .models import Document, DocumentItem, DocumentTemplate
DOCUMENTS_AVAILABLE = True

# Alias for compatibility
Receipt = Document
Quotation = Document
Invoice = Document


def generate_qr_code(data, size=10):
    """Generate QR code for document."""
    qr = qrcode.QRCode(version=1, box_size=size, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer.getvalue()


def generate_pdf_from_html(html_content, title="Document"):
    """Generate PDF from HTML content using ReportLab."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Add title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 12))
    
    # Add content (simplified - you might want to parse HTML properly)
    story.append(Paragraph(html_content, styles['Normal']))
    
    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content


def get_company_info(request=None):
    """Get company information from SiteSettings."""
    # Always use the official static logo from core/static/images/
    logo_url = None
    if request:
        # Build absolute URL for static logo (try SVG first, then PNG)
        try:
            # Try SVG first
            logo_url = request.build_absolute_uri('/static/images/logo.svg')
        except:
            # Fallback to PNG
            logo_url = request.build_absolute_uri('/static/images/logo.png')
    else:
        # Fallback: use STATIC_URL
        logo_url = '/static/images/logo.png'
    
    try:
        from core.models import SiteSettings
        site_settings = SiteSettings.objects.first()
        if site_settings:
            return {
                'company_name': site_settings.site_name or 'NICMAH',
                'company_tagline': site_settings.tagline or 'Quality Agricultural Solutions',
                'company_address': site_settings.address or 'Naromoru town, Timberland building near KFA',
                'company_phone': site_settings.phone_number or '0726476128/0740368581',
                'company_email': site_settings.contact_email or 'nicmahagrovet@gmail.com',
                'company_logo': logo_url,
            }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error loading company info: {str(e)}")
    
    # Fallback values
    return {
        'company_name': 'NICMAH',
        'company_tagline': 'Quality Agricultural Solutions',
        'company_address': 'Naromoru town, Timberland building near KFA',
        'company_phone': '0726476128/0740368581',
        'company_email': 'nicmahagrovet@gmail.com',
        'company_logo': logo_url,
    }


def generate_receipt_pdf(receipt, request=None):
    """Generate PDF for receipt."""
    if not DOCUMENTS_AVAILABLE:
        return None
    
    company_info = get_company_info(request)
    
    # Create HTML content for receipt
    html_content = render_to_string('inventory/receipt_pdf.html', {
        'receipt': receipt,
        'items': receipt.documentitem_set.all(),
        **company_info,
    })
    
    return generate_pdf_from_html(html_content, f"Receipt {receipt.document_number}")


def generate_quotation_pdf(quotation, request=None):
    """Generate PDF for quotation."""
    if not DOCUMENTS_AVAILABLE:
        return None
    
    company_info = get_company_info(request)
    
    # Create HTML content for quotation
    html_content = render_to_string('inventory/quotation_pdf.html', {
        'quotation': quotation,
        'items': quotation.documentitem_set.all(),
        **company_info,
    })
    
    return generate_pdf_from_html(html_content, f"Quotation {quotation.document_number}")


def generate_invoice_pdf(invoice, request=None):
    """Generate PDF for invoice."""
    if not DOCUMENTS_AVAILABLE:
        return None
    
    company_info = get_company_info(request)
    
    # Create HTML content for invoice
    html_content = render_to_string('inventory/invoice_pdf.html', {
        'invoice': invoice,
        'items': invoice.documentitem_set.all(),
        **company_info,
    })
    
    return generate_pdf_from_html(html_content, f"Invoice {invoice.document_number}")


def generate_purchase_order_pdf(po, request=None):
    """Generate PDF for purchase order."""
    if not DOCUMENTS_AVAILABLE:
        return None
    
    company_info = get_company_info(request)
    
    # Create HTML content for purchase order
    html_content = render_to_string('inventory/purchase_order_pdf.html', {
        'po': po,
        'items': po.documentitem_set.all(),
        **company_info,
    })
    
    return generate_pdf_from_html(html_content, f"Purchase Order {po.document_number}")


def send_document_email(document, email_address, subject, message="", request=None):
    """Send document via email."""
    if not DOCUMENTS_AVAILABLE:
        return False
    
    try:
        # Generate PDF
        if document.document_type == 'receipt':
            pdf_content = generate_receipt_pdf(document, request)
        elif document.document_type == 'quotation':
            pdf_content = generate_quotation_pdf(document, request)
        elif document.document_type == 'invoice':
            pdf_content = generate_invoice_pdf(document, request)
        elif document.document_type == 'purchase_order':
            pdf_content = generate_purchase_order_pdf(document, request)
        else:
            return False
        
        # Send email with PDF attachment
        send_mail(
            subject=subject,
            message=message or f"Please find attached {document.document_type.title()} {document.document_number}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_address],
            fail_silently=False,
        )
        
        return True
    except Exception as e:
        print(f"Error sending document email: {str(e)}")
        return False


def print_document(document, request=None):
    """Print document (placeholder for actual printing functionality)."""
    if not DOCUMENTS_AVAILABLE:
        return False
    
    try:
        # This is a placeholder - actual printing would require additional setup
        # For now, we'll just generate the PDF and return success
        if document.document_type == 'receipt':
            pdf_content = generate_receipt_pdf(document, request)
        elif document.document_type == 'quotation':
            pdf_content = generate_quotation_pdf(document, request)
        elif document.document_type == 'invoice':
            pdf_content = generate_invoice_pdf(document, request)
        elif document.document_type == 'purchase_order':
            pdf_content = generate_purchase_order_pdf(document, request)
        else:
            return False
        
        # In a real implementation, you would send this to a printer
        # For now, we'll just return success
        return True
    except Exception as e:
        print(f"Error printing document: {str(e)}")
        return False
