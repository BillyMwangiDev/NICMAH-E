"""
Management command to create sample educational articles for testing the UI.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from educational.models import Article
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Create sample educational articles for testing"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample articles...")

        # Get or create a user for the articles
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@nichmahagrovet.com", "first_name": "Admin", "last_name": "User", "role": "admin"},
        )

        if created:
            user.set_password("admin123")
            user.save()
            self.stdout.write(f"Created user: {user.username}")

        # Create sample articles
        articles_data = [
            {
                "title": "Best Practices for Poultry Farming",
                "content": """
                <h3>Introduction to Modern Poultry Farming</h3>
                <p>Poultry farming has evolved significantly over the years. Modern techniques focus on efficiency,
                animal welfare, and sustainable production methods.</p>

                <h4>Key Considerations:</h4>
                <ul>
                    <li>Proper housing and ventilation</li>
                    <li>Balanced nutrition and feeding schedules</li>
                    <li>Disease prevention and biosecurity</li>
                    <li>Regular health monitoring</li>
                </ul>

                <h4>Feeding Guidelines:</h4>
                <p>Provide high-quality feed with proper protein content. Layer feed should contain
                16-18% protein, while broiler feed should have 20-22% protein for optimal growth.</p>

                <h4>Health Management:</h4>
                <p>Regular vaccination schedules and proper hygiene practices are essential for maintaining healthy
                flocks.</p>
                """,
                "category": "Poultry Farming",
                "is_published": True,
                "published_at": timezone.now(),
            },
            {
                "title": "Dairy Cow Nutrition Essentials",
                "content": """
                <h3>Understanding Dairy Cow Nutritional Needs</h3>
                <p>Proper nutrition is crucial for dairy cow productivity and health. A well-balanced diet
                ensures optimal milk production and reproductive performance.</p>

                <h4>Nutritional Requirements:</h4>
                <ul>
                    <li>High-quality forage and concentrates</li>
                    <li>Adequate protein (16-18% of dry matter)</li>
                    <li>Proper energy balance</li>
                    <li>Essential minerals and vitamins</li>
                </ul>

                <h4>Feeding Strategies:</h4>
                <p>Implement total mixed ration (TMR) feeding for consistent nutrition. Monitor body
                condition scores and adjust rations accordingly throughout the lactation cycle.</p>

                <h4>Common Issues:</h4>
                <p>Watch for signs of nutritional deficiencies such as reduced milk production, poor coat
                condition, or reproductive problems.</p>
                """,
                "category": "Dairy Farming",
                "is_published": True,
                "published_at": timezone.now(),
            },
            {
                "title": "Sustainable Farming Methods",
                "content": """
                <h3>Implementing Sustainable Farming Practices</h3>
                <p>Sustainable farming ensures long-term productivity while protecting the environment and
                natural resources for future generations.</p>

                <h4>Sustainable Practices:</h4>
                <ul>
                    <li>Crop rotation and diversification</li>
                    <li>Integrated pest management</li>
                    <li>Soil conservation techniques</li>
                    <li>Water management and conservation</li>
                </ul>

                <h4>Benefits:</h4>
                <p>Sustainable farming reduces environmental impact, improves soil health, and can increase
                long-term profitability while ensuring food security.</p>

                <h4>Getting Started:</h4>
                <p>Begin with small changes and gradually implement more sustainable practices. Monitor results
                and adjust strategies based on local conditions and resources.</p>
                """,
                "category": "Sustainable Farming",
                "is_published": True,
                "published_at": timezone.now(),
            },
        ]

        for article_data in articles_data:
            article, created = Article.objects.get_or_create(
                title=article_data["title"], defaults={**article_data, "author": user}
            )

            if created:
                self.stdout.write(f"Created article: {article.title}")
            else:
                self.stdout.write(f"Article already exists: {article.title}")

        self.stdout.write(self.style.SUCCESS("Successfully created sample articles!"))
