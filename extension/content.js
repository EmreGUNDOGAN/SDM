(() => {
  if (window.top !== window || document.getElementById('sdm-video-overlay')) return;
  const host = document.createElement('div');
  host.id = 'sdm-video-overlay';
  host.style.cssText = 'position:fixed;z-index:2147483647;display:none;font:13px Inter,Segoe UI,sans-serif;';
  const root = host.attachShadow({mode: 'open'});
  root.innerHTML = `<style>
    @font-face{font-family:Inter;src:url('${chrome.runtime.getURL('fonts/Inter-Regular.ttf')}')}@font-face{font-family:Inter;font-weight:600;src:url('${chrome.runtime.getURL('fonts/Inter-SemiBold.ttf')}')}
    *{box-sizing:border-box}button{font:600 13px Inter,Segoe UI,sans-serif;cursor:pointer;border:0;border-radius:10px;padding:10px 14px}
    button:focus-visible{outline:2px solid #2156d9;outline-offset:2px}
    #toggle{color:#fff;background:#2156d9;box-shadow:0 6px 20px #0f172a29;display:flex;align-items:center;gap:8px}
    #panel{margin-top:8px;width:380px;padding:16px;border-radius:14px;background:#fff;color:#111827;box-shadow:0 12px 32px #0f172a29;border:1px solid #e5e8ec;max-height:70vh;overflow:auto}
    #title{font-size:14px;font-weight:600;margin:0 0 10px;overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
    #status{font-size:12px;white-space:pre-wrap;color:#5b6472;margin:8px 0}
    #tabs{display:flex;padding:3px;border-radius:10px;background:#f1f3f6;gap:3px}#tabs button{flex:1;background:transparent;color:#5b6472}#tabs button[aria-selected=true]{background:#fff;color:#111827;box-shadow:0 1px 3px #0001}
    #choices{margin-top:10px}#choices button{display:flex;align-items:center;justify-content:space-between;gap:12px;width:100%;text-align:left;background:#fff;color:#1f2937;margin-top:4px;font-weight:400;min-height:48px}
    #choices button:hover{background:#eef3fe}#choices button.recommended{background:#eef3fe;color:#1a44ad}
    #foot{margin-top:12px;padding:10px;border-radius:8px;background:#f6f7f9;color:#5b6472;font-size:11px;line-height:1.5}
    button:disabled{opacity:.55;cursor:wait}[hidden]{display:none!important}
  </style><button id="toggle"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/></svg>SDM ile indir</button><div id="panel" hidden><p id="title">Video kalitesi</p><div id="tabs" role="tablist"><button id="video-tab" role="tab" aria-selected="true">Video</button><button id="audio-tab" role="tab" aria-selected="false">Yalnız ses (MP3)</button></div><div id="status" aria-live="polite"></div><div id="choices"></div><div id="foot">Boyutlar tahminidir. Ses ve görüntü MKV olarak birleştirilir.</div></div>`;
  document.documentElement.append(host);
  const toggle = root.getElementById('toggle'), panel = root.getElementById('panel');
  const status = root.getElementById('status'), choices = root.getElementById('choices');
  let previousUrl = '', busy = false, mediaMode = 'video';
  function setMode(mode){mediaMode=mode;for(const button of choices.children)button.hidden=button.dataset.media!==mode;root.getElementById('video-tab').setAttribute('aria-selected',String(mode==='video'));root.getElementById('audio-tab').setAttribute('aria-selected',String(mode==='audio'));root.getElementById('foot').textContent=mode==='audio'?'Boyutlar tahminidir. Ses MP3 olarak kaydedilir.':'Boyutlar tahminidir. Ses ve görüntü MKV olarak birleştirilir.';}
  root.getElementById('video-tab').onclick=()=>setMode('video');root.getElementById('audio-tab').onclick=()=>setMode('audio');
  document.addEventListener('pointerdown', event => {
    if (!panel.hidden && !event.composedPath().includes(host)) panel.hidden = true;
  }, true);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') panel.hidden = true;
  });
  const pageUrl = () => location.href;
  // YouTube Music: MP3 only, quality picked here, added to SDM without a dialog.
  const MUSIC = location.hostname === 'music.youtube.com';
  const MUSIC_BITRATES = [320, 256, 192, 128], MUSIC_DEFAULT = 192;
  function musicPage() {
    const query = new URLSearchParams(location.search);
    return {song: query.get('v'), list: query.get('list'), albumPage: location.pathname === '/playlist'};
  }
  if (MUSIC) {
    toggle.lastChild.textContent = 'SDM ile MP3';
    root.getElementById('tabs').hidden = true;
    host.style.flexDirection = 'column-reverse';  // the menu opens upwards, above the player bar
  }
  async function send(message) {
    const reply = await chrome.runtime.sendMessage(message);
    if (!reply || reply.error) throw new Error(reply?.error || 'SDM eklentisi yanıt vermedi');
    return reply.result;
  }
  function choice(label, height, audio, filesize=0, recommended=false) {
    const button = document.createElement('button');
    button.textContent = label;
    button.dataset.media=audio?'audio':'video';button.hidden=button.dataset.media!==mediaMode;
    if(recommended)button.className='recommended';
    button.onclick = async (event) => {
      if (!event.isTrusted) return;
      if (busy) return;
      busy = true; button.disabled = true; status.textContent = 'SDM’ye gönderiliyor…';
      try {
        await send({type: 'download', url: pageUrl(), height, audio,filesize,title:root.getElementById('title').textContent});
        status.textContent = 'SDM’de indirme seçim penceresi açıldı.';
        panel.hidden = true;
      } catch(error) { status.textContent = error.message; }
      finally { busy = false; button.disabled = false; }
    };
    choices.append(button);
  }
  function musicChoices() {
    const page = musicPage();
    root.getElementById('title').textContent = document.title.replace(/ - YouTube Music$/, '') || 'YouTube Music';
    let whole = null;
    if (page.list) {
      const row = document.createElement('label');whole = document.createElement('input');
      whole.type = 'checkbox';whole.checked = page.albumPage || !page.song;whole.disabled = !page.song;
      row.append(whole, ' Albümün / listenin tamamı');row.style.cssText = 'display:flex;gap:8px;align-items:center;margin:4px 0 6px';
      choices.append(row);
    }
    for (const bitrate of MUSIC_BITRATES) {
      const button = document.createElement('button');
      button.textContent = `MP3 · ${bitrate} kb/sn` + (bitrate === MUSIC_DEFAULT ? ' · önerilen' : '');
      if (bitrate === MUSIC_DEFAULT) button.className = 'recommended';
      button.onclick = async (event) => {
        if (!event.isTrusted || busy) return;
        const list = Boolean(whole && whole.checked);
        const url = list ? `https://music.youtube.com/playlist?list=${encodeURIComponent(page.list)}`
          : `https://music.youtube.com/watch?v=${encodeURIComponent(page.song)}`;
        busy = true; button.disabled = true; status.textContent = 'SDM’ye gönderiliyor…';
        try {
          await send({type: 'music', url, bitrate, list});
          status.textContent = list ? 'Liste SDM’de açılıyor; parçalar sırayla eklenecek.' : 'SDM indirmeye ekledi.';
        } catch(error) { status.textContent = error.message; }
        finally { busy = false; button.disabled = false; }
      };
      choices.append(button);
    }
    root.getElementById('foot').textContent = 'Sanatçı / Albüm klasörüne, etiket ve kapakla kaydedilir.';
    status.textContent = 'Ses kalitesini seç.';
  }
  async function openPicker() {
    if (!panel.hidden) { panel.hidden = true; return; }
    if (MUSIC) { panel.hidden = false; choices.replaceChildren(); musicChoices(); return; }
    panel.hidden = false; choices.replaceChildren();setMode('video');
    status.textContent = 'Videodaki kullanılabilir kaliteler alınıyor…'; toggle.disabled = true;
    try {
      const info = await send({type: 'formats', url: pageUrl()});
      root.getElementById('title').textContent = info.title;
      const preferred=info.qualities.find(q=>q.height===1080)||info.qualities.find(q=>q.height<=1080)||info.qualities[0];
      for (const quality of info.qualities) {
        const size = quality.filesize ? ' · ~'+(quality.filesize/1024/1024).toFixed(0)+' MB' : '';
        choice(quality.label + ' · Video + ses'+(quality===preferred?' · önerilen':'')+size, quality.height, false,quality.filesize,quality===preferred);
      }
      if (info.audio) choice('Yalnızca ses · MP3'+(info.audio_filesize?' · ~'+(info.audio_filesize/1024/1024).toFixed(0)+' MB':''), null, true,info.audio_filesize||0);
      if(!info.qualities.length&&info.audio)setMode('audio');
      status.textContent = choices.childElementCount ? 'İndirmek istediğin kaliteyi seç.' : 'İndirilebilir format bulunamadı.';
    } catch(error) { status.textContent = error.message; }
    finally { toggle.disabled = false; }
  }
  toggle.onclick = event=>{if(event.isTrusted)openPicker();};
  chrome.runtime.onMessage.addListener(message=>{
    if(message.type==='sdm-open-picker') {panel.hidden=true;openPicker();}
    if(message.type==='sdm-error') {panel.hidden=false;status.textContent=message.message;}
  });
  function position() {
    if (previousUrl !== pageUrl()) { panel.hidden = true; previousUrl = pageUrl(); }
    if (MUSIC) {
      // Songs often play behind cover art with no visible <video>; anchor above the player bar.
      const page = musicPage();
      host.style.display = page.song || (page.albumPage && page.list) ? 'flex' : 'none';
      host.style.top = 'auto';host.style.bottom = '96px';host.style.right = '24px';
      panel.style.maxWidth = Math.min(380, innerWidth - 24) + 'px';
      return;
    }
    const videos = [...document.querySelectorAll('video')].filter(video => {
      const r = video.getBoundingClientRect();
      return r.width > 180 && r.height > 100 && r.bottom > 0 && r.top < innerHeight;
    });
    videos.sort((a,b) => b.clientWidth*b.clientHeight - a.clientWidth*a.clientHeight);
    if (!videos.length) { host.style.display = 'none'; return; }
    const r = videos[0].getBoundingClientRect();
    host.style.display = 'block';
    host.style.top = Math.max(8, r.top + 12) + 'px';
    host.style.right = Math.max(8, innerWidth - r.right + 12) + 'px';
    // Keep the menu within the player viewport on smaller screens.
    panel.style.maxWidth = Math.min(380, innerWidth - 24) + 'px';
  }
  setInterval(position, 700);
  addEventListener('scroll', position, {passive:true});
  addEventListener('resize', position, {passive:true});
  addEventListener('fullscreenchange', () => {
    const full = document.fullscreenElement;
    if (full && full.tagName !== 'VIDEO') full.append(host);
    else document.documentElement.append(host);
    position();
  });
  position();
})();
