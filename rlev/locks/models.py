import calendar
import random
import string
import time
from datetime import datetime, timedelta, timezone
from convertdate import hebrew
from collections import Counter

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, Count, Value, Case, When, CharField
from django.db.models.functions import Concat
from django.forms import ValidationError, model_to_dict

from locks.ApiRequest import ApiRequest
from locks.templatetags.custom_filters import time_to_date, time_to_datetime
from .signals import *
from .consumers import *
from django.contrib.auth.models import User
from .webhooks import WebHooks

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

def default_timestamp():
    return int(datetime.now().timestamp() * 1000)



class Lock(models.Model):
    lock_id_ttl = models.IntegerField(unique=True)
    lock_name = models.CharField(max_length=300, null=True, blank=True)
    lock_alias = models.CharField(max_length=300, null=True, blank=True)
    electric_quantity = models.IntegerField(default=0)
    has_gateway = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    date_add = models.BigIntegerField(default=default_timestamp)


    dict_fields = {'lockId': 'lock_id_ttl', 'lockName': 'lock_name', 'lockAlias': 'lock_alias',
                   'electricQuantity': 'electric_quantity', 'hasGateway': 'has_gateway', 'date': 'date_add'}

    @classmethod
    def get_locks(cls, user=None):
        objects = cls.objects.all().order_by('lock_alias')
        if user and not user.is_superuser:
            objects = objects.filter(lockuser__user=user)

        locks = [{"id": lock.id, "alias": lock.lock_alias} for lock in objects]
        return locks

    @classmethod
    def get_alerts_electric_quantity(cls):
        objects = cls.objects.filter(electric_quantity__lt=41)
        locks = [{"id": lock.id, "lock_alias": lock.lock_alias, "electric_quantity": lock.electric_quantity} for lock in objects]
        return locks

    def get_details(self):
        passage_mode_active = self.passagemodelock_set.filter(mode=1, passage_status=1).exists()
        details = dict(id=self.id,
                       lock_id_ttl=self.lock_id_ttl,
                       lock_alias=self.lock_alias,
                       electric_quantity=self.electric_quantity,
                       has_gateway=self.has_gateway,
                       active=self.active,
                       date_add=self.date_add,
                       passage_mode_active=passage_mode_active,
                       gorup_list=self.get_link_list('group'))
        return details

    def get_link_list(self, type_link):
        if type_link == 'group':
            links_objects = self.lockaccessgroup_set.all()
        elif type_link == 'user':
            links_objects = self.lockuser_set.all()
        link_list = [{"id": item.id, "name": item.get_name()} for item in links_objects]
        return link_list

    def get_child_list(self, type_child, user=None):
        if type_child == 'permissions':
            child_objects = self.permission_set.all()
        elif type_child == 'records':
            child_objects = self.lockrecord_set.all().order_by('-server_date')
        child_list = [child.get_details() for child in child_objects]
        return child_list

    def delete_permissions(self):
        permissions = self.permission_set.all()
        for permission in permissions:
            permission.delete_permission()

    def transmission_permissions(self):
        permissions_to_transmission = self.permission_set.filter(status_record__in=[1, 2])
        if permissions_to_transmission.exists():
            for permission in permissions_to_transmission:
                permission.transmission()
            return True
        else:
            return False
        

    def update_details(self):
        api = ApiRequest()
        lock_details = api.get_lock_details(self.lock_id_ttl)
        if lock_details:
            lock_data =  {field: lock_details[json_key] for json_key, field in self.dict_fields.items()}
                
            for key, value in lock_data.items():
                setattr(self, key, value)
                
            self.save()

    def check_battery(self):
        
        battery = self.electric_quantity
        
        if battery <= 40:
            webhooks = WebHooks()

            if 30 < battery <= 40:
                level = 1
            elif 20 < battery <= 30:
                level = 2
            else:
                level = 3

            category = "בטריה"
            type = "בטריה חלשה"
            error = battery
            message = f'שים לב! מצב בטריה במנעול {self.lock_alias} הוא {battery}% בלבד!'
            lock_name = self.lock_alias

            webhooks.send(category, level, message, type, error, lock_name)

            
    def sync_permissions(self):
        api = ApiRequest()

        cards_list = []
        total_pages = 1
        p = 1
        while p <= total_pages:
            get_cards_list = api.get_cards_list(self.lock_id_ttl, p)
            if not get_cards_list:
                break
            cards_list += get_cards_list['list']
            total_pages = get_cards_list['pages']
            p += 1

        if get_cards_list:
            card_ids = [card['cardId'] for card in cards_list]
            current_cards_permissions = Permission.objects.filter(lock_id=self.id, type_object_id=8)
            current_cards_permissions.exclude(Q(card_permission_id__in=card_ids) | Q(card_permission_id__isnull=True) | Q(status_record=1)).delete()

            for card in cards_list:
                card_number = card['cardNumber']
                parts = card['cardName'].split("~")
                if len(parts) == 2:
                    person_name = parts[0]
                    card_name = parts[1]
                else:
                    person_name = parts[0]
                    card_name = "קבוע"

                person_name = person_name.strip()

                card_exists = Card.objects.filter(card_number=card_number).exists()
                if card_exists:
                    current_card = Card.objects.get(card_number=card_number)
                    person_id = current_card.person.id
                    card_name_exists = Card.objects.filter(person_id=person_id, card_name=card_name).exclude(id=current_card.id).exists()
                    if card_name_exists:
                        card_name = card_name + "_" + str(current_card.id)
                        
                    current_card.card_name = card_name
                    current_card.save()
                else:
                    try:
                        person = Person.objects.annotate(
                            full_name=Case(
                                When(
                                    Q(first_name__isnull=False) & ~Q(first_name=''), 
                                    then=Concat('first_name', Value(' '), 'last_name')
                                ),
                                default='last_name',
                                output_field=CharField()
                            )
                        ).get(full_name=person_name)
                    except Person.DoesNotExist:

                        person = Person(id_number=int(time.time() * 1000), last_name=person_name)
                        person.save()

                    try:
                        new_card = Card(card_number=card_number, card_name=card_name, person=person)
                        new_card.save()
                    except ValidationError as e:
                        errors = e.message_dict
                        message = next(iter(errors.values()))[0]
                        if message == 'Card with this Card name and Person already exists.':
                            card_name = card_name + "_" + str(current_card.id)
                            new_card = Card(card_number=card_number, card_name=card_name, person=person)
                            new_card.save()
    

                card_permission_id = card['cardId']
                permission_data = {field: card[json_key] for json_key, field in Permission.dict_fields.items()}
                permission_data['type_object_id'] = 8
                permission_data['object_id'] = Card.objects.get(card_number=card['cardNumber']).id
                permission_data['lock_id'] = Lock.objects.get(lock_id_ttl=card['lockId']).id

                if card["cardType"] == 4:
                    permission_data["cyclic_config"] = card["cyclicConfig"]
                    permission_data["type_permission"] = 3
                else:
                    if card["endDate"]:
                        permission_data["type_permission"] = 2
                    else:
                        permission_data["type_permission"] = 1

                Permission.objects.update_or_create(card_permission_id=card_permission_id, defaults=permission_data)
        send_message_to_browser('end_sync')
        send_amount_in_transmission()

    def import_records(self):
        api = ApiRequest()
        records_list = []
        total_pages = 1
        p = 1
        while p <= total_pages:
            get_recrods_list = api.get_records_list(self.lock_id_ttl, p)
            if not get_recrods_list:
                break
            records_list += get_recrods_list['list']
            total_pages = get_recrods_list['pages']
            p += 1

        if get_recrods_list:
            for record in records_list:
                record_id = record['recordId']
                record_data = {field: record[json_key] for json_key, field in LockRecord.dict_fields.items()}
                record_data['lock'] = self
                
                user_name = record['username']
                user_reg = User.objects.filter(username=user_name).first()
                if user_reg:
                    user_name = user_reg.first_name + ' ' + user_reg.last_name
                
                if user_name:
                    record_data['person_name'] = user_name  
                    record_data['done_by'] = user_name
                else:
                    record_data['done_by'] = ''

                if len(record['keyboardPwd']) > 0:
                    card = Card.objects.filter(card_number=record['keyboardPwd']).first()
                    if card:
                        record_data['person_id'] = card.person.id
                        record_data['person_name'] = card.person.get_name()
                        record_data['type_object_id'] = 8
                        record_data['done_by'] = card.card_number
                        record_data['object_record_description'] = card.person.get_name() + " (" + card.card_name + ")"
                    else:
                        record_data['done_by'] = record['keyboardPwd']
                        record_data['object_record_description'] = user_name

                LockRecord.objects.update_or_create(record_id=record_id, defaults=record_data)


    def check_active(self):
        lock_id_ttl = self.lock_id_ttl
        api = ApiRequest()
        api_response = api.get_lock_details(lock_id_ttl)
        if 'errcode' in api_response and self.active:
            self.active = False
            self.save()
        elif 'errcode' not in api_response and not self.active:
            self.active = True
            self.save()


