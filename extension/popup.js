const status=document.getElementById('status');
chrome.storage.local.get('sdmReloadNotice').then(value=>{if(value.sdmReloadNotice)status.textContent=value.sdmReloadNotice;});
document.getElementById('refresh').onclick=async()=>{
  status.textContent='Yeni dosyalar doğrulanıyor…';
  try {
    const reply=await chrome.runtime.sendMessage({type:'extension-refresh'});
    if(reply.error)throw Error(reply.error);
    status.textContent=`${reply.result.version} doğrulandı. Eklenti yeniden yükleniyor…`;
  }catch(error){status.textContent=error.message;}
};
async function control(body){
  status.textContent='Kaydediliyor…';
  try {
    const reply=await chrome.runtime.sendMessage({type:'control',body});
    if(reply.error)throw Error(reply.error);
    status.textContent='Tercihin kaydedildi.';
  }catch(error){status.textContent=error.message;}
}
for(const button of document.querySelectorAll('[data-minutes]'))button.onclick=()=>control({minutes:Number(button.dataset.minutes)});
document.getElementById('exclude').onclick=async()=>{
  const tab=(await chrome.tabs.query({active:true,currentWindow:true}))[0];
  try {await control({exclude:new URL(tab.url).hostname});}catch{status.textContent='Bu sayfa için site tercihi değiştirilemiyor.';}
};

// Page scan: list this tab's files by type, send the ticked types to SDM's batch window.
let scanned={},scannedPage='';
const found=document.getElementById('found'),send=document.getElementById('send');
function ticked(){return [...found.querySelectorAll('input:checked')].map(box=>box.value);}
function updateSend(){
  const count=selectedLinks(scanned,ticked()).length;
  send.hidden=!Object.keys(scanned).length;send.disabled=!count;
  send.textContent=count?`SDM’ye gönder (${count})`:'Tür seç';
}
document.getElementById('scan').onclick=async()=>{
  status.textContent='Sayfa taranıyor…';found.replaceChildren();scanned={};
  try {
    const tab=(await chrome.tabs.query({active:true,currentWindow:true}))[0];
    const [result]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:collectPageLinks});
    scannedPage=tab.url;scanned=groupLinks(result.result||[],tab.url);
    for(const [type] of SCAN_TYPES){
      const links=scanned[type];if(!links)continue;
      const row=document.createElement('label');const box=document.createElement('input');
      box.type='checkbox';box.value=type;box.checked=type!=='Resim';box.onchange=updateSend;
      const name=document.createElement('span');name.append(box,' '+type);
      const count=document.createElement('span');count.textContent=String(links.length);
      row.append(name,count);found.append(row);
    }
    status.textContent=found.childElementCount?'İndirmek istediğin türleri seç.':'Bu sayfada indirilebilir dosya bulunamadı.';
  }catch{status.textContent='Bu sayfa taranamıyor (tarayıcı veya mağaza sayfası olabilir).';}
  updateSend();
};
send.onclick=async()=>{
  const urls=selectedLinks(scanned,ticked());
  status.textContent='SDM’ye gönderiliyor…';
  try {
    const reply=await chrome.runtime.sendMessage({type:'batch',body:{urls,source_url:scannedPage}});
    if(reply.error)throw Error(reply.error);
    status.textContent=`${reply.result.count} bağlantı SDM’de seçime açıldı.`+(urls.length===SCAN_LIMIT?` (İlk ${SCAN_LIMIT})`:'');
  }catch(error){status.textContent=error.message;}
};
