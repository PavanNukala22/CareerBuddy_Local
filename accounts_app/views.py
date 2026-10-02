from django.shortcuts import render, redirect
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.urls import reverse

from jobs_app.models import EmployerProfile
from .forms import EmployerRegisterForm
from core.email_utils import send_transactional_email
from users.views import is_email_verified, clear_verified_emails


def send_employer_welcome_email(request, user):
    """Sends a styled welcome email to the newly registered employer HR/Admin."""
    dashboard_url = request.build_absolute_uri(reverse('employer_portal:dashboard'))
    # Send to the HR email address provided, falling back to the login email.
    to_email = user.employer_profile.hr_mail or user.email
    send_transactional_email(
        subject='Welcome to Career Buddy - Employer Registration Successful!',
        to_email=to_email,
        template_name='emails/employer_registration_success.html',
        context={
            'user': user,
            'dashboard_url': dashboard_url,
            'profile': user.employer_profile,
        },
    )


class EmployerLoginForm(AuthenticationForm):
    def clean(self):
        cleaned_data = super().clean()
        user = self.user_cache
        if user is not None and not hasattr(user, 'employer_profile'):
            raise forms.ValidationError(
                "Student accounts cannot log in through the employer portal.",
                code='invalid_login',
            )
        return cleaned_data


def employer_register(request):
    if request.method == 'POST':
        form = EmployerRegisterForm(request.POST, request.FILES)
        account_email = request.POST.get('email', '').strip()
        hr_email = request.POST.get('hr_mail', '').strip()

        # Both addresses must be OTP-verified in this session before an account is
        # created. Checked server-side (not from the POST body) so the front-end
        # guard cannot be bypassed. Runs before form.is_valid() so an unverified
        # email is reported even when the rest of the form is fine.
        unverified = [
            label for label, addr in (('account', account_email), ('HR', hr_email))
            if not is_email_verified(request, addr)
        ]
        if unverified:
            if 'account' in unverified:
                form.add_error('email', 'Verify this email address with the OTP to continue.')
            if 'HR' in unverified:
                form.add_error('hr_mail', 'Verify this email address with the OTP to continue.')
            messages.error(request, 'Please verify both email addresses with the OTP before creating your account.')
            return render(request, 'employer_login/signup.html', {'form': form})

        if form.is_valid():
            user = form.save()
            clear_verified_emails(request)
            # form.save() doesn't run authenticate(), so user.backend is unset;
            # with multiple AUTHENTICATION_BACKENDS, login() needs one specified
            # (mirrors users/views.py:register_view).
            user.backend = 'users.backends.EmailOrUsernameModelBackend'
            login(request, user)
            request.session['portal'] = 'employer'
            messages.success(request, f'Welcome, {user.username}! Your employer account is ready.')

            # Send HR welcome email with failsafe wrapper
            send_employer_welcome_email(request, user)

            return redirect('job_home')
    else:
        form = EmployerRegisterForm()
    return render(request, 'employer_login/signup.html', {'form': form})


class EmployerLoginView(auth_views.LoginView):
    form_class = EmployerLoginForm
    template_name = 'employer_login/login.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session['portal'] = 'employer'
        return response

    def get_success_url(self):
        return redirect('job_home').url


def register(request):
    # Keep for compatibility
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            request.session['portal'] = 'employer'
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('job_home')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})
