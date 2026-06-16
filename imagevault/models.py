from django.db import models
from django.utils import timezone
from datetime import timedelta

class ImageFile(models.Model):
    image=models.ImageField(upload_to='images/')
    uploaded_at=models.DateTimeField(auto_now_add=True)
    expires_at=models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at=timezone.now()+timedelta(days=4)
        super().save(*args, **kwargs)
    

@property
def file_size(self):
    try:
        size= self.image.file.size

        if size < 1024:
            return f"{size} Bytes"
        elif size < 1024 *1024:
            return f"{round(size / 1024, 2)} KB"
        else:
            return f"{round(size  / (1024 * 1024), 2)} MB"
    except Exception:
        return "Unknown"

@property
def file_format(self):
    return self.image.name.split('.')[-1].upper()

def _str_(self):
    return self.image.name