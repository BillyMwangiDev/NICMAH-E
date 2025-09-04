"""
Django management command to generate search indexes for better search performance.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import Product, Category
from django.db.models import Q
import json
import os


class Command(BaseCommand):
    help = 'Generate search indexes for better search performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='search_index.json',
            help='Output file for search index (default: search_index.json)'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing search index'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        update = options['update']
        
        self.stdout.write("Generating search index...")
        
        # Generate search index
        search_index = self.generate_search_index()
        
        # Save to file
        self.save_search_index(search_index, output_file, update)
        
        self.stdout.write(self.style.SUCCESS(f"Search index generated successfully! ({len(search_index)} products indexed)"))
    
    def generate_search_index(self):
        """Generate comprehensive search index."""
        products = Product.objects.filter(is_active=True, is_available=True).select_related('category')
        
        search_index = []
        
        for product in products:
            # Create searchable text
            searchable_text = f"{product.name} {product.sku} {product.category.name} {product.description}"
            
            # Generate keywords
            keywords = self.extract_keywords(product)
            
            # Create index entry
            index_entry = {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'category': product.category.name,
                'category_slug': product.category.slug,
                'description': product.description,
                'price': float(product.price),
                'stock_quantity': product.stock_quantity,
                'is_featured': product.is_featured,
                'searchable_text': searchable_text.lower(),
                'keywords': keywords,
                'url': product.get_absolute_url(),
                'created_at': product.created_at.isoformat(),
            }
            
            search_index.append(index_entry)
        
        return search_index
    
    def extract_keywords(self, product):
        """Extract relevant keywords from product."""
        keywords = set()
        
        # Add product name words
        keywords.update(product.name.lower().split())
        
        # Add SKU
        keywords.add(product.sku.lower())
        
        # Add category
        keywords.add(product.category.name.lower())
        
        # Add description words (common agricultural terms)
        description_words = product.description.lower().split()
        agricultural_terms = [
            'injectable', 'dewormer', 'acaricide', 'antibiotic', 'vaccine',
            'vitamin', 'mineral', 'feed', 'supplement', 'medicine', 'treatment',
            'poultry', 'cattle', 'livestock', 'animal', 'farm', 'agricultural',
            'twiga', 'bima', 'alamycin', 'opticlox', 'bendamec'
        ]
        
        for word in description_words:
            if word in agricultural_terms:
                keywords.add(word)
        
        return list(keywords)
    
    def save_search_index(self, search_index, output_file, update):
        """Save search index to file."""
        if os.path.exists(output_file) and not update:
            self.stdout.write(f"File {output_file} already exists. Use --update to overwrite.")
            return
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(search_index, f, indent=2, ensure_ascii=False)
        
        self.stdout.write(f"Search index saved to {output_file}")
        
        # Also save a summary
        summary = {
            'total_products': len(search_index),
            'categories': list(set(item['category'] for item in search_index)),
            'featured_products': len([item for item in search_index if item['is_featured']]),
            'in_stock_products': len([item for item in search_index if item['stock_quantity'] > 0]),
            'price_range': {
                'min': min(item['price'] for item in search_index),
                'max': max(item['price'] for item in search_index),
                'avg': sum(item['price'] for item in search_index) / len(search_index)
            }
        }
        
        summary_file = output_file.replace('.json', '_summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.stdout.write(f"Search summary saved to {summary_file}")

