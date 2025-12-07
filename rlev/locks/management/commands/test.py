from django.core.management.base import BaseCommand
# from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from locks.consumers import send_message_to_browser
from locks.models import Lock

class Command(BaseCommand):
    help = 'Run Tertiary Daily process'

    def handle(self, *args, **options):
        
        import requests

        url = 'https://lock2.ttlock.com/lock/changeTimezoneRawOffset'

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'he,en-US;q=0.9,en;q=0.8,he-IL;q=0.7',
            'Cache-Control': 'no-cache,no-store',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': 'JSESSIONID=D6F4FEE390821FF2493C7E4B581A7F2D; SITE_ID=h0pezvQtmpN7SgljEM6IGA==; SITE_INFO=zmc/oJZHt6ZWDHUefqTrNVfpdZZCiWzh3/0Fif5hCB1XscuT19GB0ArjjnekaW6yWtjqg9Ur5VNxCRdMdxyZSbwvKoc7a1fOzgpQxb/nZwDrak902j/KQTL3aj5QTxxHaKZagFNYu3Q8DlaqneqKOg==; COUNTRY_AREA_ID=hHJfz/Usm5J6SwhiEc+JGQ==; USER_NAME=3SQ9sZ5Q/PJDBWEBfqjrOenouezJizE2y+/g8sMx6Ps=; LOGIN_ACCOUNTS=7mc5oJdS8O4dKzEseKzmfnPFIQpz7pN0IgJBb5+/40s=; ACCESS_TOKEN=xAYXkKwbuuoiAkwAZY/UTvfNiJr4cC88w+w1mXWCFbBD3IJD3dW/LWmhQSR2iIjl',
            'Origin': 'https://lock2.ttlock.com',
            'Pragma': 'no-cache',
            'Referer': 'https://lock2.ttlock.com/manage/ekey',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'accessToken': 'qCFQW9/vVGJlzNSY7iIvmKUOkSMovaO2UF8QlTwJetI=',
            'appId': '838233ed921e44249a26f215bb0042b8',
            'appSecret': '71a3ecab58a36a0c5100ce58043550b2',
            'language': 'en-US',
            'packageName': 'com.tongtongsuo.app',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'signature': 'N1zHPMLPDMhexYF0jfkmw5XMkhCrXwNMOEDQEbzEnkg='
        }

        locks_objects = Lock.objects.all()
        for lock in locks_objects:
            data = {
                'date': '1730027334776',
            
                'timezoneRawOffSet': '7200000'
            }
            data['lockId'] = lock.lock_id_ttl

            response = requests.post(url, headers=headers, data=data)

            # Print the response from the server
            print(response.json())
