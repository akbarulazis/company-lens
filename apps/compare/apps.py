from django.apps import AppConfig


class CompareConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.compare'
    
    def ready(self):
        """Import tasks module to ensure Huey can discover the tasks"""
        import apps.compare.tasks