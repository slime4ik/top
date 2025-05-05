import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
import base64
import django
django.setup()

from .models import ChatMessage, Group
from accounts.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.group_name = f'chat_{self.group_id}'
        
        # Проверка, что пользователь состоит в группе
        if await self.is_group_member():
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'chat_message':
            message = await self.save_message(
                data['user_id'],
                data['group_id'],
                data['message']
            )
            
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': message.text,
                    'user_id': message.user.id,
                    'user_name': message.user.nickname,
                    'user_avatar': message.user.avatar.url if message.user.avatar else None,
                    'timestamp': message.created_at.isoformat(),
                    'reply_to': None
                }
            )
        
        elif message_type == 'chat_image':
            image_data = data['image'].split(';base64,')[1]
            image_file = ContentFile(base64.b64decode(image_data), name=data['file_name'])
            
            message = await self.save_image_message(
                data['user_id'],
                data['group_id'],
                image_file
            )
            
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_image',
                    'image': message.image.url,
                    'file_name': data['file_name'],
                    'user_id': message.user.id,
                    'user_name': message.user.nickname,
                    'user_avatar': message.user.avatar.url if message.user.avatar else None,
                    'timestamp': message.created_at.isoformat(),
                    'reply_to': None
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))
    
    async def chat_image(self, event):
        await self.send(text_data=json.dumps(event))
    
    @database_sync_to_async
    def is_group_member(self):
        group = Group.objects.get(id=self.group_id)
        user = self.scope['user']
        return user.is_authenticated and (
            user == group.creator or 
            user in group.admins.all() or 
            user in group.members.all()
        )
    
    @database_sync_to_async
    def save_message(self, user_id, group_id, text, reply_to=None):
        user = User.objects.get(id=user_id)
        group = Group.objects.get(id=group_id)
        return ChatMessage.objects.create(
            user=user,
            group=group,
            text=text,
            reply_to=reply_to
        )
    
    @database_sync_to_async
    def save_image_message(self, user_id, group_id, image_file):
        user = User.objects.get(id=user_id)
        group = Group.objects.get(id=group_id)
        message = ChatMessage.objects.create(
            user=user,
            group=group,
            text='[image]'
        )
        message.image.save(image_file.name, image_file)
        return message