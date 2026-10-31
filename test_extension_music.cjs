// YouTube Music button (extension/content.js): "Bu şarkı" / "Albümün tamamı" in headless Chromium.
// Pages are local fixtures served under the music.youtube.com address; chrome.* is a stub that records messages.
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const {chromium} = require('playwright');

const script = fs.readFileSync(path.join(__dirname, 'extension', 'content.js'), 'utf8');
const stub = `window.sent = [];window.chrome = {
  runtime: {getURL: name => name, sendMessage: async message => { window.sent.push(message); return {result: {}}; }, onMessage: {addListener() {}}},
  storage: {local: {get: async () => ({})}, onChanged: {addListener() {}}}};`;

async function open(browser, url) {
  const page = await browser.newPage();
  await page.route('**/*', route => route.request().url() === url
    ? route.fulfill({contentType: 'text/html', body: '<title>Song - YouTube Music</title><body></body>'}) : route.abort());
  await page.addInitScript(stub);
  await page.goto(url);
  await page.addScriptTag({content: script});
  await page.locator('#toggle').click();
  return page;
}

(async () => {
  const browser = await chromium.launch();
  try {
    // A song played from an album: both choices, the song first.
    let page = await open(browser, 'https://music.youtube.com/watch?v=S1&list=OLAK5uy_A');
    const song = page.locator('#video-tab'), album = page.locator('#audio-tab');
    assert.deepEqual([await song.textContent(), await album.textContent()], ['Bu şarkı', 'Albümün tamamı']);
    assert.equal(await song.getAttribute('aria-selected'), 'true');
    await page.getByRole('button', {name: /MP3 · 192/}).click();
    await album.click();await page.getByRole('button', {name: /MP3 · 320/}).click();
    assert.deepEqual(await page.evaluate('window.sent'), [
      {type: 'music', url: 'https://music.youtube.com/watch?v=S1', bitrate: 192, list: false},
      {type: 'music', url: 'https://music.youtube.com/playlist?list=OLAK5uy_A', bitrate: 320, list: true}]);
    await page.close();

    // An album page names no song until one plays: the song choice is shown but unavailable.
    page = await open(browser, 'https://music.youtube.com/playlist?list=OLAK5uy_A');
    assert.equal(await page.locator('#video-tab').isDisabled(), true);
    assert.equal(await page.locator('#audio-tab').getAttribute('aria-selected'), 'true');
    assert.match(await page.locator('#status').textContent(), /önce şarkıyı çal/);
    await page.close();

    // Any other list is a playlist; it is offered as one too.
    page = await open(browser, 'https://music.youtube.com/playlist?list=PLmix');
    assert.equal(await page.locator('#audio-tab').textContent(), 'Playlistin tamamı');
    await page.getByRole('button', {name: /MP3 · 256/}).click();
    assert.deepEqual(await page.evaluate('window.sent'), [{type: 'music', url: 'https://music.youtube.com/playlist?list=PLmix', bitrate: 256, list: true}]);
    await page.close();

    // A single song without a list: no choice row.
    page = await open(browser, 'https://music.youtube.com/watch?v=S2');
    assert.equal(await page.locator('#tabs').isHidden(), true);
    await page.getByRole('button', {name: /MP3 · 128/}).click();
    assert.deepEqual(await page.evaluate('window.sent'), [{type: 'music', url: 'https://music.youtube.com/watch?v=S2', bitrate: 128, list: false}]);
    console.log('YouTube Music: song/album choice, album page without a song, playlist, single song: OK');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
