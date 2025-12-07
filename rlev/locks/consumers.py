import json

# from asgiref.sync import async_to_sync
# from channels.generic.websocket import WebsocketConsumer
# import channels


# class MessagesConsumer(WebsocketConsumer):
#     def connect(self):
#         async_to_sync(self.channel_layer.group_add)(
#             'chat_messages', self.channel_name
#         )

#         self.accept()

#     def disconnect(self, close_code):
#         async_to_sync(self.channel_layer.group_discard)(
#             'chat_messages', self.channel_name
#         )

#     def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         message = text_data_json["message"]
#         self.send_message(message)
        

#     def send_message(self, message):
#         async_to_sync(self.channel_layer.group_send)(
#             'chat_messages', {"type": "chat_message", "message": message}
#         )

#     def chat_message(self, event):
#         message = event["message"]

#         self.send(text_data=json.dumps({"message": message}))

# class MessagesSender(WebsocketConsumer):

#     def send(self, message):
#         self.channel_layer = channels.layers.get_channel_layer()

#         async_to_sync(self.channel_layer.group_send)(
#             'chat_messages', {"type": "chat_message", "message": message}
#         )

def send_message_to_browser(type_message, data =''):
    import pusher
    pusher_client = pusher.Pusher(
    app_id='1943812',
    key='2e4260e6830134379df9',
    secret='d1edc6d130f28e6a1feb',
    cluster='ap2',
    ssl=True
    )

    pusher_client.trigger('messages', 'get_message', {'type': type_message, 'data': data})
    
    # m = MessagesSender()
    # message = json.dumps({"type": type, "data": data})
    
    # try:
    #     m.send(message)
    # except Exception as e:
    #     return
    
def send_amount_in_transmission():
    from .models import Transmission
    amount_in_transmission = Transmission.get_amount_in_transmission()
    send_message_to_browser('amount_in_transmission', amount_in_transmission)
