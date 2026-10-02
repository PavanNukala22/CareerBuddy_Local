import re

from django.db import models
from django.contrib.auth.models import User

class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=200)
    company_website = models.URLField(blank=True)
    company_logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    industry = models.CharField(max_length=100)
    company_size = models.CharField(max_length=50, choices=[
        ('1-10','1-10'), ('11-50','11-50'), ('51-200','51-200'),
        ('201-500','201-500'), ('500+','500+')
    ], blank=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    company_gst = models.CharField(max_length=15, blank=True)
    company_pan_tin = models.CharField(max_length=15, blank=True)
    company_address = models.TextField(blank=True)
    hr_contact = models.CharField(max_length=20, blank=True, help_text='Stored in E.164 format, e.g. +919876543210')
    hr_mail = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.company_name)


class JobPosting(models.Model):
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'), ('part_time', 'Part Time'),
        ('contract', 'Contract'), ('internship', 'Internship'), ('remote', 'Remote'),
    ]
    # NON-IT -> Technical "Employment Type" (stored in job_type; 'contract'
    # is shared with the IT list so the duration logic is the same).
    TECH_EMPLOYMENT_TYPE_CHOICES = [
        ('permanent', 'Permanent'), ('contract', 'Contract'), ('project', 'Project'),
    ]
    JOB_TYPE_ALL_CHOICES = JOB_TYPE_CHOICES + [('permanent', 'Permanent'), ('project', 'Project')]
    EXPERIENCE_CHOICES = [
        ('fresher', 'Fresher'), ('1-2', '1-2 Years'), ('3-5', '3-5 Years'),
        ('5-8', '5-8 Years'), ('8+', '8+ Years'),
        # Manual entry: the exact number of years lives in experience_years.
        ('custom', 'Enter manually'),
    ]
    STATUS_CHOICES = [('active', 'Active'), ('closed', 'Closed'), ('draft', 'Draft')]

    WORK_ENV_CHOICES = [
        ('wfh', 'Work From Home'), ('hybrid', 'Hybrid'), ('wfo', 'Work From Office'),
    ]
    # NON-IT "Work Mode" dropdowns (stored in work_environment), one list
    # per sheet. 'hybrid' is shared with the IT list.
    TECH_WORK_MODE_CHOICES = [
        ('onsite', 'On-site'), ('field', 'Field'), ('plant', 'Plant'), ('office', 'Office'),
    ]
    NONTECH_WORK_MODE_CHOICES = [
        ('onsite', 'On-site'), ('office', 'Office'), ('field', 'Field'), ('hybrid', 'Hybrid'),
    ]
    WORK_ENV_ALL_CHOICES = WORK_ENV_CHOICES + TECH_WORK_MODE_CHOICES
    INTERVIEW_MODE_CHOICES = [
        ('walk_in', 'Walk In'), ('virtual', 'Virtual'), ('others', 'Others'),
    ]
    NOTICE_PERIOD_CHOICES = [
        ('immediate', 'Immediately'), ('15_days', '15 Days'), ('30_days', '30 Days'), ('others', 'Others'),
    ]
    # NON-IT -> Non-Technical "Joining Requirement" (stored in notice_period).
    NONTECH_JOINING_CHOICES = [
        ('immediate', 'Immediate'), ('notice_ok', 'Notice period acceptable'),
    ]
    NOTICE_PERIOD_ALL_CHOICES = NOTICE_PERIOD_CHOICES + [('notice_ok', 'Notice period acceptable')]
    GENDER_CHOICES = [
        ('male', 'Male'), ('female', 'Female'), ('both', 'Both'),
    ]

    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name='job_postings')
    JOB_CATEGORY_CHOICES = [('it', 'IT'), ('non_it', 'Non-IT')]
    # Required on the job form; blank allowed at the DB level for existing rows.
    job_category = models.CharField(max_length=10, choices=JOB_CATEGORY_CHOICES, blank=True)
    JOB_CLASSIFICATION_CHOICES = [('technical', 'Technical'), ('non_technical', 'Non-Technical')]
    # Required when job_category == 'non_it'; always blank for IT postings.
    job_classification = models.CharField(max_length=15, choices=JOB_CLASSIFICATION_CHOICES, blank=True)
    DEPARTMENT_CHOICES = [
        ('engineering', 'Engineering Skills'),
        ('epc_construction', 'EPC & Construction Skills'),
        ('hse_safety', 'HSE / EHS / Safety Skills'),
        ('fire_emergency', 'Fire & Emergency Skills'),
        ('quality_inspection', 'Quality & Inspection Skills'),
        ('plant_operations', 'Plant Operations & Maintenance'),
        ('skilled_trades', 'Skilled & Technical Trades'),
        ('renewable_energy', 'Renewable Energy Skills'),
        ('industrial_manufacturing', 'Industrial & Manufacturing Skills'),
        ('automotive_ev', 'Automotive & EV Skills'),
        ('oil_gas_energy', 'Oil & Gas / Energy Skills'),
        ('logistics_workforce', 'Logistics & Industrial Workforce Skills'),
    ]
    # Required on the job form; blank allowed at the DB level for existing rows.
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES, blank=True)
    # Job Role / Designation offered on the job form, grouped by Job
    # Classification (Technical / Non-Technical). Keys of
    # DESIGNATION_GROUPS are JOB_CLASSIFICATION_CHOICES keys; a Non-IT
    # posting's designation must belong to its classification's group.
    DESIGNATION_GROUPS = {
        'technical': [
            ('manager', 'Manager'),
            ('project_engineer', 'Project Engineer'),
            ('site_engineer', 'Site Engineer'),
            ('estimation_engineer', 'Estimation Engineer'),
            ('back_office_manager', 'Back Office Manager'),
            ('project_coordinator', 'Project Coordinator'),
            ('project_director', 'Project Director'),
        ],
        'non_technical': [
            ('hr_manager', 'HR Manager'),
            ('hr_executive', 'HR Executive'),
            ('hr_recruiter', 'HR Recruiter'),
            ('back_office_executive', 'Back Office Executive'),
            ('accountant', 'Accountant'),
            ('account_executive', 'Account Executive'),
            ('sales_executive', 'Sales Executive'),
            ('sales_manager', 'Sales Manager'),
            ('sales_officer', 'Sales Officer'),
            ('sales_marketing_executive', 'Sales & Marketing Executive'),
            ('store_executive', 'Store Executive'),
            ('store_supervisor', 'Store Supervisor'),
            ('store_manager', 'Store Manager'),
            ('purchase_executive', 'Purchase Executive'),
            ('purchase_manager', 'Purchase Manager'),
        ],
    }
    DESIGNATION_CHOICES = [
        ('Technical', DESIGNATION_GROUPS['technical']),
        ('Non-Technical', DESIGNATION_GROUPS['non_technical']),
    ]
    designation = models.CharField(max_length=30, choices=DESIGNATION_CHOICES, blank=True)
    # NON-IT postings only (the "NON-IT Job Posting - Field Format" sheets,
    # one per Job Classification). Blank for IT postings. Which ones are
    # required on the form depends on the classification (see the form).
    industry_sector = models.CharField(max_length=100, blank=True)          # Industry / Sector
    industry_experience = models.CharField(max_length=200, blank=True)      # Industry Experience
    responsibilities = models.TextField(blank=True)                          # Job Responsibilities
    certifications = models.CharField(max_length=300, blank=True)           # Required Certifications (if applicable)
    working_hours = models.CharField(max_length=100, blank=True)            # Working Hours / Shift
    age_limit = models.CharField(max_length=50, blank=True)                 # Age Limit (if applicable)
    keywords = models.CharField(max_length=300, blank=True)                 # Key Skills / Keywords
    application_contact = models.CharField(max_length=200, blank=True)      # Application Contact
    # NON-IT -> Non-Technical sheet only. That sheet's Department / Function
    # (e.g. HR, Admin, Sales, Accounts) and Functional Skills are free text;
    # the department dropdown + skill pills are for IT and NON-IT Technical.
    department_function = models.CharField(max_length=100, blank=True)     # Department / Function (mandatory)
    functional_skills = models.CharField(max_length=300, blank=True)       # Functional Skills (mandatory)
    software_skills = models.CharField(max_length=300, blank=True)         # Software / MS Office Skills
    language_requirements = models.CharField(max_length=200, blank=True)   # Language Requirements
    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    skills_required = models.CharField(max_length=500, blank=True, help_text='Comma separated skills')
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_ALL_CHOICES)
    # Project duration in months, required when job_type == 'contract'.
    contract_duration_months = models.PositiveSmallIntegerField(null=True, blank=True)
    experience = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES)
    # Years required when experience == 'custom' (whole years, 0-99).
    experience_years = models.PositiveSmallIntegerField(null=True, blank=True)
    # True when the employer typed the years with a trailing "+" (10+ = ten or more).
    experience_plus = models.BooleanField(default=False)
    # Upper bound of a typed range ("2-5 years"); None for a single value.
    experience_years_max = models.PositiveSmallIntegerField(null=True, blank=True)
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    SALARY_FORMAT_CHOICES = [
        ('monthly', 'Monthly'),
        ('lpa', 'LPA (Lakhs Per Annum)'),
    ]
    # Unit the employer entered salary_min / salary_max in. Decides both the
    # validation applied on the job form and the unit shown everywhere the
    # salary is displayed. Rows that predate the field default to monthly.
    salary_format = models.CharField(max_length=10, choices=SALARY_FORMAT_CHOICES, default='monthly')
    location = models.CharField(max_length=200)
    is_remote = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    openings = models.PositiveIntegerField(default=1)
    deadline = models.DateField(null=True, blank=True)
    work_environment = models.CharField(max_length=10, choices=WORK_ENV_ALL_CHOICES, blank=True, default='wfo')
    interview_mode = models.CharField(max_length=10, choices=INTERVIEW_MODE_CHOICES, blank=True, default='virtual')
    interview_mode_other = models.CharField(max_length=100, blank=True)
    # The candidate profile's education levels (users.models.EDUCATION_CHOICES),
    # with 7th-9th collapsed into a single "Below 10th Standard" option.
    EDUCATION_CHOICES = [
        ('below_10th', 'Below 10th Standard'),
        ('10th', '10th / SSLC'), ('11th', '11th Standard'), ('12th', '12th / HSC / PUC'),
        ('iti', 'ITI'), ('diploma', 'Diploma'),
        ('ug', 'Under-Graduate / Degree'), ('pg', 'Post-Graduate'),
        # NON-IT -> Technical "Qualification" presets (Degree / Diploma /
        # ITI / Certification); the two below are offered there only.
        ('degree', 'Degree'), ('certification', 'Certification'),
        ('custom', 'Enter manually'),
    ]
    TECH_EDUCATION_KEYS = ['degree', 'diploma', 'iti', 'certification']
    TECH_ONLY_EDUCATION_KEYS = ['degree', 'certification']
    # Minimum educational qualification; 'custom' keeps the free text in education_other.
    education = models.CharField(max_length=20, choices=EDUCATION_CHOICES, blank=True)
    education_other = models.CharField(max_length=100, blank=True)
    notice_period = models.CharField(max_length=10, choices=NOTICE_PERIOD_ALL_CHOICES, blank=True, default='immediate')
    notice_period_other = models.CharField(max_length=100, blank=True)
    gender_preference = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, default='both')
    # Additional perks offered with the job, in display order. Stored as a
    # comma-separated list of keys (same convention as skills_required).
    PERK_CHOICES = [
        ('flexible_hours', 'Flexible Working Hours'),
        ('weekly_payout', 'Weekly Payout'),
        ('overtime_pay', 'Overtime Pay'),
        ('joining_bonus', 'Joining Bonus'),
        ('annual_bonus', 'Annual Bonus'),
        ('pf', 'PF'),
        ('travel_allowance', 'Travel Allowance (TA)'),
        ('petrol_allowance', 'Petrol Allowance'),
        ('mobile_allowance', 'Mobile Allowance'),
        ('internet_allowance', 'Internet Allowance'),
        ('laptop', 'Laptop'),
        ('health_insurance', 'Health Insurance'),
        ('esi', 'ESI (ESIC)'),
        ('food_meals', 'Food/Meals'),
        ('accommodation', 'Accommodation'),
        ('five_working_days', '5 Working Days'),
        ('one_way_cab', 'One-Way Cab'),
        ('two_way_cab', 'Two-Way Cab'),
    ]
    perks = models.CharField(max_length=500, blank=True)
    # IT postings: the general skill pills (optional; when any are chosen,
    # 3-4 of them are starred as mandatory). skills_required keeps every
    # selected skill (mandatory ones first) as a comma-separated list, and
    # mandatory_skills the 3-4 the employer marked as must-have.
    SKILL_OPTIONS = [
        'Communication', 'English Proficiency', 'Teamwork', 'Problem Solving',
        'Time Management', 'Leadership', 'Customer Service', 'Sales & Negotiation',
        'MS Office / Excel', 'Data Analysis', 'Computer Basics',
        'Project Management', 'Technical / Domain Knowledge', 'Adaptability',
    ]
    # NON-IT -> Technical postings: skills per Department / Function (taken
    # verbatim from the "Skills - Non-IT" document); only the chosen
    # department's skills are offered and at least one must be selected.
    DEPARTMENT_SKILLS = {
        'engineering': [
            'Civil Engineering', 'Mechanical Engineering', 'Electrical Engineering',
            'Instrumentation', 'Automation & Control', 'Electronics',
            'Chemical / Process Engineering', 'Industrial Engineering',
            'Production Engineering', 'Maintenance Engineering',
            'Reliability Engineering', 'Marine Engineering', 'Renewable Energy',
        ],
        'epc_construction': [
            'Project Management', 'Construction Management', 'Project Planning',
            'Project Scheduling', 'Project Controls', 'Cost Control',
            'Site Supervision', 'Contract Management',
            'Quantity/Commercial Management', 'Testing & Commissioning',
            'Project Handover',
        ],
        'hse_safety': [
            'HSE Management', 'EHS', 'Industrial Safety', 'Process Safety',
            'Environmental Safety', 'Permit-to-Work', 'Emergency Response',
            'Safety Auditing', 'Fire Safety', 'Firefighting',
        ],
        'fire_emergency': [
            'Fire & Safety Officer', 'Fire Engineer', 'Fire Supervisor',
            'Fire Technician', 'Firefighter', 'Emergency Response',
            'Emergency Preparedness',
        ],
        'quality_inspection': [
            'QA/QC', 'Quality Inspection', 'Quality Engineering', 'NDT',
            'Welding Inspection', 'Mechanical Inspection', 'Electrical Inspection',
            'Documentation & Quality Reporting',
        ],
        'plant_operations': [
            'Plant Operations', 'Equipment Maintenance', 'Mechanical Maintenance',
            'Electrical Maintenance', 'Instrumentation Maintenance',
            'Maintenance Planning', 'Reliability', 'Production Operations',
            'Supervisory Skills',
        ],
        'skilled_trades': [
            'Electrician', 'Fitter', 'Welder', 'Rigger', 'Fabricator', 'Technician',
            'Machine Operator', 'Plant Operator', 'Foreman', 'Site Supervisor',
        ],
        'renewable_energy': [
            'Solar EPC', 'Solar O&M', 'Wind Energy', 'Electrical Power Systems',
            'SCADA', 'Monitoring & Analytics', 'Testing & Commissioning',
            'Renewable Energy QA/QC', 'Environmental & HSE',
        ],
        'industrial_manufacturing': [
            'Production', 'Manufacturing Operations', 'Industrial Automation',
            'Maintenance', 'Quality Control', 'Production Planning',
            'Process Operations', 'Equipment Operations', 'Smart Manufacturing',
        ],
        'automotive_ev': [
            'Automotive Production', 'EV Manufacturing', 'Electrical Systems',
            'Mechanical Assembly', 'Production Operations', 'Quality Inspection',
            'Maintenance', 'Industrial Automation',
        ],
        'oil_gas_energy': [
            'Refinery Operations', 'Petrochemical Operations', 'Oil & Gas Maintenance',
            'Process Engineering', 'HSE', 'Fire Safety', 'Shutdown & Turnaround',
            'Commissioning', 'Inspection',
        ],
        'logistics_workforce': [
            'Warehouse Operations', 'Industrial Logistics', 'Material Handling',
            'Inventory Management', 'Supervisory Skills', 'Workforce Coordination',
            'Shift Management',
        ],
    }
    MANDATORY_SKILLS_MIN = 3
    MANDATORY_SKILLS_MAX = 4

    @classmethod
    def designations_for_classification(cls, classification):
        """Designation keys allowed for a Job Classification ('' = all)."""
        if classification in cls.DESIGNATION_GROUPS:
            return [key for key, _ in cls.DESIGNATION_GROUPS[classification]]
        return [key for group in cls.DESIGNATION_GROUPS.values() for key, _ in group]

    @classmethod
    def skills_for_department(cls, department):
        return list(cls.DEPARTMENT_SKILLS.get(department, []))

    @classmethod
    def all_skill_options(cls):
        """Every offered skill (IT list, then departments), de-duplicated."""
        seen = []
        for skills in [cls.SKILL_OPTIONS] + list(cls.DEPARTMENT_SKILLS.values()):
            for s in skills:
                if s not in seen:
                    seen.append(s)
        return seen
    mandatory_skills = models.CharField(max_length=500, blank=True)
    is_seeded = models.BooleanField(default=False, help_text='True if this job was seeded from job_photos directory')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} @ {self.employer.company_name}"

    def get_skills_list(self):
        return [s.strip() for s in self.skills_required.split(',') if s.strip()]

    def get_mandatory_skills_list(self):
        return [s.strip() for s in (self.mandatory_skills or '').split(',') if s.strip()]

    def get_additional_skills_list(self):
        """Selected skills that were not marked mandatory."""
        mandatory = set(self.get_mandatory_skills_list())
        return [s for s in self.get_skills_list() if s not in mandatory]

    def get_perks_list(self):
        """Selected perk keys, in PERK_CHOICES order."""
        chosen = {p.strip() for p in (self.perks or '').split(',') if p.strip()}
        return [key for key, _label in self.PERK_CHOICES if key in chosen]

    def get_perks_display(self):
        """Selected perk labels, in PERK_CHOICES order."""
        labels = dict(self.PERK_CHOICES)
        return [labels[key] for key in self.get_perks_list()]

    def application_count(self):
        return self.applications.count()

    def get_job_type_display(self):
        """Choice label; for contracts, with the project duration appended."""
        label = dict(self.JOB_TYPE_CHOICES).get(self.job_type, self.job_type)
        if self.job_type == 'contract' and self.contract_duration_months:
            months = self.contract_duration_months
            return f"{label} ({months} Month{'s' if months != 1 else ''})"
        return label

    def get_education_display(self):
        """Choice label, or the manually entered qualification for 'custom'."""
        if self.education == 'custom':
            return self.education_other
        return dict(self.EDUCATION_CHOICES).get(self.education, self.education)

    def get_experience_display(self):
        """Choice label, or the manually entered years for 'custom'."""
        if self.experience == 'custom' and self.experience_years is not None:
            years = self.experience_years
            if self.experience_years_max is not None:
                return f"{years}-{self.experience_years_max} Years"
            if years == 0 and not self.experience_plus:
                return 'Fresher'
            if self.experience_plus:
                return f"{years}+ Years"
            return f"{years} Year{'s' if years != 1 else ''}"
        return dict(self.EXPERIENCE_CHOICES).get(self.experience, self.experience)

    def get_salary_display(self):
        """Salary range in the unit the employer chose (``salary_format``):

          monthly → "₹30,000 – ₹50,000 per month"
          lpa     → "₹3 LPA – ₹6 LPA"

        Legacy rows stored in a different unit are normalised by
        ``_to_monthly`` / ``_to_lpa``.
        """
        if self.salary_format == 'lpa':
            return self._range_display(self._to_lpa, self._fmt_lpa_amount)
        return self._range_display(self._to_monthly, self._fmt_monthly_amount)

    def _range_display(self, convert, fmt):
        lo = convert(self.salary_min)
        hi = convert(self.salary_max)
        if lo is None and hi is None:
            return "As per industry norms"
        if lo is not None and hi is not None:
            return f"{fmt(lo)} – {fmt(hi)}" + self._period_suffix()
        if lo is not None:
            return fmt(lo, plus=True) + self._period_suffix()
        return f"Up to {fmt(hi)}" + self._period_suffix()

    def _period_suffix(self):
        return "" if self.salary_format == 'lpa' else " per month"

    def _fmt_monthly_amount(self, monthly, plus=False):
        return f"₹{self._fmt_monthly(monthly)}{'+' if plus else ''}"

    def _fmt_lpa_amount(self, lpa, plus=False):
        return f"₹{self._fmt_lpa(lpa)}{'+' if plus else ''} LPA"

    @staticmethod
    def _to_monthly(val):
        """Convert a stored salary value to monthly rupees (float).

        Monthly-format postings store monthly rupees directly. Older rows
        (and some seed data) used other conventions, so the storage band is
        detected:
          - val < 100          : stored as LPA (e.g. 6.0 → 50,000/month)
          - 100 <= val < 1000000: stored as monthly rupees (up to 6 digits, e.g. 90000)
          - val >= 1000000       : stored as annual rupees (e.g. 1800000 → 150,000/month)
        """
        if val is None:
            return None
        val_f = float(val)
        if val_f < 100:
            return (val_f * 100000.0) / 12.0
        elif val_f >= 1000000:
            return val_f / 12.0
        else:
            return val_f

    @classmethod
    def _to_lpa(cls, val):
        """Convert a stored salary value to lakhs per annum (float), using
        the same storage-band detection as ``_to_monthly``. LPA-format
        postings store the LPA figure directly (e.g. 6.0)."""
        monthly = cls._to_monthly(val)
        if monthly is None:
            return None
        return (monthly * 12.0) / 100000.0

    @staticmethod
    def _fmt_monthly(monthly):
        """Format monthly rupees as a whole number with Indian digit grouping
        (30,000 / 1,50,000)."""
        if monthly is None:
            return "?"
        n = int(round(monthly))
        digits = str(abs(n))
        if len(digits) > 3:
            head, tail = digits[:-3], digits[-3:]
            head = re.sub(r'(\d)(?=(\d{2})+$)', r'\1,', head)
            digits = f"{head},{tail}"
        return f"-{digits}" if n < 0 else digits

    @staticmethod
    def _fmt_lpa(lpa):
        """Format an LPA value cleanly (no trailing .0): 3 / 4.5 / 12."""
        if lpa is None:
            return "?"
        if lpa % 1 == 0:
            return str(int(lpa))
        return f"{lpa:.1f}"

    def get_monthly_salary_for_experience(self, years_experience):
        """
        Calculates standard monthly salary based on normalized min/max values
        and the user's experience years interpolated within the job's experience requirements.
        """
        s_min = self._to_monthly(self.salary_min)
        s_max = self._to_monthly(self.salary_max)

        if s_min is None and s_max is None:
            return None
        if s_min is not None and s_max is None:
            return s_min
        if s_max is not None and s_min is None:
            return s_max

        # Parse experience requirement range
        exp_min, exp_max = 0.0, 1.0
        exp_str = (self.experience or '').lower().strip()
        if exp_str == 'custom' and self.experience_years is not None:
            # "N-M" is the typed range; "N" is exact; "N+" is treated like
            # the preset "8+" band (N to N+4)
            exp_min = float(self.experience_years)
            if self.experience_years_max is not None:
                exp_max = float(self.experience_years_max)
            else:
                exp_max = exp_min + 4.0 if self.experience_plus else exp_min
        elif 'fresher' in exp_str:
            exp_min, exp_max = 0.0, 1.0
        elif '+' in exp_str:
            try:
                val = float(exp_str.replace('+', '').strip())
                exp_min, exp_max = val, val + 4.0
            except ValueError:
                pass
        elif '-' in exp_str:
            parts = exp_str.split('-')
            if len(parts) == 2:
                try:
                    exp_min = float(parts[0].strip())
                    exp_max = float(parts[1].strip())
                except ValueError:
                    pass
        else:
            try:
                val = float(exp_str)
                exp_min, exp_max = val, val
            except ValueError:
                pass

        # Interpolate
        years = float(years_experience or 0.0)
        if exp_max <= exp_min:
            ratio = 0.5
        else:
            clamped_years = max(exp_min, min(exp_max, years))
            ratio = (clamped_years - exp_min) / (exp_max - exp_min)

        s_min_f, s_max_f = float(s_min), float(s_max)  # type: ignore[arg-type]
        return s_min_f + (s_max_f - s_min_f) * ratio

    def get_salary_display_for_user(self, user):
        """
        Returns a formatted monthly salary display based on the user's
        experience (extracted from their latest resume), or the full monthly
        range when experience is unavailable.
        """
        def extract_exp(text):
            if not text:
                return 0.0
            text_lower = text.lower()
            match = re.search(r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:year|yr)', text_lower)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
            return 0.0

        years_experience = 0.0
        if user and user.is_authenticated:
            from core.models import Resume
            resume = Resume.objects.filter(user=user).order_by('-uploaded_at').first()
            if resume and resume.extracted_text:
                years_experience = extract_exp(resume.extracted_text)

        m_min = self._to_monthly(self.salary_min)
        m_max = self._to_monthly(self.salary_max)

        if m_min is None and m_max is None:
            return "As per industry norms"

        # Only one boundary set, or no user / no experience → full range
        if (m_min is None or m_max is None
                or not user or not user.is_authenticated or years_experience == 0.0):
            return self.get_salary_display()

        # Personalised: interpolate monthly within the range, then show it
        # in the posting's own unit
        calc_monthly = self.get_monthly_salary_for_experience(years_experience) or m_min
        if self.salary_format == 'lpa':
            amount = self._fmt_lpa_amount((calc_monthly * 12.0) / 100000.0)
        else:
            amount = self._fmt_monthly_amount(calc_monthly) + " per month"
        return f"{amount} (based on your {years_experience:.1f} yr exp)"



