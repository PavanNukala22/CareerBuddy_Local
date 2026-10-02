import re

with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'\{\{[\s\S]*?\}\}', lambda m: m.group(0).replace('\n', ' ').replace('\r', ' '), content)
content = re.sub(r'\{%[\s\S]*?%\}', lambda m: m.group(0).replace('\n', ' ').replace('\r', ' '), content)

content = re.sub(r'(\s*<th>Method</th>\s*)<th>Status</th>(\s*<th>Transaction ID</th>)', r'\g<1>\g<2>', content)
content = re.sub(r'(\s*<td>Razorpay</td>\s*)<td>\s*\{% if payment\.status == \'captured\' %\}.*?\{% endif %\}\s*</td>(\s*<td><small class="text-muted">\{\{ payment\.razorpay_payment_id \}\}</small></td>)', r'\g<1>\g<2>', content, flags=re.DOTALL)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
