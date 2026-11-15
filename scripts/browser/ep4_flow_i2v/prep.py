from drv import *
import re,sys
shot=sys.argv[1]
sheet=open("C:/mooniex/ep4s/EP04-FULL-SHEET.md",encoding="utf-8").read()
blk=re.search(r"## EP04-S%s \|.*?(?=\n## EP04-S|\Z)"%shot,sheet,re.S).group(0)
body=re.search(r"Google Flow prompt \(15s\): (.*?)\n\nLines:",blk,re.S).group(1).strip()
FIRST="The attached first frame is the preparatory pose at second 0; keep its characters, costume, room and lighting exactly, and animate forward from it. "
# task-255aea73 prompt fixes (from the 3-shot test), appended to every prompt
SUFFIX=" No glowing objects, no orbs, no magic light, no supernatural effects unless the shot names them. No signs, banners, plaques or written marks anywhere in frame. Do not swing the camera away from the described action; keep the subject leading as described."
prompt=FIRST+body+SUFFIX
assert "blush" not in prompt.lower() and "red face" not in prompt.lower()
open(f"C:/mooniex/ep4s/prompt_S{shot}.txt","w",encoding="utf-8").write(prompt)
d=D()
try:
    p=d.page
    p.evaluate("document.querySelectorAll('.cdk-overlay-container .cdk-overlay-backdrop').length&&document.body.click()")
    # 1. clear a filled start slot (clicking a filled chip removes its image)
    start=p.locator(".frame-trigger").first
    if start.locator("img.chip-image").count():
        start.locator("button.chip-container").click(); p.wait_for_timeout(1000)
    assert not start.locator("img.chip-image").count(), "start slot would not clear"
    # 2. the end slot must be empty too
    endf=p.locator(".frame-trigger").nth(1)
    if endf.locator("img.chip-image").count():
        endf.locator("button.chip-container").click(); p.wait_for_timeout(1000)
    # 3. open the START picker (the chip labelled เริ่ม, never the end chip)
    start.locator("button.empty-chip").click(timeout=8000); p.wait_for_timeout(1500)
    # the picker list is virtualised (15 rows): filter with its search box first
    sb=p.locator('.cdk-overlay-container input[placeholder="ค้นหาเนื้อหา"]').first
    sb.fill(f"EP04-S{shot}"); p.wait_for_timeout(1800)
    row=p.locator(".cdk-overlay-container .asset-item").filter(has_text=f"EP04-S{shot}.png").first
    row.click(); p.wait_for_timeout(1500)
    add=p.locator(".cdk-overlay-container").get_by_text("เพิ่มไปยังพรอมต์")
    if add.count(): add.last.click(); p.wait_for_timeout(2000)
    print("overlay open:",p.evaluate("!!document.querySelector('.cdk-overlay-container .asset-item')"))
    slots=p.evaluate("JSON.stringify([...document.querySelectorAll('.frame-trigger')].map(e=>!!e.querySelector('img.chip-image')))")
    print("slots:",slots); assert slots=="[true,false]","slots not start-only"
    # save the start-slot image so verify.py can match it against the still
    src=p.evaluate("document.querySelector('.frame-trigger img.chip-image').src")
    open("C:/mooniex/ep4s/chip.bin","wb").write(d.ctx.request.get(src).body())
    # 4. prompt
    ed=p.locator("[contenteditable=true]").first
    ed.click(); p.wait_for_timeout(300)
    p.evaluate("(()=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('selectAll'); document.execCommand('delete')})()")
    p.evaluate("t=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('insertText',false,t)}",prompt)
    p.wait_for_timeout(800)
    got=p.evaluate("[...document.querySelectorAll('[contenteditable=true] p')].map(x=>x.innerText).join(' ')")
    import re as _r; print("prompt ok:",_r.sub(r"\s+"," ",got).strip()==_r.sub(r"\s+"," ",prompt).strip(),len(got),len(prompt))
finally: d.close()
