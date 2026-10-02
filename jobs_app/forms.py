from django import forms
from django.core.validators import validate_email
from .models import EmployerProfile, JobPosting, JobApplication
from users.forms import validate_international_mobile
import json
import re

PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
GST_REGEX = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$')

class EmployerProfileForm(forms.ModelForm):
    company_gst = forms.CharField(
        max_length=15, min_length=15, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. 27ABCDE1234F1Z5',
            'maxlength': '15', 'pattern': '[0-9]{2}[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}[A-Za-z0-9]{1}Z[A-Za-z0-9]{1}',
            'title': 'GSTIN must be in format 99AAAAA9999A1Z9',
            'style': 'text-transform:uppercase'
        })
    )
    company_pan_tin = forms.CharField(
        max_length=10, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. ABCDE1234F',
            'maxlength': '10', 'minlength': '10',
            'pattern': '[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}',
            'title': 'PAN must be in format AAAAA9999A (5 letters, 4 digits, 1 letter).',
            'style': 'text-transform:uppercase'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # PAN (unlike GST, which isn't in scope here): mirror
        # users.forms.ProfileUpdateForm's mask-and-reveal treatment — never
        # pre-fill the real saved value into the rendered input (the edit
        # template shows a masked "XXXXXX1234" instead, via
        # templates/includes/mask_reveal_field.html), and relax `required`
        # only when there's an existing value a blank submission can fall
        # back to (see clean_company_pan_tin below). Skipped entirely when
        # there's no instance/value yet (profile creation), where the field
        # stays required and normally rendered.
        if getattr(self.instance, 'company_pan_tin', ''):
            self.initial['company_pan_tin'] = ''
            self.fields['company_pan_tin'].required = False

    def clean_company_gst(self):
        gst = self.cleaned_data.get('company_gst', '').strip().upper()
        if gst:
            if len(gst) != 15:
                raise forms.ValidationError('GSTIN must be exactly 15 characters long.')
            if not GST_REGEX.match(gst):
                raise forms.ValidationError('Invalid GSTIN format. Must be 99AAAAA9999A1Z9.')
        return gst

    def clean_hr_contact(self):
        # Mirrors EmployerRegisterForm.clean_hr_contact in accounts_app/forms.py
        # so the field is validated identically whether it is set at signup or
        # edited later from the employer profile page.
        return validate_international_mobile(
            self.cleaned_data.get('hr_contact', ''), 'HR contact number')

    def clean_company_pan_tin(self):
        pan = self.cleaned_data.get('company_pan_tin', '').strip().upper()
        if not pan:
            # Masked field left untouched — keep whatever is already saved.
            return getattr(self.instance, 'company_pan_tin', '') or ''
        if pan:
            if len(pan) != 10:
                raise forms.ValidationError('PAN must be exactly 10 characters long.')
            if not PAN_REGEX.match(pan):
                raise forms.ValidationError(
                    'Invalid PAN format. Must be AAAAA9999A '
                    '(5 uppercase letters, 4 digits, 1 uppercase letter).'
                )
        return pan

    class Meta:
        model = EmployerProfile
        exclude = ['user']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name', 'autofocus': 'autofocus'}),
            'company_website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'}),
            'company_logo': forms.FileInput(attrs={'class': 'form-control'}),
            'industry': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Information Technology'}),
            'company_size': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, State'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'company_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Company Headquarters Address'}),
            # Rendered by templates/includes/phone_input.html as a country-code
            # picker + local-number input; static/js/phone-input.js keeps this
            # hidden field's value in sync as "+<dial code><digits>" for
            # clean_hr_contact above to validate against the selected country.
            'hr_contact': forms.HiddenInput(),
            'hr_mail': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'HR Email Address'}),
        }

# Field-level input rules for the job form's free-text fields, shared with
# the page script (JobPostingForm.text_rules_js) so both sides agree.
# `chars` is a regex character class (valid in Python and JavaScript) of the
# characters the field may contain; a value must also contain at least
# `min_letters` letters, so numeric-only or symbol-only input is refused.
# `no_long_digits` refuses standalone runs of 3+ digits (e.g. "Manager12345")
# in fields that name something rather than list items.
TEXT_FIELD_RULES = {
    'title': dict(label='Job Title', chars=r"A-Za-z0-9 .,&/()'\-+#", min_letters=2, no_long_digits=True,
                  message='Job Title should contain a valid job title and should not contain only numbers or special characters.'),
    'department_function': dict(label='Department / Function', chars=r"A-Za-z0-9 .,&/()'\-", min_letters=2, no_long_digits=True,
                                message='Department / Function should contain a valid name and should not contain only numbers or special characters.'),
    'industry_sector': dict(label='Industry / Sector', chars=r"A-Za-z0-9 .,&/()'\-", min_letters=2, no_long_digits=True,
                            message='Industry / Sector should contain a valid industry name and should not contain only numbers or special characters.'),
    'industry_experience': dict(label='Industry Experience', chars=r"A-Za-z0-9 .,&/()'\-+", min_letters=2, no_long_digits=False,
                                message='Industry Experience should describe the relevant experience and should not contain only numbers or special characters.'),
    'certifications': dict(label='Required Certifications', chars=r"A-Za-z0-9 .,&/()'\-+", min_letters=2, no_long_digits=False,
                           message='Required Certifications should contain valid certification names and should not contain only numbers or special characters.'),
    'functional_skills': dict(label='Functional Skills', chars=r"A-Za-z0-9 .,&/()'\-+#", min_letters=2, no_long_digits=False,
                              message='Functional Skills should contain valid skill names and should not contain only numbers or special characters.'),
    'software_skills': dict(label='Software / MS Office Skills', chars=r"A-Za-z0-9 .,&/()'\-+#", min_letters=2, no_long_digits=False,
                            message='Software / MS Office Skills should contain valid software names and should not contain only numbers or special characters.'),
    'language_requirements': dict(label='Language Requirements', chars=r"A-Za-z .,&/()'\-", min_letters=2, no_long_digits=False,
                                  message='Language Requirements should contain language names only.'),
    'keywords': dict(label='Key Skills / Keywords', chars=r"A-Za-z0-9 .,&/()'\-+#", min_letters=2, no_long_digits=False,
                     message='Key Skills / Keywords should contain valid keywords and should not contain only numbers or special characters.'),
    'location': dict(label='Job Location', chars=r"A-Za-z0-9 .,&/()'\-", min_letters=2, no_long_digits=False,
                     message='Location should contain a valid place name (e.g. Hyderabad, Telangana) and should not contain only numbers or special characters.'),
}
AGE_LIMIT_RE = re.compile(r'^(\d{1,2})(?:\s*-\s*(\d{1,2}))?\+?$')
AGE_LIMIT_MESSAGE = 'Please enter a valid numeric age limit, e.g. 25 or 25-35.'
PHONE_PART_RE = re.compile(r'^\+?[\d\s().\-]{7,20}$')
CONTACT_NAME_RE = re.compile(r"^[A-Za-z .'\-]+$")
CONTACT_MESSAGE = 'Application Contact should be a valid email address, phone number or contact name.'


