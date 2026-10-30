// Page scanner grouping (extension/scan.js); plain Node, no browser needed.
const assert = require('assert/strict');
const {scanType, groupLinks, selectedLinks, SCAN_LIMIT} = require('./extension/scan.js');

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
