from django.contrib import admin
from django.urls import path, include
from core.consumer import NotificationConsumer
from django.conf.urls.static import static
from django.conf import settings
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.users.urls')),
    path('workspaces/', include('apps.workspaces.urls')),
    path('compare/', include('apps.compare.urls')),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi())
]