def text_field_error(value, rule):
    """Return the validation message for a free-text field value, or ''."""
    text = re.sub(r'\s+', ' ', value or '').strip()
    if not text:
        return ''
    if not re.match('^[' + rule['chars'] + ']+$', text):
        return rule['message']
    if len(re.findall(r'[A-Za-z]', text)) < rule['min_letters']:
        return rule['message']
    if rule['no_long_digits'] and re.search(r'\d{3,}', text):
        return rule['message']
    return ''


def contact_part_error(part):
    part = part.strip()
    if not part:
        return ''
    if '@' in part:
        try:
            validate_email(part)
            return ''
        except forms.ValidationError:
            return CONTACT_MESSAGE
    digits = re.sub(r'\D', '', part)
    if digits and PHONE_PART_RE.match(part):
        return '' if 7 <= len(digits) <= 15 else CONTACT_MESSAGE
    if CONTACT_NAME_RE.match(part) and len(re.findall(r'[A-Za-z]', part)) >= 2:
        return ''
    return CONTACT_MESSAGE


# IT postings: skills the employer types in (beyond the preset pills).
CUSTOM_SKILL_MAX_LENGTH = 40
CUSTOM_SKILL_RE = re.compile(r"^[A-Za-z0-9 .&/()'+#\-]+$")


def custom_skill_error(skill):
    """Why a typed IT skill is not acceptable, or '' when it is fine.

    Commas are refused because skills_required stores the list comma-separated.
    """
    if len(skill) > CUSTOM_SKILL_MAX_LENGTH:
        return f'"{skill[:20]}..." is too long; keep each skill under {CUSTOM_SKILL_MAX_LENGTH} characters.'
    if not CUSTOM_SKILL_RE.match(skill) or len(re.findall(r'[A-Za-z]', skill)) < 1:
        return (f'"{skill}" is not a valid skill name. Use letters, numbers and . & / ( ) \' + # - only, '
                'one skill at a time.')
    return ''


