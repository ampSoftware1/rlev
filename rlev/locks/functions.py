from datetime import datetime, timedelta
from .models import *

def get_seven_days_ago_timestamp_ms():
    seven_days_ago_timestamp = datetime.now() - timedelta(days=7)
    seven_days_ago_timestamp_ms = int(seven_days_ago_timestamp.timestamp() * 1000)
    return seven_days_ago_timestamp_ms

def get_tranmissions(user):
    if user.is_superuser:
        transmissions = Transmission.objects.all()
    else:
        locks_objects = Lock.objects.filter(lockuser__user=user)
        locks_alias = [lock.lock_alias for lock in locks_objects]
        transmissions = Transmission.objects.filter(lock_name__in=locks_alias)
    return transmissions


def do_main_sync():
    send_message_to_browser("start_main_sync")
    
    for lock in Lock.objects.filter(active=1):
        lock.update_details()
        lock.sync_permissions()

    for lock in Lock.objects.all():
        lock.check_active()

    send_message_to_browser('end_main_sync')

def do_passages():
    passages = PassageMode.objects.all()
    for passage in passages:
        passage.change_modes()
        passage.do_locks_actions()


def check_locks_battery():
    for lock in Lock.objects.filter(active=1):
        lock.check_battery()

def cleen_record_to_delete(user_name):
    person_to_delete = Person.objects.filter(status_record=1)
    for person in person_to_delete:
        person.delete_person(user_name)

    cards_to_delete = Card.objects.filter(status_record=1)
    for card in cards_to_delete:
        card.delete_card(user_name)
