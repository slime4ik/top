# groups/serializers.py
from rest_framework import serializers
from .models import ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'text', 'image', 'timestamp', 'user_id', 'user_name', 'user_avatar']

    def get_user_name(self, obj):
        return obj.user.nickname if obj.user else 'Неизвестный'

    def get_user_avatar(self, obj):
        if obj.user and obj.user.avatar:
            return obj.user.avatar.url
        return '/static/images/default-avatar.png'