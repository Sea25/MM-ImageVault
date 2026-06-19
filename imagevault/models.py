from django.db import models
from django.utils import timezone
from datetime import timedelta


class ConvertedImage(models.Model):
    original_image = models.ImageField(upload_to='originals/')
    converted_image = models.ImageField(upload_to='converted/', blank=True, null=True)
    original_format = models.CharField(max_length=20, blank=True)
    output_format = models.CharField(max_length=20)
    converted_file_size = models.PositiveBigIntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.original_image and not self.original_format:
            self.original_format = self.original_image.name.split('.')[-1].upper()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=4)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_image.name