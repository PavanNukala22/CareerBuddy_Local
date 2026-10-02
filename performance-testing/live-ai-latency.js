// Issue #12: measure real AI (Sarvam) call latency on the live site by
// submitting one resume + job description through the actual form, once.
// Deliberately a single run (not a stress test) — this hits a real paid API.
const { chromium } = require('playwright');
const path = require('path');

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

  await page.goto('https://careerbuddy4u.com/resume-builder/', { waitUntil: 'load', timeout: 45000 });

  const fileInput = await page.$('input[type="file"]');
  const jdInput = await page.$('textarea[name="text"], textarea#id_text, textarea');
  console.log('file input found:', !!fileInput, 'jd textarea found:', !!jdInput);
  if (!fileInput) {
    console.log('Could not find file input on the page. Dumping form field names:');
    const fields = await page.$$eval('input, textarea', els => els.map(e => ({ tag: e.tagName, name: e.name, type: e.type, id: e.id })));
    console.log(JSON.stringify(fields, null, 2));
    await browser.close();
    return;
  }

  await fileInput.setInputFiles(path.resolve(__dirname, 'test-resume.pdf'));
  if (jdInput) {
    await jdInput.fill('Software Engineer with Python and Django experience, REST APIs, and SQL databases required.');
  }

  const submitBtn = await page.$('#analyzeBtn');
  console.log('submit button found:', !!submitBtn);

  const t0 = Date.now();
  const [response] = await Promise.all([
    page.waitForNavigation({ waitUntil: 'load', timeout: 120000 }),
    submitBtn.click(),
  ]);
  const elapsedMs = Date.now() - t0;

  console.log('AI resume-match request total wall time:', elapsedMs, 'ms');
  console.log('Resulting URL:', page.url());
  const bodyText = await page.evaluate(() => document.body.innerText.slice(0, 500));
  console.log('Page content preview:', bodyText);

  await browser.close();
}
main().catch(e => { console.error('ERROR', e); process.exit(1); });
