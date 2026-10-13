const status=document.getElementById('status');
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
