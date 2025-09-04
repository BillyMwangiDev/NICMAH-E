"""
Admin views for catalog app - handles quick image upload functionality.
"""

import json
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Product, ProductImage


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def quick_upload_image(request):
    """
    Handle quick image upload from admin interface.
    """
    try:
        # Get form data
        product_id = request.POST.get('product_id')
        image_type = request.POST.get('image_type')
        image_file = request.FILES.get('image')
        
        if not product_id or not image_type or not image_file:
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            })
        
        # Get the product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Product not found'
            })
        
        # Handle main image upload
        if image_type == 'main':
            # Save main image
            file_path = f'products/{product.slug}_main_{image_file.name}'
            saved_path = default_storage.save(file_path, ContentFile(image_file.read()))
            product.main_image = saved_path
            product.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Main image uploaded successfully for {product.name}',
                'image_url': product.main_image.url if product.main_image else None
            })
        
        # Handle additional image upload
        elif image_type == 'additional':
            alt_text = request.POST.get('alt_text', '')
            order = int(request.POST.get('order', 1))
            
            # Create ProductImage instance
            product_image = ProductImage.objects.create(
                product=product,
                image=image_file,
                alt_text=alt_text,
                order=order,
                is_active=True
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Additional image uploaded successfully for {product.name}',
                'image_url': product_image.image.url if product_image.image else None
            })
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid image type'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
