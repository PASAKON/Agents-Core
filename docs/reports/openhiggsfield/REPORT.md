# OpenHiggsfield / Openjutsu: ศึกษาโค้ด (PH#81f, 29 ต.ค. 2026)

**ที่ CEO เรียกว่า "OpenJetsu" น่าจะเป็น `D3voz/openjutsu`** (184 ดาว, MIT, push 28 ต.ค.) ไม่ใช่ open-higgsfield.
Openjutsu = ตัวทำ Genjutsu ของ Higgsfield (สลับตัวละคร/วัตถุในวิดีโอ) แบบรันเองฟรีบน GPU เรา.
ส่วน `wide-trace/open-higgsfield` (5k ดาว) ที่ CMO เจอ เป็นแค่หน้า UI ที่เรียก API เสียเงินของ Higgsfield.
ไม่มี repo ชื่อ Jetsu บน GitHub (gh search 29 ต.ค.).

## 1. มันคืออะไร
| | open-higgsfield (b16a0ef) | Openjutsu (47c3724) |
|---|---|---|
| ประเภท | UI Next.js อย่างเดียว ไม่มีโมเดลในเครื่อง | UI Next.js ครอบ ComfyUI ในเครื่อง |
| gen ไปที่ไหน | `POST {HF_API_BASE_URL}/{model}` header `Key id:secret` (src/generation/platform.ts:53-78, credentials.ts:45); path แบบ `higgsfield-ai/dop/lite` (catalog/dop.ts:3) = Higgsfield Cloud API | ComfyUI ผ่าน comfy-api-proxy ที่ 127.0.0.1:8189 (README §Run it locally); `COMFY_API_KEY` ว่างได้ |
| โมเดล | 38 ตัวของ Higgsfield (Seedance, Kling, Soul...) | MiniMax H3 int8 + SAM 3.1 + Qwen3-VL 8B, open weights |
| ต้องมี | key + ยอดเงิน Higgsfield | NVIDIA ≥16 GB + RAM 64 GB (ทดสอบบน 4060 Ti) |

## 2. ต้นทุนต่อคลิป 8 วิ
| ช่องทาง | ต่อคลิป 8 วิ | สถานะ |
|---|---|---|
| open-higgsfield → Higgsfield API, Seedance 2.5 | $0.59 (0.0738×8) | ราคาเริ่มต้นจาก blog Higgsfield, assumed |
| open-higgsfield → Kling 3.0 | $0.90 (0.112×8) | assumed เหมือนกัน |
| open-higgsfield → MiniMax H3 | $1.04 | assumed |
| Openjutsu บน winbox (RTX 4080 SUPER) | $0 เงินสด, ~8-17 นาที/คลิป 480p | assumed จาก README (6 วิ 6-13 นาที บน 4060 Ti) |
| Openjutsu บน RunPod H100 $3.29/ชม. | ราว $0.3-0.6 | assumed; H3 ของเราวัดได้ 720p 15 วิ $0.94 (research 28 ก.ย., verified) |
| Higgsfield plan ของเรา | Seedance 2.5 5 วิ 1080p = 60 credits; Unlimited = $0 ถ้ายังไม่หมดอายุ | verified 1 ต.ค.; สิทธิ์วันนี้ไม่ได้เช็ก |
| Flow Omni 720p/8 วิ | 60 credits (Pro $19.99/1,000 = ~$1.20) | verified ในบัญชีเครดิต |
| champa | $0 | ตามที่ทีมใช้อยู่ ไม่ได้เช็กวันนี้ |

## 3. License + ToS
- open-higgsfield: **ไม่มี license** = ห้าม copy/ใช้โค้ด ดูได้อย่างเดียว. Higgsfield API บอกว่าผลงานใช้เชิงพาณิชย์ได้.
- Openjutsu: **MIT** ใช้ได้. แต่ custom node 12 ตัว และน้ำหนัก H3/SAM/Qwen/SolarRenderer มี license ของตัวเอง ยังไม่ได้ตรวจ. กฎ CEO 11 ต.ค.: ใช้เป็นไอเดีย ไม่เอามาเป็นฐาน.

## 4. ความปลอดภัย
- open-higgsfield: key เก็บใน cookie 30 วันบน server ที่โฮสต์ (credentials.ts:3-9). ใช้เว็บ openhiggsfield.ai = ยก secret ที่ใช้เงินได้ให้คนอื่นถือ. ไฟล์ที่อัปโหลดขึ้น Vercel Blob แบบ **public** (upload.ts:20). log ทุก request รวม prompt + URL (platform.ts:55,66). cookie อุปกรณ์ 400 วัน, ไม่มี analytics SDK.
- Openjutsu: ทุกอย่างอยู่ในเครื่อง; ไฟล์ค้างใน ComfyUI `input/` ต้องลบเอง.

## 5. เข้ากับงานเราไหม
- open-higgsfield: แทนอะไรไม่ได้. เป็นแค่หน้าจอใหม่ของ Higgsfield ที่เรามีแพลนอยู่แล้ว และต้องเติมเงิน API แยก (ขั้นต่ำ $5).
- Openjutsu: ตรงกับงานสลับหน้า/ชุด/ฉากใน ILAG, FilmFormula, KhaoHom (แทน Genjutsu ที่ใช้เครดิต). Contabo ไม่มี GPU. winbox มี GPU แต่ฟาร์ม Cookie Run อยู่ (ต้องยืมเครื่อง) และ RAM 64 GB ยังไม่ได้เช็ก. Colab สงวนไว้ให้ CEO.
- **เทสต์ $0 ที่ถูกสุด**: worker อ่าน workflow JSON ของ Openjutsu เทียบกับ H3 studio เรา แล้วยืม winbox รันคลิป 6 วิ 480p 1 ครั้ง (ต้องได้ PC lease ก่อน).

## 6. คำตัดสิน
- open-higgsfield: **skip**.
- Openjutsu: **study only** ตอนนี้ (ดูวิธีทำ mask/SAM/montage) แล้วค่อยเทสต์ winbox 1 คลิปถ้า CEO อยากได้.

## Not checked / risk
- ราคา API เป็น "ราคาเริ่มต้น" จาก blog ไม่มีตารางต่อความละเอียด; Seedance 2.0 ที่ $0.93/วิ ดูผิดปกติ.
- license ของน้ำหนักโมเดลและ custom node ของ Openjutsu ยังไม่ตรวจ.
- winbox: RAM, VRAM ว่างตอนบอทวิ่ง, เวลาเรนเดอร์จริง ยังไม่ได้วัด.
- สิทธิ์ Higgsfield Unlimited วันนี้ ต้อง login ถึงจะรู้.
- ไม่ได้รันโค้ดใด ๆ อ่านอย่างเดียว ($0).
