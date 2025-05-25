from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add('notification', self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('notification', self.channel_name)

    async def send_notification(self, event):
        message = event['message']
        notification_type = event.get('type', 'notification')
        
        await self.send(text_data=json.dumps({
            'type': notification_type,
            'message': message
        }))
        
    async def comparison_result(self, event):
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'type': 'comparison_result',
            'message': message
        }))