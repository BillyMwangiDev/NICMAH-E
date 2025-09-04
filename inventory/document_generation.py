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


def generate_receipt_pdf(receipt):
    """Generate PDF for receipt."""
    if not DOCUMENTS_AVAILABLE:
        return None
    
    # Create HTML content for receipt
    html_content = render_to_string('inventory/receipt_pdf.html', {
        'receipt': receipt,
        'items': receipt.documentitem_set.all(),
        'company_name': 'Nicmah Agrovet',
        'company_address': 'Naromoru town, Timberland building near KFA',
        'company_phone': '0726476128/0740368581',
        'company_email': 'nicmahagrovet@gmail.com',
    })
    
    return generate_pdf_from_html(html_content, f"Receipt {receipt.document_number}")


def generate_quotation_pdf(quotation):
    """Generate PDF for quotation."""
    if not DOCUMENTS_AVAILABLE:
        return None
    
    # Create HTML content for quotation
    html_content = render_to_string('inventory/quotation_pdf.html', {
        'quotation': quotation,
        'items': quotation.documentitem_set.all(),
        'company_name': 'Nicmah Agrovet',
        'company_address': 'Naromoru town, Timberland building near KFA',
        'company_phone': '0726476128/0740368581',
        'company_email': 'nicmahagrovet@gmail.com',
    })
    
    return generate_pdf_from_html(html_content, f"Quotation {quotation.document_number}")


def generate_invoice_pdf(invoice):
    """Generate PDF for invoice."""
    if not DOCUMENTS_AVAILABLE:
        return None
    
    # Create HTML content for invoice
    html_content = render_to_string('inventory/invoice_pdf.html', {
        'invoice': invoice,
        'items': invoice.documentitem_set.all(),
        'company_name': 'Nicmah Agrovet',
        'company_address': 'Naromoru town, Timberland building near KFA',
        'company_phone': '0726476128/0740368581',
        'company_email': 'nicmahagrovet@gmail.com',
    })
    
    return generate_pdf_from_html(html_content, f"Invoice {invoice.document_number}")


def generate_purchase_order_pdf(po):
    """Generate PDF for purchase order."""
    if not DOCUMENTS_AVAILABLE:
        return None
    
    # Create HTML content for purchase order
    html_content = render_to_string('inventory/purchase_order_pdf.html', {
        'po': po,
        'items': po.documentitem_set.all(),
        'company_name': 'Nicmah Agrovet',
        'company_address': 'Naromoru town, Timberland building near KFA',
        'company_phone': '0726476128/0740368581',
        'company_email': 'nicmahagrovet@gmail.com',
    })
    
    return generate_pdf_from_html(html_content, f"Purchase Order {po.document_number}")


def send_document_email(document, email_address, subject, message=""):
    """Send document via email."""
    if not DOCUMENTS_AVAILABLE:
        return False
    
    try:
        # Generate PDF
        if document.document_type == 'receipt':
            pdf_content = generate_receipt_pdf(document)
        elif document.document_type == 'quotation':
            pdf_content = generate_quotation_pdf(document)
        elif document.document_type == 'invoice':
            pdf_content = generate_invoice_pdf(document)
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


def print_document(document):
    """Print document (placeholder for actual printing functionality)."""
    if not DOCUMENTS_AVAILABLE:
        return False
    
    try:
        # This is a placeholder - actual printing would require additional setup
        # For now, we'll just generate the PDF and return success
        if document.document_type == 'receipt':
            pdf_content = generate_receipt_pdf(document)
        elif document.document_type == 'quotation':
            pdf_content = generate_quotation_pdf(document)
        elif document.document_type == 'invoice':
            pdf_content = generate_invoice_pdf(document)
        else:
            return False
        
        # In a real implementation, you would send this to a printer
        # For now, we'll just return success
        return True
    except Exception as e:
        print(f"Error printing document: {str(e)}")
        return False
