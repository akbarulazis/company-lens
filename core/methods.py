from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def send_notification(notification_type, content):
    """
    Send a notification to all connected WebSocket clients.
    
    Args:
        notification_type: The type of notification (e.g. 'notification', 'comparison_result')
        content: The content of the notification
    """
    channel = get_channel_layer()
    
    # For comparison_result, use the dedicated handler
    if notification_type == 'comparison_result':
        async_to_sync(channel.group_send)('notification', {
            'type': 'comparison_result',
            'message': content,
        })
    else:
        async_to_sync(channel.group_send)('notification', {
            'type': 'send_notification',
            'message': {
                'content': content,
                'type': notification_type
            },
        })