
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import *


@login_required
def coffee_cards(request):
    return render(request, 'locks/coffee_cards.html')

def check_card_number(request, card_number):
    exists = Card.objects.filter(card_number=card_number).exists()
    if exists:
        card_object = Card.objects.get(card_number=card_number)
        details = card_object.get_details()
        return JsonResponse({'exist': True, 'details': details})
    else:
        return JsonResponse({'exist': False})
    
        
def mark_card_faulty(request, card_id, status):
    card_object = Card.objects.get(id=card_id)
    card_object.coffee_card = status
    card_object.save()
    return JsonResponse({'success': True})

def get_persons_and_roles(request):
    persons = Person.objects.all().order_by('last_name', 'first_name')
    persons = [person.get_name() for person in persons]
    roles = Person.get_all_roles()
    return JsonResponse({'persons': persons, 'roles': roles})

def check_exist_person(request, id_number):
    exists = Person.objects.filter(id_number=id_number).exists()
    if exists:
        person_object = Person.objects.get(id_number=id_number)
        details = person_object.get_details()
        return JsonResponse({'exist': True, 'details': details})
    else:
        return JsonResponse({'exist': False})
    
def save_new_card(request):
    data = json.loads(request.body.decode('utf-8'))
    card_number= data['card_number']
    card_name = data['card_name']
    id_number = data['id_number']


    exists_person = Person.objects.filter(id_number=id_number).exists()
    if exists_person:
        person_object = Person.objects.get(id_number=id_number)
        orginal_card_name = card_name
        n = 1
        while True:
            exists_card_name = Card.objects.filter(card_name=card_name, person=person_object).exists()
            if exists_card_name:
                card_name = f"{orginal_card_name}{n}"
                n += 1
            else:
                break
            
    else:
        person_object = Person.objects.create(id_number=id_number)
        person_object.save()

    card_object = Card.objects.create(card_number=card_number,
                                      card_name=card_name,
                                      person=person_object,
                                      coffee_card=True)
    card_object.save()
    return JsonResponse({'success': True})