"""
Issue #11 — Database performance profiling.
Runs each authenticated view through Django's test Client with a real user,
counts SQL queries via CaptureQueriesContext, and flags likely N+1 patterns
(the same normalized query text repeated many times in one request).
No app code or settings are modified — read-only diagnostic.
"""
import os
import re
import sys
import django
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'business_english_lms.settings')
django.setup()

from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.contrib.auth import get_user_model

override_settings(ALLOWED_HOSTS=['testserver']).enable()

User = get_user_model()
user = User.objects.filter(username='SridurgaG').first()
if not user:
    user = User.objects.filter(is_superuser=False, is_active=True).first()
print("Testing as user:", user.username)

client = Client()
client.force_login(user)

ROUTES = [
    ('/dashboard/', 'Dashboard'),
    ('/activities/', 'Activities list'),
    ('/resume-builder/', 'Resume Builder home'),
    ('/skill-up/', 'Skill Up hub'),
    ('/subject/', 'Grammar (Subject home)'),
]


def normalize(sql):
    # Strip numeric/string literals so repeated queries with different
    # parameter values collapse to the same "shape" for N+1 detection.
    sql = re.sub(r"'[^']*'", '?', sql)
    sql = re.sub(r'\b\d+\b', '?', sql)
    return sql[:160]


for path, label in ROUTES:
    with CaptureQueriesContext(connection) as ctx:
        resp = client.get(path)
    n = len(ctx.captured_queries)
    shapes = Counter(normalize(q['sql']) for q in ctx.captured_queries)
    repeated = [(shape, count) for shape, count in shapes.items() if count >= 3]
    print(f"\n=== {label} ({path}) === status={resp.status_code} queries={n}")
    if repeated:
        print("  Likely N+1 (same query shape repeated >=3x):")
        for shape, count in sorted(repeated, key=lambda x: -x[1])[:5]:
            print(f"    x{count}: {shape}")
    else:
        print("  No repeated query shape >=3x found.")
