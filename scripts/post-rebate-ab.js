#!/usr/bin/env node
/**
 * MoonieX — Rebate C1 A/B scheduled publisher → MoonieX TradeTech FB.
 * Clone of claudeflow/scripts/post-musk-poster.js, extended for 2 variants
 * + native PostForMe scheduled_at.
 *
 * DRY RUN by default (prints the plan, touches nothing).
 * Pass --go to upload images + schedule the posts.
 * Idempotent: fixed external_id per variant → safe re-run (dedupes on PostForMe).
 *
 * Prepared 2026-06-16 by CMO. DO NOT --go without CEO confirmation.
 *
 *   node scripts/post-rebate-ab.js          # dry run — review plan
 *   node scripts/post-rebate-ab.js --go     # live — upload + schedule
 */
'use strict';

const CF = '/Users/gob/Projects/mooniex-claudeflow';
const AG = '/Users/gob/Projects/Agents';
require(CF + '/node_modules/dotenv').config({ path: CF + '/.env' });
const fs = require('fs');
const { createClient } = require(CF + '/node_modules/@supabase/supabase-js');

const GO = process.argv.includes('--go');
const BASE = 'https://api.postforme.dev/v1';
const KEY = process.env.POSTFORME_API_KEY;
const ACCOUNT = 'spc_A5gUAgpaKC9gLWV4awEHI'; // MoonieX TradeTech (facebook)
const BUCKET = 'claudeflow-media';

const LINK_A = 'https://mooniex.com/tools?utm_source=fb&utm_campaign=rebate_ab&utm_content=A';
const LINK_B = 'https://mooniex.com/tools?utm_source=fb&utm_campaign=rebate_ab&utm_content=B';

const VARIANTS = [
  {
    id: 'A',
    file: AG + '/output/mooniex-rebate-c1/c1-a-final.png',
    bucketName: 'rebate-ab-a-final-20260617.png',
    externalId: 'mooniex-rebate-ab-A-20260617',
    scheduledAt: '2026-06-17T20:30:00+07:00', // Wed 17 Jun, 20:30 TH
    caption: [
      'โบนัสหมดอายุ… แต่เงินคืนไม่มีวันหมด 🌙',
      '',
      'ทุกล็อตทองคำที่คุณเทรด = ต้นทุนค่าสเปรด/ค่าคอมที่เสียไป',
      'MoonieX คืนให้ทุกล็อต ตราบที่คุณยังเทรด — ไม่ใช่โบนัสครั้งเดียวแล้วจบ',
      '',
      '✅ XM คืน $15 /ล็อต (ทองคำ)',
      '✅ Exness คืน $8 /ล็อต (ทองคำ)',
      '✅ เทรดเท่าเดิม · มีบัญชีอยู่แล้วย้ายมารับได้',
      '',
      '👉 คำนวณเงินคืนของคุณเอง: ' + LINK_A,
      'ทักรับสิทธิ์เงินคืนค่าเทรด LINE @mooniex',
      '',
      '⚠️ การเทรด CFD มีความเสี่ยงสูง อาจสูญเสียเงินลงทุน โปรดศึกษาก่อนตัดสินใจ — เนื้อหานี้เพื่อให้ข้อมูล ไม่ใช่คำแนะนำการลงทุน',
      '#MoonieX #Exness #XM #Forex #เงินคืนค่าเทรด #เทรดทองคำ',
    ].join('\n'),
  },
  {
    id: 'B',
    file: AG + '/output/mooniex-rebate-c1/c1-b-final.png',
    bucketName: 'rebate-ab-b-final-20260618.png',
    externalId: 'mooniex-rebate-ab-B-20260618',
    scheduledAt: '2026-06-18T20:30:00+07:00', // Thu 18 Jun, 20:30 TH
    caption: [
      'เทรดทองคำอยู่แล้ว? คุณจ่ายค่าสเปรดทุกออเดอร์ — ทวงคืนได้ 🌙',
      '',
      'ทุกล็อตที่ปิดมีต้นทุนซ่อนอยู่ MoonieX ดึงกลับเข้ากระเป๋าคุณทุกล็อต',
      'ไม่ต้องเทรดเพิ่ม ไม่ต้องเปลี่ยนพฤติกรรม',
      '',
      '✅ XM คืน $15 /ล็อต (ทองคำ)',
      '✅ Exness คืน $8 /ล็อต (ทองคำ)',
      '✅ มีบัญชีอยู่แล้วย้ายมารับเงินคืนได้',
      '',
      '👉 เช็คว่าคุณได้คืนเท่าไหร่: ' + LINK_B,
      'ทักรับสิทธิ์เงินคืนค่าเทรด LINE @mooniex',
      '',
      '⚠️ การเทรด CFD มีความเสี่ยงสูง อาจสูญเสียเงินลงทุน โปรดศึกษาก่อนตัดสินใจ — เนื้อหานี้เพื่อให้ข้อมูล ไม่ใช่คำแนะนำการลงทุน',
      '#MoonieX #Exness #XM #Forex #เงินคืนค่าเทรด #เทรดทองคำ',
    ].join('\n'),
  },
];

