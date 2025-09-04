"""
Context processors for Nichmah Agrovet application.
Provides global template variables.
"""


def site_settings(request):
    """
    Add site-wide settings to template context.
    """
    try:
        from .models import SiteSettings

        settings_obj = SiteSettings.objects.first()

        if settings_obj:
            return {
                "site_name": settings_obj.site_name,
                "site_tagline": settings_obj.tagline,
                "site_description": settings_obj.tagline,
                "business_description": settings_obj.business_description,
                "mission_statement": settings_obj.mission_statement,
                "vision_statement": settings_obj.vision_statement,
                "livestock_services": settings_obj.livestock_services,
                "crop_services": settings_obj.crop_services,
                "contact_email": settings_obj.contact_email,
                "phone_number": settings_obj.phone_number,
                "veterinary_phone": settings_obj.veterinary_phone,
                "address": settings_obj.address,
                "facebook_url": settings_obj.facebook_url,
                "tiktok_url": settings_obj.tiktok_url,
                "instagram_url": settings_obj.instagram_url,
                "twitter_url": settings_obj.twitter_url,
                "currency": settings_obj.currency,
                "business_hours": settings_obj.business_hours,
                "years_in_business": settings_obj.years_in_business,
                "cattle_ai_count": settings_obj.cattle_ai_count,
                "farmers_served": settings_obj.farmers_served,

            }
    except Exception as e:
        # Log the error for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Error loading site settings in context processor: {str(e)}")

    # Fallback values if SiteSettings is not available
    return {
        "site_name": "Nicmah Agrovet",
        "site_tagline": "Your trusted partner in animal health and nutrition",
        "site_description": "Your trusted partner in animal health and nutrition",
        "business_description": (
            "Farmers focused business specializing in livestock farming " "and crop farming for over two decades."
        ),
        "mission_statement": (
            "Our mission is to ensure quality, hardy and resistant herds are "
            "maintained and passed on through generations."
        ),
        "vision_statement": (
            "Our goal is to help farmers achieve their goals and educating " "them to ensure their prosperity."
        ),
        "livestock_services": (
            "• AI (Artificial Insemination) services\n"
            "• Best livestock breeding practices\n"
            "• Quality semen and breeding materials"
        ),
        "crop_services": (
            "• Quality seeds\n• Foliar applications\n• Pest control products\n"
            "• Crop management solutions\n• Market access support"
        ),
        "contact_email": "nicmahagrovet@gmail.com",
        "phone_number": "0726476128/0740368581",
        "veterinary_phone": "0721908023",
        "address": "Naromoru town, Timberland building near KFA",
        "facebook_url": "https://facebook.com/NicmahAgrovet",
        "tiktok_url": "https://tiktok.com/@Nicmah",
        "instagram_url": "",
        "twitter_url": "",
        "currency": "KES",
        "business_hours": "Monday - Friday: 8:00 AM - 6:00 PM\nSaturday: 8:00 AM - 4:00 PM\nSunday: Closed",
        "years_in_business": 20,
        "cattle_ai_count": 1000,
        "farmers_served": 1000,

    }


def seo_meta_tags(request):
    """
    Add SEO meta tags to template context.
    """
    # Basic SEO meta tags
    return {
        "seo_meta_tags": {
            "title": "Nicmah Agrovet - Leading Agricultural Supplies & Services in Kenya",
            "description": "Quality agricultural supplies, livestock services, crop management solutions, and expert farming advice. Serving farmers across Kenya with trusted agrovet products and services.",
            "keywords": "agrovet, agricultural supplies, farming equipment, livestock services, crop management, fertilizers, pesticides, seeds, farming tools, Kenya agriculture",
            "author": "Nicmah Agrovet",
            "robots": "index, follow",
            "og_type": "website",
            "og_title": "Nicmah Agrovet - Your Trusted Agricultural Partner",
            "og_description": "Quality agricultural supplies and expert farming services for Kenyan farmers.",
            "og_image": "/static/images/logo.png",
            "twitter_card": "summary_large_image",
        }
    }
