"""
Management command to set up product images for demonstration.
"""

from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from catalog.models import Product, ProductImage
import requests


class Command(BaseCommand):
    help = 'Set up sample product images for demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing images before adding new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing product images...')
            ProductImage.objects.all().delete()
            for product in Product.objects.all():
                if product.main_image:
                    product.main_image.delete()
                    product.save()

        self.stdout.write('Setting up sample product images...')
        
        # Sample image URLs (placeholder images)
        sample_images = [
            'https://via.placeholder.com/400x400/4CAF50/FFFFFF?text=Product+1',
            'https://via.placeholder.com/400x400/2196F3/FFFFFF?text=Product+2',
            'https://via.placeholder.com/400x400/FF9800/FFFFFF?text=Product+3',
            'https://via.placeholder.com/400x400/9C27B0/FFFFFF?text=Product+4',
            'https://via.placeholder.com/400x400/F44336/FFFFFF?text=Product+5',
        ]

        products = Product.objects.all()
        
        for i, product in enumerate(products):
            if i >= len(sample_images):
                break
                
            try:
                # Download and save main image
                response = requests.get(sample_images[i])
                if response.status_code == 200:
                    # Create a temporary file
                    img_temp = NamedTemporaryFile(delete=True)
                    img_temp.write(response.content)
                    img_temp.flush()
                    
                    # Save as main image
                    product.main_image.save(
                        f'{product.slug}_main.jpg',
                        File(img_temp),
                        save=True
                    )
                    
                    # Add additional images
                    for j in range(2):
                        if i + j + 1 < len(sample_images):
                            response2 = requests.get(sample_images[i + j + 1])
                            if response2.status_code == 200:
                                img_temp2 = NamedTemporaryFile(delete=True)
                                img_temp2.write(response2.content)
                                img_temp2.flush()
                                
                                ProductImage.objects.create(
                                    product=product,
                                    image=File(img_temp2),
                                    alt_text=f'{product.name} - Additional Image {j+1}',
                                    order=j+1,
                                    is_active=True
                                )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Added images for {product.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Failed to download image for {product.name}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {product.name}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS('Product image setup completed!')
        )
