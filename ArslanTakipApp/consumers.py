from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json

class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = 'notifications_group'
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        # Process the message as needed
        async_to_sync(self.channel_layer.group_send)(
            'notifications_group',  # Name of the WebSocket group
            {
                'type': 'send_notification',
                'message': message
            }
        )