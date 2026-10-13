const {chromium} = require('playwright');
const path = require('path');
const assert = require('assert/strict');
(async () => {
  const extension = process.env.SDM_TEST_EXTENSION_PATH || path.join(__dirname,'extension');
  const context = await chromium.launchPersistentContext(path.join(__dirname,'build/live-extension-profile-031'), {
    channel:'chromium', headless:true,
    args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]
  });
  try {
    await context.route('https://www.youtube.com/**',route=>route.fulfill({contentType:'text/html',
      body:'<html><body style="margin:40px"><video style="display:block;width:800px;height:450px;background:#111" controls></video></body></html>'}));
    const page = await context.newPage();
    await page.goto('https://www.youtube.com/watch?v=jNQXAC9IVRw');
    await page.locator('#sdm-video-overlay').getByRole('button',{name:'SDM ile indir'}).click();
    const quality=page.getByRole('button',{name:'144p · Video + ses',exact:true});
    await quality.waitFor({timeout:90000});
    await quality.click();
    await page.waitForTimeout(700);
    await page.locator('#sdm-video-overlay').getByRole('button',{name:'SDM ile indir'}).click();
    await page.getByRole('button',{name:'Yalnızca ses · MP3',exact:true}).click();
    await page.waitForTimeout(1000);
    assert.equal(await page.locator('#sdm-video-overlay #panel').isVisible(),false);
    await page.screenshot({path:path.join(__dirname,'build/live-extension-preview.png')});
    console.log('Live native messaging, packaged app formats, video and MP3 queue: OK');
  } finally {await context.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
