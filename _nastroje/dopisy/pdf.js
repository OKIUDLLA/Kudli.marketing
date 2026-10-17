const pw=require('playwright');const fs=require('fs');const path=require('path');
(async()=>{
 const exe=fs.existsSync('/opt/pw-browsers/chromium')&&fs.statSync('/opt/pw-browsers/chromium').isFile()?'/opt/pw-browsers/chromium':undefined;
 const b=await pw.chromium.launch({executablePath:exe});const p=await b.newPage();const errs=[];
 p.on('pageerror',e=>errs.push(e.message));p.on('requestfailed',r=>errs.push('fail '+r.url()));
 const dir=path.join(__dirname,'html');fs.mkdirSync(path.join(__dirname,'pdf'),{recursive:true});
 for(const f of fs.readdirSync(dir).filter(x=>x.endsWith('.html')).sort()){
  await p.goto('file://'+path.join(dir,f));await p.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(i=>i.complete?1:new Promise(r=>{i.onload=i.onerror=r;})));});
  const info=await p.evaluate(()=>{const t=document.querySelector('.text').getBoundingClientRect();const u=document.querySelector('.ukazka').getBoundingClientRect();const font=getComputedStyle(document.body).fontFamily;return {textBottomMM:(t.bottom/96*25.4).toFixed(1),ukazkaTopMM:(u.top/96*25.4).toFixed(1),imgs:[...document.images].map(i=>i.naturalWidth),font};});
  await p.pdf({path:path.join(__dirname,'pdf',f.replace('.html','.pdf')),preferCSSPageSize:true,printBackground:true});
  console.log(f,JSON.stringify(info));
 }
 console.log(errs.length?errs.join('\n'):'NO_ERRORS');await b.close();})();
