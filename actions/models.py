from django.db import models
from django.conf import settings

class Action(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, 
                              related_name='actions', 
                              on_delete=models.SET_NULL, 
                              null=True, 
                              blank=True)
    group = models.ForeignKey('groups.Group', 
                              on_delete=models.CASCADE, 
                              related_name='actions')
    verb = models.CharField(max_length=250)
    created = models.DateTimeField(auto_now_add=True)
    # is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['-created']),
        ]
        ordering = ['-created']

    def __str__(self):
        return f"{self.user} - {self.verb} in group {self.group}"
