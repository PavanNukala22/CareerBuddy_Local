// Issue #10: authenticated module performance, against the live deployed site.
// Logs in with the test account, then profiles the dashboard and one or two
// other authenticated modules: request count, sizes, timing, duplicate calls.
const { chromium } = require('playwright');

async function profile(page, url, label) {
  const requests = [];
  const onResponse = (res) => {
    requests.push({ url: res.url(), status: res.status(), resourceType: res.request().resourceType() });
  };
  page.on('response', onResponse);

  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'load', timeout: 45000 });
  const wallMs = Date.now() - t0;
  await page.waitForTimeout(500);
  page.off('response', onResponse);

  const perf = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    return {
      ttfb: nav ? Math.round(nav.responseStart - nav.requestStart) : null,
      domContentLoaded: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
      loadEvent: nav ? Math.round(nav.loadEventEnd) : null,
      transferSize: nav ? nav.transferSize : null,
    };
  });

  const failed = requests.filter(r => r.status >= 400);
  const urlCounts = {};
  requests.forEach(r => { urlCounts[r.url] = (urlCounts[r.url] || 0) + 1; });
  const duplicates = Object.entries(urlCounts).filter(([u, c]) => c > 1 && !u.includes('flagcdn'));

  console.log('\n=== ' + label + ' (' + url + ') ===');
  console.log('wallMs:', wallMs, 'perf:', JSON.stringify(perf));
  console.log('requestCount:', requests.length, 'failed:', failed.length);
  if (failed.length) console.log('FAILED:', JSON.stringify(failed, null, 2));
  if (duplicates.length) console.log('DUPLICATE requests (same URL >1x, excluding flags):', JSON.stringify(duplicates, null, 2));
  return { label, url, wallMs, perf, requestCount: requests.length, failed, duplicates };
}

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('Logging in...');
  await page.goto('https://careerbuddy4u.com/users/login/', { waitUntil: 'load', timeout: 45000 });
  await page.fill('#id_username', 'test111');
  await page.fill('#id_password', 'Sri@7032');
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'load', timeout: 45000 }),
    page.click('button[type="submit"]'),
  ]);
  console.log('Post-login URL:', page.url());

  const results = [];
  results.push(await profile(page, 'https://careerbuddy4u.com/dashboard/', 'Dashboard'));
  results.push(await profile(page, 'https://careerbuddy4u.com/activities/', 'Activities'));

  await browser.close();
}

main().catch(e => { console.error('ERROR', e); process.exit(1); });
