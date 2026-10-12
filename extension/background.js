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
  if (!sender.tab || sender.id !== chrome.runtime.id || !['formats', 'download'].includes(message.type)) return;
  try {
    const page = new URL(sender.url);
    const url = new URL(message.url);
    if (!['https:', 'http:'].includes(url.protocol) || page.origin !== url.origin) throw new Error('Geçersiz sayfa');
  } catch { respond({error: 'Geçersiz sayfa'}); return; }
  const body = message.type === 'formats' ? {url: message.url}
    : {url: message.url, height: message.height, audio: message.audio === true};
  request('/' + message.type, body).then(result => respond({result})).catch(error => respond({error: error.message}));
  return true;
});

// Pause first, transfer only after the app preflights and accepts the URL.
// If transfer fails, resume the original browser download. No cookies are read.
const capturing = new Set();
if (chrome.downloads?.onCreated) chrome.downloads.onCreated.addListener(item => {
  if (item.state !== 'in_progress' || !/^https?:\/\//i.test(item.finalUrl || item.url)) return;
  (async () => {
    let paused = false;
    try {
      const settings = await request('/settings', {});
      if (!settings.capture) return;
      const current = (await chrome.downloads.search({id:item.id}))[0];
      if (!current || current.state !== 'in_progress' || current.paused) return;
      capturing.add(item.id);
      await chrome.downloads.pause(item.id);
      paused = true;
      await request('/file', {url:item.finalUrl || item.url});
      await chrome.downloads.cancel(item.id);
      await chrome.downloads.erase({id:item.id});
    } catch (error) {
      if (paused) {
        try { await chrome.downloads.resume(item.id); } catch { /* browser may have completed or user cancelled */ }
      }
    } finally { capturing.delete(item.id); }
  })();
});
