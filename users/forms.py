from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, SetPasswordForm
from django.contrib.auth.models import User
from .models import (
    UserProfile,
    GENDER_CHOICES, EDUCATION_CHOICES,
    BLOOD_GROUP_CHOICES, INDUSTRY_CHOICES,
    LANGUAGE_PROFICIENCY_CHOICES,
)
import datetime
import re
import phonenumbers

PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
PASSPORT_REGEX = re.compile(r'^[A-Z][0-9]{7}$')
AADHAR_REGEX = re.compile(r'^[0-9]{12}$')


def validate_international_mobile(value, field_label='mobile number'):
    """Validate + normalise a phone number entered via the country-code picker.

    The picker (static/js/phone-input.js) always submits the combined value as
    a "+<dial code><digits>" string, so phonenumbers.parse can auto-detect the
    region from the leading "+" without a separate country field. Returns the
    canonical E.164 form (e.g. "+919876543210") so the same number always
    saves identically regardless of how the digits were formatted on entry.
    """
    value = (value or '').strip()
    if not value:
        return value
    try:
        parsed = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException:
        raise forms.ValidationError(
            f'Please select a country and enter a valid {field_label}.'
        )
    if not phonenumbers.is_valid_number(parsed):
        raise forms.ValidationError(
            f'Please enter a valid {field_label} for the selected country.'
        )
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

def get_max_passed_out_year():
    """Latest passing-out year a candidate may select: the year before this one.

    Computed per call rather than at import so a process that stays up across
    New Year does not keep offering (and accepting) a year that has since
    become the current one.
    """
    return datetime.date.today().year - 1


def get_year_choices():
    """Passing-out years, newest first, ending at last year.

    The current year and anything beyond it are excluded outright, so an
    invalid year cannot normally be picked at all; PassedOutYearField.validate
    below is the backstop for a tampered POST or a stale value already saved
    against a profile.
    """
    return [('', 'Select Year')] + [
        (year, str(year)) for year in range(get_max_passed_out_year(), 1989, -1)
    ]


