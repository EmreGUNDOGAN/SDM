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
// Self-contained: executeScript sends only this function's source.
// Media elements are typed by their tag: most players use blob: or
// extensionless stream addresses, so the page itself is offered instead.
function collectPageLinks() {
  const urls = [];
  for (const a of document.querySelectorAll('a[href]')) urls.push(a.href);
  for (const img of document.querySelectorAll('img')) urls.push(img.currentSrc || img.src);
  for (const el of document.querySelectorAll('video, audio')) {
    const type = el.tagName === 'AUDIO' ? 'Ses' : 'Video';
    const sources = [el.currentSrc, el.src, ...[...el.querySelectorAll('source')].map(s => s.src)].filter(Boolean);
    const direct = sources.filter(src => /^https?:/.test(src));
    for (const src of direct) urls.push([src, type]);
    if (!direct.length) urls.push([location.href, type]);
  }
  // Embedded players SDM's video engine can open as pages.
  const players = [
    /^https:\/\/(www\.)?youtube(-nocookie)?\.com\/embed\//, /^https:\/\/player\.vimeo\.com\/video\//,
    /^https:\/\/(www\.)?dailymotion\.com\/embed\//, /^https:\/\/geo\.dailymotion\.com\/player/,
  ];
  for (const frame of document.querySelectorAll('iframe[src]'))
    if (players.some(pattern => pattern.test(frame.src))) urls.push([frame.src, 'Video']);
  for (const entry of performance.getEntriesByType('resource')) urls.push(entry.name);
  return urls;
}

function groupLinks(urls, pageUrl) {
  const groups = {};
  const seen = new Set();
  for (const item of urls) {
    // A [url, type] pair comes from a media element or player; it may be the page itself.
    const [raw, given] = Array.isArray(item) ? item : [item, null];
    let url;
    try { url = new URL(raw, pageUrl); } catch { continue; }
    if (!['http:', 'https:'].includes(url.protocol)) continue;
    url.hash = '';
    const key = url.href;
    const type = given || scanType(key);
    if (!type || seen.has(key) || (key === pageUrl && !given)) continue;
    seen.add(key);
    (groups[type] ||= []).push(key);
  }
  return groups;
}

function selectedLinks(groups, types) {
  return types.flatMap(type => groups[type] || []).slice(0, SCAN_LIMIT);
}

if (typeof module !== 'undefined') module.exports = {SCAN_TYPES, SCAN_LIMIT, scanType, collectPageLinks, groupLinks, selectedLinks};
