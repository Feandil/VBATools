# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-28 14:11
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DecodedVBA',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.IntegerField()),
                ('md5', models.CharField(max_length=32)),
                ('sha1', models.CharField(max_length=40)),
                ('sha256', models.CharField(max_length=64)),
                ('content', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='DeobfuscatedVBA',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.IntegerField()),
                ('md5', models.CharField(max_length=32)),
                ('sha1', models.CharField(max_length=40)),
                ('sha256', models.CharField(max_length=64)),
                ('content', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Email',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(verbose_name=b'date sent')),
                ('sender', models.EmailField(blank=True, max_length=254)),
                ('messageid', models.CharField(max_length=100)),
                ('subject', models.CharField(max_length=100)),
                ('returnpath', models.EmailField(blank=True, max_length=254)),
                ('useragent', models.CharField(blank=True, max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='EmailRecipient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient', models.EmailField(max_length=254)),
                ('email', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipients', to='webui.Email')),
            ],
        ),
        migrations.CreateModel(
            name='RawVBA',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.IntegerField()),
                ('content', models.TextField()),
            ],
            options={
                'ordering': ['position'],
            },
        ),
        migrations.CreateModel(
            name='Sample',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=100)),
                ('size', models.IntegerField()),
                ('md5', models.CharField(max_length=32)),
                ('sha1', models.CharField(max_length=40)),
                ('sha256', models.CharField(max_length=64)),
                ('decoded', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='samples', to='webui.DecodedVBA')),
                ('deobfuscated', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='samples', to='webui.DeobfuscatedVBA')),
                ('email', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='samples', to='webui.Email')),
            ],
        ),
        migrations.AddField(
            model_name='rawvba',
            name='sample',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='raw', to='webui.Sample'),
        ),
        migrations.AlterUniqueTogether(
            name='deobfuscatedvba',
            unique_together=set([('size', 'md5', 'sha1', 'sha256')]),
        ),
        migrations.AlterUniqueTogether(
            name='decodedvba',
            unique_together=set([('size', 'md5', 'sha1', 'sha256')]),
        ),
    ]