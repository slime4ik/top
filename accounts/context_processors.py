from .models import Notification, FriendRequest

def notification_counts(request):
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(user=request.user, read=False).count()
        pending_requests = FriendRequest.objects.filter(user_to=request.user, status='pending').count()
        return {
            'notification_total': unread_notifications + pending_requests
        }
    return {'notification_total': 0}
