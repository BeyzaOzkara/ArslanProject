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

        self.send(text_data = json.dumps({
            'type': 'connection_established',
            'message': str(self.group_name)
        }))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        print(message)
        # Process the message as needed
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, 
            {
                "type": "send_notification", 
                "message": message
            }
        )

    def notif_message(self, event):
        message = event['message']
        print(message)
        # Send message to WebSocket
        self.send(text_data=json.dumps({"message": message}))