class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('applied', 'Applied'), ('reviewing', 'Under Review'),
        ('shortlisted', 'Shortlisted'), ('interview', 'Interview Scheduled'),
        ('offered', 'Offer Extended'), ('rejected', 'Rejected'),
    ]

    SOURCE_CHOICES = [
        ('direct', 'Direct Apply'),
        ('resume_parsed', 'Resume Parsed'),
    ]

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    # Optional link to the student user who applied via resume parsing
    applicant_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='job_applications', help_text='Student user who applied via resume parsing'
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='direct')
    # The AI interview that qualified this specific application (set at apply
    # time from the session the candidate had just completed). Recordings are
    # resolved per application through this link, so two applications by the
    # same person — different emails or different jobs — each show their own
    # interview instead of the applicant's newest one overall.
    interview_session = models.ForeignKey(
        'career_app.ResumeInterviewSession', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='job_applications',
    )
    applicant_name = models.CharField(max_length=200)
    applicant_email = models.EmailField()
    applicant_phone = models.CharField(max_length=20)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    cover_letter = models.TextField(blank=True)
    applicant_skills = models.CharField(max_length=500, blank=True, help_text='Comma separated skills e.g. Python, Django, React')
    years_experience = models.PositiveIntegerField(default=0)
    current_company = models.CharField(max_length=200, blank=True)
    current_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    employer_notes = models.TextField(blank=True)
    # Status the candidate was last emailed about — per application, so a
    # repeated/retried save of the same status never re-notifies, while a
    # second application by the same person to the same employer is
    # notified independently.
    last_notified_status = models.CharField(max_length=20, blank=True, default='')
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']
        unique_together = ['job', 'applicant_email']

    def __str__(self):
        return f"{self.applicant_name} → {self.job.title}"

    def get_skills_list(self):
        return [s.strip() for s in self.applicant_skills.split(',') if s.strip()]
