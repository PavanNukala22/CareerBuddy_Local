const { chromium } = require('playwright');

async function profile(page, url, label) {
  const requests = [];
  page.on('response', (res) => requests.push({ url: res.url(), status: res.status() }));
  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'load', timeout: 45000 });
  const wallMs = Date.now() - t0;
  console.log('\n=== ' + label + ' ===');
  console.log('wallMs:', wallMs, 'requests:', requests.length, 'failed:', requests.filter(r => r.status >= 400).length);
  return wallMs;
}

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto('https://careerbuddy4u.com/users/login/', { waitUntil: 'load', timeout: 45000 });
  await page.fill('#id_username', 'test111');
  await page.fill('#id_password', 'Sri@7032');
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'load', timeout: 45000 }),
    page.click('button[type="submit"]'),
  ]);

  await profile(page, 'https://careerbuddy4u.com/resume-builder/', 'Resume Builder home');
  await profile(page, 'https://careerbuddy4u.com/resume-builder/history/', 'Resume history');

  await browser.close();
}
main().catch(e => { console.error('ERROR', e); process.exit(1); });
