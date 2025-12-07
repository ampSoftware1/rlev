

import requests
from datetime import datetime

class WebHooks:

    make_base_url = "https://hook.eu1.make.com/994d0q2xbamdgqr9i1uclwjx7a4ft7sr"
    sms_base_url = "https://call2all.co.il/ym/api/SendSms?token=033132035:7762&phones=0509186000"

    def send(self, category, level, message, type, error, name):
       

        data = {
            "category": category,
            "level": level,
            "message": message,
            "type": type,
            "error": error,
            "name": name
        }
        
        response = requests.post(self.make_base_url, json=data)
        print(response)
        return response
    
    def send_sms(self, message):
        request = self.sms_base_url + "&message="+ message
        requests.post(request)
