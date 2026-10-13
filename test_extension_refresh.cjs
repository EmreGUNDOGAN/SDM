const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
(async()=>{
  const folder=path.join(__dirname,'build/refresh-extension-040');fs.cpSync(path.join(__dirname,'extension'),folder,{recursive:true});
  const context=await chromium.launchPersistentContext(path.join(__dirname,'build/refresh-profile-040-'+Date.now()),{channel:'chromium',headless:true,ignoreDefaultArgs:['--disable-extensions'],args:['--enable-unsafe-extension-debugging']});
  const cdp=await context.browser().newBrowserCDPSession();await cdp.send('Extensions.loadUnpacked',{path:folder});
  try {
    let worker=context.serviceWorkers()[0] || await context.waitForEvent('serviceworker',{timeout:5000});
    const files={};
    for(const name of fs.readdirSync(folder))if(fs.statSync(path.join(folder,name)).isFile())files[name]=crypto.createHash('sha256').update(fs.readFileSync(path.join(folder,name))).digest('hex');
    await worker.evaluate(status=>{chrome.runtime.sendNativeMessage=async()=>status;},{version:'0.4.0',files});
    const result=await worker.evaluate(()=>verifyExtensionFiles());assert.equal(result.reload,true);
    // A separately loaded, mismatched copy must be rejected rather than falsely reported updated.
    await worker.evaluate(()=>{chrome.runtime.sendNativeMessage=async()=>({version:'0.4.1',files:{'manifest.json':'0'.repeat(64)}});});
    const rejected=await worker.evaluate(async()=>{try{await verifyExtensionFiles();return false;}catch{return true;}});assert.equal(rejected,true);
    const id=new URL(worker.url()).hostname;
    const popup=await context.newPage();await popup.goto(`chrome-extension://${id}/popup.html`);
    assert.equal(await popup.getByRole('button',{name:'Eklentiyi yenile',exact:true}).count(),1);
    await worker.evaluate(status=>{chrome.runtime.sendNativeMessage=async()=>status;},{version:'0.4.0',files});
    await worker.evaluate(()=>{globalThis.testReloadCalled=false;chrome.runtime.reload=()=>{globalThis.testReloadCalled=true;};});
    await popup.getByRole('button',{name:'Eklentiyi yenile',exact:true}).click();
    await new Promise(resolve=>setTimeout(resolve,1000));
    assert.equal(await worker.evaluate(()=>globalThis.testReloadCalled),true);
    console.log('Real Chromium file hash validation, mismatched-copy rejection, popup and reload invocation: OK (runtime.reload mocked; command-line/CDP installs are disabled by Chrome on real reload)');
  }finally{await context.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
