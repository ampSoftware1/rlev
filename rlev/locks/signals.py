messages_to_browser = []
import json
import time
from django.dispatch import Signal
from django.http import StreamingHttpResponse
from django.db.models.signals import post_delete
from django.dispatch import receiver

def handle_messages_to_browser(sender, message, **kwargs):
    global messages_to_browser
    if not messages_to_browser:
        messages_to_browser = []
    messages_to_browser.append(message)


singal_messages_to_browser = Signal()
singal_messages_to_browser.connect(handle_messages_to_browser)

def event_stream():
    global messages_to_browser
    while True:
        yield ""
        time.sleep(1)

        if messages_to_browser:
            message_to_browser = json.dumps(messages_to_browser)
            yield f'data: {message_to_browser}\n\n'
            messages_to_browser = []

def sse_stream(request):
    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


