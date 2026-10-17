// Obrázky vymyšlené vzorové ukázky Klíč a kolo do dopisu (počítač a mobil), čas pevně úterý 20. 10. 2026 10:00 v Praze.
const pw=require('playwright');const fs=require('fs');const path=require('path');
(async()=>{
 const exe=fs.existsSync('/opt/pw-browsers/chromium')&&fs.statSync('/opt/pw-browsers/chromium').isFile()?'/opt/pw-browsers/chromium':undefined;
 const b=await pw.chromium.launch({executablePath:exe});
 const url='file://'+path.join(__dirname,'..','..','ukazky','klic-a-kolo','index.html');
 for(const [name,w,h,dpr,mobile,clipH] of [['vzor-mobil-crop',390,844,3,true,593],['vzor-pc-crop',1280,800,2,false,685]]){
  const ctx=await b.newContext({viewport:{width:w,height:h},deviceScaleFactor:dpr,isMobile:mobile,hasTouch:mobile,timezoneId:'Europe/Prague',locale:'cs-CZ'});
  const p=await ctx.newPage();await p.clock.setFixedTime(new Date('2026-10-20T10:00:00+02:00'));
  await p.goto(url);await p.waitForTimeout(600);
  await p.screenshot({path:path.join(__dirname,name+'.png'),clip:{x:0,y:0,width:w,height:clipH}});await ctx.close();
 }
 await b.close();console.log('hotovo');})();
