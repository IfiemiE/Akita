from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    
    name = 'apps.identity.users'
    label = 'identity_users'
    
    def ready(self):
        # Importing the module registers all @receiver decorators in signals.py.
        # The import path mirrors `name` above — always keep them in sync.
        import apps.identity.users.signals  # noqa: F401
        