class JobPostingForm(forms.ModelForm):
    # Additional perks: rendered as selectable pills; stored on the model as
    # a comma-separated list of keys.
    perks = forms.MultipleChoiceField(
        choices=JobPosting.PERK_CHOICES, required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    # Skills: pills for the chosen Department (JobPosting.DEPARTMENT_SKILLS);
    # the field accepts any documented skill and clean() checks the chosen
    # ones belong to the posting's department. The employer stars 3-4 of the
    # selected skills as mandatory; those arrive in the hidden
    # mandatory_skills input.
    skills = forms.MultipleChoiceField(
        choices=[(s, s) for s in JobPosting.all_skill_options()], required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    mandatory_skills = forms.CharField(required=False, widget=forms.HiddenInput)

    # Override radio fields explicitly to remove blank empty option
    work_environment = forms.ChoiceField(
        choices=JobPosting.WORK_ENV_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'radio-group-input'}),
        required=True,
    )
    # NON-IT dropdowns (sheets: Work Mode, Employment Type, and the
    # Non-Technical Joining Requirement). clean() copies them into
    # work_environment / job_type / notice_period for the NON-IT sheets;
    # they are ignored for IT postings. Work Mode offers a different option
    # list per sheet (WORK_MODE_OPTIONS); the field accepts the union.
    WORK_MODE_OPTIONS = {
        'technical': JobPosting.TECH_WORK_MODE_CHOICES,
        'non_technical': JobPosting.NONTECH_WORK_MODE_CHOICES,
    }
    work_mode = forms.ChoiceField(
        choices=[('', 'Select work mode')] + JobPosting.TECH_WORK_MODE_CHOICES
                + [c for c in JobPosting.NONTECH_WORK_MODE_CHOICES if c[0] not in dict(JobPosting.TECH_WORK_MODE_CHOICES)],
        required=False, widget=forms.Select(attrs={'class': 'form-select'}),
    )
    employment_type = forms.ChoiceField(
        choices=[('', 'Select employment type')] + JobPosting.TECH_EMPLOYMENT_TYPE_CHOICES,
        required=False, widget=forms.Select(attrs={'class': 'form-select'}),
    )
    joining_requirement = forms.ChoiceField(
        choices=[('', 'Select joining requirement')] + JobPosting.NONTECH_JOINING_CHOICES,
        required=False, widget=forms.Select(attrs={'class': 'form-select'}),
    )

    @property
    def work_mode_options(self):
        """Rows for the Work Mode select: (value, label, sheets, order per sheet).

        The template tags each option with the sheet(s) it belongs to and its
        position on each sheet, so the page shows one sheet's list in that
        sheet's order."""
        rows = []
        for value, label in self.fields['work_mode'].choices:
            if not value:
                continue
            modes, orders = [], []
            for sheet, opts in self.WORK_MODE_OPTIONS.items():
                keys = [k for k, _ in opts]
                if value in keys:
                    modes.append(sheet)
                    orders.append(f'{sheet}:{keys.index(value)}')
            rows.append((value, label, ' '.join(modes), ' '.join(orders)))
        return rows
    TECH_EDUCATION_KEYS = JobPosting.TECH_EDUCATION_KEYS
    TECH_ONLY_EDUCATION_KEYS = JobPosting.TECH_ONLY_EDUCATION_KEYS

    @property
    def tech_education_choices(self):
        """Qualification presets of the NON-IT Technical sheet, in sheet order."""
        labels = dict(JobPosting.EDUCATION_CHOICES)
        return [(k, labels[k]) for k in JobPosting.TECH_EDUCATION_KEYS]
    interview_mode = forms.ChoiceField(
        choices=JobPosting.INTERVIEW_MODE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'radio-group-input'}),
        required=True,
    )
    notice_period = forms.ChoiceField(
        choices=JobPosting.NOTICE_PERIOD_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'radio-group-input'}),
        required=True,
    )
    gender_preference = forms.ChoiceField(
        choices=JobPosting.GENDER_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'radio-group-input'}),
        required=True,
    )

    # Fields from the "NON-IT Job Posting - Field Format" sheets that exist
    # only for NON-IT postings, keyed by Job Classification: (field, sheet
    # label). Required ones must be filled for that classification; every
    # sheet field is blanked for any posting the sheet does not apply to.
    NON_IT_FIELDS = {
        'technical': {
            'required': [
                ('industry_sector', 'Industry / Sector'),
                ('industry_experience', 'Industry Experience'),
                ('responsibilities', 'Job Responsibilities'),
                ('working_hours', 'Working Hours / Shift'),
                ('keywords', 'Key Skills / Keywords'),
                ('application_contact', 'Application Contact'),
            ],
            'optional': [
                ('certifications', 'Required Certifications'),
                ('age_limit', 'Age Limit'),
            ],
        },
        'non_technical': {
            'required': [
                ('department_function', 'Department / Function'),
                ('functional_skills', 'Functional Skills'),
                ('industry_sector', 'Industry / Sector'),
                ('responsibilities', 'Job Responsibilities'),
                ('working_hours', 'Working Hours / Shift'),
                ('keywords', 'Key Skills / Keywords'),
                ('application_contact', 'Application Contact'),
            ],
            'optional': [
                ('industry_experience', 'Industry Experience'),
                ('certifications', 'Required Certifications'),
                ('software_skills', 'Software / MS Office Skills'),
                ('language_requirements', 'Language Requirements'),
                ('age_limit', 'Age Limit'),
            ],
        },
    }
    NON_IT_ALL_FIELDS = [
        'department_function', 'functional_skills', 'industry_sector', 'industry_experience', 'responsibilities', 'certifications',
        'software_skills', 'language_requirements', 'working_hours', 'age_limit',
        'keywords', 'application_contact',
    ]

    class Meta:
        model = JobPosting
        # is_seeded is an internal/system flag (BR-27: seeded postings are
        # excluded from public counts and the public board) — it was not
        # excluded here, and job_form.html renders no control for it, so
        # Django's ModelForm silently treated the absent checkbox data as
        # False on every save, un-seeding any seeded posting the instant an
        # employer edited it (FR-EMP-10 lets any employer take over a seeded
        # posting's *ownership*, not silently flip its seeded status).
        # skills_required is set from the `skills` pills in clean().
        exclude = ['employer', 'created_at', 'updated_at', 'is_seeded', 'skills_required']
        widgets = {
            'job_category': forms.Select(attrs={'class': 'form-select'}),
            # Shown only when job_category == 'non_it'.
            'job_classification': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            # Grouped Technical / Non-Technical; for Non-IT postings the
            # options follow the chosen Job Classification.
            'designation': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Python Developer'}),
            # NON-IT only (see NON_IT_FIELDS).
            'industry_sector': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Oil & Gas, Construction, Manufacturing'}),
            'industry_experience': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Relevant industry / project experience'}),
            'responsibilities': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Key duties and responsibilities'}),
            'certifications': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. NDT, AWS, CSWIP, safety certifications'}),
            'working_hours': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Shift timing / working hours'}),
            'age_limit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Only if genuinely required'}),
            'keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Searchable recruitment keywords'}),
            'application_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email / phone / application method'}),
            'department_function': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HR, Admin, Sales, Accounts'}),
            'functional_skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Communication, coordination, sales, admin'}),
            'software_skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Excel, ERP, CRM'}),
            'language_requirements': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. English / Hindi / regional language'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'job_type': forms.Select(attrs={'class': 'form-select'}),
            # Shown only when job_type == 'contract'; whole months, 2 digits, max 12.
            'contract_duration_months': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 6',
                'inputmode': 'numeric', 'maxlength': '2', 'autocomplete': 'off',
            }),
            'experience': forms.Select(attrs={'class': 'form-select'}),
            # Shown only when experience == 'custom'; whole years, 2 digits max.
            'experience_years': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 4',
                'inputmode': 'numeric', 'maxlength': '2', 'autocomplete': 'off',
            }),
            # Set by the Experience combo when the typed value ends with "+".
            'experience_plus': forms.HiddenInput,
            # Set by the Experience combo when a range ("2-5") is typed.
            'experience_years_max': forms.HiddenInput,
            'salary_format': forms.Select(attrs={'class': 'form-select'}),
            # Text inputs (numeric keypad on mobile) rather than type=number:
            # a text input honours maxlength natively and lets the script
            # read the caret position, which Chrome refuses on number inputs.
            # placeholder / maxlength are set per salary_format by the job
            # form's script (see templates/employer/job_form.html).
            'salary_min': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 30000',
                'inputmode': 'numeric', 'maxlength': '6', 'autocomplete': 'off',
            }),
            'salary_max': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 50000',
                'inputmode': 'numeric', 'maxlength': '6', 'autocomplete': 'off',
            }),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City or Remote'}),
            'is_remote': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'openings': forms.NumberInput(attrs={'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'interview_mode_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specify interview mode...'}),
            'notice_period_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specify notice period...'}),
            'education': forms.Select(attrs={'class': 'form-select'}),
            # Shown only when education == 'custom'.
            'education_other': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Diploma in Mechanical Engineering',
                'maxlength': '100', 'autocomplete': 'off',
            }),
        }

    # Salary is entered and stored in the unit chosen in salary_format:
    # monthly rupees, or LPA. Each unit has its own required / floor /
    # ceiling rules and messages; the format is read from the submitted
    # data so field-level clean_* (which runs before clean()) can apply the
    # right unit. The job form's <form> carries novalidate (see
    # templates/employer/job_form.html), so the min/max widget attrs are a
    # client-side hint only — this is what actually enforces them. The
    # monthly floor keeps monthly entries clear of the legacy "< 100 means
    # LPA" band, and the 6-digit monthly ceiling clear of the ">= 1000000
    # means annual rupees" band, that JobPosting._to_monthly still
    # recognises for older rows. Both salary fields are required on the form; the model
    # columns stay nullable for existing rows.
    # Monthly values are whole rupees of up to 6 digits; LPA values are
    # whole lakhs of up to 2 digits.
    SALARY_RULES = {
        'monthly': {
            'label': 'Salary', 'min': 1000, 'max': 999999, 'integer': True, 'max_digits': 6,
            'fmt': lambda v: f'₹{JobPosting._fmt_monthly(v)} per month',
            'ceiling_message': 'Salary must not exceed ₹9,99,999 per month (6 digits).',
        },
        'lpa': {
            'label': 'LPA', 'min': 1, 'max': 99, 'integer': True, 'max_digits': 2,
            'fmt': lambda v: f'{v} LPA',
            'ceiling_message': 'LPA must not exceed 99 LPA (2 digits).',
        },
    }

    EXPERIENCE_YEARS_MAX = 99
    MANDATORY_SKILLS_MIN = JobPosting.MANDATORY_SKILLS_MIN
    MANDATORY_SKILLS_MAX = JobPosting.MANDATORY_SKILLS_MAX

    # Typed education text (education == 'custom'). The same rules and
    # messages are applied in the job form's script:
    #   - at most EDUCATION_MAX_LEN characters after trimming
    #   - letters, digits, spaces and . / - , ( ) & + ' only
    #   - at least one letter (never digits or symbols alone)
    #   - numbers only as part of a qualification word (10th, 12th, 1st):
    #     every digit run must be 1-2 digits immediately followed by
    #     letters, and no more than 4 digits in total; a standalone number
    #     (Class 10, B.Tech 2020, 202020) is rejected
    #   - leading/trailing spaces trimmed, repeated spaces collapsed
    EDUCATION_MAX_LEN = 60
    EDUCATION_ALLOWED_RE = re.compile(r"^[A-Za-z0-9 ./,()&+'\-]+$")
    EDUCATION_MESSAGES = {
        'too_long': f'Education must be {EDUCATION_MAX_LEN} characters or fewer.',
        'chars': "Education can contain only letters, numbers, spaces and . / - , ( ) & + '",
        'no_letters': 'Education must include letters, for example 10th, B.Tech or Diploma.',
        'digits': 'Numbers are allowed only as part of a qualification, such as 10th or 12th.',
    }

    @classmethod
    def normalise_education_text(cls, text):
        return re.sub(r'\s+', ' ', (text or '')).strip()

    @classmethod
    def education_text_error(cls, text):
        """Return the validation message for typed education text, or None."""
        if len(text) > cls.EDUCATION_MAX_LEN:
            return cls.EDUCATION_MESSAGES['too_long']
        if not cls.EDUCATION_ALLOWED_RE.match(text):
            return cls.EDUCATION_MESSAGES['chars']
        if not re.search(r'[A-Za-z]', text):
            return cls.EDUCATION_MESSAGES['no_letters']
        # A digit run not directly followed by a letter is a standalone number.
        if (re.search(r'\d{3,}', text) or re.search(r'\d+(?![A-Za-z\d])', text)
                or len(re.findall(r'\d', text)) > 4):
            return cls.EDUCATION_MESSAGES['digits']
        return None
    CONTRACT_DURATION_MAX = 12  # months

    def clean_contract_duration_months(self):
        value = self.cleaned_data.get('contract_duration_months')
        if value is not None and value > self.CONTRACT_DURATION_MAX:
            raise forms.ValidationError(
                f'Project duration cannot exceed {self.CONTRACT_DURATION_MAX} months.'
            )
        return value

    def __init__(self, *args, employer=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Job Category must be chosen on the form (the column stays blank-able
        # so postings created before the field existed still load).
        category = self.fields['job_category']
        category.required = True
        category.choices = [('', 'Select a category')] + list(JobPosting.JOB_CATEGORY_CHOICES)
        category.error_messages['required'] = 'Select a job category.'
        classification = self.fields['job_classification']
        classification.choices = [('', 'Select a classification')] + list(JobPosting.JOB_CLASSIFICATION_CHOICES)
        department = self.fields['department']
        # Required except on the NON-IT Non-Technical sheet, which has its
        # own free-text Department / Function; clean() applies the rule.
        department.required = False
        department.choices = [('', 'Select a department')] + list(JobPosting.DEPARTMENT_CHOICES)
        department.error_messages['required'] = 'Select a department.'
        designation = self.fields['designation']
        designation.required = False
        # Gender Requirement is "If Applicable" on the NON-IT sheets and
        # required for IT; Interview Mode is not on the NON-IT sheets at all
        # (the model default applies there) and required for IT. clean()
        # applies both rules per Job Category / Classification.
        self.fields['gender_preference'].required = False
        self.fields['interview_mode'].required = False
        # Job Type / Work Environment / Notice Period are required for IT;
        # on the NON-IT sheets the Employment Type / Work Mode / Joining
        # Requirement dropdowns feed them instead (see clean()). The IT job
        # type list stays as it was.
        job_type = self.fields['job_type']
        job_type.required = False
        job_type.choices = ([c for c in job_type.choices if c[0] == '']
                            + list(JobPosting.JOB_TYPE_CHOICES))
        self.fields['work_environment'].required = False
        self.fields['notice_period'].required = False
        # Editing a NON-IT posting: pre-select its dropdowns.
        if self.instance and self.instance.pk and not self.is_bound:
            if self.instance.job_category == 'non_it' and self.instance.job_classification in self.WORK_MODE_OPTIONS:
                self.initial['employment_type'] = self.instance.job_type
                self.initial['work_mode'] = self.instance.work_environment
                if self.instance.job_classification == 'non_technical':
                    self.initial['joining_requirement'] = self.instance.notice_period
        designation.choices = [('', 'Select a job role / designation')] + list(JobPosting.DESIGNATION_CHOICES)
        # IT skill pills: the general list, plus every skill the employer has
        # typed in themselves - on this posting (so editing never loses one)
        # and on their earlier IT postings (so a skill added once is offered
        # again next time) - plus any skills typed on this submission.
        known = JobPosting.all_skill_options()
        extras = []

        def add_extra(skill):
            skill = re.sub(r'\s+', ' ', str(skill or '')).strip()
            if skill and skill.lower() not in {s.lower() for s in known + extras}:
                extras.append(skill)

        if self.instance and self.instance.pk:
            for s in self.instance.get_skills_list():
                add_extra(s)
        if employer is not None:
            previous = (JobPosting.objects.filter(employer=employer, job_category='it')
                        .order_by('-created_at').values_list('skills_required', flat=True)[:50])
            for skills_csv in previous:
                for s in (skills_csv or '').split(','):
                    if not custom_skill_error(s.strip()):
                        add_extra(s)
        self.custom_skills_posted = []
        if self.is_bound and self.data.get(self.add_prefix('job_category')) == 'it':
            for s in self.data.getlist(self.add_prefix('skills')) if hasattr(self.data, 'getlist') else []:
                before = len(extras)
                add_extra(s)
                if len(extras) > before:
                    self.custom_skills_posted.append(extras[-1])
        self.it_skill_options = JobPosting.SKILL_OPTIONS + extras
        self.fields['skills'].choices = [(s, s) for s in JobPosting.all_skill_options() + extras]
        if self.instance and self.instance.pk and not self.is_bound:
            self.initial['perks'] = self.instance.get_perks_list()
            self.initial['skills'] = self.instance.get_skills_list()
            self.initial['mandatory_skills'] = ','.join(self.instance.get_mandatory_skills_list())
        self.fields['openings'].error_messages.update({
            'invalid': 'Please enter a valid numeric value.',
            'required': 'Please enter a valid numeric value.',
        })
        years = self.fields['experience_years']
        years.error_messages.update({
            'invalid': 'Enter a whole number of years (0-99).',
            'min_value': 'Experience years cannot be negative.',
        })
        self.fields['experience_years_max'].error_messages.update({
            'invalid': 'Enter the maximum experience as a whole number of years (0-99).',
            'min_value': 'Experience years cannot be negative.',
        })
        duration = self.fields['contract_duration_months']
        duration.error_messages.update({
            'invalid': 'Enter the project duration as a whole number of months.',
            'min_value': 'Project duration cannot be negative.',
        })
        rules = self.SALARY_RULES[self._salary_format()]
        for field_name, bound in (('salary_min', 'Minimum'), ('salary_max', 'Maximum')):
            field = self.fields[field_name]
            field.required = True
            label = f'{bound} {rules["label"]}'
            invalid = f'Enter a valid numeric value for {label}.'
            # A value with too many digits for the column is, by definition,
            # above the ceiling — report it as such rather than as "invalid".
            too_large = (rules['ceiling_message']
                         or f'{label} must not exceed {rules["fmt"](rules["max"])}.')
            field.error_messages.update({
                'required': f'{label} is required.',
                'invalid': invalid,
                'max_digits': too_large,
                'max_decimal_places': invalid,
                'max_whole_digits': too_large,
            })

    @property
    def text_rules_js(self):
        # Field-level text rules for the job form's script (mirror of
        # text_field_error), keyed by field name.
        return json.dumps({name: {'chars': r['chars'], 'minLetters': r['min_letters'],
                                  'noLongDigits': r['no_long_digits'], 'message': r['message']}
                           for name, r in TEXT_FIELD_RULES.items()})

    def _clean_text_field(self, name):
        value = self.cleaned_data.get(name) or ''
        problem = text_field_error(value, TEXT_FIELD_RULES[name])
        if problem:
            raise forms.ValidationError(problem)
        return re.sub(r'\s+', ' ', value).strip()

    def clean_age_limit(self):
        value = (self.cleaned_data.get('age_limit') or '').strip()
        if not value:
            return ''
        m = AGE_LIMIT_RE.match(value)
        if not m:
            raise forms.ValidationError(AGE_LIMIT_MESSAGE)
        low, high = int(m.group(1)), m.group(2)
        if low < 1 or (high is not None and (int(high) < 1 or int(high) < low)):
            raise forms.ValidationError(AGE_LIMIT_MESSAGE)
        return re.sub(r'\s*-\s*', '-', value)

    def clean_application_contact(self):
        value = re.sub(r'\s+', ' ', self.cleaned_data.get('application_contact') or '').strip()
        if not value:
            return ''
        parts = [p for p in re.split(r'[,/|;]', value) if p.strip()]
        if not parts or any(contact_part_error(p) for p in parts):
            raise forms.ValidationError(CONTACT_MESSAGE)
        return value

    @property
    def salary_rules_js(self):
        # min / max limits per format for the job form's script.
        return {k: json.dumps({'min': v['min'], 'max': v['max'],
                               'integer': v['integer'], 'maxDigits': v['max_digits'],
                               'ceilingMessage': v['ceiling_message']})
                for k, v in self.SALARY_RULES.items()}

    def _salary_format(self):
        # Field-level clean_* runs before clean(), so read the raw value;
        # fall back to the model default when it is missing or invalid.
        fmt = self.data.get(self.add_prefix('salary_format')) if self.is_bound else None
        return fmt if fmt in self.SALARY_RULES else 'monthly'

    def clean_salary_min(self):
        return self._clean_salary_range('salary_min', 'Minimum')

    def clean_salary_max(self):
        return self._clean_salary_range('salary_max', 'Maximum')

    def _clean_salary_range(self, field_name, bound):
        value = self.cleaned_data.get(field_name)
        if value is None:
            return value
        rules = self.SALARY_RULES[self._salary_format()]
        label = f'{bound} {rules["label"]}'
        if rules['integer'] and value != value.to_integral_value():
            raise forms.ValidationError(
                f'{label} must be a whole number (no decimals).'
            )
        if value < rules['min']:
            raise forms.ValidationError(
                f'{label} must be at least {rules["fmt"](rules["min"])}.'
            )
        if value > rules['max']:
            raise forms.ValidationError(
                rules['ceiling_message']
                or f'{label} must not exceed {rules["fmt"](rules["max"])}.'
            )
        return value

    # ── helpers for the job form template ───────────────────────────────
    @property
    def designation_groups(self):
        """[(classification key, [(value, label)])] for the role dropdown."""
        return [(key, list(roles)) for key, roles in JobPosting.DESIGNATION_GROUPS.items()]

    def selected_designation(self):
        if self.is_bound:
            return self.data.get(self.add_prefix('designation'), '')
        return self.initial.get('designation') or ''

    def department_skill_groups(self):
        """[(department key, label, [skills])] in dropdown order."""
        return [(key, label, JobPosting.skills_for_department(key))
                for key, label in JobPosting.DEPARTMENT_CHOICES]

    @property
    def selected_skills_list(self):
        if self.is_bound:
            return self.data.getlist(self.add_prefix('skills')) if hasattr(self.data, 'getlist') else []
        return list(self.initial.get('skills') or [])

    @property
    def selected_department(self):
        if self.is_bound:
            return self.data.get(self.add_prefix('department'), '')
        return self.initial.get('department') or ''

    def clean_mandatory_skills(self):
        raw = self.cleaned_data.get('mandatory_skills') or ''
        seen = []
        for s in raw.split(','):
            s = s.strip()
            if s and s not in seen:
                seen.append(s)
        return seen

    def clean_perks(self):
        # Keep only known keys, in the canonical order, as a comma-separated string.
        chosen = set(self.cleaned_data.get('perks') or [])
        return ','.join(key for key, _label in JobPosting.PERK_CHOICES if key in chosen)

    def clean_experience_years_max(self):
        value = self.cleaned_data.get('experience_years_max')
        if value is not None and value > self.EXPERIENCE_YEARS_MAX:
            raise forms.ValidationError(
                f'Experience years must not exceed {self.EXPERIENCE_YEARS_MAX} (2 digits).'
            )
        return value

    def clean_experience_years(self):
        value = self.cleaned_data.get('experience_years')
        if value is not None and value > self.EXPERIENCE_YEARS_MAX:
            raise forms.ValidationError(
                f'Experience years must not exceed {self.EXPERIENCE_YEARS_MAX} (2 digits).'
            )
        return value

    def clean(self):
        cleaned = super().clean()
        s_min = cleaned.get('salary_min')
        s_max = cleaned.get('salary_max')
        if s_min is not None and s_max is not None and s_min > s_max:
            label = self.SALARY_RULES[self._salary_format()]['label']
            self.add_error(
                'salary_min',
                f'Minimum {label} must not be greater than Maximum {label}.',
            )
        # Department / Function + department-wise skills exist for NON-IT ->
        # Technical only. IT keeps its optional general skill pills, and
        # NON-IT -> Non-Technical uses free-text Department / Function and
        # Functional Skills (validated with the sheet fields below).
        category = cleaned.get('job_category')
        classification = cleaned.get('job_classification')
        dept_mode = category == 'non_it' and classification == 'technical'
        nontech = category == 'non_it' and classification == 'non_technical'
        uses_pills = not nontech
        if dept_mode:
            if not cleaned.get('department') and 'department' not in self.errors:
                self.add_error('department', 'Select a department.')
        else:
            cleaned['department'] = ''
        if nontech:
            cleaned['skills'] = []
            cleaned['mandatory_skills'] = ''
        # Skills: every selected skill is kept; 3-4 of them must be starred
        # as mandatory, and a mandatory skill must be among the selected ones.
        selected = cleaned.get('skills') or []
        mandatory = [s for s in (cleaned.get('mandatory_skills') or []) if s in selected]
        lo, hi = JobPosting.MANDATORY_SKILLS_MIN, JobPosting.MANDATORY_SKILLS_MAX
        # NON-IT Technical: skills are required and must belong to the chosen
        # department. IT: optional, from the general list. Either way 3-4 of
        # the selected skills must be mandatory.
        if dept_mode:
            allowed = JobPosting.skills_for_department(cleaned.get('department'))
        else:
            allowed = self.it_skill_options
        if not dept_mode and not nontech and 'skills' not in self.errors:
            problems = [custom_skill_error(s) for s in self.custom_skills_posted if s in selected]
            problems = [p for p in problems if p]
            if problems:
                self.add_error('skills', problems[0])
            elif len(', '.join(selected)) > JobPosting._meta.get_field('skills_required').max_length:
                self.add_error('skills', 'Too many skills selected; remove a few and try again.')
        outside = [s for s in selected if s not in allowed]
        if outside and 'skills' not in self.errors:
            self.add_error('skills', 'Select skills from the chosen department only.'
                           if dept_mode else 'Select skills from the list only.')
        if not uses_pills:
            # Functional Skills double as the posting's skills list so job
            # cards, matching and the AI interview keep working.
            self.instance.skills_required = (cleaned.get('functional_skills') or '').strip()
        elif 'skills' not in self.errors:
            if not selected:
                if dept_mode:
                    self.add_error('skills', 'Select the skills required for this job.')
                else:
                    cleaned['mandatory_skills'] = ''
                    self.instance.skills_required = ''
            elif len(mandatory) < lo or len(mandatory) > hi:
                self.add_error(
                    'skills',
                    f'Mark {lo} to {hi} of the selected skills as mandatory '
                    f'(currently {len(mandatory)}).'
                )
            else:
                ordered = mandatory + [s for s in selected if s not in mandatory]
                cleaned['mandatory_skills'] = ','.join(mandatory)
                self.instance.skills_required = ', '.join(ordered)
        # Job Classification applies to Non-IT postings only: required there,
        # discarded for IT.
        if cleaned.get('job_category') == 'non_it':
            if not cleaned.get('job_classification') and 'job_classification' not in self.errors:
                self.add_error('job_classification', 'Select a job classification.')
        else:
            cleaned['job_classification'] = ''
        # Job Role / Designation applies to Non-IT postings only (discarded
        # for IT). It is optional, but a chosen role must belong to the
        # posting's Job Classification (Technical / Non-Technical).
        designation = cleaned.get('designation')
        if cleaned.get('job_category') != 'non_it':
            cleaned['designation'] = ''
        elif designation and 'designation' not in self.errors:
            classification = cleaned.get('job_classification')
            allowed = JobPosting.designations_for_classification(classification) if classification else []
            if designation not in allowed:
                self.add_error('designation', 'Select a job role that matches the chosen job classification.')
        # The "NON-IT Job Posting - Field Format" sheets apply to NON-IT
        # postings, one sheet per Job Classification; IT postings keep the
        # existing form and rules.
        sheet = None
        if cleaned.get('job_category') == 'non_it':
            sheet = self.NON_IT_FIELDS.get(cleaned.get('job_classification'))
        non_it = sheet is not None
        # Sheet fields: required / if-applicable per the sheet, and every
        # sheet field the posting's sheet does not list is discarded.
        keep = set()
        if sheet:
            for name, label in sheet['required']:
                keep.add(name)
                value = (cleaned.get(name) or '').strip()
                cleaned[name] = value
                if not value and name not in self.errors:
                    self.add_error(name, f'{label} is required.')
            for name, _label in sheet['optional']:
                keep.add(name)
                cleaned[name] = (cleaned.get(name) or '').strip()
        for name in self.NON_IT_ALL_FIELDS:
            if name not in keep:
                cleaned[name] = ''
        # Qualification is mandatory on both NON-IT sheets.
        if non_it and not cleaned.get('education') and 'education' not in self.errors:
            self.add_error('education', 'Qualification is required.')
        # Gender: "If Applicable" on both NON-IT sheets, required for IT.
        if not non_it and not cleaned.get('gender_preference') and 'gender_preference' not in self.errors:
            self.add_error('gender_preference', 'This field is required.')
        # Interview Mode: not on the NON-IT sheets (hidden there, model
        # default used when left unset), required for IT.
        if non_it:
            if not cleaned.get('interview_mode'):
                cleaned['interview_mode'] = JobPosting._meta.get_field('interview_mode').default
                cleaned['interview_mode_other'] = ''
        elif not cleaned.get('interview_mode') and 'interview_mode' not in self.errors:
            self.add_error('interview_mode', 'This field is required.')
        # Work Mode / Employment Type (both NON-IT sheets) and Joining
        # Requirement (Non-Technical) come from dropdowns copied into
        # work_environment / job_type / notice_period. IT postings use the
        # existing Job Type select and the Work Environment / Notice Period
        # pills.
        if non_it:
            copies = [('work_mode', 'work_environment', 'Select a work mode.'),
                      ('employment_type', 'job_type', 'Select an employment type.')]
            if nontech:
                copies.append(('joining_requirement', 'notice_period', 'Select a joining requirement.'))
            for src, dest, message in copies:
                value = cleaned.get(src)
                if not value:
                    if src not in self.errors:
                        self.add_error(src, message)
                else:
                    cleaned[dest] = value
            allowed_modes = dict(self.WORK_MODE_OPTIONS[classification])
            if cleaned.get('work_mode') and cleaned['work_mode'] not in allowed_modes and 'work_mode' not in self.errors:
                self.add_error('work_mode', 'Select a work mode from the list.')
            if nontech:
                cleaned['notice_period_other'] = ''
            else:
                # Technical keeps the Notice Period pills as its mandatory
                # Joining Requirement.
                cleaned['joining_requirement'] = ''
                if not cleaned.get('notice_period') and 'notice_period' not in self.errors:
                    self.add_error('notice_period', 'This field is required.')
        else:
            cleaned['work_mode'] = ''
            cleaned['employment_type'] = ''
            cleaned['joining_requirement'] = ''
            for name in ('job_type', 'work_environment', 'notice_period'):
                if not cleaned.get(name) and name not in self.errors:
                    self.add_error(name, 'This field is required.')
        # Qualification presets on the NON-IT Technical sheet: Degree /
        # Diploma / ITI / Certification, or a manual entry.
        if dept_mode and cleaned.get('education') and cleaned.get('education') != 'custom' \
                and cleaned.get('education') not in JobPosting.TECH_EDUCATION_KEYS \
                and 'education' not in self.errors:
            self.add_error('education', 'Select Degree, Diploma, ITI or Certification, or enter the qualification manually.')
        # IT and NON-IT Non-Technical postings offer the general qualification
        # list; Degree / Certification belong to the Technical sheet only, so
        # a stale value carried over from that sheet is rejected here too.
        if not dept_mode and cleaned.get('education') in JobPosting.TECH_ONLY_EDUCATION_KEYS \
                and 'education' not in self.errors:
            self.add_error('education', 'Select a qualification from the list, or enter it manually.')
        # Contract postings must state a project duration (IT and both
        # NON-IT sheets); for any other type the value is discarded.
        if cleaned.get('job_type') == 'contract':
            duration = cleaned.get('contract_duration_months')
            if 'contract_duration_months' not in self.errors:
                if duration is None:
                    self.add_error('contract_duration_months', 'Enter the project duration in months.')
                elif duration < 1:
                    self.add_error('contract_duration_months', 'Project duration must be at least 1 month.')
        else:
            cleaned['contract_duration_months'] = None
        # Education: the manual text is required with 'custom' and discarded
        # with any preset option, so the two never disagree.
        if cleaned.get('education') == 'custom':
            other = self.normalise_education_text(cleaned.get('education_other'))
            if not other:
                self.add_error('education_other', 'Enter the educational qualification.')
            else:
                problem = self.education_text_error(other)
                if problem:
                    self.add_error('education_other', problem)
                else:
                    cleaned['education_other'] = other
        else:
            cleaned['education_other'] = ''
        # Manual experience entry: the years are required with 'custom' and
        # discarded with any preset option, so the two never disagree.
        if cleaned.get('experience') == 'custom':
            years_min = cleaned.get('experience_years')
            years_max = cleaned.get('experience_years_max')
            if years_min is None and 'experience_years' not in self.errors:
                self.add_error('experience_years', 'Enter the required years of experience.')
            elif years_max is not None:
                # A range: minimum must not exceed maximum, and "+" does not apply.
                if years_min is not None and years_min > years_max:
                    self.add_error('experience_years', 'Minimum experience cannot be greater than maximum experience.')
                cleaned['experience_plus'] = False
        else:
            cleaned['experience_years'] = None
            cleaned['experience_years_max'] = None
            cleaned['experience_plus'] = False
        return cleaned

    def clean_title(self): return self._clean_text_field('title')
    def clean_department_function(self): return self._clean_text_field('department_function')
    def clean_industry_sector(self): return self._clean_text_field('industry_sector')
    def clean_industry_experience(self): return self._clean_text_field('industry_experience')
    def clean_certifications(self): return self._clean_text_field('certifications')
    def clean_functional_skills(self): return self._clean_text_field('functional_skills')
    def clean_software_skills(self): return self._clean_text_field('software_skills')
    def clean_language_requirements(self): return self._clean_text_field('language_requirements')
    def clean_keywords(self): return self._clean_text_field('keywords')
    def clean_location(self): return self._clean_text_field('location')

    def clean_openings(self):
        # openings is a PositiveIntegerField (allows 0 at the DB level), and
        # the widget's min="1" is a client-side hint only (this form's
        # <form> carries novalidate) — without this, a posting advertising
        # zero open positions was silently accepted.
        value = self.cleaned_data.get('openings')
        if value is not None and value < 1:
            raise forms.ValidationError('Openings must be 1 or greater.')
        return value


class JobApplicationForm(forms.ModelForm):
    # Every other optional field on this model has blank=True; years_experience
    # was the one left required=True by ModelForm's default (blank=False),
    # contradicting its own "default=0, not mandatory" intent (FSD §17.4).
    years_experience = forms.IntegerField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'}))

    class Meta:
        model = JobApplication
        fields = ['applicant_name', 'applicant_email', 'applicant_phone', 'resume',
                  'cover_letter', 'applicant_skills', 'years_experience', 'current_company',
                  'current_salary', 'expected_salary']
        widgets = {
            'applicant_name': forms.TextInput(attrs={'class': 'form-control'}),
            'applicant_email': forms.EmailInput(attrs={'class': 'form-control'}),
            # Rendered by templates/includes/phone_input.html as a country-code
            # picker + local-number input; static/js/phone-input.js keeps this
            # hidden field's value in sync as "+<dial code><digits>" for
            # clean_applicant_phone below to validate against the selected
            # country with the `phonenumbers` library.
            'applicant_phone': forms.HiddenInput(),
            'resume': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
            'cover_letter': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'applicant_skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Python, Django, React, SQL'}),
            'current_company': forms.TextInput(attrs={'class': 'form-control'}),
            'current_salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'expected_salary': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_years_experience(self):
        # required=False means a blank submission yields None here, but the
        # model column is NOT NULL (years_experience = PositiveIntegerField(
        # default=0), no null=True) — model defaults only apply when the
        # field is omitted from a .create()/.save() call entirely, not when
        # it's explicitly assigned None, so an unfilled form used to raise
        # IntegrityError at the database on every single submission.
        return self.cleaned_data.get('years_experience') or 0

    def clean_applicant_phone(self):
        return validate_international_mobile(
            self.cleaned_data.get('applicant_phone', ''), 'phone number')

class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['status', 'employer_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'employer_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
