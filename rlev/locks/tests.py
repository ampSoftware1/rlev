from django.http import StreamingHttpResponse
from django.test import TestCase

from locks.ApiRequest import ApiRequest


api = ApiRequest()

lock_id = '16841228'

print(api.update_lock_time(lock_id))
