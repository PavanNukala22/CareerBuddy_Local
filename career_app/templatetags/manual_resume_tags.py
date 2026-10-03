"""Embeds the manual Resume Builder's predefined role data in a page.

    {% load manual_resume_tags %}{% manual_resume_data %}

renders a ``<script type="application/json" id="cb-resume-data">`` block that
the landing page's role cards and resume form read on load.
"""
from django import template
from django.utils.html import json_script

from career_app.resume_roles import client_payload

register = template.Library()


@register.simple_tag
def manual_resume_data(element_id='cb-resume-data'):
    return json_script(client_payload(), element_id)
