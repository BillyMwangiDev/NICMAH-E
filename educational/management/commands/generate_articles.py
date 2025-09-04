"""
Management command to generate sample educational articles.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from educational.models import Article, Category


User = get_user_model()


class Command(BaseCommand):
    help = "Generate sample educational articles for the website"

    def handle(self, *args, **options):
        try:
            # Create categories if they don't exist
            livestock_category, created = Category.objects.get_or_create(
                name="Livestock Farming",
                slug="livestock-farming",
                defaults={"description": "Articles about livestock farming practices and management"},
            )

            crop_category, created = Category.objects.get_or_create(
                name="Crop Farming",
                slug="crop-farming",
                defaults={"description": "Articles about crop farming techniques and management"},
            )

            # Get or create a user for the author
            user, created = User.objects.get_or_create(
                username="admin", defaults={"email": "admin@nicmahagrovet.com", "is_staff": True, "is_superuser": True}
            )
            if created:
                user.set_password("admin123")
                user.save()

            # Article content
            articles_data = [
                {
                    "title": "Best Practices in Livestock Farming in Kenya",
                    "category": livestock_category,
                    "excerpt": (
                        "Discover the essential practices that every Kenyan livestock farmer should know "
                        "to ensure healthy and productive animals."
                    ),
                    "content": """
# Best Practices in Livestock Farming in Kenya

Livestock farming is a cornerstone of Kenya's agricultural economy, providing food security, employment,
and income for millions of people.

## Key Practices

1. **Proper Housing**: Ensure adequate ventilation and space
2. **Nutrition**: Provide balanced diet with clean water
3. **Health Management**: Regular vaccinations and health checks
4. **Record Keeping**: Maintain detailed farm records
5. **Market Access**: Build relationships with buyers

For more information, visit Nicmah Agrovet or contact our expert team.
                    """,
                },
                {
                    "title": "Modern Crop Farming Techniques for Kenyan Farmers",
                    "category": crop_category,
                    "excerpt": (
                        "Learn about innovative crop farming techniques that can significantly improve "
                        "yields and profitability."
                    ),
                    "content": """
# Modern Crop Farming Techniques for Kenyan Farmers

Kenya's diverse climate and fertile soils provide excellent opportunities for crop farming. However, to maximize
yields and profitability, farmers need to adopt modern techniques.

## Key Techniques

1. **Soil Health Management**: Regular testing and conservation
2. **Precision Agriculture**: Use technology for better results
3. **Irrigation Management**: Efficient water use
4. **Integrated Pest Management**: Sustainable pest control
5. **High-Yield Varieties**: Choose the right seeds

Contact Nicmah Agrovet for expert advice on crop farming.
                    """,
                },
            ]

            # Create articles
            for article_data in articles_data:
                article, created = Article.objects.get_or_create(
                    title=article_data["title"],
                    defaults={
                        "category": article_data["category"],
                        "excerpt": article_data["excerpt"],
                        "content": article_data["content"],
                        "author": user,
                        "is_published": True,
                    },
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created article: {article.title}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Article already exists: {article.title}"))

            self.stdout.write(self.style.SUCCESS("Successfully generated sample articles"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error generating articles: {str(e)}"))
