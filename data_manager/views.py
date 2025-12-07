import json
from django.forms import model_to_dict
from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from importlib import import_module
import os
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.db.models import Q

def table(request, model_name):
    model = get_model(model_name)
    app_lable = model.app_label
    model_class = model.model_class()
    objects = model_class.objects.all()

    # מטפל ביישום מרובה משתמשים
    if getattr(request, "is_multi_user_app", False) and not request.user.is_superuser:
        multy_user_field = request.multy_user_field
        multy_user_related_fields = request.multy_user_related_fields
        multy_user_id = getattr(request.user, multy_user_field)
        
        if hasattr(model_class, multy_user_field):
            objects = objects.filter(**{multy_user_field: multy_user_id})
        else:
            # מודלים משניים עבור מזהה מפריד היישום מרובה משתמשים
            for multy_user_related_field in multy_user_related_fields:
                if hasattr(model_class, multy_user_related_field):
                    objects = objects.filter(**{multy_user_related_field + '__' + multy_user_field: multy_user_id})
    
    # עבור טבלה בתצוגת דפים או סינון
    if request.method == 'POST':
        pages_details = json.loads(request.body)
        
        speical_objects = pages_details.get("speical_objects", None)
        
        if speical_objects:
            speical_objects = getattr(model_class, speical_objects, None)
            if speical_objects:
                objects = speical_objects.all()
        
        filters = pages_details.get("filters", {})
        if filters:
            q_object = Q()
            for key, value in filters.items():
                if key.startswith('*'):
                    q_object &= model_class.convert_filter(key[1:], value)
                else:
                    q_object &= Q(**{key: value})
            objects = objects.filter(q_object)
              

        order_by = pages_details.get("sort", None)
      
        objects = objects.order_by(order_by) if order_by else objects  

        page_number = pages_details.get("page", 1) 
        page_number = int(page_number)

        amount_in_page = pages_details.get("amount_in_page", 50)
        paginator = Paginator(objects, amount_in_page)
        page_number = min(page_number, paginator.num_pages)
        objects = paginator.page(page_number)

    object_list = [get_details_for_item(item) for item in objects]

    if request.method == 'POST':
        result = dict(
            html = render_to_string(f'{app_lable}/{model_name}s_table.html', {'list': object_list, 'user': request.user}),
            page_number = page_number,
            max_page = paginator.num_pages,
            total_records = paginator.count,
            min_record = paginator.page(page_number).start_index(),
            max_record = paginator.page(page_number).end_index(),
        )
        return JsonResponse(result)
    else:
        return render(request, f'{app_lable}/{model_name}s_table.html', {'list': object_list})


# מציג חלון של פריט ממודל
def item(request, model_name, item_id=None):
    model = get_model(model_name)  
    app_lable = model.app_label
    model_class = model.model_class()

    data = {}
    if item_id:
        item = model_class.objects.get(id=item_id)
        data['details'] = get_details_for_item(item)
        data['type'] = 'edit'
    else:
        data['type'] = 'new'
    
    for list_name in getattr(model_class, 'lists', []):
        list = run_custom_function_from_project("get_list", list_name, request.user)
        data[list_name] = list
    
    for data_function_model in getattr(model_class, 'data_functions_model', []):
        data_from_function = getattr(model_class, data_function_model)(request.user)
        data[data_function_model] = data_from_function

    for data_function in getattr(model_class, 'data_functions', []):
        data_from_function = run_custom_function_from_project(data_function, request.user)
        data[data_function] = data_from_function


    spical_window_to_new_item = getattr(model_class, "spical_window_to_new_item", False)
    if spical_window_to_new_item and not item_id:
        spical_window_to_new_item = "_new"
    else:
        spical_window_to_new_item = ''

    data['user'] = request.user

    return render(request, f'{app_lable}/{model_name}{spical_window_to_new_item}.html', data)

# מביא רשימה של בנים עבור מודל
def childs_items(request, main_model_name, childs_model_name, item_id):
    model_class = ContentType.objects.get(model=main_model_name.replace("_", "")).model_class()

    parant_item = model_class.objects.get(id=item_id)
    childs_model_name_lable = childs_model_name.replace("_", "")

    # אם רשימת הבנים היא מודל, מביא הבנים ישירות מהמודל המקושר, אם הוא מודל מורחב, קורא לפונקציה שמחזירה את הבנים
    if hasattr(parant_item, f"{childs_model_name_lable}_set"):
        childs_items_objects = getattr(parant_item, f"{childs_model_name_lable}_set").all()
    else:
        childs_items_objects = getattr(parant_item, f"{childs_model_name_lable}s")()
    childs_items = [get_details_for_item(item) for item in childs_items_objects]

    return JsonResponse({childs_model_name: childs_items})


def get_item(request, model_name, item_id):
    model_class = ContentType.objects.get(model=model_name.replace("_", "")).model_class()
    item = model_class.objects.get(id=item_id)
    return JsonResponse({model_name: get_details_for_item(item)})


# שומר פריט חדש או קיים
def save_item(request, model_name, item_id=None):
    model = get_model(model_name)
    model_class = model.model_class()

    raw_data = json.loads(request.body)
    data = {key.replace(f'on-{model_name}-', '').replace('-', '_'): value for key, value in raw_data.items()}
    
    if item_id:
        obj = model_class.objects.get(id=item_id)
    else:
        obj = model_class()

    if hasattr(obj, "valid_data"):
        valid = obj.valid_data(data)
        if not valid['is_valid']:
            error_message = valid['error_message']
            return JsonResponse({'status': 'error', 'message': error_message})

    if hasattr(obj, "process_data"):
        data = obj.process_data(data)

    for key, value in data.items():
        if key == "password":
            value = make_password(value)
        setattr(obj, key, value)

    if getattr(request, "is_multi_user_app", False) and not request.user.is_superuser:
        multy_user_field = request.multy_user_field
        if hasattr(obj, multy_user_field):
            multy_user_id = getattr(request.user, multy_user_field)
            setattr(obj, multy_user_field, multy_user_id)

    obj.save()

    item = model_class.objects.get(id=obj.pk)
    return JsonResponse({'status': 'ok', model_name: get_details_for_item(item)})


def delete_item(request, model_name, item_id):
    model = get_model(model_name)
    model_class = model.model_class()
    obj = model_class.objects.get(id=item_id)
    obj.delete()

    return JsonResponse({'status': 'ok'})


def get_list(request, list_name):
    list = run_custom_function_from_project("get_list", list_name, request.user)
    return JsonResponse({list_name: list})


def get_details_for_item(item):
    if hasattr(item, "get_details"):
        details = item.get_details()
    else:
        details = model_to_dict(item)
    return details

def run_custom_function_from_project(function_name, *args):
    project_name = os.path.basename(settings.BASE_DIR)
    module = import_module(f"{project_name}.functions.data_manager")
    function = getattr(module, function_name)
    result = function(*args)
    return result


def get_model(model_name):
    model_name = model_name.replace("_", "")
    # בודק אם הוא מודל רגיל או מורחב, ומביא את המודל
    model = ContentType.objects.filter(model=model_name)
    if model.exists():
        model = model.first()
    else:
        extended_models = ContentType.objects.get(model="extendedmodel").model_class()
        extended_model = extended_models.objects.get(model=model_name)
        model = extended_model.parent_model
    return model