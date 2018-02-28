from django.db import models

class LDPSource(models.Model):
    container = models.URLField()
    federation = models.CharField(max_length=255)
    
    class Meta:
        rdf_type = 'hd:federation'
    
    def __str__(self):
        return "{}: {}".format(self.federation, self.container)
