from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
import json
import logging

class NotificationConsumer(AsyncWebsocketConsumer):
    logger = logging.getLogger(__name__)

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
        self.logger.debug(f"WebSocket connected for user {self.user.id}")
        await self.send_unread_notifications()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        self.logger.debug(f"WebSocket disconnected for user {self.user.id}")

    async def receive(self, text_data):
        data_json = json.loads(text_data)
        message_type = data_json.get('type')

        if message_type == 'mark_as_read':
            notification_id = data_json.get('notification_id')
            self.logger.debug(f"Received message with type mark_as_read")
            await self.mark_notification_as_read(notification_id)

    async def send_notification(self, event):
        notification_data = event['notification']
        # Send notification data to the WebSocket if it's unread
        self.logger.debug(f"Sent notification start: {notification_data['id']}")
        if not notification_data['is_read']:
            await self.send(text_data=json.dumps({
                'type': 'notification',
                'notification': notification_data
            }))
            self.logger.debug(f"Sent notification if not is_read: {notification_data['id']}")
            

    async def mark_notification_as_read(self, notification_id):
        try:
            from .models import Notification
            @database_sync_to_async
            def get_noti():
                return Notification.objects.get(id=notification_id)
            notification = await get_noti()
            if notification.user == self.user and not notification.is_read:
                notification.is_read =True
                await notification.save()
        except Exception as e:
            self.logger.debug(f"Error mark notification as read: {e}")

    async def send_unread_notifications(self):
        try:
            from .models import Notification
            @database_sync_to_async
            def fetch_unread_notifications():
                return list(Notification.objects.filter(user_id=self.user.id, is_read=False))
            
            unread_notifications_list = await fetch_unread_notifications()
            for notification in unread_notifications_list:
                await self.send_notification({'notification': {
                    'id': notification.id,
                    'message': notification.message,
                    'is_read': notification.is_read,
                    'timestamp': notification.timestamp.strftime('%d-%m-%Y %H:%M'),
                }})
            self.logger.debug(f"Notifications are sent")
        except Exception as e:
            self.logger.debug(f"Error fetching unread notifications: {e}")