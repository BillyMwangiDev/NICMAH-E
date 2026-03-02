"""
Core models for the NICMAH system
"""

from django.db import models
from django.contrib.sites.models import Site


class SiteSettings(models.Model):
    """Site-wide settings and configuration."""

    site = models.OneToOneField(Site, on_delete=models.CASCADE)
    site_name = models.CharField(max_length=100, default="NICMAH", help_text="Name of the business/site")
    tagline = models.CharField(
        max_length=200,
        blank=True,
        default="Farmers focused business specializing in livestock farming and crop farming for over two decades.",
    )
    logo = models.ImageField(upload_to="site/", blank=True, null=True)

    # Business Information
    business_description = models.TextField(
        blank=True,
        help_text="Detailed business description and history",
        default=(
            "NICMAH is a farmers focused business that majors on livestock farming "
            "and crop farming for over two decades. We provide comprehensive agricultural "
            "solutions including AI services, quality seeds, and expert farming guidance."
        ),
    )
    mission_statement = models.TextField(
        blank=True,
        help_text="Company mission statement",
        default=(
            "Our mission is to ensure quality, hardy and resistant herds are maintained "
            "and passed on through breeding."
        ),
    )
    vision_statement = models.TextField(
        blank=True,
        help_text="Company vision statement",
        default="Our goal is to help farmers achieve their goals and educating them to ensure their prosperity.",
    )

    # Services
    livestock_services = models.TextField(
        blank=True,
        help_text="Livestock farming services offered",
        default=(
            "• AI (Artificial Insemination) services\n• Best livestock breeding practices\n"
            "• Quality semen from local and international bulls\n• Livestock health management\n"
            "• Breeding consultation and support"
        ),
    )
    crop_services = models.TextField(
        blank=True,
        help_text="Crop farming services offered",
        default=(
            "• Quality seeds\n• Foliar applications\n• Pest control products\n"
            "• Crop management solutions\n• Maximum yield optimization\n• Soil health management"
        ),
    )

    # Contact Information
    contact_email = models.EmailField(blank=True, default="nicmahagrovet@gmail.com")
    phone_number = models.CharField(max_length=20, blank=True, default="0726476128/0740368581")
    whatsapp_number = models.CharField(max_length=20, blank=True, default="254740368581", help_text="WhatsApp number in international format (without +)")
    veterinary_phone = models.CharField(max_length=20, blank=True, default="0721908023", help_text="Veterinary services phone number")
    address = models.TextField(blank=True, default="Naromoru town, Timberland building near KFA")

    # Social Media
    facebook_url = models.URLField(blank=True, default="https://facebook.com/NicmahAgrovet")
    tiktok_url = models.URLField(blank=True, default="https://tiktok.com/@Nicmah")
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)

    # Business Settings
    currency = models.CharField(max_length=10, default="KES")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    business_hours = models.TextField(
        blank=True,
        help_text="Business operating hours",
        default="Monday - Friday: 8:00 AM - 6:00 PM\nSaturday: 8:00 AM - 4:00 PM\nSunday: Closed",
    )

    # Experience and Achievements
    years_in_business = models.PositiveIntegerField(default=20, help_text="Number of years in business")
    cattle_ai_count = models.PositiveIntegerField(default=1000, help_text="Number of cattle served through AI")
    farmers_served = models.PositiveIntegerField(default=1000, help_text="Number of farmers served")
    
    # Receipt Printer Settings
    printer_enabled = models.BooleanField(default=False, help_text="Enable receipt printing")
    printer_type = models.CharField(
        max_length=20,
        choices=[
            ('system', 'System/USB Printer'),
            ('serial', 'Serial/COM Port'),
            ('network', 'Network Printer'),
        ],
        default='system',
        help_text="Type of receipt printer connection"
    )
    printer_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Printer name (for system printers) or device path/name"
    )
    printer_host = models.CharField(
        max_length=200,
        blank=True,
        help_text="Network printer IP address or hostname"
    )
    printer_port = models.IntegerField(
        default=9100,
        help_text="Network printer port (default: 9100 for raw printing)"
    )
    printer_serial_port = models.CharField(
        max_length=100,
        blank=True,
        help_text="Serial port (e.g., COM1 on Windows, /dev/ttyUSB0 on Linux)"
    )
    printer_baudrate = models.IntegerField(
        default=9600,
        help_text="Serial printer baudrate"
    )
    auto_print_receipts = models.BooleanField(
        default=False,
        help_text="Automatically print receipts after completing a sale"
    )

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return f"{self.site_name} Settings"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SiteSettings.objects.exists():
            return
        super().save(*args, **kwargs)
