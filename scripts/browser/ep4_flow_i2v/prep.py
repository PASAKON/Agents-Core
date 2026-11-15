from drv import *
import re,sys
shot=sys.argv[1]
sheet=open("C:/mooniex/ep4s/EP04-FULL-SHEET.md",encoding="utf-8").read()
blk=re.search(r"## EP04-S%s \|.*?(?=\n## EP04-S|\Z)"%shot,sheet,re.S).group(0)
body=re.search(r"Google Flow prompt \(15s\): (.*?)\n\nLines:",blk,re.S).group(1).strip()
FIRST="The attached first frame is the preparatory pose at second 0; keep its characters, costume, room and lighting exactly, and animate forward from it. "
prompt=FIRST+body
assert "blush" not in prompt.lower() and "red face" not in prompt.lower()
open(f"C:/mooniex/ep4s/prompt_S{shot}.txt","w",encoding="utf-8").write(prompt)
d=D()
try:
    p=d.page
    # open start picker if empty
    picker=p.evaluate("!!document.querySelector('.cdk-overlay-container .asset-item')")
    if picker or p.locator("button.empty-chip").count():
        if not picker:
            p.locator("button.empty-chip").first.click(timeout=8000); p.wait_for_timeout(1500)
        row=p.locator(".cdk-overlay-container .asset-item").filter(has_text=f"EP04-S{shot}.png").first
        row.click(); p.wait_for_timeout(1200)
        p.locator(".cdk-overlay-container").get_by_text("เพิ่มไปยังพรอมต์").last.click(); p.wait_for_timeout(2000)
    print("overlay open:",p.evaluate("!!document.querySelector('.cdk-overlay-container .asset-item')"))
    print("empty chips:",p.locator("button.empty-chip").count())
    # prompt
    ed=p.locator("[contenteditable=true]").first
    ed.click(); p.wait_for_timeout(300)
    p.evaluate("(()=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('selectAll'); document.execCommand('delete')})()")
    p.evaluate("t=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('insertText',false,t)}",prompt)
    p.wait_for_timeout(800)
    got=p.evaluate("[...document.querySelectorAll('[contenteditable=true] p')].map(x=>x.innerText).join(' ')")
    import re as _r; print("prompt ok:",_r.sub(r"s+"," ",got).strip()==_r.sub(r"s+"," ",prompt).strip(),len(got),len(prompt))
    print("frame imgs:",p.evaluate("[...document.querySelectorAll('flow-prompt-box img, .frame-trigger img')].map(i=>i.alt+'|'+(i.naturalWidth)).slice(0,6)"))
finally: d.close()
