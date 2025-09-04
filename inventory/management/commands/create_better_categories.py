"""
Django management command to create a better category structure for easier browsing.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import Product, Category
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Create a better organized category structure for easier browsing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        # Define the new organized category structure
        new_categories = {
            # Veterinary Medicines
            'veterinary_medicines': {
                'name': 'Veterinary Medicines',
                'description': 'All veterinary medications and treatments',
                'subcategories': {
                    'injectables': {
                        'name': 'Injectables',
                        'description': 'Injectable medications for animals',
                        'keywords': ['injectable', 'injection', 'adamycin', 'tetroxy', 'bimoxyl', 'bilosin', 'dipen', 'adacycline', 'oxytetra', 'penstrep', 'tylovet', 'penican', 'histacure', 'kombitrim', 'levimox', 'nitrodox', 'ivamed', 'troxamed', 'ethiudium', 'diminatryp', 'trimec', 'vitaboost', 'dextramed', 'calcikel', 'dexaphan', 'butaphos', 'ivosec', 'bupalet', 'supermec', 'bimectin', 'endospec', 'buparvex', 'buvanol', 'parvexon', 'terrexine', 'multimas']
                    },
                    'dewormers': {
                        'name': 'Dewormers',
                        'description': 'Deworming medications for livestock',
                        'keywords': ['dewormer', 'albendazole', 'curafluke', 'vermofas', 'multidose', 'nemarid', 'multicure', 'ashiniel', 'abbezzole', 'abbeyfas', 'nilzan', 'nerifluke', 'gardal', 'force']
                    },
                    'acaricides': {
                        'name': 'Acaricides',
                        'description': 'Tick and mite control products',
                        'keywords': ['acaricide', 'mostraz', 'bimatraz', 'cyperguard', 'bimatix', 'pyrotix', 'taktik', 'dabotik', 'supasense', 'diepest', 'triatix', 'twigatraz']
                    },
                    'antibiotics': {
                        'name': 'Antibiotics',
                        'description': 'Antibiotic medications',
                        'keywords': ['alamycin', 'opticlox', 'bendamec']
                    },
                    'hormones': {
                        'name': 'Hormones',
                        'description': 'Hormonal treatments and reproductive products',
                        'keywords': ['estropl', 'gonabreed', 'bimatryp', 'bimahistamine']
                    }
                }
            },
            
            # Animal Health Products
            'animal_health': {
                'name': 'Animal Health Products',
                'description': 'Health and wellness products for animals',
                'subcategories': {
                    'wound_care': {
                        'name': 'Wound Care',
                        'description': 'Wound treatment and care products',
                        'keywords': ['wound', 'spray', 'eye cream', 'opticlox']
                    },
                    'milking_supplies': {
                        'name': 'Milking Supplies',
                        'description': 'Milking equipment and supplies',
                        'keywords': ['milking', 'salve', 'udderwash', 'underwash', 'ckl milk']
                    },
                    'poultry_products': {
                        'name': 'Poultry Products',
                        'description': 'Products specifically for poultry',
                        'keywords': ['poultry', 'intradine', 'levacide', 'pirazine', 'tylovet poultry', 'medi ampro', 'medirtim', 'tyloxy poultry', 'lemicin egg', 'ascacure']
                    },
                    'disinfectants': {
                        'name': 'Disinfectants',
                        'description': 'Cleaning and disinfection products',
                        'keywords': ['disinfect', 'norocleanse']
                    },
                    'bloat_treatment': {
                        'name': 'Bloat Treatment',
                        'description': 'Products for treating bloat in livestock',
                        'keywords': ['stopbloat', 'mastrite']
                    }
                }
            },
            
            # Agricultural Products
            'agricultural_products': {
                'name': 'Agricultural Products',
                'description': 'Farming and agricultural products',
                'subcategories': {
                    'pesticides': {
                        'name': 'Pesticides',
                        'description': 'Crop protection and pest control',
                        'keywords': ['gramoxone', 'actellic', 'duduthrin', 'twigasate', 'katrin', 'twigalaxyl', 'milthane']
                    },
                    'dust_products': {
                        'name': 'Dust Products',
                        'description': 'Dusting powders and treatments',
                        'keywords': ['trevin', 'chalidudu', 'poultry dust']
                    },
                    'seeds': {
                        'name': 'Seeds',
                        'description': 'Agricultural seeds',
                        'keywords': ['carrots', 'spinach', 'pretoria']
                    }
                }
            },
            
            # Animal Feeds & Supplements
            'animal_feeds': {
                'name': 'Animal Feeds & Supplements',
                'description': 'Feed and nutritional supplements',
                'subcategories': {
                    'animal_feeds': {
                        'name': 'Animal Feeds',
                        'description': 'Complete feeds for livestock',
                        'keywords': ['dairy meal', 'highyeald', 'pig feed', 'chicken feed', 'mash', 'germ', 'mollases']
                    },
                    'mineral_supplements': {
                        'name': 'Mineral Supplements',
                        'description': 'Mineral supplements and licks',
                        'keywords': ['twigalick', 'twiga stocklick', 'maziwazaidi', 'maziwamax', 'joto', 'drycow', 'dcp', 'supreme', 'white energy', 'highchem']
                    },
                    'vitamins': {
                        'name': 'Vitamins',
                        'description': 'Vitamin supplements',
                        'keywords': ['vitamin', 'multivitamin', 'capovit', 'ketonex']
                    }
                }
            },
            
            # Farming Tools & Equipment
            'farming_equipment': {
                'name': 'Farming Tools & Equipment',
                'description': 'Tools and equipment for farming',
                'subcategories': {
                    'tools': {
                        'name': 'Farming Tools',
                        'description': 'Hand tools and equipment',
                        'keywords': ['hoe', 'syringe', 'reusable syringe', 'teat cannula', 'sucking preventor', 'ear tag', 'ear tag applicator', 'erastrator', 'rubberings', 'dehorning wire', 'feeding bottle', 'lactometer', 'thermometer', 'weing band', 'needls']
                    },
                    'pet_care': {
                        'name': 'Pet Care',
                        'description': 'Pet care products',
                        'keywords': ['dog shampoo', 'pet']
                    },
                    'veterinary_equipment': {
                        'name': 'Veterinary Equipment',
                        'description': 'Veterinary tools and equipment',
                        'keywords': ['cattle dewormer', 'dairy cow supplement']
                    }
                }
            }
        }
        
        if dry_run:
            self.show_dry_run_results(new_categories)
        else:
            self.create_organized_categories(new_categories)
    
    def show_dry_run_results(self, new_categories):
        """Show what would be done without making changes."""
        self.stdout.write("\n" + "="*80)
        self.stdout.write("BETTER CATEGORY STRUCTURE PLAN")
        self.stdout.write("="*80)
        
        self.stdout.write(f"\nNew Organized Category Structure:")
        for main_slug, main_cat in new_categories.items():
            self.stdout.write(f"\n📁 {main_cat['name']}")
            self.stdout.write(f"   Description: {main_cat['description']}")
            
            for sub_slug, sub_cat in main_cat['subcategories'].items():
                self.stdout.write(f"   └── {sub_cat['name']}")
                self.stdout.write(f"       Description: {sub_cat['description']}")
                
                # Count products that would be moved
                product_count = 0
                for keyword in sub_cat['keywords']:
                    count = Product.objects.filter(name__icontains=keyword).count()
                    if count > 0:
                        product_count += count
                
                if product_count > 0:
                    self.stdout.write(f"       Products: {product_count}")
        
        # Show products that might not fit
        total_products = Product.objects.count()
        self.stdout.write(f"\nTotal products in system: {total_products}")
    
    def create_organized_categories(self, new_categories):
        """Create the organized category structure."""
        with transaction.atomic():
            created_categories = 0
            moved_products = 0
            
            # Create main categories and subcategories
            category_objects = {}
            
            for main_slug, main_cat in new_categories.items():
                # Create main category
                main_category, created = Category.objects.get_or_create(
                    slug=main_slug,
                    defaults={
                        'name': main_cat['name'],
                        'description': main_cat['description'],
                        'is_active': True
                    }
                )
                
                if created:
                    created_categories += 1
                    self.stdout.write(f"Created main category: {main_category.name}")
                
                category_objects[main_slug] = main_category
                
                # Create subcategories
                for sub_slug, sub_cat in main_cat['subcategories'].items():
                    full_slug = f"{main_slug}_{sub_slug}"
                    sub_category, created = Category.objects.get_or_create(
                        slug=full_slug,
                        defaults={
                            'name': sub_cat['name'],
                            'description': sub_cat['description'],
                            'is_active': True
                        }
                    )
                    
                    if created:
                        created_categories += 1
                        self.stdout.write(f"Created subcategory: {sub_category.name}")
                    
                    category_objects[full_slug] = sub_category
            
            # Move products to appropriate categories
            for main_slug, main_cat in new_categories.items():
                for sub_slug, sub_cat in main_cat['subcategories'].items():
                    full_slug = f"{main_slug}_{sub_slug}"
                    category = category_objects[full_slug]
                    
                    # Find products that match keywords
                    for keyword in sub_cat['keywords']:
                        products = Product.objects.filter(name__icontains=keyword)
                        
                        for product in products:
                            old_category = product.category.name
                            product.category = category
                            product.save()
                            moved_products += 1
                            self.stdout.write(f"Moved '{product.name}' to '{category.name}'")
            
            # Summary
            self.stdout.write("\n" + "="*80)
            self.stdout.write("CATEGORY ORGANIZATION COMPLETE")
            self.stdout.write("="*80)
            self.stdout.write(f"Created categories: {created_categories}")
            self.stdout.write(f"Moved products: {moved_products}")
            
            # Show final structure
            self.stdout.write(f"\nFinal Organized Structure:")
            for main_slug, main_cat in new_categories.items():
                main_category = category_objects[main_slug]
                main_count = main_category.products.count()
                self.stdout.write(f"\n📁 {main_category.name}: {main_count} products")
                
                for sub_slug, sub_cat in main_cat['subcategories'].items():
                    full_slug = f"{main_slug}_{sub_slug}"
                    sub_category = category_objects[full_slug]
                    sub_count = sub_category.products.count()
                    if sub_count > 0:
                        self.stdout.write(f"   └── {sub_category.name}: {sub_count} products")
            
            self.stdout.write(self.style.SUCCESS("\nCategory organization completed successfully!"))

