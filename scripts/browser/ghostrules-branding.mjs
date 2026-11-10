// Replay: Ghost Rules (UCBhmXUsXrAFPXJJeyC4vcxQ) Studio > Customization > Profile: banner, avatar,
// description, video watermark (entire video), Publish. winbox Chrome CDP 9226, already signed in.
// Usage: node scripts/browser/ghostrules-branding.mjs [--publish]   (without --publish it stages only)
// NOTE: assembled from the steps that ran by hand in task-5f9b0d7a; not run end-to-end as one script.
// File paths MUST use forward slashes (backslashes reach DOM.setFileInputFiles mangled -> NotReadableError).
import fs from 'node:fs';
import { newTab, closeTab, Tab, sleep } from './cdp_raw.mjs';

const CH = 'UCBhmXUsXrAFPXJJeyC4vcxQ';
const KIT = 'C:/Users/passg/ghostrules-kit';
const click = (t, label) => t.clickEl(`[...document.querySelectorAll('ytcp-button, button')].find(b=>b.innerText.trim()==='${label}' && b.offsetWidth)`);
const info = await newTab('about:blank');
let t;
try {
  t = await new Tab(info).open();
  await t.goto(`https://studio.youtube.com/channel/${CH}/editing/profile`, 9000);
  const who = await t.eval(`document.body.innerText.includes('Ghost Rules')`);
  if (!who) throw new Error('not on the Ghost Rules channel (switch account first)');

  for (const [sec, file] of [['ytcp-banner-upload', 'banner_B_2560x1440.jpg'], ['ytcp-profile-image-upload', 'avatar_B_800x800.png']]) {
    await t.eval(`document.querySelector('${sec}').scrollIntoView({block:'center'})`);
    await t.chooseFile(`document.querySelector('${sec} ytcp-button, ${sec} button')`, [`${KIT}/${file}`]);
    await sleep(5000); await t.frame();
    await click(t, 'เสร็จ'); await sleep(3000); await t.frame(); // accept default crop
  }

  const desc = fs.readFileSync(`${KIT}/description.txt`, 'utf8');
  await t.clickEl(`document.querySelector('#textbox[contenteditable]')`);
  await t.send('Input.insertText', { text: desc });
  await sleep(1500);
  const got = await t.eval(`document.querySelector('#textbox[contenteditable]').innerText`);
  if (got.trim() !== desc.trim()) throw new Error('description mismatch');

  const wm = `(()=>{const i=[...document.querySelectorAll('input[type=file]')].pop(); return i.closest('ytcp-channel-editing-section')})()`;
  await t.eval(`(${wm}).scrollIntoView({block:'center'})`);
  await t.chooseFile(`[...(${wm}).querySelectorAll('ytcp-button,button')].find(b=>b.innerText.trim()==='อัปโหลด' && b.offsetWidth)`, [`${KIT}/watermark_150.png`]);
  await sleep(5000); await t.frame();
  await click(t, 'เสร็จ'); await sleep(3000); await t.frame();
  await t.clickEl(`[...document.querySelectorAll('tp-yt-paper-radio-button')].find(e=>e.innerText.trim()==='ตลอดทั้งวิดีโอ')`);
  await sleep(1500);
  const checked = await t.eval(`[...document.querySelectorAll('tp-yt-paper-radio-button')].find(e=>e.innerText.trim()==='ตลอดทั้งวิดีโอ').getAttribute('aria-checked')`);
  if (checked !== 'true') throw new Error('watermark display time not set');

  if (process.argv.includes('--publish')) {
    await click(t, 'เผยแพร่'); await sleep(6000); await t.frame();
    console.log('published');
  } else console.log('staged only (pass --publish)');
} finally {
  if (t) t.close();
  await closeTab(info.id); // do NOT navigate this tab right after publish: the renderer froze once; read back from a fresh tab
}
