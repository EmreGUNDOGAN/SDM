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
