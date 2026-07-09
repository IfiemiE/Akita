import os
from datetime import datetime


def set_user_uploaded_file_path(instance, filename):
    """ 
    Creates a file path for a user-uploaded file.
    """
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%b")
    day = now.strftime("%d")
    user_name = instance.user.username if instance.user else "anonymous"
    user_dir_path = os.path.join(year, month, day, user_name, filename)
    return user_dir_path
        