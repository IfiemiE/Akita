from django.core.management.base import BaseCommand
from apps.infrastructure.core.models import Language, Dialect
from apps.common.constants import(
    APPLICATION_LANGUAGE, APPLICATION_DIALECT,
    APPLICATION_LANGUAGE_ISO_CODE, APPLICATION_DIALECT_ISO_CODE,
) 
 
"""
USAGE:
python manage.py load_appdialect : (default) Creates records from APPLICATION data, skips if already present,
                                    for both APPLICATION Language and Dialect.
                                
python manage.py load_appdialect -d : Same as default

python manage.py load_appdialect --dialect : Same as default

python manage.py load_appdialect --lang-only : Creates record from APPLICATION data, skips if already present,
                                                for the Language only, without Dialect.
                                                
python manage.py load_appdialect --l : Creates record from APPLICATION data, skips if already present,
                                       for the Language only, without Dialect.
"""


class Command(BaseCommand):
    help = "Seed Application language and dialect records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lang-only", "-l", # long and short flags accepted
            action="store_true",
            help="Seed only the language record.",
        )
        parser.add_argument(
            "--dialect", "-d", # Both accepted. Any of them maps to the other in the 'options' argument.
            action="store_true",
            help="Seed the both the language and the dialect records.\
                It is also the default if no flag is entered",
        )
        
    def seed_language(self):
        language, created = Language.objects.get_or_create(
            name = APPLICATION_LANGUAGE,
            iso_code = APPLICATION_LANGUAGE_ISO_CODE,
            is_target = True
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {APPLICATION_LANGUAGE} language."))
        else:
            self.stdout.write(f"{APPLICATION_LANGUAGE} language already exists — skipped.")
        return language

    def seed_dialect(self):
        app_language = self.seed_language()
        dialect, created = Dialect.objects.get_or_create(
            language = app_language,
            name = APPLICATION_DIALECT,
            iso_code = APPLICATION_DIALECT_ISO_CODE,
            is_target = True
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {APPLICATION_DIALECT} dialect."))
        else:
            self.stdout.write(f"{APPLICATION_DIALECT} dialect already exists — skipped.")
        return dialect
    
    
    def handle(self, *args, **options):
        if options["lang_only"]:   # True if --language is passed, False if not
            self.seed_language()
        else: # Covers when --dialect is used and when "--language" is NOT passed; which could mean when no flag
            self.seed_dialect()
        
