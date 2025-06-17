# models.py
from django.db import models

class SiteSetting(models.Model):
    title = models.CharField(max_length=200, default="My App")
    description = models.TextField(blank=True)
    terms_url = models.URLField(blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        return cls.objects.get_or_create(pk=1)[0]