class PassageMode(models.Model):
    description = models.CharField(max_length=50)
    is_cyclic = models.BooleanField()
    unlock_in_active = models.BooleanField()
    type_range = models.IntegerField()
    start_range = models.CharField(max_length=50)
    end_range = models.CharField(max_length=50)
    type_start_time = models.IntegerField()
    start_time = models.IntegerField()
    type_end_time = models.IntegerField()
    end_time = models.IntegerField()
    error_level=models.IntegerField(default=1)
    active = models.BooleanField(default=1)
    done = models.IntegerField(default=0)
    send_webhook = models.BooleanField(default=0)
    active_now = models.BooleanField(default=0)

    week_days = {
    1: "ראשון", 2: "שני", 3: "שלישי", 4: "רביעי", 5: "חמישי", 
    6: "שישי", 7: "שבת"
    }

    months = {
        1: "ניסן", 2: "אייר", 3: "סיון", 4: "תמוז", 5: "אב", 
        6: "אלול", 7: "תשרי", 8: "חשון", 9: "כסליו", 10: "טבת", 
        11: "שבט", 12: "אדר", 13: "אדר ב"
    }

        
    months_day = {
        1: "א", 2: "ב", 3: "ג", 4: "ד", 5: "ה", 6: "ו", 7: "ז", 8: "ח", 9: "ט", 10: "י",
        11: "יא", 12: "יב", 13: "יג", 14: "יד", 15: "טו", 16: "טז", 17: "יז", 18: "יח", 19: "יט",
        20: "כ", 21: "כא", 22: "כב", 23: "כג", 24: "כד", 25: "כה", 26: "כו", 27: "כז", 28: "כח", 29: "כט", 30: "ל"
    }

    def get_details(self):
        in_range = self.check_in_range()
        locks=self.get_locks_list()
        if len(locks) > 5:
            locks_not_on_view = len(locks) - 5
        else:
            locks_not_on_view = 0
        status_locks=self.get_status_locks(locks)
        start_range_description, end_range_description=self.get_range_description()
        next_range=self.get_next_range()
        
        if self.type_range == 3:
            start_range_details = self.start_range.split('-')
            start_range = {"day_in_month": start_range_details[0], "month": start_range_details[1]}
            end_range_details = self.end_range.split('-')
            end_range = {"day_in_month": end_range_details[0], "month": end_range_details[1]}
        else:
            start_range=self.start_range
            end_range=self.end_range
            
        start_time_description = self.get_time_description('start', 'value')
        end_time_description = self.get_time_description('end', 'value')
            
                   
        details = dict(
            id=self.id,
            description = self.description,
            is_cyclic = self.is_cyclic,
            type_range = self.type_range,
            start_range = start_range,
            end_range = end_range,
            type_start_time = self.type_start_time,
            start_time = start_time_description,
            type_end_time = self.type_end_time,
            end_time = end_time_description,
            error_level=self.error_level,
            active=self.active,
            done=self.done,
            unlock_in_active=self.unlock_in_active,
            start_range_description=start_range_description,
            end_range_description=end_range_description,
            next_range=next_range,
            in_range=in_range,
            locks=locks,
            locks_not_on_view=locks_not_on_view,
            status_locks=status_locks
        )
        return details


    def change_modes(self):
        check_to_action = self.check_to_action()

        if check_to_action and not self.active_now :
            self.active_now = 1
            self.send_webhook = 0
            self.save()
        elif not check_to_action and self.active_now :
            self.active_now = 0
            self.send_webhook = 0
            self.save()

        locks = self.passagemodelock_set.all()
 
        if self.is_cyclic == 0:
            if check_to_action and self.done == 0:
                self.done = 1
                self.save()

            if not check_to_action and self.done == 1:
                self.done = 2
                self.save()

        for lock in locks:
            if check_to_action and lock.mode in [0, 2]:
                lock.mode = 1
                lock.change_status('passage', 0)  
                lock.change_status('unlock', 0) 

            elif not check_to_action and not lock.mode == 2:
                lock.mode = 2
                lock.change_status('passage', 0)
                lock.change_status('unlock', 0)  
      
            lock.save()

    def do_locks_actions(self):
        passages_locks = self.passagemodelock_set
        
        for lock in passages_locks.all():
            lock.change_passage_mode()
            lock.unlock()

        if self.send_webhook == 0:
            if self.active_now:
                count_active = passages_locks.filter(passage_status=1).count()
                if count_active == passages_locks.count():
                    self.do_send_webhook('success_active')
                    self.send_webhook = 1
                    self.save()
            else:
                count_cancel = passages_locks.filter(passage_status=2).count()
                if count_cancel == passages_locks.count():
                    self.do_send_webhook('success_unactive')
                    self.send_webhook = 1
                    self.save()
                

    def check_to_action(self):
        in_range = self.check_in_range()
        return not self.done == 2 and self.active and in_range

    
    def do_send_webhook(self, webhook_type):
        webhooks = WebHooks()
        category = "מצב מעבר"
        passage_name = self.description
        level = 1
        type = "סטטוס הפעלה"
        
        if webhook_type == 'success_active':
            message = f'מצב מעבר "{self.description}" הופעל בהצלחה על {self.passagemodelock_set.count()} מנעולים!'
            error = "הופעל בהצלחה"
        elif webhook_type == 'success_unactive':
            message = f'מצב מעבר "{self.description}" הסתיים בהצלחה!'
            error = "הסתיים בהצלחה"

        webhooks.send(category, level, message, type, error, passage_name)


    def get_locks_list(self):
        locks_objects = self.passagemodelock_set.all()
        locks = [lock.get_details() for lock in locks_objects]
        return locks 
    

    def get_range_description(self):
        if self.type_range == 1:
            start_range_date = datetime.strptime(self.start_range, "%Y-%m-%d")
            start_range_formatted = start_range_date.strftime("%d/%m/%Y")

            end_range_date = datetime.strptime(self.end_range, "%Y-%m-%d")
            end_range_formatted = end_range_date.strftime("%d/%m/%Y")

            start_range_description = start_range_formatted
            end_range_description = end_range_formatted
        if self.type_range == 2:
            start_range_description = 'יום '
            start_range_description += self.week_days.get(int(self.start_range), '')
            end_range_description = 'יום '
            end_range_description += self.week_days.get(int(self.end_range), '')
        if self.type_range == 3:
            hebrew_date_day_start, hebrew_date_month_start, hebrew_date_day_end, hebrew_date_month_end = self.get_range_by_hebrew_date() 

            start_range_description = self.months_day.get(hebrew_date_day_start, '')
            start_range_description += " "
            start_range_description += self.months.get(hebrew_date_month_start, '')
            end_range_description = self.months_day.get(hebrew_date_day_end, '')
            end_range_description += ' '
            end_range_description += self.months.get(hebrew_date_month_end, '')

        start_time_description = self.get_time_description('start', 'text')
        end_time_description = self.get_time_description('end', 'text')

        return f"{start_range_description} {start_time_description}", f"{end_range_description} {end_time_description}"

    def get_time_description(self, type, type_description):

        type_time = getattr(self, f'type_{type}_time')
        if type_time == 1:   
            minute = getattr(self, f'{type}_time')      
            hours = minute // 60
            minutes = minute % 60
            time_description = f"{hours:02}:{minutes:02}" 
            
            if type_description == 'text':
                time_description = "בשעה " + time_description  
                  
        if type_time == 2:
            diff_minute = getattr(self, f'{type}_time')  
            if type_description == 'text':
                type_diff_start = "אחרי" if diff_minute > 0 else "לפני"
                diff_minute = abs(diff_minute)
                time_description = f"{diff_minute} דקות {type_diff_start} השקיעה"
            else:
                diff_time = 2 if diff_minute > 0 else 1
                diff_minute = abs(diff_minute)
                time_description = {"diff_type": diff_time,
                                    "diff_minute": diff_minute}
                

        return time_description

    def get_range_by_hebrew_date(self):
        start_day = self.start_range.split('-')
        end_day = self.end_range.split('-')

        hebrew_date_day_start = int(start_day[0])
        hebrew_date_month_start = int(start_day[1])
        hebrew_date_day_end = int(end_day[0])
        hebrew_date_month_end = int(end_day[1])

        return hebrew_date_day_start, hebrew_date_month_start, hebrew_date_day_end, hebrew_date_month_end 

    def check_in_range(self):
        now = datetime.now()
        date_start, date_end = self.get_ranges()
        if date_start <= now <= date_end:
            return True
        else:
            return False
        
    def get_next_range(self):
        now = datetime.now()
        if self.is_cyclic == 0 and self.done == 2:
            return '-'
        date_start, date_end = self.get_ranges()
        
        if date_start < now:
            if date_end > now:
                return '-'
            if self.type_range == 1:
                return '-'
            if self.type_range == 2:
                date_start = date_start + timedelta(days=7)

            if self.type_range == 3:
                hebrew_date_day_start, hebrew_date_month_start, hebrew_date_day_end, hebrew_date_month_end = self.get_range_by_hebrew_date() 

                current_hebrew_date = hebrew.from_gregorian(now.year, now.month, now.day)
                current_hebrew_year = current_hebrew_date[0]

                date_start = self.convert_hebrew_date_to_gregorian(current_hebrew_year + 1, hebrew_date_month_start, hebrew_date_day_start)

        if self.type_start_time == 2:
            diff_start = self.start_time
            sunset_in_date_start = Sunset.objects.get(date=date_start).minute
            diff_start += sunset_in_date_start

            hours = diff_start // 60
            minutes = diff_start % 60

            date_start = date_start.replace(hour=hours, minute=minutes, second=0, microsecond=0)

        return date_start.strftime('%d/%m/%Y %H:%M')
    
    def get_status_locks(self, locks):
        status_counts = Counter(lock['passage_status_description'] for lock in locks)
        return dict(status_counts)

    def get_ranges(self):

        now = datetime.now()

        if self.type_range == 1:
            date_start = datetime.fromisoformat(self.start_range)
            date_end = datetime.fromisoformat(self.end_range)
        
        if self.type_range == 2:
            day_in_week_start = int(self.start_range)
            day_in_week_end = int(self.end_range)
            

            day_in_week_today = now.weekday()
            day_in_week_today = day_in_week_today + 2
            if day_in_week_today == 8:
                day_in_week_today = 1
            start_of_week = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=day_in_week_today) 

            if day_in_week_start <= day_in_week_end:
                date_start = start_of_week + timedelta(days=day_in_week_start)
                date_end = start_of_week + timedelta(days=day_in_week_end)
            else:
                if day_in_week_today < day_in_week_start:
                    date_start = start_of_week + timedelta(days=day_in_week_start - 7)
                    date_end = start_of_week + timedelta(days=day_in_week_end)
                else:
                    date_start = start_of_week + timedelta(days=day_in_week_start)
                    date_end = start_of_week + timedelta(days=day_in_week_end + 7)
        if self.type_range == 3:
            hebrew_date_day_start, hebrew_date_month_start, hebrew_date_day_end, hebrew_date_month_end = self.get_range_by_hebrew_date() 

            current_hebrew_date = hebrew.from_gregorian(now.year, now.month, now.day)
            current_hebrew_year = current_hebrew_date[0]

            date_start = self.convert_hebrew_date_to_gregorian(current_hebrew_year, hebrew_date_month_start, hebrew_date_day_start)
            date_end = self.convert_hebrew_date_to_gregorian(current_hebrew_year, hebrew_date_month_end, hebrew_date_day_end)
            if date_start > date_end:
                date_end = self.convert_hebrew_date_to_gregorian(current_hebrew_year + 1, hebrew_date_month_end, hebrew_date_day_end)

        diff_start = self.start_time
        diff_end = self.end_time

        if self.type_start_time == 2:
            sunset_in_date_start = Sunset.objects.get(date=date_start).minute
            diff_start += sunset_in_date_start
            
        if self.type_end_time == 2:
            sunset_in_date_end = Sunset.objects.get(date=date_end).minute
            diff_end += sunset_in_date_end

        date_start = date_start + timedelta(minutes=diff_start)
        date_end = date_end + timedelta(minutes=diff_end)
        return date_start, date_end

    def convert_hebrew_date_to_gregorian(self, h_year, h_month, h_day):
        g_year, g_month, g_day = hebrew.to_gregorian(h_year, h_month, h_day)
        return datetime(g_year, g_month, g_day)


