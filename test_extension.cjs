const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const readline = require('readline');
const assert = require('assert/strict');

(async () => {
  const root = __dirname;
  const extension=path.join(root,'build/extension-test-031');
  fs.cpSync(path.join(root,'extension'),extension,{recursive:true});
  const bg=path.join(extension,'background.js');
  fs.writeFileSync(bg,fs.readFileSync(bg,'utf8').replaceAll('49282','49382'));
  const fixture = spawn(path.join(root, '.venv/Scripts/python.exe'), ['browser_fixture.py'], {
    cwd: root, env: {...process.env, SDM_DATA_DIR: path.join(root, 'build/browser-fixture-data-031'), SDM_BRIDGE_PORT:'49382'},
    windowsHide: true
  });
  const lines = readline.createInterface({input: fixture.stdout});
  const messages = [];
  let resolveConfig;
  const configPromise = new Promise(resolve => { resolveConfig = resolve; });
  lines.on('line', line => {
    const message = JSON.parse(line);
    if (message.token) resolveConfig(message); else messages.push(message);
  });
  fixture.stderr.on('data', chunk => process.stderr.write(chunk));
  let context;
  try {
    const config = await Promise.race([configPromise, new Promise((_,reject)=>setTimeout(()=>reject(new Error('fixture timeout')),15000))]);
    context = await chromium.launchPersistentContext(path.join(root, 'build/extension-test-profile-031'), {
      channel: 'chromium', headless: true,
      args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`]
    });
    let worker = context.serviceWorkers()[0];
    if (!worker) worker = await context.waitForEvent('serviceworker');
    // The native host transport is tested separately; pair the isolated worker
    // with the fixture to exercise real extension fetch/CORS and the UI.
    await worker.evaluate(config => {
      chrome.runtime.sendNativeMessage = async () => config;
    }, config);
    await context.route('https://www.youtube.com/**', route => route.fulfill({
      contentType: 'text/html', body: '<html><body style="margin:40px"><video style="display:block;width:800px;height:450px;background:#111" controls></video></body></html>'
    }));
    const page = await context.newPage();
    await page.goto('https://www.youtube.com/watch?v=sdm-test');
    const button = page.locator('#sdm-video-overlay').getByRole('button', {name:'SDM ile indir'});
    await button.click();
    await page.getByRole('button', {name:'1080p · Video + ses', exact:true}).waitFor().catch(async error=>{console.error(await page.locator('#sdm-video-overlay #status').textContent());throw error});
    assert.equal(await page.getByRole('button', {name:'720p · Video + ses', exact:true}).count(), 1);
    await page.getByRole('button', {name:'1080p · Video + ses', exact:true}).click();
    await page.waitForTimeout(500);
    assert.equal(await page.locator('#sdm-video-overlay #panel').isVisible(),false);
    assert.equal(messages[0].height, 1080);
    await button.click();
    await page.getByRole('button', {name:'Yalnızca ses · MP3', exact:true}).click();
    await page.waitForTimeout(500);
    assert.equal(messages[1].audio, true);
    await page.screenshot({path:path.join(root,'build/extension-preview.png')});
    console.log('Extension browser UI, real authenticated bridge fetch, 1080p selection and MP3: OK');
  } finally {
    if (context) await context.close();
    fixture.kill();
    lines.close();
  }
})().catch(error => { console.error(error); process.exitCode=1; });
