#!/usr/bin/env node
/**
 * gold-giveaway June 2026 ticket-leaderboard → MoonieX TradeTech FB, 3-post series.
 * Clone of scripts/post-fed-warsh.js pattern (dry-run default, --go to publish,
 * fixed externalId per post = idempotent re-run).
 *
 * Prepared 2026-07-02 by CMO. DO NOT --go without CEO confirmation.
 *
 *   node scripts/post-gold-giveaway-leaderboard.js          # dry run — review plan
 *   node scripts/post-gold-giveaway-leaderboard.js --go     # live — upload + post all 3
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

// Caption skeleton per wiki playbooks/mooniex-fb-caption-style.md (2026-07-02):
// hook (1 emoji, end) → body → framed link → fixed LINE CTA → fixed disclaimer → fixed hashtag base + campaign tags.
const LINK = 'https://mooniex.com/tools?utm_source=fb&utm_campaign=gold_giveaway_june2026';
const LINE_CTA = 'ทักรับสิทธิ์เงินคืนค่าเทรด LINE @mooniex';
const DISCLAIMER = '⚠️ การเทรด CFD มีความเสี่ยงสูง อาจสูญเสียเงินลงทุน โปรดศึกษาก่อนตัดสินใจ — เนื้อหานี้เพื่อให้ข้อมูล ไม่ใช่คำแนะนำการลงทุน';
const HASHTAG_BASE = '#MoonieX #Exness #XM #Forex';
const HASHTAGS = HASHTAG_BASE + ' #GoldGiveaway';

const POSTS = [
  {
    poster: AG + '/output/mooniex-posters/gold-giveaway-recap/poster-1-top10.png',
    bucketName: 'gold-giveaway-top10-20260702.png',
    externalId: 'mooniex-gold-giveaway-top10-20260702-v2',
    caption: [
      'TOP 10 สะสมสิทธิ์สูงสุด เดือนมิถุนายน 2026 📊',
      '',
      'กติกา: เทรด 1.0 lot = 1 สิทธิ์ (คิดจากบัญชีวอลุ่มสูงสุดของแต่ละคน)',
      'นี่คือสรุปสิทธิ์สะสม ยังไม่ใช่ผลจับรางวัล — จับรางวัลจริง 5 กรกฎาคมนี้',
      '',
      '👉 อยากติดอันดับเดือนหน้า เทรดต่อเนื่องผ่าน MoonieX: ' + LINK,
      LINE_CTA,
      '',
      DISCLAIMER,
      HASHTAGS,
    ].join('\n'),
  },
  {
    poster: AG + '/output/mooniex-posters/gold-giveaway-recap/poster-2-rank11-30.png',
    bucketName: 'gold-giveaway-rank11-30-20260702.png',
    externalId: 'mooniex-gold-giveaway-rank11-30-20260702-v2',
    caption: [
      'ต่อกันด้วยอันดับ 11-30 เดือนมิถุนายน 2026 📊',
      '',
      'ใครยังไม่เจอเลขบัญชีตัวเองใน TOP 10 เช็คต่อที่นี่ได้เลย',
      'ยังไม่ใช่ผลจับรางวัลจริง — จับรางวัลจริง 5 กรกฎาคมนี้',
      '',
      '👉 เช็คอันดับของคุณ: ' + LINK,
      LINE_CTA,
      '',
      DISCLAIMER,
      HASHTAGS,
    ].join('\n'),
  },
  {
    poster: AG + '/output/mooniex-posters/gold-giveaway-recap/poster-3-rank31-57.png',
    bucketName: 'gold-giveaway-rank31-57-20260702.png',
    externalId: 'mooniex-gold-giveaway-rank31-57-20260702-v2',
    caption: [
      'ปิดท้ายด้วยอันดับ 31-57 ครบทุกคนที่มีสิทธิ์เดือนมิถุนายน 📊',
      '',
      'เทรดแค่ 1 ออเดอร์ก็มีสิทธิ์แล้ว เดือนหน้าสะสมเพิ่มขยับอันดับได้เรื่อยๆ',
      'ยังไม่ใช่ผลจับรางวัลจริง — จับรางวัลจริง 5 กรกฎาคมนี้',
      '',
      '👉 อ่านต่อ: ' + LINK,
      LINE_CTA,
      '',
      DISCLAIMER,
      HASHTAGS,
    ].join('\n'),
  },
];

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
function sb() {
  return createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY);
}

async function runOne(p, idx) {
  console.log(`\n--- Post ${idx + 1}/3 ---`);
  console.log('media   : ' + (fs.existsSync(p.poster) ? 'OK' : 'MISSING') + '  ' + p.poster);
  console.log('ext_id  : ' + p.externalId);
  console.log('caption ▼\n  ' + p.caption.replace(/\n/g, '\n  ') + '\n');

  if (!fs.existsSync(p.poster)) throw new Error('missing media: ' + p.poster);
  if (!GO) return;

  const buf = fs.readFileSync(p.poster);
  const c = sb();
  const up = await c.storage.from(BUCKET).upload(p.bucketName, buf, { contentType: 'image/png', upsert: true });
  if (up.error) throw new Error('upload: ' + up.error.message);
  const url = c.storage.from(BUCKET).getPublicUrl(p.bucketName).data.publicUrl;
  console.log('[1] uploaded →', url);

  const res = await fetch(BASE + '/social-posts', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ caption: p.caption, social_accounts: [ACCOUNT], external_id: p.externalId, media: [{ url }] }),
  });
  const post = await res.json();
  if (!res.ok) throw new Error('createPost: ' + res.status + ' ' + JSON.stringify(post));
  console.log('[2] createPost id =', post.id, 'status =', post.status || '?');

  let status = post.status || '?';
  for (let i = 0; i < 24; i++) {
    await sleep(5000);
    const r = await fetch(BASE + '/social-posts/' + post.id, { headers: { Authorization: 'Bearer ' + KEY } });
    const pp = await r.json().catch(() => null);
    status = (pp && pp.status) || status;
    process.stdout.write('[3] poll ' + (i + 1) + ' status=' + status + '\n');
    if (status === 'processed') break;
  }

  let urls = [];
  try {
    const rr = await fetch(BASE + '/social-post-results?post_id=' + encodeURIComponent(post.id), { headers: { Authorization: 'Bearer ' + KEY } });
    const jj = await rr.json();
    urls = ((jj && jj.data) || []).map((r) => (r.platform_data && r.platform_data.url) || '').filter(Boolean);
  } catch (e) { console.warn('[4] getPostResults read-fail:', e.message); }

  console.log('postforme_id:', post.id, ' status:', status, ' permalinks:', urls.length ? urls.join(', ') : '(none yet)');
}

(async () => {
  console.log('=== gold-giveaway leaderboard (3-post series) → MoonieX TradeTech — ' + (GO ? '*** LIVE (--go) ***' : 'DRY RUN (no --go)') + ' ===');
  console.log('account : ' + ACCOUNT + '  (MoonieX TradeTech, facebook)');
  console.log('key     : ' + (KEY ? 'POSTFORME_API_KEY present' : 'MISSING — cannot post'));

  if (GO && !KEY) throw new Error('POSTFORME_API_KEY missing — aborting live run');

  for (let i = 0; i < POSTS.length; i++) {
    await runOne(POSTS[i], i);
    if (GO && i < POSTS.length - 1) await sleep(5000);
  }

  if (!GO) {
    console.log('\n— DRY RUN: nothing uploaded, nothing posted. Re-run with --go to publish all 3. —');
  }
})().catch((e) => { console.error('ERROR:', e.message); process.exit(1); });
