from django.conf import settings
from rest_framework.renderers import JSONRenderer
from kafka import KafkaProducer

from ..serializers import SampleSerializer

#TODO: cache the connection between submissions

def submit_sample(sample):
    payload = JSONRenderer().render(SampleSerializer(sample).data)
    kafka = KafkaProducer(bootstrap_servers=settings.KAFKA_SERVER['SERVERS'],
                          client_id=settings.KAFKA_SERVER['CLIENT_ID']) #Fixme: Handle Failure
    kafka.send(settings.KAFKA_SERVER['TOPIC'], payload).get(20) #Fixme: Handle Failure
    kafka.flush()
    kafka.close()