class PassageModeLock(models.Model):
    passage_mode = models.ForeignKey(PassageMode, on_delete=models.CASCADE)
    lock = models.ForeignKey(Lock, on_delete=models.CASCADE)
    passage_status = models.IntegerField(default=0)
    passage_time = models.IntegerField(default=0)
    unlock_status = models.IntegerField(default=0)
    unlock_time = models.IntegerField(default=0)
    mode = models.IntegerField(default=0)

    class Meta:
        unique_together = ('passage_mode', 'lock')

    def get_details(self):
        passage_status_description = self.get_passage_status_description()
        details = dict(
            id=self.id,
            lock_details=self.lock.get_details(),
            unlock_in_active=self.passage_mode.unlock_in_active,
            mode=self.mode,
            passage_status=self.passage_status,
            passage_time=self.passage_time,
            unlock_status=self.unlock_status,
            unlock_time=self.unlock_time,
            passage_status_description=passage_status_description
        )
        return details

    def get_passage_status_description(self):
        if self.passage_status == 1:
            return 'active'
        if self.passage_status == 0:
            return 'in_action'
        if self.passage_status == 2:
            if self.mode == 2:
                return 'unactive'
            if self.mode == 3:
                return 'canceled'

    def change_passage_mode(self):

        if self.passage_time == 0 or (self.mode == 1 and self.passage_status == 1) or (self.mode in [2, 3] and self.passage_status == 2):
            return
        
        current_time = int(time.time())

        if self.passage_time < current_time - 600:
            self.send_webhook('passage')
            self.passage_time = 0
            self.save()
            send_message_to_browser('change_lock_passage')
            return
        
        if self.mode in [2, 3]:
            self.undo_passage_mode()
        else:
            self.do_passage_mode()
            self.unlock()

    def do_passage_mode(self):

        api = ApiRequest()

        if not self.passage_status == 1 and self.passage_time:
            passage_mode = api.send_passage_mode(self.lock.lock_id_ttl, 1)
            if passage_mode:
                self.change_status('passage', 1)
                self.change_status('unlock', 1)


    def undo_passage_mode(self):
        api = ApiRequest()
        
        if not self.passage_status == 2:
            if PassageModeLock.objects.filter(lock=self.lock, mode=1).exists():
                self.change_status('passage', 2)
            else:
                cancel_passage_mode = api.send_passage_mode(self.lock.lock_id_ttl, 2)
                if cancel_passage_mode:
                    self.change_status('passage', 2)


    def unlock(self):
        current_time = int(time.time())
        if not self.passage_status == 1 or self.unlock_time == 0 or self.passage_mode.unlock_in_active == 0 or self.unlock_status == 3 or self.unlock_status == 0:
            return
        
        api = ApiRequest()

        if self.unlock_time < current_time - 600:
            self.send_webhook('unlock')
            self.unlock_time = 0
            self.save()
            send_message_to_browser('change_lock_passage')
            return
        
        if self.unlock_status == 1:
            unlock = api.unlock(self.lock.lock_id_ttl)
            if unlock:
                self.change_status('unlock', 2)
    
        if self.unlock_status == 2 and self.unlock_time < current_time - 30:
            lock_status = api.get_lock_status(self.lock.lock_id_ttl)
            if lock_status:
                test_unlock = lock_status['state'] == 1
                if test_unlock:
                    self.change_status('unlock', 3)
                


    def change_status(self,property, status):
        setattr(self, property + '_status', status)
        setattr(self, property + '_time', int(time.time()))
        self.save()
        send_message_to_browser('change_lock_passage')



    def send_webhook(self, webhook_type):
        webhooks = WebHooks()
        category = "מצב מעבר"
        lock_name = self.lock.lock_alias

        if webhook_type == 'passage':
            level = self.passage_mode.error_level
            message = f'שגיאה! מצב מעבר במנעול {self.lock.lock_alias} נכשל, יש לבדוק ידנית'
            type = "הפעלת מצב מעבר"
            error = "נכשל"

        if webhook_type == 'unlock':
            level = 1
            message = f'שגיאה! מצב מעבר עבור מנעול {self.lock.lock_alias} מופעל, אך לא ניתן לקבל את מצב הפתיחה שלו'
            type = "פתיחת מנעול"
            error = "לא ידוע"
            lock_name = self.lock.lock_alias


        webhooks.send(category, level, message, type, error, lock_name)


class Sunset(models.Model):
    date = models.DateField()
    minute = models.IntegerField(default=0)

