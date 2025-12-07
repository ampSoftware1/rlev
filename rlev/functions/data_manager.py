from locks.models import *


def get_list(list_name, user = None):
    if list_name == 'roles':
        the_list = Person.objects.values_list('role', flat=True).distinct()
        
    return the_list