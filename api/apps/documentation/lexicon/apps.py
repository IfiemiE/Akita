from django.apps import AppConfig


class LexiconConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    
    name = 'apps.documentation.lexicon'
    label = 'documentation_lexicon'

    def ready(self):
        # Importing the module registers all @receiver decorators in signals.py.
        # The import path mirrors `name` above — always keep them in sync.
        import apps.documentation.lexicon.signals  # noqa: F401
        