class Person(models.Model):
    last_name = models.CharField(max_length=50)
    last_name_eng = models.CharField(max_length=50, null=True)
    first_name = models.CharField(max_length=50)
    first_name_eng = models.CharField(max_length=50, null=True)
    id_number = models.CharField(max_length=10, unique=True)
    birth_date = models.DateField(null=True, blank=True)
    email = models.CharField(max_length=50)
    address = models.CharField(max_length=50)
    house_number = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    person_phone = models.CharField(max_length=50)
    role = models.CharField(max_length=50, null=True)
    date_add = models.BigIntegerField(default=default_timestamp)
    note = models.CharField(max_length=500, default='')
    status_record = models.IntegerField(default=0)
    not_to_view = models.BooleanField(default=False)
    id_number_file = models.FileField(upload_to='id_number_files/', null=True, blank=True)

    @classmethod
    def get_persons(cls, also_empty_permission_objects=False):
        objects = cls.objects.all().order_by('last_name', 'first_name')
        if also_empty_permission_objects == False:
            objects = objects.filter( Q(card__isnull=False) | Q(phone__isnull=False)).distinct()

        persons = [{"id": person.id, "name": f'{person.last_name} {person.first_name}'} for person in objects]
        return persons

    @classmethod
    def get_all_roles(cls):
        roles = cls.objects.exclude(Q(role__isnull=True) | Q(role='') | Q(role='אורח')).values_list('role', flat=True).distinct()
        return sorted(roles) 
    
    def get_name(self):
        return f'{self.first_name} {self.last_name}'


    def get_details(self):
        cards_objects = self.card_set.all()
        cards = [{"id": card.id, "card_name": card.card_name, "card_number": card.card_number, "coffee_card": card.coffee_card } for card in cards_objects]

        phones_objects = self.phone_set.all()
        phones = [{"id": phone.id, "phone_name": phone.phone_name} for phone in phones_objects]

        if self.person_phone:
            phone = self.person_phone
        else:
            phone = ''

        if self.role:
            role = self.role
        else:
            role = ''
  
        date_object = datetime.fromtimestamp(self.date_add / 1000)
        date_add = date_object.strftime('%Y-%m-%d %H:%M')

        hosting_in_house = ''
        current_date = datetime.now()
        hostings_active = Hosting.objects.filter(guest=self,lodging_start__lte=current_date, lodging_end__gte=current_date)
        if hostings_active.exists():
            hosting = hostings_active.first()
            hosting_in_house = hosting.house.description


        details = dict(
            id=self.id,
            id_number=self.id_number,
            name=self.get_name(),
            first_name=self.first_name,
            last_name=self.last_name,
            first_name_eng=self.first_name_eng,
            last_name_eng=self.last_name_eng,
            birth_date=self.birth_date.strftime('%Y-%m-%d') if self.birth_date else '',
            phone=phone,
            email=self.email,
            address=self.address,
            house_number=self.house_number,
            city=self.city,
            role=role,
            note=self.note,
            status_record=self.status_record,
            time_add=self.date_add,
            date_add=date_add,
            cards=cards,
            phones=phones,
            hosting_in_house=hosting_in_house,
            id_number_file=self.id_number_file.name if self.id_number_file else '',
            id_number_file_url=self.id_number_file.url if self.id_number_file else ''
        )
        return details

    def get_base_details(self):
        if self.person_phone:
            phone = self.person_phone
        else:
            phone = ''

        details = dict(
            id=self.id,
            id_number=self.id_number,
            name=self.get_name(),
            first_name=self.first_name,
            last_name=self.last_name,
            phone=phone,
            email=self.email,
            address=self.address,
            house_number=self.house_number,
            city=self.city
        )
        return details


    def delete_person(self, user_name):
        cards = self.card_set.all()
        for card in cards:
            card.delete_card(user_name)
        
        Phone.objects.filter(person=self).delete()
                
        permissions = self.get_permissions()
        if permissions.count() > 0:     
                self.status_record = 1
                self.save()
        else:
            self.delete()

    def get_child_list(self, type_child, user):
        if type_child == 'cards':
            child_objects = self.card_set.all()
        elif type_child == 'phones':
            child_objects = self.phone_set.all()
        elif type_child == 'permissions':
            child_objects = self.get_permissions(user)
        elif type_child == 'records':
            child_objects = LockRecord.objects.filter(person_id=self.id).order_by('-server_date')
            if not user.is_superuser:
                lock_ids_with_permission = LockUser.objects.filter(user=user).values_list('lock_id', flat=True)
                child_objects = child_objects.filter(lock_id__in=lock_ids_with_permission)
        elif type_child == 'hostings':
            as_guest = self.hostings_as_guest.all()
            as_patient = self.hostings_as_patient.all()
            child_objects = as_guest.union(as_patient).order_by('-lodging_start')
        elif type_child == 'hostings_ichilov':
            child_objects = self.hostingichilov_set.all()
        child_list = [child.get_details() for child in child_objects]
        
        return child_list

    def get_permissions(self, user=None):
        cards_objects = self.card_set.all()
        cards = [card.id for card in cards_objects]

        phones_objects = self.phone_set.all()
        phones = [phone.id for phone in phones_objects]

        permissions = Permission.objects.filter((Q(object_id__in=cards) & Q(type_object=8)) | (Q(object_id__in=phones) & Q(type_object=16)))
        if user and not user.is_superuser:
            lock_ids_with_permission = LockUser.objects.filter(user=user).values_list('lock_id', flat=True)
            permissions = permissions.filter(lock_id__in=lock_ids_with_permission)

        permissions = permissions.order_by('type_object', 'object_id', 'lock_id')

        return permissions

class HostingIchilov(models.Model):
    person = models.ForeignKey(Person, on_delete=models.RESTRICT)
    send_feedback = models.BooleanField(default=0)
    hospital_ward = models.CharField(max_length=50, null=True)
    lodging_start = models.DateField()
    lodging_end = models.DateField()
    date_add = models.BigIntegerField(default=default_timestamp)

    def get_name(self):
        return f'{self.person.first_name} {self.person.last_name}'

    def get_details(self):
        lodging_start_str = self.lodging_start.strftime('%Y-%m-%d')
        lodging_end_str = self.lodging_end.strftime('%Y-%m-%d')

        hospital_wards = ['אונקולוגיה ילדים', 'אונקולוגיה מבוגרים', 'נפגעי חרבות ברזל']
        if self.hospital_ward is None or self.hospital_ward == '':
            hospital_ward_val = 98
        elif self.hospital_ward not in hospital_wards:
            hospital_ward_val = 99
        else:
            hospital_ward_val = hospital_wards.index(self.hospital_ward) + 1

        date_object = datetime.fromtimestamp(self.date_add / 1000)
        date_add = date_object.strftime('%Y-%m-%d %H:%M')

        details = {
            "id": self.id,
            "person_name": self.get_name(),
            "person_details": self.person.get_base_details(),
            "date_add": date_add,
            "send_feedback": self.send_feedback,
            "hospital_ward": self.hospital_ward if self.hospital_ward is not None else '',
            "hospital_ward_val": hospital_ward_val,
            "lodging_start": lodging_start_str,
            "lodging_end": lodging_end_str
        }
        return details
    

def generate_random_string(length=10):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))


class House(models.Model):
    description = models.CharField(max_length=15, unique=True)
    page_description1 = models.CharField(max_length=50, default='')
    page_description2 = models.CharField(max_length=50, default='')
    lock = models.ForeignKey(Lock, on_delete=models.SET_NULL, null=True)
    link_code = models.CharField(max_length=15, default=generate_random_string)
    active = models.BooleanField(default=1)

    @classmethod
    def get_houses(cls, user):
        if user.is_superuser:
            objects = cls.objects.all()
        else:
            objects = cls.objects.filter(houseuser__user=user)
        houses = [{"id": houses.id, "description": houses.description} for houses in objects]
        return houses

    @classmethod
    def get_houses_with_hosting_status(cls, lodging_start,lodging_end, exclude_id ):
        houses = cls.objects.all()
        houses_list = []
        for house in houses:
            hosting_details = ''
            hostings = house.hosting_set.filter(Q(lodging_start__lte=lodging_end) &  Q(lodging_end__gte=lodging_start)
                                                  & ~Q(id=exclude_id))

            if not hostings.exists():
                hosting = None
                hosting_status = "free"
            elif hostings.filter(lodging_end=lodging_start).exists():
                hosting = hostings.filter(lodging_end=lodging_start).first()
                hosting_status = "partially"
            else:
                hosting_status = "block"
                hosting = hostings.first()

            if hosting:
                hosting_details = {"id": hosting.id,
                                   "guest_name": hosting.guest.get_name(),
                                    "lodging_start": hosting.lodging_start,
                                    "lodging_end": hosting.lodging_end}
            houses_list.append({
                'id': house.id,
                'description': house.description,
                'page_description1': house.page_description1,
                'hosting_status': hosting_status,
                'hosting_details': hosting_details 
            })
        
        return houses_list
            

    def get_link_list(self, type_link):
        if type_link == 'lock':
            links_objects = self.lockshouse_set.all()
        elif type_link == 'user':
            links_objects = self.houseuser_set.all()
        link_list = [{"id": item.id, "name": item.get_name()} for item in links_objects]
        return link_list


    def get_child_list(self, type_child):
        if type_child == 'hostings':
            child_objects = self.hosting_set.all().order_by('-lodging_start')
        
        child_list = [child.get_details() for child in child_objects]
        return child_list
    
    def get_hostings_by_date(self, date=None):
        if date is None:
            date = datetime.now().date()

        hostings_obj = self.hosting_set.filter(lodging_start__lte=date, lodging_end__gte=date).order_by('lodging_start')
        hostings = [hosting.get_details_by_date(date) for hosting in hostings_obj]
        return hostings

    def get_details(self):
        current_hostings = self.get_hostings_by_date()
        current_hosting_ids = [h['id'] for h in current_hostings]

        details = dict(
            id=self.id,
            description=self.description,
            page_description1=self.page_description1,
            page_description2=self.page_description2,
            current_hostings=current_hostings,
            current_hosting_ids=current_hosting_ids,
            lock=self.lock.get_details() if self.lock else None,
            lock_id = self.lock.id if self.lock else None,
            link_code=self.link_code,
            active=self.active
        )
        return details 

