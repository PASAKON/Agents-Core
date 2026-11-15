EP04 Omni 1.2 Flash image-to-video test (task-77b20e0f). Run ON winbox with /c/mooniex/pwvenv python (Playwright), Chrome :9226 signed in, a Flow project tab open.
Scratch dir C:/mooniex/ep4s holds the EP04-FULL-SHEET.md copy, stills/ and clips/ (paths are hard-coded; edit them).
- drv.py   : attach over CDP, own tab (window.name=ep4s_op)
- prep.py <S###> : builds the prompt from the sheet ("Google Flow prompt (15s)" line + first-frame sentence), picks the still in the START slot via the frame picker, types the prompt, reads it back.
  Stills are uploaded beforehand via add-media menu -> อัปโหลด (file chooser), see tools/flow_upload_element.py.
- fire.py <S###> : asserts prompt, start-only slots [true,false], model Omni 1.2 Flash / 15 s, estimate <= 60, total cap 180 (6930 start balance hard-coded); reads balance, ONE click on เริ่มสร้าง, reads balance.
- dl.py <S###>   : on the clip's /edit page, ดาวน์โหลดสื่อ -> "720p ขนาดดั้งเดิม" only (refuses any item with เครดิต/4K), saves the mp4.
- cards.py : lists generation cards (scene, status) from the feed.
Traps seen: running prep twice put the same still in the END slot too (prep clicks the first empty chip); the account panel must be closed with its own "close" button (Escape leaves its backdrop and blocks the submit click); 1080p download costs 5 cr and 4K 75 cr here.
Fragile: button.empty-chip, .frame-trigger img.chip-image, aria-label ดาวน์โหลดสื่อ / เริ่มสร้าง / รายละเอียดบัญชี / ทริกเกอร์การตั้งค่า, flow-prompt-box-settings, img.thumbnail.
