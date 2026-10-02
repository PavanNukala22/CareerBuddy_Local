from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from jobs_app.models import EmployerProfile
from users.forms import validate_international_mobile
import re

PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
GST_REGEX = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$')

class EmployerRegisterForm(UserCreationForm):
    # ── User Fields ──────────────────────────────────────────────────────────
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Account Email Address'})
    )
    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HR First Name'})
    )
    last_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HR Last Name'})
    )

    # ── Company Profile Fields ────────────────────────────────────────────────
    company_name = forms.CharField(
        max_length=200, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registered Company Name'})
    )
    company_logo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )
    company_gst = forms.CharField(
        max_length=15, min_length=15, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. 27ABCDE1234F1Z5',
            'maxlength': '15', 'pattern': '[0-9]{2}[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}[A-Za-z0-9]{1}Z[A-Za-z0-9]{1}',
            'title': 'GSTIN must be in format 99AAAAA9999A1Z9',
            'style': 'text-transform:uppercase'
        })
    )
    company_pan_tin = forms.CharField(
        max_length=10, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. ABCDE1234F (optional)',
            'maxlength': '10', 'minlength': '10',
            'pattern': '[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}',
            'title': 'PAN must be in format AAAAA9999A (5 letters, 4 digits, 1 letter).',
            'style': 'text-transform:uppercase'
        })
    )
    company_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Company Headquarters Address', 'rows': 2})
    )
    industry = forms.ChoiceField(
        choices=[('', 'Select Industry')] + [
            ('it_software', 'IT / Software'),
            ('manufacturing', 'Manufacturing'),
            ('healthcare', 'Healthcare'),
            ('finance', 'Finance / Banking'),
            ('education', 'Education'),
            ('consulting', 'Consulting'),
            ('retail', 'Retail / FMCG'),
            ('other', 'Other')
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # ── HR Contact Fields ────────────────────────────────────────────────────
    # Rendered by templates/includes/phone_input.html as a country-code picker
    # + local-number input; static/js/phone-input.js keeps this hidden field's
    # value in sync as "+<dial code><digits>" for clean_hr_contact below to
    # validate against the selected country.
    hr_contact = forms.CharField(
        max_length=20, required=True,
        widget=forms.HiddenInput()
    )
    hr_mail = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'HR Email Address'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'username' in self.fields:
            self.fields['username'].widget.attrs.pop('autofocus', None)

        # Password fields - make them match Username styling.
        # maxlength caps typing AND pasting at 8; MaximumLengthValidator in
        # users/password_validators.py is the server-side backstop.
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password',
            'maxlength': '8',
        })

        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password',
            'maxlength': '8',
        })


    def clean_company_gst(self):
        gst = self.cleaned_data.get('company_gst', '').strip().upper()
        if gst:
            if len(gst) != 15:
                raise forms.ValidationError('GSTIN must be exactly 15 characters long.')
            if not GST_REGEX.match(gst):
                raise forms.ValidationError('Invalid GSTIN format. Must be 99AAAAA9999A1Z9.')
        return gst

    def clean_company_pan_tin(self):
        pan = self.cleaned_data.get('company_pan_tin', '').strip().upper()
        if pan:
            if len(pan) != 10:
                raise forms.ValidationError('PAN must be exactly 10 characters long.')
            if not PAN_REGEX.match(pan):
                raise forms.ValidationError(
                    'Invalid PAN format. Must be AAAAA9999A '
                    '(5 uppercase letters, 4 digits, 1 uppercase letter).'
                )
        return pan

    def clean_hr_contact(self):
        return validate_international_mobile(
            self.cleaned_data.get('hr_contact', ''), 'HR contact number')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            profile, created = EmployerProfile.objects.get_or_create(user=user)
            profile.company_name = self.cleaned_data['company_name']
            if self.cleaned_data.get('company_logo'):
                profile.company_logo = self.cleaned_data['company_logo']
            profile.company_gst = self.cleaned_data['company_gst']
            profile.company_pan_tin = self.cleaned_data['company_pan_tin']
            profile.company_address = self.cleaned_data['company_address']
            profile.hr_contact = self.cleaned_data['hr_contact']
            profile.hr_mail = self.cleaned_data['hr_mail']
            profile.industry = self.cleaned_data['industry']
            profile.save()
        return user