class LocksHouse(models.Model):
    house = models.ForeignKey(House, on_delete=models.CASCADE)
    lock = models.ForeignKey(Lock, on_delete=models.CASCADE)

    def get_name(self):
        return self.lock.lock_alias



class HouseUser(models.Model):
    house = models.ForeignKey(House, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def get_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    @classmethod
    def get_user_permission(cls, user_id):
        houses_objects = cls.objects.filter(user_id=user_id)
        houses_list = [{"id": house.house.id, "alias": house.house.description} for house in houses_objects]
        count_houses = houses_objects.count()

        user_permission = {'houses': houses_list, "count_houses": count_houses}
        return user_permission


class HostingRecord(models.Model):
    guest = models.ForeignKey(Person, related_name='record_hostings_as_guest', on_delete=models.CASCADE)
    guest_is_patient = models.BooleanField(default=0)
    patient = models.ForeignKey(Person, related_name='record_hostings_as_patient', on_delete=models.CASCADE, null=True)
    affinity = models.CharField(max_length=50, null=True)
    hospital_ward = models.CharField(max_length=50, null=True)

    def get_details(self):
        details = dict(
            guest = self.guest.get_details(),
            guest_is_patient = self.guest_is_patient,
            patient = self.patient.get_details() if self.patient else None,
            affinity = self.affinity,
            hospital_ward = self.hospital_ward
        )
        return details

class Donor(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50, unique=True, default=generate_random_string)




class Hosting(models.Model):
    house = models.ForeignKey(House, on_delete=models.RESTRICT)
    guest = models.ForeignKey(Person, related_name='hostings_as_guest', on_delete=models.CASCADE)
    patient = models.ForeignKey(Person, related_name='hostings_as_patient', on_delete=models.CASCADE, null=True)
    affinity = models.CharField(max_length=50, null=True)
    guest_is_patient = models.BooleanField(default=0)
    lodging_start = models.DateField()
    lodging_end = models.DateField()
    hospital_ward = models.CharField(max_length=50, null=True)
    hospital_ward_eng = models.CharField(max_length=100, null=True)
    trigger = models.CharField(max_length=50, default='')
    documents = models.BooleanField(default=0)
    note = models.CharField(max_length=500, null=True)
    date_add = models.BigIntegerField(default=default_timestamp)
    send_feedback = models.BooleanField(default=0)
    file_path1 = models.CharField(max_length=100, null=True)
    file_path2 = models.CharField(max_length=100, null=True)
    persons_in_house = models.IntegerField(default=0)
    
    @classmethod
    def get_all_triggers(cls):
        triggers = cls.objects.exclude(Q(trigger__isnull=True) | Q(trigger='')).values_list('trigger', flat=True).distinct()
        return sorted(triggers)
    
    @classmethod
    def get_all_hospital_wards(cls):
        hospital_wards = cls.objects.exclude(Q(hospital_ward__isnull=True) | Q(hospital_ward='')).values_list('hospital_ward', flat=True).distinct()
        return sorted(hospital_wards)
    
    @classmethod
    def convert_filter(cls, key, value):
        if key == 'name':
            words = value.strip().split()
            q = Q()
            for word in words:
                q &= Q(
                    Q(guest__first_name__icontains=word) |
                    Q(guest__last_name__icontains=word) |
                    Q(patient__first_name__icontains=word) |
                    Q(patient__last_name__icontains=word) 
                )
            return q

    def get_details_by_date(self, date):

        check_in = self.lodging_start == date 
        check_out = self.lodging_end == date

        details = dict(
            id=self.id,
            house_id=self.house.id,
            house_description=self.house.description,
            guest_name=self.guest.get_name(),
            lodging_start_formater=self.lodging_start.strftime('%d/%m/%Y'),
            lodging_end_formater=self.lodging_end.strftime('%d/%m/%Y'),
            check_in=check_in,
            check_out=check_out
        )
        return details

    def get_details(self):
        lodging_start_str = self.lodging_start.strftime('%Y-%m-%d')
        lodging_end_str = self.lodging_end.strftime('%Y-%m-%d')
        count_days = (self.lodging_end - self.lodging_start).days

        if self.guest_is_patient:
            patient_to_report = self.guest
            status_guest = "מטופל"
        else:
            patient_to_report = self.patient
            status_guest = 'מלווה'
            if len(self.affinity):
                status_guest += f' ({self.affinity})'
        
        current_date = datetime.now().date()
        check_in = self.lodging_start == current_date 
        check_out = self.lodging_end == current_date

        details = dict(
            id=self.id,
            house_id=self.house.id,
            house_description=self.house.description,
            guest_id=self.guest.id,
            guest_name=self.guest.get_name(),
            guest = self.guest.get_details(),
            patient_id=self.patient.id if self.patient else None,
            patient_name=self.patient.get_name() if self.patient else '',
            patient = self.patient.get_details()  if self.patient else None,
            guest_is_patient=self.guest_is_patient,
            status_guest=status_guest,
            patient_to_report=patient_to_report.get_details(),
            affinity=self.affinity,
            lodging_start=lodging_start_str,
            lodging_end=lodging_end_str,
            lodging_start_val=self.lodging_start,
            lodging_end_val=self.lodging_end,
            lodging_start_formater=self.lodging_start.strftime('%d/%m/%Y'),
            lodging_end_formater=self.lodging_end.strftime('%d/%m/%Y'),
            check_in=check_in,
            check_out=check_out,
            persons_in_house=self.persons_in_house,
            count_days=count_days,
            hospital_ward=self.hospital_ward,
            hospital_ward_eng=self.hospital_ward_eng,
            trigger=self.trigger,
            documents=self.documents,
            note=self.note,
            file_path1=self.file_path1,
            file_path2=self.file_path2,
            date_add=time_to_datetime(self.date_add),
            send_feedback=self.send_feedback
        )
        return details

    def get_details_for_page(self):
        
        details_for_page = dict(
            id=self.id,
            guest_description = self.guest.first_name + " " + self.guest.last_name,
            guest_description_eng = self.guest.first_name_eng + " " + self.guest.last_name_eng,
            hospital_ward = self.hospital_ward,
            hospital_ward_eng = self.hospital_ward_eng,
            lodging_start=self.lodging_start.strftime("%d.%m.%y"),
            lodging_end=self.lodging_end.strftime("%d.%m.%y")
        )
        return details_for_page

    def get_details_for_donor_page(self):
        
        details_for_page = dict(
            id=self.id,
            guest_description = self.guest.first_name_eng + " " + self.guest.last_name_eng,
            hospital_ward = self.hospital_ward_eng,
            lodging_start=self.lodging_start.strftime("%d.%m.%y"),
            lodging_end=self.lodging_end.strftime("%d.%m.%y"),
            status="active" if self.lodging_start <= datetime.now().date() <= self.lodging_end else "inactive",
            house_description = self.house.description,
        )
        return details_for_page

class HousesReport(models.Model):
    description = models.CharField(max_length=30, unique=True)
    report_date = models.DateField()
    date_create = models.BigIntegerField(default=default_timestamp)


    @classmethod
    def create_new_report(cls, str_date):
        time_date = datetime.strptime(str_date, '%Y-%m-%d')
        date = time_date.date()

        formatted_date = time_date.strftime("%d_%m_%Y")
        unique_date = formatted_date
        counter = 1

        while cls.objects.filter(description=unique_date).exists(): 
            unique_date = f"{formatted_date}__{counter}"
            counter += 1
        
        report = cls.objects.create(description=unique_date,report_date=date)
        return report

    @classmethod
    def get_list_reports(cls):
        reports_objects = cls.objects.all().order_by('-date_create')[:20]
        list_report = [{"id": report.id, "description": report.description } for report in reports_objects]
        return list_report

    def get_houses_records_old(self, houses_records_ids=None):
        houses_records = []
        if houses_records_ids:
            houses_records_objects = self.housesreportrecord_set.filter(id__in=houses_records_ids)  
        else:
            houses_records_objects = self.housesreportrecord_set.all()
        all_hostings = Hosting.objects.filter(lodging_start__lte=self.report_date, lodging_end__gte=self.report_date)
        
        hostings_dict = {}
        for hosting in all_hostings:
            if hosting.house.id not in hostings_dict:
                hostings_dict[hosting.house.id] = []
            hostings_dict[hosting.house.id].append(hosting.get_details())

        for house_record_object in houses_records_objects:
            house = house_record_object.house
            
            check_in = next((hosting for hosting in hostings_dict.get(house.id, []) if hosting['lodging_start_val'] == self.report_date), None)
            check_out = next((hosting for hosting in hostings_dict.get(house.id, []) if hosting['lodging_end_val'] == self.report_date), None)

            house_data = dict(
                id=house_record_object.id,
                name=house.description,
                first_hosting=hostings_dict.get(house.id, [None])[0],
                hosting_check_in=check_in,
                hosting_check_out=check_out,
                report_details=house_record_object.get_details()
            )
            houses_records.append(house_data)

        return houses_records

    def get_houses_records(self, houses_records_ids=None):
        houses_records = []
        if houses_records_ids:
            houses_records_objects = self.housesreportrecord_set.filter(id__in=houses_records_ids)  
        else:
            houses_records_objects = self.housesreportrecord_set.all()
        all_hostings = Hosting.objects.filter(lodging_start__lte=self.report_date, lodging_end__gte=self.report_date)
        
        hostings_dict = {}
        for hosting in all_hostings:
            if hosting.house.id not in hostings_dict:
                hostings_dict[hosting.house.id] = []
            hostings_dict[hosting.house.id].append(hosting.get_details())

        for house_record_object in houses_records_objects:
            house = house_record_object.house
            
            check_in = next((hosting for hosting in hostings_dict.get(house.id, []) if hosting['lodging_start_val'] == self.report_date), None)
            check_out = next((hosting for hosting in hostings_dict.get(house.id, []) if hosting['lodging_end_val'] == self.report_date), None)

            house_data = dict(
                id=house_record_object.id,
                name=house.description,
                hostings=hostings_dict.get(house.id, None),
                hosting_check_in=check_in,
                hosting_check_out=check_out,
                report_details=house_record_object.get_details()
            )
            houses_records.append(house_data)

        return houses_records

class HousesReportRecord(models.Model):
    report = models.ForeignKey(HousesReport, on_delete=models.CASCADE)
    house = models.ForeignKey(House, on_delete=models.CASCADE)
    clean = models.BooleanField(default=False)
    clean_check_out = models.BooleanField(default=False)
    meal = models.BooleanField(default=False)
    fault = models.BooleanField(default=False)
    bed = models.BooleanField(default=False)
    note = models.CharField(max_length=300, default='')

    def get_details(self):
        details = dict(
            clean=self.clean,
            clean_check_out=self.clean_check_out,
            meal=self.meal,
            fault=self.fault,
            bed=self.bed,
            note=self.note
        )
        return details


class Transmission(models.Model):
    type_action = models.IntegerField()
    lock_name = models.CharField(max_length=50)
    card_number = models.CharField(max_length=15)
    card_description = models.CharField(max_length=50)
    status_transmission = models.IntegerField(default=0)
    amount_attempts = models.IntegerField(default=0)
    last_transmission = models.BigIntegerField(null=True)
    permission_id = models.IntegerField()
    date_create = models.BigIntegerField(default=default_timestamp)
    user_transmission = models.CharField(max_length=50)

    @classmethod
    def get_amount_in_transmission(cls):
        amount_in_transmission = cls.objects.filter(status_transmission__in=[0, 1, 3]).count()
        if amount_in_transmission == 0:
            amount_in_transmission = ''
        return amount_in_transmission

    def get_details(self):
        details = dict(id=self.id,
                       type_action=self.type_action,
                       lock_name=self.lock_name,
                       card_number=self.card_number,
                       card_description=self.card_description,
                       status_transmission=self.status_transmission,
                       amount_attempts=self.amount_attempts,
                       last_transmission=time_to_datetime(self.last_transmission),
                       permission_id=self.permission_id,
                       date_create=time_to_datetime(self.date_create),
                       user_transmission=self.user_transmission
                       )
        return details


class PermissionCardsManager(models.Manager):
    
    def get_queryset(self):
        from django.db.models import OuterRef, Subquery

        card_type = ContentType.objects.get_for_model(Card)
        cards = Card.objects.filter(pk=OuterRef('object_id'))

        last_use_qs = LockRecord.objects.filter(
            keyboard_pwd=OuterRef('card_number'),
            lock=OuterRef('lock')
        ).order_by('-server_date').values('server_date')[:1]

        qs = super().get_queryset().filter(type_object=card_type).annotate(
            person_full_name=Subquery(cards.annotate(
            full_name=Concat('person__first_name', Value(' '), 'person__last_name')
            ).values('full_name')[:1]),
            person_role=Subquery(cards.values('person__role')[:1]),
            card_number=Subquery(cards.values('card_number')[:1]),
            card_name= Subquery(cards.values('card_name')[:1]),
            last_use=Subquery(last_use_qs)
        )
        return qs

class Permission(models.Model):
    lock = models.ForeignKey(Lock, on_delete=models.CASCADE)
    type_object = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="type_object")
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('type_object', 'object_id')
    card_permission_id = models.IntegerField(null=True)
    type_permission = models.IntegerField()
    start_date = models.BigIntegerField(null=True)
    end_date = models.BigIntegerField(null=True)
    cyclic_config = models.JSONField(null=True)
    grant_by = models.CharField(max_length=50, null=True)
    status_record = models.IntegerField(default=0)
    date_add = models.BigIntegerField(null=True)

    dict_fields = {'cardId': 'card_permission_id',
                   'startDate': 'start_date', "endDate": "end_date", "senderUsername": "grant_by",
                   "createDate": "date_add"}

    objects = models.Manager()
    cards_objects = PermissionCardsManager()


    def get_details(self):
        if self.type_permission == 1:
            type_permission_description = '<i class="bi bi-shield"></i> קבוע'
        elif self.type_permission == 2:
            type_permission_description = '<i class="bi bi-hourglass-split"></i> זמני - ' + time_to_date(self.start_date) + ' עד ' + time_to_date(self.end_date)
        elif self.type_permission == 3:
            type_permission_description = '<i class="bi bi-arrow-clockwise"></i> מחזורי'

        type_ocject_id = self.type_object.id
        if type_ocject_id == 8:
            last_use = LockRecord.objects.filter(keyboard_pwd=self.content_object.card_number, lock=self.lock).order_by('-server_date').first()
            if last_use:
                last_use = time_to_date(last_use.server_date)
            else:
                last_use = ''
        else:
            last_use = ''

        details = dict(
            id=self.id,
            lock_id=self.lock.id,
            lock_alias=self.lock.lock_alias,
            object=self.content_object.get_details(),
            type_object=self.type_object.id,
            object_description=self.content_object.get_description(),
            person_id=self.content_object.person.id,
            person_name=self.content_object.person.get_name(),
            date_add=time_to_date(self.date_add),
            status=self.get_status(),
            type_permission=self.type_permission,
            type_permission_description= type_permission_description,
            start_date=self.start_date,
            end_date=self.end_date,
            cyclic_config=self.get_cyclic_config(),
            last_use=last_use
        )
        return details

    def get_status(self):
            if self.end_date == 0 or self.end_date > int(time.time() * 1000) or not self.status_record == 0:
                return self.status_record
            else:
                return 4


    def get_cyclic_config(self):
        if self.type_permission != 3:
            return {}
        else:
            days = {calendar.day_name[day["weekDay"] - 1]: True for day in self.cyclic_config}
            start_time = self.cyclic_config[0]['startTime']
            hours, remainder = divmod(start_time, 60)
            start_time = "{:02d}:{:02d}".format(hours, remainder)

            end_time = self.cyclic_config[0]['endTime']
            hours, remainder = divmod(end_time, 60)
            end_time = "{:02d}:{:02d}".format(hours, remainder)

            cyclic_config = dict(
                days=days,
                start_time=start_time,
                end_time=end_time
            )
            return cyclic_config

    def delete_permission(self, user_name):
        if self.type_object_id == 16:
            self.delete()
        else:  
            self.status_record = 2
            self.save()

            transmission_record, created = Transmission.objects.get_or_create(permission_id=self.id, type_action=2)

            if created:
                transmission_record.lock_name = self.lock.lock_alias
                transmission_record.card_number = self.content_object.card_number
                transmission_record.card_description = self.content_object.get_full_description()
                transmission_record.user_transmission = user_name

                transmission_record.save()

    def transmission(self):
        api = ApiRequest()

        if self.status_record == 0 or self.status_record == 3:
            return

        transmission_record, created = Transmission.objects.get_or_create(permission_id=self.id, type_action=self.status_record)
        
        if created:
            transmission_record.lock_name = self.lock.lock_alias
            transmission_record.card_number = self.content_object.card_number
            transmission_record.card_description = self.content_object.get_full_description()

        else:
            if transmission_record.status_transmission == 1 or transmission_record.status_transmission == 4:
                return
        
        transmission_record.status_transmission = 1
        transmission_record.amount_attempts = transmission_record.amount_attempts + 1
        transmission_record.last_transmission = int(time.time() * 1000)
        
        transmission_record.save()

        send_message_to_browser('start_transmission')
        send_amount_in_transmission()
        succeeded = False

        if self.lock.active == 0:
            transmission_record.status_transmission = 3
            transmission_record.save()
            return

        if self.status_record == 1:             
            card_name = self.content_object.person.get_name() + "~" + self.content_object.card_name
            if self.type_permission < 3:
                card_type = 1
            else:
                card_type = 4

            add_card_permission_data = dict(lockId=self.lock.lock_id_ttl,
                                            cardNumber=self.content_object.card_number,
                                            cardName=card_name,
                                            startDate=self.start_date,
                                            endDate=self.end_date,
                                            cardType=card_type,
                                            addType=2)

            if self.type_permission == 3:
                add_card_permission_data['cyclicConfig'] = str(self.cyclic_config)

            add_card_permission = api.add_card_permission(add_card_permission_data)
            if add_card_permission and "cardId" in add_card_permission:
                card_permission_id = add_card_permission['cardId']               
                self.card_permission_id = card_permission_id
                self.status_record = 0
                self.save()
                succeeded = True

        elif self.status_record == 2:
            if self.card_permission_id:
                delete_card_permission = api.delete_card_permission(self.lock.lock_id_ttl, self.card_permission_id)

                if delete_card_permission:
                    self.delete()                    
                    succeeded = True
            else:
                self.delete()
                succeeded = True

        if succeeded:
            transmission_record.status_transmission = 2
            transmission_record.save()
            
        else:
            if transmission_record.amount_attempts >= 5:
                transmission_record.status_transmission = 4
            else:
                transmission_record.status_transmission = 3
            transmission_record.save()

        send_message_to_browser('end_transmission')
        send_amount_in_transmission()

