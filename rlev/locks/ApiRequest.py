import hashlib
import logging
import sys
import time
import datetime 
import os
import requests

from .consumers import send_message_to_browser

class ApiRequest:
    
    CLIENT_ID = "4c866d9878464ce5abc3fbf3c54b3c1e"
    CLIENT_SECRET = "7e455c015c9a2e931a1a3e61f75b6cdc"
    ACCESS_TOKEN = None

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        access_token_path = os.path.join(current_dir, 'accessToken')
        with open(access_token_path, 'r') as file:
            self.ACCESS_TOKEN = file.read()
            
    def send_request(self, url, data):
        data['clientId'] = self.CLIENT_ID
        data['accessToken'] = self.ACCESS_TOKEN
        data['date'] = int(time.time() * 1000)
        response = requests.post(url, data=data)
        response_json = response.json() 
        # print(response_json)
        if "errcode" in response_json:
            if not response_json['errcode'] == 0:
                if response_json['errcode'] == 20002 and "lockId" in data:
                    from .models import Lock
                    from django.core.exceptions import ObjectDoesNotExist
                    try:
                        lock = Lock.objects.get(lock_id_ttl=data['lockId'])
                        lock.active = False
                        lock.save()
                        send_message_to_browser('error_lock_not_active')
                        
                    except ObjectDoesNotExist:
                        pass
                self.logger.error(f"Sens data: {data}: Error received: {response_json}")
                return False
        
        return response_json

    def get_access_token(self, user_name, password):
        url = 'https://euapi.ttlock.com/oauth2/token'

        md5_hash_object = hashlib.md5()
        md5_hash_object.update(password.encode('utf-8'))
        md5_hex_digest = md5_hash_object.hexdigest()
        data = {'username': user_name, 'password': md5_hex_digest, 'clientSecret': self.CLIENT_SECRET}

        response = self.send_request(url, data)
        return response
    
    def get_lock_details(self, lock_id):
        url = "https://euapi.ttlock.com/v3/lock/detail"
        data = {"lockId": lock_id}

        response = self.send_request(url, data)
        return response

    def update_lock_time(self, lock_id):
        url = 'https://euapi.ttlock.com/v3/lock/updateDate'

        data = {"lockId": lock_id}
        response = self.send_request(url, data)
        return response

    def get_lock_status(self, lock_id):
        url = "https://euapi.ttlock.com/v3/lock/queryOpenState"
        data = {"lockId": lock_id}
        response = self.send_request(url, data)
        return response

    def change_lock_alias(self, lock_id, new_alias):
        url = "https://euapi.ttlock.com/v3/lock/rename"
        data = {"lockId": lock_id, "lockAlias": new_alias}

        response = self.send_request(url, data)
        return response

    def lock(self, lock_id):
        url = "https://euapi.ttlock.com/v3/lock/lock"
        data = {"lockId": lock_id}

        response = self.send_request(url, data)
        return response

    def unlock(self, lock_id):
        url = "https://euapi.ttlock.com/v3/lock/unlock"
        data = {"lockId": lock_id}

        response = self.send_request(url, data)
        return response
    
    def send_passage_mode(self, lock_id, mode, days = []):
        url = "https://euapi.ttlock.com/v3/lock/configPassageMode"
        
        data = {"lockId": lock_id,
                "type": 2,
                "passageMode" : mode}
        

        if not days:
            days = "[1,2,3,4,5,6,7]"
        data['weekDays'] = days
        response = self.send_request(url, data)
        print(response)
        return response

    def get_locks_list(self, page_no=1, page_size=100):
        url = 'https://euapi.ttlock.com/v3/lock/list'
        data = {"pageNo": page_no, "pageSize": page_size}

        response = self.send_request(url, data)
        return response

    def get_cards_list(self, lock_id, page_no=1, page_size=100):
        url = "https://euapi.ttlock.com/v3/identityCard/list"
        data = {"lockId": lock_id, "pageNo": page_no, "pageSize": page_size}

        response = self.send_request(url, data)
        return response

    def get_records_list(self, lock_id, page_no=1, page_size=100, start_date=None, end_date=None):
        if start_date is None:
            start_date = int((datetime.datetime.now() - datetime.timedelta(days=1)).timestamp()) * 1000
        url = "https://euapi.ttlock.com/v3/lockRecord/list"
        data = {"lockId": lock_id, "startDate": start_date, "pageNo": page_no, "pageSize": page_size}
        if end_date is not None:
            data['endDate'] = end_date

        # print(data)
        response = self.send_request(url, data)
        return response

    def add_card_permission(self, data, to_reversed=False):
        if to_reversed:
            url = "https://euapi.ttlock.com/v3/identityCard/addForReversedCardNumber"
        else:
            url = "https://euapi.ttlock.com/v3/identityCard/add"

        response = self.send_request(url, data)
        return response
    
    def rename_card_permission(self, card_id, lock_id, new_name):
        url = "https://euapi.ttlock.com/v3/identityCard/rename"
        data = {"lockId": lock_id, "cardId": card_id, "cardName": new_name}

        response = self.send_request(url, data)
        print(response)
        return response        

    def delete_card_permission(self, lock_id, card_id):
        url = "https://euapi.ttlock.com/v3/identityCard/delete"
        data = {"lockId": lock_id, "cardId": card_id,  "deleteType": 2}

        response = self.send_request(url, data)
        return response




