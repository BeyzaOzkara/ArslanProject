from channels.generic.websocket import AsyncWebsocketConsumer
import json

# class NotificationConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.group_name = 'notifications_group'
#         await self.channel_layer.group_add(
#             self.group_name,
#             self.channel_name
#         )
#         await self.accept()
#         await self.send(text_data = json.dumps({
#             'type': 'connection_established',
#             'message': 'Connection established!'
#         }))

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         message = text_data_json["message"]
#         # Process the message as needed
#         await self.channel_layer.group_send(
#             self.group_name, 
#             {
#                 "type": "chat.message", 
#                 "message": message
#             }
#         )

#     async def chat_message(self, event):
#         message = event['message']
#         # Send message to WebSocket
#         await self.send(text_data=json.dumps({"message": message}))

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_name = f'user_{self.user.id}_notifications'
        self.room_group_name = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        await self.send(text_data = json.dumps({
            'type': 'connection_established',
            'message': str(self.user) + ' ' + str(self.user.id),
        }))
        await self.send_unread_notifications()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data_json = json.loads(text_data)
        message_type = data_json.get('type')

        if message_type == 'mark_as_read':
            notification_id = data_json.get('notification_id')
            await self.mark_notification_as_read(notification_id)

    async def send_notification(self, event):
        notification_data = event['notification']
        # Send notification data to the WebSocket if it's unread
        if not notification_data['is_read']:
            await self.send(text_data=json.dumps({
                'notification': notification_data
            }))

    async def mark_notification_as_read(self, notification_id):
        try:
            from .models import Notification
            notification = await Notification.objects.get(id=notification_id)
            if notification.user == self.user and not notification.is_read:
                notification.is_read =True
                await notification.save()
        except Notification.DoesNotExist:
            pass

    async def send_unread_notifications(self):
        from .models import Notification
        unread_notifications = await Notification.objects.filter(user=self.user, is_read = False)
        for notification in unread_notifications:
            await self.send_notification({'notification': {
                'id': notification.id,
                'message': notification.message,
                'is_read': notification.is_read,
                'timestamp': notification.timestamp.strftime('%d-%m-%Y %H:%M'),
            }})