class Card(models.Model):
    card_number = models.CharField(max_length=10, unique=True)
    card_name = models.CharField(max_length=50)
    person = models.ForeignKey(Person, on_delete=models.RESTRICT, null=True)
    status_record = models.IntegerField(default=0)
    coffee_card = models.IntegerField(default=0)
    date_add = models.BigIntegerField(default=default_timestamp)
        
    class Meta:
        unique_together = ('card_name', 'person')


    def save(self, *args, **kwargs):
        self.full_clean()
        super(Card, self).save(*args, **kwargs)

    @classmethod
    def get_cards(cls, person_id=None):
        objects = cls.objects.all()
        if person_id:
            objects = objects.filter(person_id=person_id)
        cards = [{"id": card.id, "name": card.card_name} for card in objects]
        return cards

    def get_description(self):
        return self.card_name
    
    def get_full_description(self):
        full_description = self.person.get_name() + " - " + self.card_name
        return  full_description


    def get_details(self):
        details = dict(id=self.id,
                       card_number=self.card_number,
                       card_name=self.card_name,
                       person_name=self.person.get_name(),
                       person_first_name=self.person.first_name,
                       person_last_name=self.person.last_name,
                       prrson_id_number=self.person.id_number,
                       person_phone=self.person.person_phone,
                       person_role=self.person.role,
                       date_add=time_to_datetime(self.date_add),
                       coffee_card=self.coffee_card,
                       description=self.card_name,
                       full_description=self.get_full_description()
                       )
        return details

    def delete_card(self, user_name):
        if self.card_number == '':
            self.delete()
        else:
            permissions = Permission.objects.filter(type_object_id=8, object_id=self.id)
            if permissions.count() > 0:
                for permission in permissions:
                    permission.delete_permission(user_name)
                self.status_record = 1
                self.save()
            else:
                self.delete()

    def rename_care(self):
        api = ApiRequest()
        permissions = Permission.objects.filter(type_object_id=8, object_id=self.id)
        for permission in permissions:
            new_name = self.person.get_name() + "~" + self.card_name
            api.rename_card_permission(permission.card_permission_id, permission.lock.lock_id_ttl, new_name)


