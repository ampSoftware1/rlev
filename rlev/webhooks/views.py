from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CrossData

@csrf_exempt
def webhook(request):
    import json
    # try:
    if True:

        data = request.POST
        # אני מקבל את זה כ form-data אני רוצה להפוך את זה לjson

        if not data:
            return JsonResponse({"error": "No data received"}, status=400)
        

        data_from_sf = data.get("data_from_sf", [])
   
        data_from_sf = json.loads(data_from_sf) 

        data_from_page = data.get('data_from_page', '').split(';') if data.get('data_from_page') else []

        if not data_from_sf:
            return JsonResponse({"error": "data_from_sf is empty"}, status=400)
        
        fields_name = data_from_sf[0].keys()
        fields_name_heb = data.get('fields_name', '').split(';') if data.get('fields_name') else []
        priority = data.get('priority', '').split(';') if data.get('priority') else []
   

        fields = []
        for i, field in enumerate(fields_name):
            field_heb = fields_name_heb[i] 
            field_priority = priority[i] 
            fields.append({
                'field_name': field,
                'field_heb': field_heb,
                'priority': field_priority
            })
        

        data_from_page_as_json = {}
        for i, field in enumerate(fields):
            field_name = field['field_name']
            data_from_page_as_json[field_name] = data_from_page[i]


        cross_data = CrossData.objects.create(
            data_from_sf=data_from_sf,
            data_from_page=data_from_page_as_json,
            fields=fields
        )
        cross_data.save()

        form_url = f'https://rlev.utilitiesphone.com/cross-form/{cross_data.uuid}'
        delete_url = f'https://rlev.utilitiesphone.com/delete-cross-data/{cross_data.uuid}'
        cross_prioritys = cross_data.get_cross_prioritys()
        return JsonResponse({
            "cross_priority_1": cross_prioritys.get('cross_priority_1', 0),
            "cross_priority_2": cross_prioritys.get('cross_priority_2', 0),
            "cross_priority_3": cross_prioritys.get('cross_priority_3', 0),
            "form_url": form_url,
            "delete_url": delete_url
        }, status=200)

    # except Exception as e:
    #     return JsonResponse({"error": str(e)}, status=500)

def cross_form(request, data_id):
    data = CrossData.objects.get(uuid=data_id)

    return render(request, 'webhooks/cross_form.html', {'data': data})

def delete_cross_data(request, data_id):
    try:
        data = CrossData.objects.get(uuid=data_id)
        data.delete()
        return JsonResponse({"message": "Data deleted successfully"}, status=200)
    except CrossData.DoesNotExist:
        return JsonResponse({"error": "Data not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

