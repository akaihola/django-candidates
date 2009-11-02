from django.db import models

class TestModel(models.Model):

    text = models.CharField(max_length=100)