class LockRecord(models.Model):
    record_id = models.BigIntegerField()
    lock = models.ForeignKey(Lock, on_delete=models.CASCADE)
    record_type_from_lock = models.IntegerField()
    record_type = models.IntegerField()
    success = models.BooleanField()
    username = models.CharField(max_length=50, null=True)
    keyboard_pwd = models.CharField(max_length=50)
    person_id = models.IntegerField(null=True)
    person_name = models.CharField(max_length=50, null=True)
    type_object_id = models.IntegerField(null=True)
    done_by = models.CharField(max_length=50,  default='')
    object_record_description = models.CharField(max_length=50, default='')
    lock_date = models.BigIntegerField()
    server_date = models.BigIntegerField()

    dict_fields = {'recordId': 'record_id', 'recordTypeFromLock': 'record_type_from_lock',
                   'recordType': 'record_type',
                   "success": "success", "username": "username", "keyboardPwd": "keyboard_pwd", "lockDate": "lock_date",
                   "serverDate": "server_date"}

    class Meta:
        # index on lock and keyboard_pwd
        indexes = [
            models.Index(fields=['lock', 'keyboard_pwd'])
        ]


    def get_details(self):
        details = dict(
            id=self.id,
            lock_alias=self.lock.lock_alias,
            record_type_description=self.get_record_type_description(),
            record_type=self.record_type_from_lock,
            username=self.username,
            date=time_to_datetime(self.server_date),
            time=self.server_date,
            person_id=self.person_id,
            type_object_id=self.type_object_id,
            done_by=self.done_by,
            object_record_description=self.object_record_description,
            person_name=self.person_name
        )

        if self.record_type_from_lock == 25:
            details['person_name'] = self.person_name + ' - ' + self.keyboard_pwd

        return details

            # records_types = {"1": "ביטול נעילה באמצעות אפליקציה",
            #              "4": "ביטול נעילה באמצעות סיסמה",
            #              "17": "ביטול נעילה באמצעות כרטיס",
            #              "8": "ביטול נעילה באמצעות טביעת אצבע",
            #              "11": 'נעילה מרוחקת באמצעות שער',
            #              "28": "ביטול נעילה מרוחק באמצעות שער",
            #              "45": "נעילה אוטומטית",
            #              "47": "נעילה באמצעות מפתח מנעול",
            #              "48": "נעילת מערכת",
            #              "99": "ביטול נעילה באמצעות פלאפון"}

    def get_record_type_description(self):
        record_type = str(self.record_type_from_lock)
        records_types = {
                        "0": "ביטול נעילה באמצעות פלאפון",
                         "1" : "ביטול נעילה באמצעות אפליקציה",
                         "4": "ביטול נעילה באמצעות קוד סיסמה",
                         "7": "ביטול נעילה באמצעות קוד סיסמה נכשל - קוד סיסמה לא ידוע",
                         "17": "ביטול נעילה באמצעות כרטיס",
                         "20": "ביטול נעילה באמצעות טביעת אצבע",
                         "22": "ביטול הנעילה באמצעות טביעת אצבע נכשל - פג תוקף",
                         "25": "ביטול נעילה באמצעות כרטיס נכשל - פג תוקף",
                         "28": "ביטול נעילה מרוחק באמצעות שער",
                         "39": "ביטול הנעילה באמצעות כרטיס נכשל - בוצעה נעילה כפולה",
                         "40": "ביטול הנעילה באמצעות טביעת אצבע נכשל - בוצעה נעילה כפולה",
                         "41": "ביטול הנעילה על ידי אפליקציה נכשל - בוצעה נעילה כפולה",
                         "45": "נעילה אוטומטית",
                         "47": "נעילה באמצעות מפתח מנעול",
                         "48": "נעילת מערכת"
                        }
        return records_types.get(record_type, f'רשומה לא מוכרת ({self.record_type_from_lock})')


