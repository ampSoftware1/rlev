from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path
from django.conf.urls import include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from locks.views import CustomLoginView, guest_form, guest_form_hostings_ichilov, house_page, donor_page,get_form_links
from webhooks.views import *


urlpatterns = [
    path('', RedirectView.as_view(url='/dashboard/')),
    path('dashboard/', include("locks.urls")),
    path('data_manager/', include('data_manager.urls')),
    path('coffee_cards/', include("locks.urls_coffee")),
    path('GuestForm', guest_form),
    path('GuestFormIchilov',guest_form_hostings_ichilov),
    path('house-page/<str:house_code>',house_page),
    path('donor-page/<str:donor_code>',donor_page),
    path('get_form_links',get_form_links),
    path('end-point', webhook, name='webhook'),
    path('cross-form/<str:data_id>', cross_form, name='cross_form'),
    path('delete-cross-data/<str:data_id>', delete_cross_data, name='delete_cross_data'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

# הגשת קבצי מדיה (גם בייצור וגם בפיתוח)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers for production
handler404 = 'rlev.views.custom_404'
handler500 = 'rlev.views.custom_500'
handler403 = 'rlev.views.custom_403'
handler400 = 'rlev.views.custom_400'