function sb() {
  return createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY);
}

async function upload(v) {
  const buf = fs.readFileSync(v.file);
  const c = sb();
  const up = await c.storage.from(BUCKET).upload(v.bucketName, buf, { contentType: 'image/png', upsert: true });
  if (up.error) throw new Error('upload ' + v.id + ': ' + up.error.message);
  return c.storage.from(BUCKET).getPublicUrl(v.bucketName).data.publicUrl;
}

async function schedulePost(v, url) {
  const body = {
    caption: v.caption,
    social_accounts: [ACCOUNT],
    external_id: v.externalId,
    media: [{ url }],
    scheduled_at: v.scheduledAt,
  };
  const res = await fetch(BASE + '/social-posts', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const j = await res.json();
  if (!res.ok) throw new Error('createPost ' + v.id + ': ' + res.status + ' ' + JSON.stringify(j));
  return j;
}

(async () => {
  console.log('=== MoonieX Rebate C1 A/B — ' + (GO ? '*** LIVE (--go) ***' : 'DRY RUN (no --go)') + ' ===');
  console.log('account : ' + ACCOUNT + '  (MoonieX TradeTech, facebook)');
  console.log('key     : ' + (KEY ? 'POSTFORME_API_KEY present' : 'MISSING — cannot post') + '\n');

  for (const v of VARIANTS) {
    const ok = fs.existsSync(v.file);
    console.log('[' + v.id + '] media=' + (ok ? 'OK' : 'MISSING') + '  ' + v.file);
    console.log('     schedule=' + v.scheduledAt + '  ext_id=' + v.externalId);
    console.log('     bucket=' + BUCKET + '/' + v.bucketName);
    console.log('     caption ▼\n       ' + v.caption.replace(/\n/g, '\n       ') + '\n');
    if (!ok) throw new Error('missing media: ' + v.file);
  }

  if (!GO) {
    console.log('— DRY RUN: nothing uploaded, nothing posted.');
    console.log('  Re-run with  --go  to upload images + schedule both posts. —');
    return;
  }
  if (!KEY) throw new Error('POSTFORME_API_KEY missing — aborting live run');

  for (const v of VARIANTS) {
    const url = await upload(v);
    console.log('[' + v.id + '] uploaded → ' + url);
    const post = await schedulePost(v, url);
    console.log('[' + v.id + '] scheduled  id=' + post.id + '  status=' + (post.status || '?') + '  at=' + (post.scheduled_at || v.scheduledAt));
  }
  console.log('\nDone. Verify in PostForMe dashboard. Re-run is safe (idempotent external_id).');
})().catch((e) => { console.error('FATAL', e.message); process.exit(1); });
