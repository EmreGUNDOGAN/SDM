const {chromium}=require('playwright');
const {spawn}=require('child_process');
const readline=require('readline');
const http=require('http');
const path=require('path');
const fs=require('fs');
const assert=require('assert/strict');

(async()=>{
  const root=__dirname,temporary=fs.mkdtempSync(path.join(root,'build/capture-phase3-')),extension=path.join(temporary,'extension');
  fs.cpSync(path.join(root,'extension'),extension,{recursive:true});
  const bg=path.join(extension,'background.js');
  fs.writeFileSync(bg,fs.readFileSync(bg,'utf8').replaceAll('49282','49382'));
  const fixture=spawn(process.env.SDM_TEST_PYTHON || path.join(root,'.venv/Scripts/python.exe'),['browser_fixture.py'],{
    cwd:root,windowsHide:true,env:{...process.env,SDM_BRIDGE_PORT:'49382',SDM_ALLOW_LOCAL_TEST_URLS:'1',
    SDM_DATA_DIR:path.join(temporary,'data')}});
  const rl=readline.createInterface({input:fixture.stdout}), messages=[];
  let resolve; const ready=new Promise(r=>resolve=r);
  rl.on('line',line=>{const data=JSON.parse(line);if(data.token)resolve(data);else messages.push(data)});
  fixture.stderr.on('data',data=>process.stderr.write(data));
  const size=4*1024*1024;
  const server=http.createServer((req,res)=>{
    if(req.headers.range){
      if(req.url==='/fallback.bin'){res.writeHead(403);return res.end();}
      res.writeHead(206,{'Content-Length':1,'Content-Type':'application/octet-stream','Content-Range':`bytes 0-0/${size}`,
        'Content-Disposition':'attachment; filename="capture.bin"'});return res.end('S');
    }
    res.writeHead(200,{'Content-Type':'application/octet-stream','Content-Length':size,
      'Content-Disposition':`attachment; filename="${req.url.includes('fallback')?'fallback':'capture'}.bin"`});
    let sent=0;const timer=setInterval(()=>{if(sent>=size){clearInterval(timer);res.end();return}
      res.write(Buffer.alloc(65536,83));sent+=65536;},30);
    res.on('close',()=>clearInterval(timer));
  });
  await new Promise(r=>server.listen(49383,'127.0.0.1',r));
  let context;
  async function until(fn){for(let i=0;i<100;i++){if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('capture timeout')}
  try{
    const config=await ready;
    context=await chromium.launchPersistentContext(path.join(temporary,'profile'),{
      channel:'chromium',headless:true,acceptDownloads:true,downloadsPath:path.join(temporary,'downloads'),
      args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]});
    let worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker');
    await worker.evaluate(c=>{chrome.runtime.sendNativeMessage=async()=>c},config);
    const page=await context.newPage();
    await page.setContent('<a id="file" href="http://127.0.0.1:49383/file.bin">Download</a><a id="fallback" href="http://127.0.0.1:49383/fallback.bin">Fallback</a>');
    await page.locator('#file').click();
    await until(()=>messages.some(m=>m.kind==='file'));
    await until(async()=>{const items=await worker.evaluate(()=>chrome.downloads.search({}));return !items.some(i=>i.url.endsWith('/file.bin'))});
    assert.equal(messages.filter(m=>m.kind==='file').length,1);
    await page.locator('#fallback').click();
    await until(async()=>{const items=await worker.evaluate(()=>chrome.downloads.search({}));return items.some(i=>i.url.endsWith('/fallback.bin')&&i.state==='complete')});
    assert.equal(messages.filter(m=>m.kind==='file').length,1);
    console.log('Real Chromium normal file capture and failed-transfer browser fallback: OK');
  }finally{
    if(context)await context.close();
    server.closeAllConnections();server.close();fixture.kill();rl.close();
  }
})().catch(e=>{console.error(e);process.exitCode=1});
