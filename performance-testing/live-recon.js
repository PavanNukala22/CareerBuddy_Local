// Live recon for Issues #8 (404s) and #9 (cache headers) against the
// deployed production site. Read-only: navigates public pages, records
// every response's status/headers, and any console errors.
const { chromium } = require('playwright');

const PAGES = [
  'https://careerbuddy4u.com/',
  'https://careerbuddy4u.com/users/login/',
  'https://careerbuddy4u.com/users/register/',
];

async function checkPage(page, url) {
  const requests = [];
  const consoleMsgs = [];
  const onResponse = (res) => {
    requests.push({
      url: res.url(),
      status: res.status(),
      headers: res.headers(),
    });
  };
  const onConsole = (msg) => consoleMsgs.push({ type: msg.type(), text: msg.text() });
  page.on('response', onResponse);
  page.on('console', onConsole);

  await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
  await page.waitForTimeout(1000);

  page.off('response', onResponse);
  page.off('console', onConsole);

  const failed = requests.filter(r => r.status >= 400);
  const staticAssets = requests.filter(r => /\.(css|js|png|jpe?g|woff2?|svg)(\?|$)/.test(r.url) && r.url.includes('careerbuddy4u.com'));

  return { url, requestCount: requests.length, failed, staticAssets, consoleMsgs };
}

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();

  for (const url of PAGES) {
    console.log('\n=== ' + url + ' ===');
    const result = await checkPage(page, url);
    console.log('Total requests:', result.requestCount);
    console.log('FAILED (>=400):', JSON.stringify(result.failed, null, 2));
    console.log('Console errors/warnings:', JSON.stringify(result.consoleMsgs.filter(m => m.type === 'error' || m.type === 'warning'), null, 2));
    console.log('Static asset cache headers (first 5):');
    result.staticAssets.slice(0, 5).forEach(a => {
      console.log(' ', a.url.replace('https://careerbuddy4u.com', ''), '-> cache-control:', a.headers['cache-control'] || 'ABSENT', '| content-encoding:', a.headers['content-encoding'] || 'ABSENT');
    });
  }

  await browser.close();
}

main().catch(e => { console.error('ERROR', e); process.exit(1); });
