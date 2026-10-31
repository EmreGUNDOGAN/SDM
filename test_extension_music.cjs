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

// The player bar parts SDM reads: song, artist, cover and the right-hand buttons.
const PAGE = `<meta charset="utf-8"><title>Song - YouTube Music</title><body style="margin:0;background:#030303">
  <ytmusic-player-bar style="position:fixed;left:0;right:0;bottom:0;height:72px;display:block;background:#212121">
    <img class="image" src="https://music.youtube.com/cover.jpg"><div class="title">Je pense à vous</div>
    <div class="byline">Linh • Je pense à vous • 2024</div>
    <div class="right-controls-buttons" style="position:absolute;right:20px;top:16px;width:160px;height:40px"></div>
  </ytmusic-player-bar></body>`;

async function open(browser, url) {
  const page = await browser.newPage();
  await page.route('**/*', route => route.request().url() === url
    ? route.fulfill({contentType: 'text/html', body: PAGE}) : route.abort());
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
    fs.mkdirSync(path.join(__dirname, 'build'), {recursive: true});
    let page = await open(browser, 'https://music.youtube.com/watch?v=S1&list=OLAK5uy_A');
    const song = page.locator('#video-tab'), album = page.locator('#audio-tab');
    // The red round button sits in the player bar, left of its buttons; the menu shows the playing song.
    const button = await page.locator('#toggle').boundingBox(), controls = await page.locator('.right-controls-buttons').boundingBox();
    assert.ok(button.x + button.width <= controls.x && controls.x - (button.x + button.width) <= 12, JSON.stringify([button, controls]));
    assert.ok(Math.abs(button.y + button.height / 2 - (controls.y + controls.height / 2)) <= 2, JSON.stringify([button, controls]));
    await page.mouse.move(5, 5);
    assert.equal(await page.locator('#toggle').evaluate(node => getComputedStyle(node).backgroundColor), 'rgb(255, 0, 51)');
    assert.equal(await page.locator('#title small').textContent(), 'Je pense à vous · Linh');
    await page.screenshot({path: path.join(__dirname, 'build', 'youtube-music-menu.png')});
    assert.deepEqual([await song.textContent(), await album.textContent()], ['Bu şarkı', 'Albümün tamamı']);
    assert.equal(await song.getAttribute('aria-selected'), 'true');
    await page.getByRole('button', {name: /192 kb\/sn/}).click();
    await album.click();await page.getByRole('button', {name: /320 kb\/sn/}).click();
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
    await page.getByRole('button', {name: /256 kb\/sn/}).click();
    assert.deepEqual(await page.evaluate('window.sent'), [{type: 'music', url: 'https://music.youtube.com/playlist?list=PLmix', bitrate: 256, list: true}]);
    await page.close();

    // A single song without a list: no choice row.
    page = await open(browser, 'https://music.youtube.com/watch?v=S2');
    assert.equal(await page.locator('#tabs').isHidden(), true);
    await page.getByRole('button', {name: /128 kb\/sn/}).click();
    assert.deepEqual(await page.evaluate('window.sent'), [{type: 'music', url: 'https://music.youtube.com/watch?v=S2', bitrate: 128, list: false}]);
    console.log('YouTube Music: song/album choice, album page without a song, playlist, single song: OK');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
