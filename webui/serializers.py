from rest_framework import serializers

from .models import Email, EmailRecipient, Sample, RawVBA, DecodedVBA, DeobfuscatedVBA

class DeobfuscatedVBASerializer(serializers.ModelSerializer):
    class Meta:
        model = DeobfuscatedVBA
        fields = ('id', 'size', 'md5', 'sha1', 'sha256', 'content')

class DecodedVBASerializer(serializers.ModelSerializer):
    class Meta:
        model = DecodedVBA
        fields = ('id', 'size', 'md5', 'sha1', 'sha256', 'content')

class RawVBASerializer(serializers.ModelSerializer):
    class Meta:
        model = RawVBA
        fields = ('position', 'content')

class SampleSerializer(serializers.ModelSerializer):
    raw = RawVBASerializer(many=True, read_only=True)
    class Meta:
        model = Sample
        fields = ('id', 'filename', 'size', 'md5', 'sha1', 'sha256', 'raw', 'decoded', 'deobfuscated')

class EmailRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailRecipient
        fields = ('recipient')

class EmailSerializer(serializers.ModelSerializer):
    recipients = EmailRecipientSerializer(many=True, read_only=True)
    samples = SampleSerializer(many=True, read_only=True)

    class Meta:
        model = Email
        fields = ('id', 'date', 'sender', 'messageid', 'subject', 'returnpath', 'useragent', 'recipients', 'samples')
