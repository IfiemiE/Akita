from .base import BASE_DIR 
from .base import *
from .development import SECRET_KEY as SECRET_KEY_TEST

# Use same secret key as for development
SECRET_KEY = SECRET_KEY_TEST

# Use sqlite for tests
DATABASES = {
    'default': {
       'ENGINE': 'django.db.backends.sqlite3',
       'NAME': BASE_DIR / 'test_db.sqlite3',
     }
}

# Fixture Directories and Files
FIXTURE_DIRS = [
    BASE_DIR/ 'fixtures',
]

# Overwrite DEBUG
DEBUG = True
