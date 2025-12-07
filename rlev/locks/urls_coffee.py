import os
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import consumers
from .views_coffee import *


urlpatterns = [
    path('', coffee_cards, name='coffee_cards'),
    path('check_card_number/<int:card_number>', check_card_number),
    path('mark_card_faulty/<int:card_id>/<int:status>', mark_card_faulty),
    path('get_persons_and_roles', get_persons_and_roles),
    path('check_exist_person/<str:id_number>', check_exist_person),
    path('save_new_card', save_new_card)
]