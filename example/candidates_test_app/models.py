from django.db import models
from candidates.models import ApplicationBase

class Application(ApplicationBase):
    cv = models.TextField()
    experience_years = models.IntegerField()
