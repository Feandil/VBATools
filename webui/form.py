from django import forms

class EmailUploadForm(forms.Form):
    emails = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))

class SampleUploadForm(forms.Form):
    samples = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))
