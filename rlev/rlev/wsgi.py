"""
WSGI config for rlev project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application
sys.path.append('/usr/django_projects')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rlev.settings')

# os.environ["DJANGO_SETTINGS_MODULE"] = "rlev.settings"

application = get_wsgi_application()
