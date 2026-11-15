from drv import *
import re
d=D()
try:
    p=d.page
    res=p.evaluate(r"""(()=>{
      const out=[]; const seen=new Set();
      const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
      let n; while(n=walker.nextNode()){ if(n.textContent.includes('The attached first frame')){
        let e=n.parentElement, best=e;
        for(let i=0;i<10&&e;i++){ const c=(e.innerText.match(/The attached first frame/g)||[]).length; if(c===1) best=e; else break; e=e.parentElement; }
        if(seen.has(best)) continue; seen.add(best);
        const t=best.innerText.replace(/\n+/g,' | ');
        const href=(best.querySelector('a')||{}).getAttribute? (best.querySelector('a').getAttribute('href')||'').slice(0,8):'';
        out.push({scene: t.includes('Family backroom')?'S042':(t.includes('At the back gate')?'S067':(t.includes('ghost-market')?'S109':'?')), head:t.slice(0,60), tail:t.slice(-200), hasVideo: !!best.querySelector('video'), imgs: best.querySelectorAll('img').length, href});
      }}
      return JSON.stringify(out)})()""")
    import json
    for c in json.loads(res): print(c['scene'],'|',c['head'],'|',c['tail'],'|video',c['hasVideo'],'imgs',c['imgs'],c['href']); print('--')
finally: d.close()
