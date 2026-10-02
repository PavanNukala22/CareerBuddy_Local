from django import template

from riya_bot.section_names import SECTION_NAMES

register = template.Library()


@register.simple_tag
def riya_section_names():
    """Translated section names for BOTscript.js (rendered via json_script)."""
    return SECTION_NAMES
