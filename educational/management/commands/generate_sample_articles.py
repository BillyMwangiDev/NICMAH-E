from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from educational.models import Article
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = "Generate sample educational articles for testing"

    def handle(self, *args, **options):
        # Get or create a default user
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@nichmah.com",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Admin",
                "last_name": "User",
            },
        )

        if created:
            user.set_password("admin123")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created default user: {user.username}"))

        # Sample articles data
        articles_data = [
            {
                "title": "Introduction to Poultry Farming",
                "content": """
                Poultry farming is one of the most profitable agricultural businesses in Kenya.
                This comprehensive guide covers everything from selecting the right breed to
                managing diseases and maximizing egg production.

                Key topics include:
                - Choosing the right poultry breed for your climate
                - Proper housing and ventilation requirements
                - Feeding strategies for optimal growth
                - Disease prevention and management
                - Marketing and profitability analysis
                """,
                "excerpt": (
                    "Learn the fundamentals of successful poultry farming in Kenya, from breed selection "
                    "to disease management and marketing strategies."
                ),
                "is_published": True,
                "is_featured": True,
                "published_at": timezone.now() - timedelta(days=5),
            },
            {
                "title": "Organic Farming Methods for Small Scale Farmers",
                "content": """
                Organic farming is not just a trend - it's a sustainable approach that can
                improve soil health and increase crop yields while reducing input costs.

                This article covers:
                - Natural pest control methods
                - Composting and soil enrichment techniques
                - Crop rotation strategies
                - Organic certification requirements
                - Market opportunities for organic produce
                """,
                "excerpt": (
                    "Discover sustainable organic farming techniques that can improve your yields " "and reduce costs."
                ),
                "is_published": True,
                "is_featured": False,
                "published_at": timezone.now() - timedelta(days=3),
            },
            {
                "title": "Dairy Farming Best Practices",
                "content": """
                Dairy farming can be highly profitable when done correctly. Learn the best
                practices for managing dairy cattle, optimizing milk production, and
                maintaining herd health.

                Topics covered:
                - Breed selection and genetics
                - Feeding and nutrition management
                - Milking procedures and hygiene
                - Calf rearing and breeding programs
                - Milk quality and safety standards
                """,
                "excerpt": (
                    "Master the essential practices for successful dairy farming and optimal " "milk production."
                ),
                "is_published": True,
                "is_featured": True,
                "published_at": timezone.now() - timedelta(days=1),
            },
            {
                "title": "Greenhouse Technology for Year-Round Production",
                "content": """
                Greenhouse farming allows you to grow crops throughout the year, regardless
                of weather conditions. This technology can significantly increase your
                farming income and productivity.

                Learn about:
                - Different types of greenhouse structures
                - Climate control and automation systems
                - Crop selection for greenhouse cultivation
                - Pest and disease management in controlled environments
                - Return on investment calculations
                """,
                "excerpt": (
                    "Explore how greenhouse technology can revolutionize your farming with " "year-round production."
                ),
                "is_published": True,
                "is_featured": False,
                "published_at": timezone.now(),
            },
            {
                "title": "Financial Management for Agribusiness",
                "content": """
                Successful farming requires more than just agricultural knowledge - you need
                strong financial management skills to ensure profitability and sustainability.

                Key areas covered:
                - Budgeting and financial planning
                - Record keeping and accounting systems
                - Accessing agricultural loans and grants
                - Risk management and insurance
                - Investment planning for farm expansion
                """,
                "excerpt": (
                    "Master the financial aspects of agribusiness to ensure long-term " "profitability and growth."
                ),
                "is_published": True,
                "is_featured": False,
                "published_at": timezone.now() - timedelta(hours=12),
            },
        ]

        articles_created = 0
        for article_data in articles_data:
            article, created = Article.objects.get_or_create(
                title=article_data["title"],
                defaults={
                    "content": article_data["content"],
                    "excerpt": article_data["excerpt"],
                    "author": user,
                    "is_published": article_data["is_published"],
                    "is_featured": article_data["is_featured"],
                    "published_at": article_data["published_at"],
                    "view_count": 0,
                },
            )

            if created:
                articles_created += 1
                self.stdout.write(self.style.SUCCESS(f"Created article: {article.title}"))
            else:
                self.stdout.write(self.style.WARNING(f"Article already exists: {article.title}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {len(articles_data)} articles. " f"Created {articles_created} new articles."
            )
        )
