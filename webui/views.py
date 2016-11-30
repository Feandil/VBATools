from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic.edit import FormView
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer, TemplateHTMLRenderer

from .form import EmailUploadForm, SampleUploadForm
from .models import Email, Sample, DecodedVBA, DeobfuscatedVBA
from .serializers import EmailSerializer, SampleSerializer, DecodedVBASerializer, DeobfuscatedVBASerializer
from .utils import process_email, process_file

class EmailUploadView(FormView):
    form_class = EmailUploadForm
    template_name = 'email_upload.html'

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        emails = request.FILES.getlist('emails')
        if form.is_valid():
            ids = set()
            for raw_email in emails:
                ids.update(process_email(raw_email.read()))
            return render(request, 'upload_result.html', {'name': 'emails', 'ids': ids, })
        else:
            return self.form_invalid(form)

class SampleUploadView(FormView):
    form_class = SampleUploadForm
    template_name = 'sample_upload.html'

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        samples = request.FILES.getlist('samples')
        if form.is_valid():
            ids = set()
            for sample in samples:
                ids.add(process_file(sample.read(), filename=sample.name))
            return render(request, 'upload_result.html', {'name': 'samples', 'ids': ids, })
        else:
            return self.form_invalid(form)

class ListTemplateHTMLRenderer(TemplateHTMLRenderer):
    def get_template_context(self, data, renderer_context):
        ret = super(ListTemplateHTMLRenderer, self).get_template_context(data, renderer_context)
        if isinstance(ret, list):
            return {'data_list': ret}
        return ret

class EmailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Email.objects.all()
    serializer_class = EmailSerializer
    renderer_classes = [JSONRenderer, ListTemplateHTMLRenderer, BrowsableAPIRenderer]
    template_name = 'email.html'

class SampleViewSet(viewsets.ModelViewSet):
    queryset = Sample.objects.all()
    serializer_class = SampleSerializer
    renderer_classes = [JSONRenderer, ListTemplateHTMLRenderer, BrowsableAPIRenderer]
    template_name = 'sample.html'

class DecodedViewSet(viewsets.ModelViewSet):
    queryset = DecodedVBA.objects.all()
    serializer_class = DecodedVBASerializer
    renderer_classes = [JSONRenderer, ListTemplateHTMLRenderer, BrowsableAPIRenderer]
    template_name = 'decoded.html'

class DeobfuscatedViewSet(viewsets.ModelViewSet):
    queryset = DeobfuscatedVBA.objects.all()
    serializer_class = DeobfuscatedVBASerializer
    renderer_classes = [JSONRenderer, ListTemplateHTMLRenderer, BrowsableAPIRenderer]
    template_name = 'decoded.html'

@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'emails': reverse('emails-list', request=request, format=format),
        'samples': reverse('samples-list', request=request, format=format),
        'decoded': reverse('decoded-list', request=request, format=format),
        'deobfuscated': reverse('deobfuscated-list', request=request, format=format),
    })
