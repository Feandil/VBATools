from django.db import models
from django.utils import timezone

class Email(models.Model):
    date = models.DateTimeField('date sent')
    sender = models.EmailField(blank=True)
    messageid = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    returnpath = models.EmailField(blank=True)
    useragent =  models.CharField(blank=True,max_length=100)

class EmailRecipient(models.Model):
    recipient = models.EmailField()
    email = models.ForeignKey('Email', related_name='recipients', on_delete=models.CASCADE)

class Sample(models.Model):
    email = models.ForeignKey('Email', related_name='samples', on_delete=models.CASCADE, null=True, blank=True)
    filename = models.CharField(max_length=100)
    size = models.IntegerField()
    md5 = models.CharField(max_length=32)
    sha1 = models.CharField(max_length=40)
    sha256 = models.CharField(max_length=64)
    decoded = models.ForeignKey('DecodedVBA', related_name='samples', on_delete=models.CASCADE, null=True, blank=True)
    deobfuscated = models.ForeignKey('DeobfuscatedVBA', related_name='samples', on_delete=models.CASCADE, null=True, blank=True)

class RawVBA(models.Model):
    sample = models.ForeignKey('Sample', related_name='raw', on_delete=models.CASCADE)
    position = models.IntegerField()
    content = models.TextField()
    class Meta:
        ordering = ['position']

class DecodedVBA(models.Model):
    size = models.IntegerField()
    md5 = models.CharField(max_length=32)
    sha1 = models.CharField(max_length=40)
    sha256 = models.CharField(max_length=64)
    content = models.TextField()
    class Meta:
        unique_together = ('size', 'md5', 'sha1', 'sha256')

class DeobfuscatedVBA(models.Model):
    size = models.IntegerField()
    md5 = models.CharField(max_length=32)
    sha1 = models.CharField(max_length=40)
    sha256 = models.CharField(max_length=64)
    content = models.TextField()
    class Meta:
        unique_together = ('size', 'md5', 'sha1', 'sha256')
