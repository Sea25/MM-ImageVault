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
    def _str_(self):
        return self.image.name