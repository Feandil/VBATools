"""webui URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = format_suffix_patterns([
    url(r'^api/$', views.api_root),
    url(r'^api/emails/$',
        views.EmailViewSet.as_view({'get': 'list'}),
        name='emails-list'),
    url(r'^api/emails/(?P<pk>[0-9]+)/$',
        views.EmailViewSet.as_view({'get': 'retrieve'}),
        name='emails-detail'),
    url(r'^api/samples/$',
        views.SampleViewSet.as_view({'get': 'list'}),
        name='samples-list'),
    url(r'^api/samples/(?P<pk>[0-9]+)/$',
        views.SampleViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update',}),
        name='samples-detail'),
    url(r'^api/decoded/$',
        views.DecodedViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='decoded-list'),
    url(r'^api/decoded/(?P<pk>[0-9]+)/$',
        views.DecodedViewSet.as_view({'get': 'retrieve'}),
        name='decoded-detail'),
    url(r'^api/deobfuscated/$',
        views.DeobfuscatedViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='deobfuscated-list'),
    url(r'^api/deobfuscated/(?P<pk>[0-9]+)/$',
        views.DeobfuscatedViewSet.as_view({'get': 'retrieve'}),
        name='deobfuscated-detail'),
])

urlpatterns += [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^email/new$', views.EmailUploadView.as_view(), name='EmailUpload'),
    url(r'^sample/new$', views.SampleUploadView.as_view(), name='SampleUpload'),
    url(r'^api/', include('rest_framework.urls', namespace='rest_framework'))
]
