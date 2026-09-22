#!/usr/bin/env node
/**
 * One-off publisher: FED result-summary poster (round 2) → MoonieX TradeTech FB.
 * Clone of post-fed-warsh.js. Posts the post-FOMC result recap.
 *
 * DRY RUN by default. Pass --go to upload + post. Idempotent external_id.
 * Prepared 2026-06-18 by CMO. DO NOT --go without CEO confirmation.
 *
 *   node scripts/post-fed-result.js          # dry run
 *   node scripts/post-fed-result.js --go      # live
 */
'use strict';

const CF = '/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow';
const AG = '/Users/gob/Projects/Agents';
require(CF + '/node_modules/dotenv').config({ path: CF + '/.env' });
const fs = require('fs');
const { createClient } = require(CF + '/node_modules/@supabase/supabase-js');

const GO = process.argv.includes('--go');
const BASE = 'https://api.postforme.dev/v1';
const KEY = process.env.POSTFORME_API_KEY;
const ACCOUNT = 'spc_A5gUAgpaKC9gLWV4awEHI'; // MoonieX TradeTech (facebook)
const BUCKET = 'claudeflow-media';

const POSTER = AG + '/output/mooniex-posters/fed-warsh/fed-warsh-result.png';
const BUCKET_NAME = 'fed-warsh-result-20260618.png';
const EXTERNAL_ID = 'mooniex-fed-warsh-result-20260618';
const LINK = 'https://mooniex.com/tools?utm_source=fb&utm_campaign=fed_warsh_result';

const CAPTION = [
  '📊 ผลออกแล้ว! ประชุมเฟด (FOMC) มิ.ย. — ประชุมแรกของประธานคนใหม่ Kevin Warsh',
  '',
  '🟡 คงดอกเบี้ย 3.50–3.75% (ครั้งที่ 4 ติด) — ตามที่ตลาดคาด',
  '🦅 แต่ Dot plot พลิกเป็นสายเหยี่ยว! ตัดมุมมอง “ลดดอกเบี้ย” ทิ้ง ส่งสัญญาณ “ขึ้น” ปีนี้ (median สิ้นปี 3.4% → 3.8%)',
  '',
  '“คง” แต่ตลาดไม่นิ่ง — ตอบรับทันที 👇',
  '🔴 ทองคำ ดิ่ง จ่อหลุด $4,000',
  '🔴 หุ้นสหรัฐ S&P −0.5% · Nasdaq −0.4%',
  '🟢 ดอลลาร์ + บอนด์ยีลด์ แข็งค่าขึ้น',
  '',
  'เฟดสายเหยี่ยว = แรงกดทอง/หุ้น จับตาต่อทั้งสัปดาห์ 👀',
  '',
  'อ่านข่าว + เครื่องมือเทรดฟรี (ปฏิทินข่าว · คำนวณ lot · แจ้งเตือนทอง)',
  '👉 ' + LINK,
  'ทักรับสิทธิ์เงินคืนค่าเทรด LINE @mooniex',
  '',
  '⚠️ การเทรด CFD มีความเสี่ยงสูง อาจสูญเสียเงินลงทุน โปรดศึกษาก่อนตัดสินใจ — เนื้อหานี้เพื่อให้ข้อมูล ไม่ใช่คำแนะนำการลงทุน',
  '#MoonieX #Exness #XM #Forex #FED #FOMC',
].join('\n');

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
function sb() {
  return createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY);
}

(async () => {
  console.log('=== FED RESULT poster → MoonieX TradeTech — ' + (GO ? '*** LIVE (--go) ***' : 'DRY RUN (no --go)') + ' ===');
  console.log('account : ' + ACCOUNT + '  (MoonieX TradeTech, facebook)');
  console.log('key     : ' + (KEY ? 'POSTFORME_API_KEY present' : 'MISSING — cannot post'));
  console.log('media   : ' + (fs.existsSync(POSTER) ? 'OK' : 'MISSING') + '  ' + POSTER);
  console.log('ext_id  : ' + EXTERNAL_ID);
  console.log('caption ▼\n  ' + CAPTION.replace(/\n/g, '\n  ') + '\n');

  if (!fs.existsSync(POSTER)) throw new Error('missing media: ' + POSTER);

  if (!GO) {
    console.log('— DRY RUN: nothing uploaded, nothing posted. Re-run with --go to publish. —');
    return;
  }
  if (!KEY) throw new Error('POSTFORME_API_KEY missing — aborting live run');

  const buf = fs.readFileSync(POSTER);
  const c = sb();
  const up = await c.storage.from(BUCKET).upload(BUCKET_NAME, buf, { contentType: 'image/png', upsert: true });
  if (up.error) throw new Error('upload: ' + up.error.message);
  const url = c.storage.from(BUCKET).getPublicUrl(BUCKET_NAME).data.publicUrl;
  console.log('[1] uploaded →', url);

  const res = await fetch(BASE + '/social-posts', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ caption: CAPTION, social_accounts: [ACCOUNT], external_id: EXTERNAL_ID, media: [{ url }] }),
  });
  const post = await res.json();
  if (!res.ok) throw new Error('createPost: ' + res.status + ' ' + JSON.stringify(post));
  console.log('[2] createPost id =', post.id, 'status =', post.status || '?');

  let status = post.status || '?';
  for (let i = 0; i < 24; i++) {
    await sleep(5000);
    const r = await fetch(BASE + '/social-posts/' + post.id, { headers: { Authorization: 'Bearer ' + KEY } });
    const p = await r.json().catch(() => null);
    status = (p && p.status) || status;
    process.stdout.write('[3] poll ' + (i + 1) + ' status=' + status + '\n');
    if (status === 'processed') break;
  }

  let urls = [];
  try {
    const rr = await fetch(BASE + '/social-post-results?post_id=' + encodeURIComponent(post.id), { headers: { Authorization: 'Bearer ' + KEY } });
    const jj = await rr.json();
    urls = ((jj && jj.data) || []).map((r) => (r.platform_data && r.platform_data.url) || '').filter(Boolean);
  } catch (e) { console.warn('[4] getPostResults read-fail:', e.message); }

  console.log('\n=== RESULT ===');
  console.log('postforme_id:', post.id);
  console.log('status      :', status);
  console.log('permalinks  :', urls.length ? urls.join('\n              ') : '(none returned — verify in Chrome/PostForMe)');
})().catch((e) => { console.error('FATAL', e.message); process.exit(1); });
