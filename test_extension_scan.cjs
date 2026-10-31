// Page scanner (extension/scan.js): grouping in plain Node, page collection in headless Chromium.
const assert = require('assert/strict');
const {scanType, groupLinks, selectedLinks, collectPageLinks, SCAN_LIMIT} = require('./extension/scan.js');

assert.equal(scanType('https://cdn.example.com/a/Song.MP3?sig=1'), 'Ses');
assert.equal(scanType('https://cdn.example.com/live/master.m3u8'), 'Video');
assert.equal(scanType('https://example.com/docs/report.pdf'), 'Belge');
assert.equal(scanType('https://example.com/page'), null);        // pages are not files
assert.equal(scanType('https://example.com/app.js'), null);      // page scripts are skipped
assert.equal(scanType('not a url'), null);

const page = 'https://example.com/list';
const groups = groupLinks([
  '/files/a.zip', 'https://example.com/files/a.zip#top',          // relative + fragment collapse to one
  'https://cdn.example.com/a.mp3', 'blob:https://example.com/123',  // blob/data/javascript never leave the page
  'data:audio/mp3;base64,AAAA', 'javascript:void(0)', page,
  'https://cdn.example.com/cover.jpg', 'https://example.com/setup.exe', '', null,
], page);
assert.deepEqual(groups, {
  'Arşiv': ['https://example.com/files/a.zip'],
  'Ses': ['https://cdn.example.com/a.mp3'],
  'Resim': ['https://cdn.example.com/cover.jpg'],
  'Program': ['https://example.com/setup.exe'],
});
assert.deepEqual(selectedLinks(groups, ['Ses', 'Arşiv']), ['https://cdn.example.com/a.mp3', 'https://example.com/files/a.zip']);

const many = groupLinks(Array.from({length: SCAN_LIMIT + 50}, (_, i) => `https://e.example/f${i}.zip`), page);
assert.equal(selectedLinks(many, ['Arşiv']).length, SCAN_LIMIT);   // bridge rejects more than BATCH_LIMIT

const bridge = require('fs').readFileSync(require('path').join(__dirname, 'browser_bridge.py'), 'utf8');
assert.equal(Number(bridge.match(/BATCH_LIMIT = (\d+)/)[1]), SCAN_LIMIT);
console.log('Page scanner grouping, filtering and limit: OK');

// Players show blob: or extensionless streams; the page or embed is offered as Video/Ses instead.
(async () => {
  const {chromium} = require('playwright');
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const watch = 'https://video.example/watch?v=1';
    await page.route('**/*', route => route.request().url() === watch
      ? route.fulfill({contentType: 'text/html', body: `
          <video src="blob:https://video.example/abc"></video>
          <audio src="https://cdn.example/stream?id=5"></audio>
          <iframe src="https://www.youtube.com/embed/xyz"></iframe>
          <iframe src="https://ads.example/frame"></iframe>
          <img src="https://cdn.example/cover.jpg">`}) : route.abort());
    await page.goto(watch);
    const found = groupLinks(await page.evaluate(`(${collectPageLinks})()`), watch);
    assert.deepEqual(found['Video'], [watch, 'https://www.youtube.com/embed/xyz']);
    assert.deepEqual(found['Ses'], ['https://cdn.example/stream?id=5']);
    assert.deepEqual(found['Resim'], ['https://cdn.example/cover.jpg']);
    console.log('Page scanner media elements, blob players and embedded players: OK');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
