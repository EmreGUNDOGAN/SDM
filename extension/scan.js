// Page scanner: runs only when the user presses "Bu sayfayı tara" (activeTab),
// so the extension needs no access to every site.
const SCAN_TYPES = [
  ['Video', ['mp4', 'mkv', 'webm', 'mov', 'avi', 'm4v', 'm3u8', 'mpd']],
  ['Ses', ['mp3', 'm4a', 'ogg', 'oga', 'opus', 'wav', 'flac', 'aac']],
  ['Belge', ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'epub']],
  ['Arşiv', ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'iso']],
  ['Program', ['exe', 'msi', 'apk', 'dmg', 'deb', 'rpm']],
  ['Resim', ['jpg', 'jpeg', 'png', 'gif', 'webp', 'avif']],
];
const SCAN_LIMIT = 200;  // browser_bridge.BATCH_LIMIT

function scanType(url) {
  let path;
  try { path = new URL(url).pathname.toLowerCase(); } catch { return null; }
  const ext = path.includes('.') ? path.split('.').pop() : '';
  const found = SCAN_TYPES.find(([, list]) => list.includes(ext));
  return found ? found[0] : null;
}

// Injected into the page: links, media elements and media the page already
// loaded (resource timing catches audio/HLS that has no <a> or <audio src>).
function collectPageLinks() {
  const urls = [];
  for (const a of document.querySelectorAll('a[href]')) urls.push(a.href);
  for (const el of document.querySelectorAll('video, audio, source, img')) urls.push(el.currentSrc || el.src);
  for (const entry of performance.getEntriesByType('resource')) urls.push(entry.name);
  return urls;
}

function groupLinks(urls, pageUrl) {
  const groups = {};
  const seen = new Set();
  for (const raw of urls) {
    let url;
    try { url = new URL(raw, pageUrl); } catch { continue; }
    if (!['http:', 'https:'].includes(url.protocol)) continue;
    url.hash = '';
    const key = url.href;
    const type = scanType(key);
    if (!type || seen.has(key) || key === pageUrl) continue;
    seen.add(key);
    (groups[type] ||= []).push(key);
  }
  return groups;
}

function selectedLinks(groups, types) {
  return types.flatMap(type => groups[type] || []).slice(0, SCAN_LIMIT);
}

if (typeof module !== 'undefined') module.exports = {SCAN_TYPES, SCAN_LIMIT, scanType, collectPageLinks, groupLinks, selectedLinks};
