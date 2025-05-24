from django.urls import  path
from .views import chat_view, chat_message

urlpatterns = [
    path('workspaces/<int:workspace_id>/chat/', chat_view, name='chat_view'),
path('workspaces/<int:workspace_id>/chat/message', chat_message, name='chat_message'),

]