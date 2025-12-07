from datetime import timezone
from django.contrib.auth.backends import ModelBackend
from django.http import JsonResponse
from locks.ApiRequest import ApiRequest
from django.contrib.auth.models import User
import os
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from datetime import timedelta
from django.conf import settings


class DomainBasedRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if host == 'forms.r-lev.com' and request.path == '/':
            return redirect('/GuestForm')
        return self.get_response(request)

class SessionExpiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
    
        not_aute_requierd_urls = ['/login', '/login/', '/dashboard/unlock_by_phone', '/GuestForm', '/GuestFormIchilov', '/ws/messages/', '/get_form_links', '/test', '/end-point']
        if request.path in not_aute_requierd_urls or 'house-page' in request.path or 'donor-page' in request.path or 'media' in request.path or 'cross' in request.path:
            return response
        
        dashboard_login_urls = ['/', '/dashboard/', '/dashboard', '/logout/', '/logout']
        coffee_cards_url = ['/coffee_cards','/coffee_cards/']

        if request.path in dashboard_login_urls:
            redirect(reverse('login'))
        elif request.path in coffee_cards_url:
            redirect(reverse('login'))
        elif not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required ' + request.path}, status=401)
        return response
    
class LoginByApi(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return
        try:
            user = User.objects.get(username=username)
            # from django.contrib.auth.hashers import make_password
            # user.password = make_password('1234')
            # user.save()
            if user.check_password(password):
                next_url = request.GET.get('next')
                if next_url:
                    view_to_run = next_url.replace('/', '')
                else:
                    view_to_run = 'dashboard'

                if view_to_run == 'dashboard' and not user.allow_main and not user.hostings_ichilov:
                    return None
               
                if view_to_run == 'coffee_cards' and not user.allow_coffee_cards:
                    return None
                
                if user.is_superuser:
                    api = ApiRequest()
                    get_access_token = api.get_access_token(username, password)

                    if get_access_token and 'access_token' in get_access_token:
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        access_token_path = os.path.join(current_dir, '', 'accessToken')

                        with open(access_token_path, 'w') as file:
                            file.write(get_access_token['access_token'])

                return user
            else:
                
                return None
        except User.DoesNotExist:
            return None


def create_user(username, password, email=None, first_name=None, last_name=None):
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name
    )
    return user