class AccessGroup(models.Model):
    group_name = models.CharField(max_length=50)

    def get_lock_count(self):
        return self.lockaccessgroup_set.count()

    @classmethod
    def get_groups(cls, user=None):
        objects = cls.objects.all()
        if user and not user.is_superuser:
            group_ids_to_exclude = []
            for group in objects:
                lock_ids_in_group = group.lockaccessgroup_set.values_list('lock__id', flat=True)
                if not LockUser.objects.filter(lock_id__in=lock_ids_in_group, user=user).exists():
                    group_ids_to_exclude.append(group.id)
            objects = objects.exclude(id__in=group_ids_to_exclude)
        groups = [{"id": group.id, "description": group.group_name, "count_locks": group.get_lock_count()} for group in objects]
        return groups


class LockAccessGroup(models.Model):
    lock = models.ForeignKey(Lock, on_delete=models.CASCADE)
    access_group = models.ForeignKey(AccessGroup, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('lock', 'access_group')

    @classmethod
    def get_group_locks(cls, group_id):
        locks_objects = cls.objects.filter(access_group=group_id)
        locks_list = [{"id": lock.lock.id, "alias": lock.lock.lock_alias} for lock in locks_objects]
        count_locks = locks_objects.count()

        group_locks = {'locks': locks_list, "count_locks": count_locks}
        return group_locks

    def get_name(self):
        return self.access_group.group_name


class LockUser(models.Model):
    lock = models.ForeignKey(Lock, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def get_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    @classmethod
    def get_user_locks(cls, user_id):
        locks_objects = cls.objects.filter(user_id=user_id)
        locks_list = [{"id": lock.lock.id, "alias": lock.lock.lock_alias} for lock in locks_objects]
        count_locks = locks_objects.count()

        group_locks = {'locks': locks_list, "count_locks": count_locks}
        return group_locks

class PassageModeUser(models.Model):
    passage_mode = models.ForeignKey(PassageMode, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def get_name(self):
        return f"{self.user.first_name} {self.user.last_name}"


class Phone(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    phone_name = models.CharField(max_length=50)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    date_add = models.BigIntegerField(default=default_timestamp)
    
    class Meta:
        unique_together = ('phone_name', 'person')

    def get_details(self):
        details = dict(id=self.id,
                       phone=self.phone,
                       phone_name=self.phone_name,
                       person_role=self.person.role,
                       description=self.phone_name,
                       date_add=time_to_datetime(self.date_add),
                       full_description=self.get_full_description()
                       )
        return details

    def get_description(self):
        return self.phone_name

    def get_full_description(self):
        return self.person.get_name() + " (" + self.phone_name + ")"

@receiver(post_delete, sender=Card)
def delete_permissions_of_card(sender, instance, **kwargs):
    Permission.objects.filter(type_object_id=8, object_id=instance.id).delete()


@receiver(post_delete, sender=Phone)
def delete_permissions_of_card(sender, instance, **kwargs):
    Permission.objects.filter(type_object_id=16, object_id=instance.id).delete()


@receiver(pre_save, sender=Person)
def store_person_original(sender, instance, **kwargs):
    """Store original Person data before save to detect changes"""
    if instance.pk:
        try:
            instance._original = Person.objects.get(pk=instance.pk)
        except Person.DoesNotExist:
            instance._original = None
    else:
        instance._original = None


@receiver(post_save, sender=Person)
def send_person_webhook(sender, instance, created, **kwargs):
    """Send webhook when Person is created or updated"""
    import requests
    import json
    
    # Check if anything actually changed (for updates only)
    if not created and hasattr(instance, '_original') and instance._original:
        old_instance = instance._original
        # Compare relevant fields
        fields_to_check = ['id_number', 'first_name', 'last_name', 'first_name_eng', 
                         'last_name_eng', 'birth_date', 'email', 'address', 'house_number',
                         'city', 'person_phone', 'role', 'note', 'status_record', 'not_to_view']
        
        has_changes = False
        for field in fields_to_check:
            if getattr(old_instance, field) != getattr(instance, field):
                has_changes = True
                break
        
        # Also check file field
        if old_instance.id_number_file != instance.id_number_file:
            has_changes = True
        
        if not has_changes:
            return  # No changes, don't send webhook
    
    webhook_url = "https://hook.eu1.make.com/p1kso9x2p2ht6ykip1cvahqw7wwyzmyq"
    
    # Prepare data
    data = {
        "type": "person",
        "action": "created" if created else "updated",
        "id": instance.id,
        "id_number": instance.id_number,
        "first_name": instance.first_name,
        "last_name": instance.last_name,
        "first_name_eng": instance.first_name_eng,
        "last_name_eng": instance.last_name_eng,
        "birth_date": instance.birth_date.isoformat() if instance.birth_date else None,
        "email": instance.email,
        "address": instance.address,
        "house_number": instance.house_number,
        "city": instance.city,
        "person_phone": instance.person_phone,
        "role": instance.role,
        "note": instance.note,
        "status_record": instance.status_record,
        "not_to_view": instance.not_to_view,
        "date_add": instance.date_add,
        "id_number_file_url": instance.id_number_file.url if instance.id_number_file else None
    }
    
    try:
        response = requests.post(webhook_url, json=data, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Log error but don't fail the save operation
        print(f"Webhook error: {e}")


@receiver(pre_save, sender=Hosting)
def store_hosting_original(sender, instance, **kwargs):
    """Store original Hosting data before save to detect changes"""
    if instance.pk:
        try:
            instance._original = Hosting.objects.get(pk=instance.pk)
        except Hosting.DoesNotExist:
            instance._original = None
    else:
        instance._original = None


@receiver(post_save, sender=Hosting)
def send_hosting_webhook(sender, instance, created, **kwargs):
    """Send webhook when Hosting is created or updated"""
    import requests
    import json
    
    # Check if anything actually changed (for updates only)
    if not created and hasattr(instance, '_original') and instance._original:
        old_instance = instance._original
        # Compare relevant fields
        fields_to_check = ['house_id', 'guest_id', 'patient_id', 'affinity', 
                         'guest_is_patient', 'lodging_start', 'lodging_end', 
                         'hospital_ward', 'hospital_ward_eng', 'trigger', 'documents',
                         'note', 'send_feedback', 'file_path1', 'file_path2', 'persons_in_house']
        
        has_changes = False
        for field in fields_to_check:
            if getattr(old_instance, field) != getattr(instance, field):
                has_changes = True
                break
        
        if not has_changes:
            return  # No changes, don't send webhook
    
    webhook_url = "https://hook.eu1.make.com/p1kso9x2p2ht6ykip1cvahqw7wwyzmyq"
    
    # Prepare data
    data = {
        "type": "hosting",
        "action": "created" if created else "updated",
        "id": instance.id,
        "house_id": instance.house.id,
        "house_description": instance.house.description,
        "guest_id": instance.guest.id,
        "guest_name": instance.guest.get_name(),
        "guest_first_name": instance.guest.first_name,
        "guest_last_name": instance.guest.last_name,
        "guest_id_number": instance.guest.id_number,
        "guest_phone": instance.guest.person_phone,
        "patient_id": instance.patient.id if instance.patient else None,
        "patient_name": instance.patient.get_name() if instance.patient else None,
        "patient_first_name": instance.patient.first_name if instance.patient else None,
        "patient_last_name": instance.patient.last_name if instance.patient else None,
        "patient_id_number": instance.patient.id_number if instance.patient else None,
        "affinity": instance.affinity,
        "guest_is_patient": instance.guest_is_patient,
        "lodging_start": instance.lodging_start.isoformat(),
        "lodging_end": instance.lodging_end.isoformat(),
        "hospital_ward": instance.hospital_ward,
        "hospital_ward_eng": instance.hospital_ward_eng,
        "trigger": instance.trigger,
        "documents": instance.documents,
        "note": instance.note,
        "date_add": instance.date_add,
        "send_feedback": instance.send_feedback,
        "file_path1": instance.file_path1,
        "file_path2": instance.file_path2,
        "persons_in_house": instance.persons_in_house
    }
    
    try:
        response = requests.post(webhook_url, json=data, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Log error but don't fail the save operation
        print(f"Webhook error: {e}")

