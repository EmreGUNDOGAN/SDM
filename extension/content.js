(() => {
  if (window.top !== window || document.getElementById('sdm-video-overlay')) return;
  const host = document.createElement('div');
  host.id = 'sdm-video-overlay';
  host.style.cssText = 'position:fixed;z-index:2147483647;display:none;font:13px system-ui;';
  const root = host.attachShadow({mode: 'open'});
  root.innerHTML = `<style>
    *{box-sizing:border-box}button{font:600 13px system-ui;cursor:pointer;border:0;border-radius:8px;padding:9px 12px}
    #toggle{color:white;background:#10244d;box-shadow:0 2px 12px #0005;border:1px solid #70dfff}
    #panel{margin-top:6px;width:250px;padding:12px;border-radius:12px;background:#fff;color:#17233b;box-shadow:0 5px 25px #0005;border:1px solid #dde5ed;max-height:380px;overflow:auto}
    #title{font-weight:600;margin:0 0 8px;overflow-wrap:anywhere}#status{font-size:12px;white-space:pre-wrap;color:#59667b}
    #choices button{display:block;width:100%;text-align:left;background:#edf5ff;color:#10244d;margin-top:5px}
    #choices button:hover{background:#d9ecff}button:disabled{opacity:.6;cursor:wait}[hidden]{display:none!important}
  </style><button id="toggle">↓ SDM ile indir</button><div id="panel" hidden><p id="title">Video kalitesi</p><div id="status"></div><div id="choices"></div></div>`;
  document.documentElement.append(host);
  const toggle = root.getElementById('toggle'), panel = root.getElementById('panel');
  const status = root.getElementById('status'), choices = root.getElementById('choices');
  let previousUrl = '', busy = false;
  document.addEventListener('pointerdown', event => {
    if (!panel.hidden && !event.composedPath().includes(host)) panel.hidden = true;
  }, true);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') panel.hidden = true;
  });
  const pageUrl = () => location.href;
  async function send(message) {
    const reply = await chrome.runtime.sendMessage(message);
    if (!reply || reply.error) throw new Error(reply?.error || 'SDM eklentisi yanıt vermedi');
    return reply.result;
  }
  function choice(label, height, audio, filesize=0) {
    const button = document.createElement('button');
    button.textContent = label;
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
  async function openPicker() {
    if (!panel.hidden) { panel.hidden = true; return; }
    panel.hidden = false; choices.replaceChildren();
    status.textContent = 'Videodaki kullanılabilir kaliteler alınıyor…'; toggle.disabled = true;
    try {
      const info = await send({type: 'formats', url: pageUrl()});
      root.getElementById('title').textContent = info.title;
      for (const quality of info.qualities) {
        const size = quality.filesize ? ' · ~'+(quality.filesize/1024/1024).toFixed(0)+' MB' : '';
        choice(quality.label + ' · Video + ses'+size, quality.height, false,quality.filesize);
      }
      if (info.audio) choice('Yalnızca ses · MP3', null, true);
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
    panel.style.maxWidth = Math.min(250, innerWidth - 24) + 'px';
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
