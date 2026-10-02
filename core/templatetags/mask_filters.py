from django import template
from core.mask_utils import mask_aadhar, mask_pan, mask_passport

register = template.Library()

register.filter('mask_aadhar', mask_aadhar)
register.filter('mask_pan', mask_pan)
register.filter('mask_passport', mask_passport)
