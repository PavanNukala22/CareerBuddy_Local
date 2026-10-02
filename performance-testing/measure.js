// Usage: node performance-testing/measure.js <url> <label>
// Navigates with a real Chrome instance, captures Navigation/Resource Timing +
// Paint timing, and prints a JSON summary. Used to produce before/after
// evidence for each performance fix (per CB-PERF remediation process).
const { chromium } = require('playwright');

async function main() {
  const url = process.argv[2] || 'http://127.0.0.1:8000/';
  const label = process.argv[3] || 'run';

  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ cacheEnabled: true });
  const page = await context.newPage();

  const requests = [];
  page.on('response', async (res) => {
    try {
      const req = res.request();
      const sizes = await res.body().then(b => b.length).catch(() => null);
      requests.push({
        url: req.url(),
        status: res.status(),
        resourceType: req.resourceType(),
        bytes: sizes,
      });
    } catch (e) { /* ignore */ }
  });

  const consoleMsgs = [];
  page.on('console', (msg) => consoleMsgs.push({ type: msg.type(), text: msg.text() }));

  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'load', timeout: 60000 });
  const wallLoadMs = Date.now() - t0;

  const perf = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const paints = performance.getEntriesByType('paint');
    const fcp = paints.find(p => p.name === 'first-contentful-paint');
    let lcp = null;
    try {
      const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
      if (lcpEntries.length) lcp = lcpEntries[lcpEntries.length - 1].startTime;
    } catch (e) {}
    return {
      ttfb: nav ? nav.responseStart - nav.requestStart : null,
      domContentLoaded: nav ? nav.domContentLoadedEventEnd : null,
      loadEvent: nav ? nav.loadEventEnd : null,
      transferSize: nav ? nav.transferSize : null,
      fcp: fcp ? fcp.startTime : null,
      lcp,
      resourceCount: performance.getEntriesByType('resource').length,
    };
  });

  const totalBytes = requests.reduce((sum, r) => sum + (r.bytes || 0), 0);
  const tailwindCdnLoaded = requests.some(r => r.url.includes('cdn.tailwindcss.com'));
  const errors = consoleMsgs.filter(m => m.type === 'error');
  const warnings = consoleMsgs.filter(m => m.type === 'warning');

  const summary = {
    label,
    url,
    wallLoadMs,
    ...perf,
    requestCount: requests.length,
    totalBytesKB: Math.round(totalBytes / 1024),
    tailwindCdnLoaded,
    consoleErrors: errors.map(e => e.text),
    consoleWarnings: warnings.map(w => w.text),
  };

  console.log(JSON.stringify(summary, null, 2));
  await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
