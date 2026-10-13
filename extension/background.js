const HOST = 'com.sdm.bridge';
let connection;
let connecting;

async function connect() {
  if (connection) return connection;
  if (!connecting) connecting = chrome.runtime.sendNativeMessage(HOST, {action: 'connect'})
    .then(value => {
      if (!value.token || value.port !== 49282) throw new Error('SDM bağlantısı kurulamadı. Setup paketini yeniden çalıştırın.');
      connection = value;
      return value;
    }).finally(() => { connecting = null; });
  return connecting;
}

async function request(path, body) {
  const config = await connect();
  let response;
  // Native host may have just started the app. Retry only connection failures.
  for (let attempt = 0; attempt < 25; attempt++) {
    try {
      response = await fetch(`http://127.0.0.1:${config.port}${path}`, {
        method: 'POST', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${config.token}`},
        body: JSON.stringify(body), signal: AbortSignal.timeout(90000)
      });
      break;
    } catch (error) {
      if (attempt === 24) { connection = null; throw new Error('SDM açılamadı. Uygulamayı açıp tekrar deneyin.'); }
      await new Promise(resolve => setTimeout(resolve, 300));
    }
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'SDM isteği başarısız');
  return result;
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (sender.id === chrome.runtime.id && sender.url?.startsWith(chrome.runtime.getURL('')) && ['control','settings'].includes(message.type)) {
    request(message.type === 'control' ? '/capture-control' : '/settings', message.body || {})
      .then(result=>respond({result})).catch(error=>respond({error:error.message}));
    return true;
  }
  if (!sender.tab || sender.id !== chrome.runtime.id || !['formats', 'download'].includes(message.type)) return;
  try {
    const page = new URL(sender.url);
    const url = new URL(message.url);
    if (!['https:', 'http:'].includes(url.protocol) || page.origin !== url.origin) throw new Error('Geçersiz sayfa');
  } catch { respond({error: 'Geçersiz sayfa'}); return; }
  const body = message.type === 'formats' ? {url: message.url}
    : {url: message.url, height: message.height, audio: message.audio === true, title:message.title, filesize:message.filesize};
  request('/' + message.type, body).then(result => respond({result})).catch(error => respond({error: error.message}));
  return true;
});

// Pause first, transfer only after the app preflights and accepts the URL.
// If transfer fails, resume the original browser download. No cookies are read.
const capturing = new Set();
function excluded(url, domains) {
  try { const host = new URL(url).hostname.toLowerCase(); return domains.some(d=>host===d || host.endsWith('.'+d)); }
  catch { return false; }
}
async function waitDecision(ticket) {
  if (!ticket) throw new Error('SDM güncellenmeli');
  for (let attempt=0;attempt<900;attempt++) {
    const result = await request('/decision',{ticket});
    if (result.action !== 'pending') return result.action;
    await new Promise(resolve=>setTimeout(resolve,1000));
  }
  throw new Error('Seçim zaman aşımına uğradı');
}
if (chrome.downloads?.onCreated) chrome.downloads.onCreated.addListener(item => {
  if (item.state !== 'in_progress' || !/^https?:\/\//i.test(item.finalUrl || item.url)) return;
  (async () => {
    let paused = false;
    try {
      const tab = (await chrome.tabs.query({active:true,lastFocusedWindow:true}))[0];
      const source = item.referrer || tab?.url || '';
      if (excluded(source,['canva.com']) || excluded(item.finalUrl || item.url,['canva.com'])) return;
      const current = (await chrome.downloads.search({id:item.id}))[0];
      if (!current || current.state !== 'in_progress' || current.paused) return;
      capturing.add(item.id);
      await chrome.downloads.pause(item.id);
      paused = true;
      const settings = await request('/settings', {});
      if (!settings.capture || excluded(source,settings.excluded_sites || []) || excluded(tab?.url,settings.excluded_sites || [])) {
        await chrome.downloads.resume(item.id);return;
      }
      const ext = (item.filename || new URL(item.url).pathname).split('.').pop().toLowerCase();
      if (settings.capture_extensions?.length && !settings.capture_extensions.includes(ext)) {
        await chrome.downloads.resume(item.id);return;
      }
      const result = await request('/file', {url:item.finalUrl || item.url, source_url:source,filename:item.filename});
      const action = await waitDecision(result.ticket);
      if (action === 'browser') { await chrome.downloads.resume(item.id); return; }
      await chrome.downloads.cancel(item.id);
      await chrome.downloads.erase({id:item.id});
    } catch (error) {
      if (paused) {
        try { await chrome.downloads.resume(item.id); } catch { /* browser may have completed or user cancelled */ }
      }
    } finally { capturing.delete(item.id); }
  })();
});

chrome.runtime.onInstalled.addListener(()=>{
  chrome.contextMenus.removeAll(()=>{
    chrome.contextMenus.create({id:'sdm-download',title:'SDM ile indir',contexts:['video','audio','link']});
    chrome.contextMenus.create({id:'sdm-exclude',title:'Bu sitede SDM yakalamasını kapat',contexts:['page']});
  });
});
chrome.contextMenus.onClicked.addListener(async (info,tab)=>{
  try {
    if(info.menuItemId==='sdm-exclude') {
      await request('/capture-control',{exclude:new URL(info.pageUrl || tab.url).hostname}); return;
    }
    if(info.menuItemId!=='sdm-download') return;
    const page=info.pageUrl || tab.url;
    const supported=/^https?:\/\/(?:[^/]+\.)?(youtube\.com|youtu\.be|vimeo\.com|dailymotion\.com|tiktok\.com|instagram\.com|x\.com|twitter\.com|facebook\.com|twitch\.tv|soundcloud\.com)(?:\/|$)/i.test(page);
    if(supported && info.mediaType) {
      await chrome.tabs.sendMessage(tab.id,{type:'sdm-open-picker'});
    } else {
      await request('/file',{url:info.linkUrl || info.srcUrl,source_url:page});
    }
  } catch(error) {
    try {await chrome.tabs.sendMessage(tab.id,{type:'sdm-error',message:error.message});} catch {}
  }
});
