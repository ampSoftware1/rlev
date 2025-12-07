from django.urls import path
from .views import *

urlpatterns = [
    path('table/<str:model_name>', table, name='table'),
    path('item/<str:model_name>/', item, name='item'),
    path('item/<str:model_name>/<int:item_id>', item, name='item'), 
    path('childs_items/<str:main_model_name>/<str:childs_model_name>/<int:item_id>', childs_items, name='childs_items'), 

    
    path('get_item/<str:model_name>/<int:item_id>', get_item, name='get_item'),
    path('save_item/<str:model_name>/', save_item, name='save_item'),
    path('save_item/<str:model_name>/<int:item_id>', save_item, name='save_item'),
    path('delete_item/<str:model_name>/<int:item_id>', delete_item, name='delete_item'),

    path('get_list/<str:list_name>', get_list, name='get_list')
]