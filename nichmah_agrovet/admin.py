"""
Enhanced admin site configuration for NICMAH.
"""

from django.contrib import admin

# Customize the admin site
admin.site.site_header = "NICMAH Administration"
admin.site.site_title = "NICMAH Admin"
admin.site.index_title = "Welcome to NICMAH Administration"
admin.site.site_url = "/"