def _validate_uploaded_resume(resume_file):
    if not resume_file:
        return
    import os
    import tempfile
    from career_app.resume_utils import extract_text_from_pdf, extract_text_from_docx, validate_resume_fields

    ext = os.path.splitext(resume_file.name)[1].lower()
    extracted_text = ""
    if ext not in ['.pdf', '.docx']:
        try:
            extracted_text = resume_file.read().decode("utf-8", errors="ignore")
            resume_file.seek(0)
        except Exception:
            pass
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            for chunk in resume_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            if ext == '.pdf':
                extracted_text = extract_text_from_pdf(tmp_path)
            elif ext == '.docx':
                extracted_text = extract_text_from_docx(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    clean_text = (extracted_text or "").strip()
    is_valid, matched_count, matched_fields, missing_fields = validate_resume_fields(clean_text)
    if not is_valid:
        raise forms.ValidationError(
            f"Invalid resume. We could only find {matched_count} out of 10 standard resume sections. "
            f"Please ensure your resume contains at least 3 of: Name & Contact Info, Summary, "
            f"Technical Skills, Work Experience, Projects, Education, Certifications, Achievements, Languages, or Additional Info."
        )


class PassedOutYearField(forms.TypedChoiceField):
    """Year dropdown that rejects the current year and anything later.

    Validation lives here rather than in a per-form clean_* method so all four
    usages (registration + profile, primary + additional education) behave
    identically. Overriding validate() also lets an out-of-range year report
    the actual rule instead of ChoiceField's generic "Select a valid choice.
    2026 is not one of the available choices.", which does not tell the
    candidate what is wrong or what to pick.
    """

    def __init__(self, *args, field_label='Passing out year', **kwargs):
        self.field_label = field_label
        kwargs.setdefault('choices', get_year_choices)
        kwargs.setdefault('coerce', int)
        kwargs.setdefault('required', False)
        super().__init__(*args, **kwargs)

    def validate(self, value):
        if value not in self.empty_values:
            try:
                year = int(value)
            except (TypeError, ValueError):
                pass  # fall through to the standard invalid-choice handling
            else:
                max_year = get_max_passed_out_year()
                if year > max_year:
                    raise forms.ValidationError(
                        f'{self.field_label} must be {max_year} or earlier. '
                        f'{datetime.date.today().year} and future years are not allowed.',
                        code='year_not_in_past',
                    )
        super().validate(value)


def validate_additional_education_years(raw_json):
    """Apply the passing-out year rule to the dynamic additional-education rows.

    Those rows are built client-side and written straight from request data in
    save(), bypassing form fields entirely — so without this a future year
    could still be stored there even though the dropdown-backed fields reject
    one.
    """
    import json
    try:
        entries = json.loads(raw_json or '[]')
    except (json.JSONDecodeError, TypeError):
        return
    if not isinstance(entries, list):
        return
    max_year = get_max_passed_out_year()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        raw_year = entry.get('passed_out_year')
        if raw_year in (None, ''):
            continue
        try:
            year = int(raw_year)
        except (TypeError, ValueError):
            continue
        if year > max_year:
            raise forms.ValidationError(
                f'Additional education passing out year must be {max_year} or '
                f'earlier. {datetime.date.today().year} and future years are '
                f'not allowed.'
            )


class RegisterForm(UserCreationForm):
    # ── Account ──────────────────────────────────────────────────────────────
    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))

    # ── Personal ─────────────────────────────────────────────────────────────
    gender = forms.ChoiceField(
        choices=[('', 'Select Gender')] + GENDER_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    # Rendered by templates/includes/phone_input.html as a country-code
    # picker + local-number input; static/js/phone-input.js keeps this
    # hidden field's value in sync as "+<dial code><digits>" for clean_mobile
    # to validate against the selected country below.
    mobile = forms.CharField(
        max_length=20, required=False,
        widget=forms.HiddenInput())
    alternate_mobile = forms.CharField(
        max_length=20, required=False,
        widget=forms.HiddenInput())
    blood_group = forms.ChoiceField(
        choices=[('', 'Select Blood Group')] + BLOOD_GROUP_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    languages_known = forms.CharField(
        max_length=300, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Hindi, Telugu, Gujarati, English, others...',
        }))
    selfie = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))

    # ── Identity ─────────────────────────────────────────────────────────────
    aadhar_number = forms.CharField(
        max_length=12, min_length=12, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': '12-digit Aadhar Number',
            'maxlength': '12', 'pattern': '[0-9]{12}', 'inputmode': 'numeric',
            'title': 'Aadhar number must be exactly 12 digits.',
        }))
    pan_number = forms.CharField(
        max_length=10, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. ABCDE1234F (optional)',
            'maxlength': '10', 'minlength': '10',
            'pattern': '[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}',
            'title': 'PAN must be in format AAAAA9999A (5 letters, 4 digits, 1 letter).',
            'style': 'text-transform:uppercase',
        }))
    passport_number = forms.CharField(
        max_length=8, min_length=8, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. A1234567',
            'maxlength': '8', 'pattern': '[A-Za-z][0-9]{7}',
            'title': 'Passport number must be exactly 8 characters: 1 letter followed by 7 digits.',
            'style': 'text-transform:uppercase',
        }))

    # ── Education ────────────────────────────────────────────────────────────
    education_level = forms.ChoiceField(
        choices=[('', 'Select Highest Education')] + EDUCATION_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_education_level'}))
    passed_out_year = PassedOutYearField(
        field_label='Passing out year',
        widget=forms.Select(attrs={
            'class': 'form-select', 'id': 'id_passed_out_year'
        }))
    iti_diploma_specialization = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. Electrician, Mechanical, Civil',
        }))
    higher_education_degree = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. B.Tech (CSE), MBA, B.Com, M.Sc Physics',
            'id': 'id_higher_education_degree',
        }))

    # ── Additional Education ──────────────────────────────────────────────────
    education_level_2 = forms.ChoiceField(
        choices=[('', 'Select Additional Education (Optional)')] + EDUCATION_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_education_level_2'}))
    passed_out_year_2 = PassedOutYearField(
        field_label='Additional passing out year',
        widget=forms.Select(attrs={
            'class': 'form-select', 'id': 'id_passed_out_year_2'
        }))
    iti_diploma_specialization_2 = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. Electrician, Mechanical, Civil',
        }))
    higher_education_degree_2 = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. MBA, M.Tech, M.Sc, MCA',
            'id': 'id_higher_education_degree_2',
        }))

    # ── Experience & Skills ───────────────────────────────────────────────────
    has_experience = forms.ChoiceField(
        choices=[('', 'Do you have work experience?'), ('True', 'Yes'), ('False', 'No')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_has_experience'}))
    experience_years = forms.IntegerField(
        required=False, min_value=0, max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'placeholder': 'Years of Experience (e.g. 3)',
            'min': '0', 'max': '50',
        }))
    company_name = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Company Name (e.g. TCS, Infosys)',
        }))
    contact_person_role = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Contact Role (e.g. HR Manager, Team Lead)',
        }))
    # Rendered by templates/includes/phone_input.html as a country-code
    # picker + local-number input; static/js/phone-input.js keeps this
    # hidden field's value in sync as "+<dial code><digits>" for
    # clean_contact_person_mobile below to validate against the selected
    # country.
    contact_person_mobile = forms.CharField(
        max_length=20, required=False,
        widget=forms.HiddenInput())
    contact_person_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'Contact Email ID',
        }))
    industry = forms.ChoiceField(
        choices=[('', 'Select Industry')] + INDUSTRY_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Welding, AutoCAD, Python, MS Office',
        }))
    current_ctc = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'placeholder': 'Current CTC (LPA)',
            'step': '0.1', 'min': '0',
        }))
    expected_ctc = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'placeholder': 'Expected CTC (LPA)',
            'step': '0.1', 'min': '0',
        }))
    certification = forms.CharField(
        max_length=500, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. AWS Certified, NCVT, ISO Lead Auditor',
        }))
    resume = forms.FileField(
        required=True,
        error_messages={'required': 'Please upload your resume to complete registration.'},
        widget=forms.FileInput(attrs={
            'class': 'form-control', 'accept': '.pdf,.doc,.docx',
        }))

    # ── Location ──────────────────────────────────────────────────────────
    current_location = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Current City, State',
        }))
    preferred_location = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Preferred City / State',
        }))

    # ── Abroad Experience ─────────────────────────────────────────────────────
    has_abroad_experience = forms.ChoiceField(
        choices=[('', 'Do you have abroad experience?'), ('True', 'Yes'), ('False', 'No')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_has_abroad'}))
    abroad_years = forms.IntegerField(
        required=False, min_value=0, max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'placeholder': 'Number of years abroad',
            'min': '0', 'max': '50',
        }))
    abroad_country = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Country (e.g. UAE, Qatar, Singapore)',
        }))
    abroad_industry = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Industry while abroad',
        }))
    abroad_skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Skills acquired abroad',
        }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Choose a Username',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # maxlength caps typing AND pasting at 8; MaximumLengthValidator in
        # users/password_validators.py is the server-side backstop.
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Password', 'maxlength': '8',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Confirm Password', 'maxlength': '8',
        })
        if 'username' in self.fields:
            self.fields['username'].widget.attrs.pop('autofocus', None)

    # ── Validators ────────────────────────────────────────────────────────────
    def clean(self):
        cleaned_data = super().clean()
        validate_additional_education_years(
            self.data.get('additional_educations_json', '[]'))
        return cleaned_data

    def clean_aadhar_number(self):
        aadhar = self.cleaned_data.get('aadhar_number', '').strip()
        if aadhar:
            if not AADHAR_REGEX.match(aadhar):
                raise forms.ValidationError('Aadhar number must be exactly 12 digits.')
        return aadhar

    def clean_passport_number(self):
        passport = self.cleaned_data.get('passport_number', '').strip().upper()
        if passport:
            if len(passport) != 8:
                raise forms.ValidationError('Passport number must be exactly 8 characters.')
            if not PASSPORT_REGEX.match(passport):
                raise forms.ValidationError('Passport number must be 1 uppercase letter followed by 7 digits.')
        return passport

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number', '').strip().upper()
        if pan:
            if len(pan) != 10:
                raise forms.ValidationError('PAN must be exactly 10 characters long.')
            if not PAN_REGEX.match(pan):
                raise forms.ValidationError(
                    'Invalid PAN format. Must be AAAAA9999A '
                    '(5 uppercase letters, 4 digits, 1 uppercase letter).'
                )
        return pan

    def clean_mobile(self):
        return validate_international_mobile(self.cleaned_data.get('mobile', ''), 'mobile number')

    def clean_alternate_mobile(self):
        return validate_international_mobile(self.cleaned_data.get('alternate_mobile', ''), 'alternative mobile number')

    def clean_contact_person_mobile(self):
        return validate_international_mobile(
            self.cleaned_data.get('contact_person_mobile', ''), 'contact mobile number')

    def clean_email(self):
        # Enforce ONE account per email (case-insensitive) so employers never
        # see duplicate candidates. A different username with the same email is
        # still rejected.
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists. Please log in instead.')
        return email

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            _validate_uploaded_resume(resume)
        return resume

    # ── Save ──────────────────────────────────────────────────────────────────
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            p = user.profile  # auto-created by post_save signal

            # Personal
            p.gender           = self.cleaned_data.get('gender', '')
            p.mobile           = self.cleaned_data.get('mobile', '')
            p.alternate_mobile = self.cleaned_data.get('alternate_mobile', '')
            p.blood_group      = self.cleaned_data.get('blood_group', '')

            # Dynamic Languages Processing
            names = self.data.getlist('lang_name[]')
            levels = self.data.getlist('lang_level[]')
            pairs = []
            for n, l in zip(names, levels):
                n_str = n.strip()
                l_str = l.strip()
                if n_str:
                    if l_str:
                        pairs.append(f"{n_str} ({l_str})")
                    else:
                        pairs.append(n_str)
            if pairs:
                p.languages_known = ", ".join(pairs)
            else:
                p.languages_known = self.cleaned_data.get('languages_known', '')
            if self.cleaned_data.get('selfie'):
                p.selfie = self.cleaned_data['selfie']

            # Identity
            p.aadhar_number   = self.cleaned_data.get('aadhar_number', '')
            p.pan_number      = self.cleaned_data.get('pan_number', '')
            p.passport_number = self.cleaned_data.get('passport_number', '')

            # Education
            p.education_level            = self.cleaned_data.get('education_level', '')
            p.passed_out_year            = self.cleaned_data.get('passed_out_year') or None
            p.iti_diploma_specialization = self.cleaned_data.get('iti_diploma_specialization', '')
            p.higher_education_degree    = self.cleaned_data.get('higher_education_degree', '')
            # Additional Education
            p.education_level_2            = self.cleaned_data.get('education_level_2', '')
            p.passed_out_year_2            = self.cleaned_data.get('passed_out_year_2') or None
            p.iti_diploma_specialization_2 = self.cleaned_data.get('iti_diploma_specialization_2', '')
            p.higher_education_degree_2    = self.cleaned_data.get('higher_education_degree_2', '')
            import json
            try:
                p.additional_educations_json = json.loads(self.data.get('additional_educations_json', '[]'))
            except json.JSONDecodeError:
                p.additional_educations_json = []

            # Experience & Skills
            has_exp        = self.cleaned_data.get('has_experience', '')
            p.has_experience        = (has_exp == 'True')
            p.experience_years      = self.cleaned_data.get('experience_years') or None
            p.company_name          = self.cleaned_data.get('company_name', '')
            p.contact_person_role   = self.cleaned_data.get('contact_person_role', '')
            p.contact_person_mobile = self.cleaned_data.get('contact_person_mobile', '')
            p.contact_person_email  = self.cleaned_data.get('contact_person_email', '')
            p.industry              = self.cleaned_data.get('industry', '')
            p.skills                = self.cleaned_data.get('skills', '')
            p.current_ctc           = self.cleaned_data.get('current_ctc') or None
            p.expected_ctc          = self.cleaned_data.get('expected_ctc') or None
            p.certification         = self.cleaned_data.get('certification', '')
            if self.cleaned_data.get('resume'):
                p.resume = self.cleaned_data['resume']

            # Location
            p.current_location   = self.cleaned_data.get('current_location', '')
            p.preferred_location = self.cleaned_data.get('preferred_location', '')

            # Abroad
            has_abroad            = self.cleaned_data.get('has_abroad_experience', '')
            p.has_abroad_experience = (has_abroad == 'True')
            p.abroad_years        = self.cleaned_data.get('abroad_years') or None
            p.abroad_country      = self.cleaned_data.get('abroad_country', '')
            p.abroad_industry     = self.cleaned_data.get('abroad_industry', '')
            p.abroad_skills       = self.cleaned_data.get('abroad_skills', '')

            p.save()
            # Extract & store resume text so the candidate is searchable by
            # the actual skills/experience/location in their resume.
            if self.cleaned_data.get('resume'):
                p.update_resume_text()
        return user


