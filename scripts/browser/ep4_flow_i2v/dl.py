from drv import *
import sys,os
shot=sys.argv[1]
d=D()
try:
    p=d.page
    p.locator('[aria-label="ดาวน์โหลดสื่อ"]').first.click(); p.wait_for_timeout(1200)
    items=p.evaluate(r"""JSON.stringify([...document.querySelectorAll('[role=menuitem], button[role=menuitem]')].map(e=>e.innerText.replace(/\s+/g,' ').trim()))""")
    print("menu:",items)
    it=p.get_by_role("menuitem").filter(has_text="720p").first
    txt=it.inner_text().replace("\n"," ")
    assert "เครดิต" not in txt and "4K" not in txt, txt
    print("clicking:",txt)
    with p.expect_download(timeout=90000) as dl:
        it.click()
    f=dl.value
    out=f"C:/mooniex/ep4s/clips/EP04-S{shot}_v1.mp4"
    f.save_as(out); print("saved",out,os.path.getsize(out))
finally: d.close()