# ── Unchanged below this line ─────────────────────────────────────────────────

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Username or Email',
        })
        self.fields['username'].label = 'Username or Email'
        self.fields['password'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Password',
        })

    def clean(self):
        cleaned_data = super().clean()
        user = self.user_cache
        if user is not None and hasattr(user, 'employer_profile'):
            raise forms.ValidationError(
                'Employer accounts cannot log in through the student portal.',
                code='invalid_login',
            )
        return cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}))

    # Profile Fields
    gender = forms.ChoiceField(
        choices=[('', 'Select Gender')] + GENDER_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    # Rendered by templates/includes/phone_input.html as a country-code
    # picker + local-number input; static/js/phone-input.js keeps this
    # hidden field's value in sync as "+<dial code><digits>" for clean_mobile
    # to validate against the selected country below.
    mobile = forms.CharField(
        max_length=20, required=False,
        widget=forms.HiddenInput())
    alternate_mobile = forms.CharField(
        max_length=20, required=False,
        widget=forms.HiddenInput())
    blood_group = forms.ChoiceField(
        choices=[('', 'Select Blood Group')] + BLOOD_GROUP_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    languages_known = forms.CharField(
        max_length=300, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Hindi, Telugu, Gujarati, English, others...',
        }))
    selfie = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))

    # Identity
    aadhar_number = forms.CharField(
        max_length=12, min_length=12, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': '12-digit Aadhar Number',
            'maxlength': '12', 'pattern': '[0-9]{12}', 'inputmode': 'numeric',
            'title': 'Aadhar number must be exactly 12 digits.',
        }))
    pan_number = forms.CharField(
        max_length=10, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. ABCDE1234F (optional)',
            'maxlength': '10', 'minlength': '10',
            'pattern': '[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}',
            'title': 'PAN must be in format AAAAA9999A (5 letters, 4 digits, 1 letter).',
            'style': 'text-transform:uppercase',
        }))
    passport_number = forms.CharField(
        max_length=8, min_length=8, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. A1234567',
            'maxlength': '8', 'pattern': '[A-Za-z][0-9]{7}',
            'title': 'Passport number must be exactly 8 characters: 1 letter followed by 7 digits.',
            'style': 'text-transform:uppercase',
        }))

    # Education
    education_level = forms.ChoiceField(
        choices=[('', 'Select Highest Education')] + EDUCATION_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_education_level'}))
    passed_out_year = PassedOutYearField(
        field_label='Passing out year',
        empty_value=None,
        widget=forms.Select(attrs={
            'class': 'form-select', 'id': 'id_passed_out_year'
        }))
    iti_diploma_specialization = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. Electrician, Mechanical, Civil',
        }))
    higher_education_degree = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. B.Tech (CSE), MBA, B.Com, M.Sc Physics',
            'id': 'id_higher_education_degree',
        }))

    # Additional Education
    education_level_2 = forms.ChoiceField(
        choices=[('', 'Select Additional Education (Optional)')] + EDUCATION_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_education_level_2'}))
    passed_out_year_2 = PassedOutYearField(
        field_label='Additional passing out year',
        empty_value=None,
        widget=forms.Select(attrs={
            'class': 'form-select', 'id': 'id_passed_out_year_2'
        }))
    iti_diploma_specialization_2 = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. Electrician, Mechanical, Civil',
        }))
    higher_education_degree_2 = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. MBA, M.Tech, M.Sc, MCA',
            'id': 'id_higher_education_degree_2',
        }))

    # Experience & Skills
    has_experience = forms.ChoiceField(
        choices=[('', 'Do you have work experience?'), ('True', 'Yes'), ('False', 'No')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_has_experience'}))
    experience_years = forms.IntegerField(
        required=False, min_value=0, max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'placeholder': 'Years of Experience (e.g. 3)',
            'min': '0', 'max': '50',
        }))
    company_name = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Company Name (e.g. TCS, Infosys)',
        }))
    contact_person_role = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Contact Role (e.g. HR Manager, Team Lead)',
        }))
    # Rendered by templates/includes/phone_input.html as a country-code
    # picker + local-number input; static/js/phone-input.js keeps this
    # hidden field's value in sync as "+<dial code><digits>" for
    # clean_contact_person_mobile below to validate against the selected
    # country.
    contact_person_mobile = forms.CharField(
        max_length=20, required=False,
        widget=forms.HiddenInput())
    contact_person_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'Contact Email ID',
        }))
    industry = forms.ChoiceField(
        choices=[('', 'Select Industry')] + INDUSTRY_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Welding, AutoCAD, Python, MS Office',
        }))
    current_ctc = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'placeholder': 'Current CTC (LPA)',
            'step': '0.1', 'min': '0',
        }))
    expected_ctc = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'placeholder': 'Expected CTC (LPA)',
            'step': '0.1', 'min': '0',
        }))
    certification = forms.CharField(
        max_length=500, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. AWS Certified, NCVT, ISO Lead Auditor',
        }))
    resume = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control', 'accept': '.pdf,.doc,.docx',
        }))

    # Location
    current_location = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Current City, State',
        }))
    preferred_location = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Preferred City / State',
        }))

    # Abroad
    has_abroad_experience = forms.ChoiceField(
        choices=[('', 'Do you have abroad experience?'), ('True', 'Yes'), ('False', 'No')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_has_abroad'}))
    abroad_years = forms.IntegerField(
        required=False, min_value=0, max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'placeholder': 'Number of years abroad',
            'min': '0', 'max': '50',
        }))
    abroad_country = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Country (e.g. UAE, Qatar, Singapore)',
        }))
    abroad_industry = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Industry while abroad',
        }))
    abroad_skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Skills acquired abroad',
        }))

    class Meta:
        model = UserProfile
        fields = [
            'english_level', 'bio', 'avatar',
            'gender', 'mobile', 'alternate_mobile', 'blood_group', 'languages_known',
            'english_proficiency', 'hindi_proficiency', 'telugu_proficiency', 'gujarati_proficiency', 'other_languages', 'selfie',
            'aadhar_number', 'pan_number', 'passport_number',
            'education_level', 'passed_out_year', 'iti_diploma_specialization', 'higher_education_degree',
            'education_level_2', 'passed_out_year_2', 'iti_diploma_specialization_2', 'higher_education_degree_2',
            'has_experience', 'experience_years', 'company_name', 'contact_person_role', 'contact_person_mobile', 'contact_person_email',
            'industry', 'skills', 'current_ctc', 'expected_ctc', 'certification', 'resume',
            'current_location', 'preferred_location',
            'has_abroad_experience', 'abroad_years', 'abroad_country', 'abroad_industry', 'abroad_skills'
        ]
        widgets = {
            'english_level': forms.Select(attrs={'class': 'form-select'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize has_experience and has_abroad_experience dropdown values correctly from boolean model fields
        if self.instance:
            self.fields['has_experience'].initial = 'True' if self.instance.has_experience else 'False'
            self.fields['has_abroad_experience'].initial = 'True' if self.instance.has_abroad_experience else 'False'

        # Sensitive ID fields (Aadhaar/PAN/Passport): never pre-fill the real
        # saved value into the rendered input — templates/includes/mask_reveal_field.html
        # shows a server-computed masked value ("XXXX XXXX 1234") instead, and
        # only swaps in this (still-empty) real input if the user clicks
        # "Change". A blank submission therefore means "leave unchanged", not
        # "clear it" — see the matching clean_* methods below, which fall
        # back to the instance's existing value when blank. aadhar_number is
        # otherwise required=True; that's relaxed only when a saved value
        # already exists to fall back to.
        for _id_field in ('aadhar_number', 'pan_number', 'passport_number'):
            self.initial[_id_field] = ''
            if getattr(self.instance, _id_field, ''):
                self.fields[_id_field].required = False

    # ── Validators ────────────────────────────────────────────────────────────
    def clean(self):
        cleaned_data = super().clean()
        validate_additional_education_years(
            self.data.get('additional_educations_json', '[]'))
        return cleaned_data

    def clean_aadhar_number(self):
        aadhar = self.cleaned_data.get('aadhar_number', '').strip()
        if not aadhar:
            # Masked field left untouched (see mask_reveal_field.html and
            # __init__ above) — keep whatever is already saved.
            return getattr(self.instance, 'aadhar_number', '') or ''
        if not AADHAR_REGEX.match(aadhar):
            raise forms.ValidationError('Aadhar number must be exactly 12 digits.')
        return aadhar

    def clean_passport_number(self):
        passport = self.cleaned_data.get('passport_number', '').strip().upper()
        if not passport:
            return getattr(self.instance, 'passport_number', '') or ''
        if len(passport) != 8:
            raise forms.ValidationError('Passport number must be exactly 8 characters.')
        if not PASSPORT_REGEX.match(passport):
            raise forms.ValidationError('Passport number must be 1 uppercase letter followed by 7 digits.')
        return passport

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number', '').strip().upper()
        if not pan:
            return getattr(self.instance, 'pan_number', '') or ''
        if len(pan) != 10:
            raise forms.ValidationError('PAN must be exactly 10 characters long.')
        if not PAN_REGEX.match(pan):
            raise forms.ValidationError(
                'Invalid PAN format. Must be AAAAA9999A '
                '(5 uppercase letters, 4 digits, 1 uppercase letter).'
            )
        return pan

    def clean_mobile(self):
        return validate_international_mobile(self.cleaned_data.get('mobile', ''), 'mobile number')

    def clean_alternate_mobile(self):
        return validate_international_mobile(self.cleaned_data.get('alternate_mobile', ''), 'alternative mobile number')

    def clean_contact_person_mobile(self):
        return validate_international_mobile(
            self.cleaned_data.get('contact_person_mobile', ''), 'contact mobile number')

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            _validate_uploaded_resume(resume)
        return resume

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Convert choice inputs back to boolean values
        has_exp = self.cleaned_data.get('has_experience')
        instance.has_experience = (has_exp == 'True')
        has_abroad = self.cleaned_data.get('has_abroad_experience')
        instance.has_abroad_experience = (has_abroad == 'True')

        # Dynamic Languages Processing
        names = self.data.getlist('lang_name[]')
        levels = self.data.getlist('lang_level[]')
        pairs = []
        for n, l in zip(names, levels):
            n_str = n.strip()
            l_str = l.strip()
            if n_str:
                if l_str:
                    pairs.append(f"{n_str} ({l_str})")
                else:
                    pairs.append(n_str)
        if pairs:
            instance.languages_known = ", ".join(pairs)
        else:
            # Fallback if no dynamic pairs were sent
            instance.languages_known = self.cleaned_data.get('languages_known', '')

        import json
        try:
            instance.additional_educations_json = json.loads(self.data.get('additional_educations_json', '[]'))
        except json.JSONDecodeError:
            instance.additional_educations_json = []

        # When replacing the resume, remember the previous file so we can delete it
        old_resume_name = None
        if self.cleaned_data.get('resume') and instance.pk:
            old_resume_name = (
                UserProfile.objects.filter(pk=instance.pk)
                .values_list('resume', flat=True).first()
            )

        if commit:
            instance.save()
            if self.cleaned_data.get('resume'):
                # Delete the old resume file so each candidate keeps only ONE
                if old_resume_name and old_resume_name != instance.resume.name:
                    try:
                        instance.resume.storage.delete(old_resume_name)
                    except Exception:
                        pass
                instance.update_resume_text()
        return instance


class StyledSetPasswordForm(SetPasswordForm):
    """Django's SetPasswordForm with the project's field styling + 8-char cap.

    Used by the password-reset-confirm view (see users/urls.py) so the "Set a
    new password" page enforces the same maxlength as the two registration
    forms. Without this the reset flow would be the one place a longer password
    could be typed, only to be rejected server-side by MaximumLengthValidator.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'New Password', 'maxlength': '8',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Confirm New Password', 'maxlength': '8',
        })
