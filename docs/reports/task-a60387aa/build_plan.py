"""Emit documentation patch only; no media operations or network calls."""
import json, math
from pathlib import Path

ROOT = Path('/opt/MoonieXHQ/Work/ghost-pilot/ep03')
timeline = json.loads((ROOT/'timeline.json').read_text())
rows = {r['id']: r for r in json.loads((ROOT/'voice/rows.json').read_text())}
# Beat ordering follows each complete take; times remain editorial estimates.
beats = [
['Old dormitory corner room','Cheap furnished room','Abandoned clothes and luggage','Former tenant departing before dawn','Room awaiting replacement'],
['Five-storey dormitory in the past','Karn searching in rain','Handwritten vacancy sign','Landlady counting beads','Deposit accepted indoors'],
['Brass key with faded red thread','Landlady warning','Fourth-floor corridor','Wardrobe rule sheet'],
['Karn opens room','Wardrobe facing bed','Black bag covering mirror','Wardrobe opens to rule sheet'],
['Rule one on paper','01:30 waking in bed','Rain beyond balcony glass','Outside hand turns knob'],
['Karn approaches peephole','Eye against brass viewer','Milky giant eye outside','Whisper through keyhole'],
['Karn recoils and falls','Hand slaps light switch','Blanket pulled over body','Shadow recedes and ceiling footsteps'],
['Heavy dragging above bed','Rule two recalled','Bricked fifth-floor access','Karn keeps gaze down'],
['Karn lies facing wall','Black drop at ceiling crack','Drop lands beside pillow','Reflection reveals hanging woman'],
['Karn bites lip and closes eyes','Black drops retreat','03:00 clock','Wet fabric snapping outside'],
['Rule three recalled','Thin curtain moving','Four shirts and fifth figure','Bent head approaches glass'],
['Karn rises to desk lamp','Returns to rule sheet','Scratched warning under seal'],
['Red-ink fourth rule','False invitation to hide','Warning contradicts the rule'],
['03:17 clock','Three knocks inside closed wardrobe','Door opens one inch','Torn fingernails and staring eyes'],
['Male voice inside wardrobe','Karn rejects invitation','Chair braces handles','Brass key locks wardrobe'],
['Angry scream inside wardrobe','Door impacts shake chair','Black fluid seeps out','Mirror bag slips halfway'],
['Blue-ink fifth rule','Pale shadow crawls from mirror','Karn turns away and closes door','Trembling hands tie sacred thread'],
['04:30 lights go out','Lightning through balcony curtain','Wardrobe knocks','Bathroom pounding and entry knob'],
['Realization of layered trapped tenants','Past peephole victim','Past wardrobe victim','Past mirror victim'],
['Karn retreats to bed talisman','Knees hugged and eyes closed','Hands cover ears during prayer','Whispers at four bed edges'],
['Wardrobe and bathroom door shake','Clock reaches 06:00','Golden light through curtain','All named sounds stop'],
['Keys and money left on table','Karn runs down stairs','Karn exits at dawn','Warning about sealed mirror','Wardrobe awaits replacement; story closed']]
movers = [
['Departing tenant legs: carry the narrated escape','Tenant arm: leaves possessions behind','Loose clothing on departing tenant: follows the exit'],
['Karn legs: walk while searching','Rain drops: fall in exposed alley only','Landlady fingers and beads: count the beads named in the take'],
['Landlady hand: passes the key','Key and thread: swing only during handover','Landlady mouth: delivers the quoted warning'],
['Karn arm: opens the room door','Room door leaf: follows the narrated opening','Wardrobe leaf: opens to reveal the rules'],
['Rain drops: fall beyond balcony glass only','Entry knob: twists at the named event','Karn torso: wakes at the disturbance'],
['Karn legs: approach the peephole','Karn head: leans to the viewer','Karn eye: focuses on the revealed eye'],
['Karn body: recoils and crawls','Karn arm: reaches the switch','Blanket: rises as he covers himself'],
['Recalled walker feet: enact named ceiling steps, only as recollection','Dragged object: follows the named dragging, only in recollection','Karn eyes: stay lowered as he recalls the warning'],
['Black drops: fall from the crack','Wet-floor rings: respond to the named drops','Karn eyes: track the reflection without looking up'],
['Karn lip: tightens in the named bite','Karn eyelids: close to feign sleep','Wet hanging fabric: snaps outside at the named sound'],
['Curtain: flutters as explicitly described','Shirt hems: move with the preceding wet-fabric event','Fifth figure: approaches the balcony glass'],
['Karn legs: rise and return to wardrobe','Karn hand: switches desk lamp on','Karn eyes: scan the warning'],
['Karn eyes: scan the fourth rule','Karn head: shifts from red rule to warning','Karn lips: silently register the contradiction, restrained performance inference'],
['Clock hands: reach the named time','Wardrobe door: shakes and opens as explicitly narrated','Pale fingers: emerge and grip the door edge'],
['Karn arms: position chair','Chair: moves only while being placed','Key: turns in the narrated lock'],
['Wardrobe door and braced chair: shake from explicit impacts','Black fluid: seeps across floor','Mirror bag: falls halfway as narrated'],
['Pale entity: crawls out of mirror','Bathroom door: is pulled closed','Karn hands and sacred thread: tremble while binding knob'],
['Wardrobe door: responds to named knocks','Bathroom door: responds to pounding','Entry knob: twists as explicitly named'],
['Past tenant head: leans into peephole in reconstruction','Past tenant body: enters wardrobe in reconstruction','Past tenant head: turns toward mirror in reconstruction'],
['Karn body: retreats and folds onto bed','Karn hands: cover both ears','Karn lips: repeat the named prayer'],
['Wardrobe door: shakes as explicitly narrated','Bathroom door: shakes as explicitly narrated','Clock hands: reach six and trigger sound stop'],
['Karn hand: deposits keys and money','Karn legs: run down stairs and out','Karn jacket hem: follows the escape movement']]
events = {5:['ลูกบิด|knob rattles three times'],6:['กระซิบ|female whisper; retain narrator, do not add invented words'],7:['หัวใจเต้นรัว|fast heartbeat','เสียงฝีเท้า|ceiling heel drags and three thuds'],8:['กระโดดเชือก|jumping impacts','ลากของหนัก|heavy dragging'],9:['แหมะ|black drips'],10:['เสียงหยดน้ำ|drips recede','เสียงผ้าเปียกน้ำสะบัด|wet fabric snap'],14:['ปัง|exactly three wardrobe knocks'],15:['เสียงผู้ชาย|male invitation retained in narration','หมุนล็อก|lock turn'],16:['เสียงกรีดร้อง|angry scream','กระแทก|wardrobe impacts','แปะ|fluid drops'],17:['กระชากประตูปิดล็อก|bathroom close and lock'],18:['เสียงเคาะ|wardrobe knocks','เสียงทุบ|bathroom pounding','เสียงบิดลูกบิด|entry knob'],20:['ท่องบทสวดมนต์|prayer retained in narration','เสียงกระซิบ|bedside whispers'],21:['เสียงทุบประตู|pounding stops','เสียงขูดไม้|wood scrape stops','เสียงกระซิบ|whispers stop'],22:['วิ่งลงบันได|running stair footsteps']}
scenes=[]; shots=[]
for i,t in enumerate(x for x in timeline if x['kind']=='voice'):
    n=i+1; sid=f'S{n:02}'; count=len(beats[i]); duration=t['duration']/count
    scene={'id':sid,'source_scene':t['scene'],'take':t['id'],'start':t['start'],'end':t['end'],'transcript':rows[t['id']]['text'],'movers':[{'reason':m} for m in movers[i]],'grade':'flashback_desaturated_sepia' if n in (2,3,19) else 'present_cool_paper','rain':{'camera':'mixed_outdoor_indoor' if n==2 else 'indoor','visual':'exposed exterior only' if n in (2,5,18) else 'none','bed':'outdoor full then indoor muffled at deposit' if n==2 else 'muffled exterior rain behind walls; continuity assumption' if 5<=n<=20 else 'none'},'sfx':[{'anchor':e.split('|')[0],'event':e.split('|')[1],'time':None,'status':'align to actual trimmed take before mix'} for e in events.get(n,[])],'shots':[]}
    if n==1: scene['rain']={'camera':'indoor','visual':'none','bed':'none'}
    for j,beat in enumerate(beats[i]):
        shot={'id':f'{sid}-{j+1:02}','plate_id':f'P{len(shots)+1:03}','plate_status':'planned_unique_paper_plate_not_created','start':round(t['start']+j*duration,3),'end':round(t['start']+(j+1)*duration,3),'beat':beat,'timing_status':'provisional clause allocation; replace with heard phrase boundary <=12s','camera':'outdoor' if n==2 and j<3 else 'indoor','grade':scene['grade']}
        if n==22 and j==2: shot['camera']='outdoor'
        scene['shots'].append(shot); shots.append(shot)
    scenes.append(scene)
cards=[dict(x,animation='paper numeral/clock reveal and settle; unique graphic, no SFX',plate_id=f'CARD-{k+1}') for k,x in enumerate(x for x in timeline if x['kind']!='voice')]
risks=[
'Shot times are provisional clause allocations, not listened/word-locked cuts. Reconcile voice takes against trimmed audio and snap each boundary to its spoken beat; split with another unique plate if any revised shot exceeds 12 s.',
'Only seven words files exist versus 22 takes. They contain fragmented Thai tokens; correspondence and trim offsets have not been verified. SFX times remain null deliberately.',
'Existing plates and paired foreground/background cutouts are inventoried references only; no image inspection or layer quality check was performed. All planned paper plates require unique scene-action framing and clean separate movers; none is claimed production-ready.',
'Three justified movers are listed per scene across its shots, not three arbitrary motions in every close-up. S13 lip motion is a performance inference; replace with a grounded action or obtain review if rejected. Still rule/architecture inserts must not be made to wobble to meet a quota.',
'Rain continuity from c05 through c20 is a storm-continuity inference, not a new spoken rain event per take. Indoor bed means muffled exterior sound only; no indoor/roof rain particles. c02 changes to indoor at the deposit shot. No thunder is authorized: lightning in c18 does not name thunder.',
'Flashback treatment: c02-c03 backstory sepia, reset at c04; c19 reconstructed earlier victims sepia, reset at c20. Entire tale also occurs in the past; these are editorial marked recalls, subject to M1 review.',
'No listening, render, contact sheet, alpha/occlusion, lip sync, loudness, rain gap/click scan, subtitle or final-frame QC performed. M2 must use >=1.5 s rain loop crossfades and scan final mix for gaps/clicks.',
'c02 says แฟ้มคดีที่สาม. Remove the ordinal case-number wording at a verified phrase boundary before production to obey no episode numbering. Source timeline act clocks also conflict with narrated time in c04 and c20; use Roman chapter numerals only, remove source clock labels.',
'No paid calls, source edits, media copies, uploads or deletion. Disk was 11 GiB available (rounded df), close to 10 GB floor; recheck exact free bytes before any later media work.',
'CMO report delivery blocked: required live-session lookup failed with DNS resolution error. One ready-to-send letter is saved locally; not sent, no duplicate attempted.'
]
inventory=[{'plate':str(p),'fg':str(Path('/opt/MoonieXHQ/Work/ghostrules-full/ep03/cutouts')/(p.stem+'_fg.png')),'bg':str(Path('/opt/MoonieXHQ/Work/ghostrules-full/ep03/cutouts')/(p.stem+'_bg.jpg'))} for p in sorted((ROOT/'plates').glob('*.jpg'))]
plan={'task':'task-a60387aa','milestone':'M1 planning only','format':'1920x1080 16:9 paper cut','duration':769.612,'counts':{'scenes':len(scenes),'story_shots':len(shots),'unique_planned_story_plates':len(shots),'graphic_cards':len(cards),'existing_reference_files':len(inventory)},'thunder_cues':0,'scenes':scenes,'cards':cards,'reference_inventory':inventory,'not_checked_risk':risks}
base='docs/reports/task-a60387aa/'
md=['# GhostRules M1 paper plan','', 'Planning only. Internal source IDs are not on-screen titles. 1920x1080, 16:9, 24 fps proposed. Source duration 769.612 s; final timing pending removal of spoken ordinal. No render or paid API.', '', '## Rules and editorial contract', '', 'The eight CEO rules in the live PH brief apply. Every named event has a transcript anchor; no invented Foley, music stingers, thunder, or gratuitous whooshes. Three movers per scene with reasons below; architectural shells remain locked. Any door or chair movement is limited to its narrated action. Paper depth and clean silhouettes; no headless cutouts, red sky or moon. Camera motion does not count as a mover. Hard cuts between unique scene-action plates. Never reuse a plate, including in recalls.', '', 'Five 2.4 s animated Roman chapter cards and one 3.2 s ending graphic use unique paper graphics; remove inaccurate source clock labels. Reveal, settle and exit animation, no freeze-frame bumpers. End on the completed escape and final warning, no sequel tease. No EP or episode/case ordinal in video, cover, title or description. Covers later: white normal type and larger red emphasis only; no blush, Thai guillemets or em dash.', '', 'Rain particles only in open air, masked outside glazing and roofs. Interior rain is an attenuated, low-pass exterior bed. Loop >=1.5 s crossfades and scan M2 mix; no thunder in this story. Golden dawn replaces storm bed at c21. Flashbacks use desaturated sepia and return to cool paper grade at the next marked present scene.', '', 'All shot plates below are unique PLANNED assets, not files already made. Existing plate/cutout paths are reference inventory in JSON. Allocate a new frame for each beat, not a renamed crop counted as a unique plate. Preserve Karn (26), landlady (70), room geography, hinge sides, four shirts plus fifth figure, and wardrobe closed before opening one inch.', '', '## Counts', '',json.dumps(plan['counts']), '', '## Scene and shot list','']
for s in scenes:
    md += [f"### {s['id']} / {s['take']} / source {s['source_scene']} ({s['start']:.3f}–{s['end']:.3f} s)", '',f"Grade: {s['grade']}. Rain: {json.dumps(s['rain'])}",'','Movers:']
    md += ['- '+m['reason'] for m in s['movers']]
    md += ['', 'Shots (provisional; seconds):', '', '| Shot | Unique plate | Start | End | Camera | Beat |','|---|---|---:|---:|---|---|']
    md += [f"| {q['id']} | {q['plate_id']} | {q['start']:.3f} | {q['end']:.3f} | {q['camera']} | {q['beat']} |" for q in s['shots']]
    md += ['', 'Named-event SFX: '+('; '.join(e['anchor']+' → '+e['event'] for e in s['sfx']) or 'none; do not infer Foley from pictured props')+'. Exact seconds pending take alignment.', '']
md += ['## Not checked / risk','']+['- '+r for r in risks]
letter=['To: cmo-e785343f','Kind: report','Subject: GhostRules M1 paper plan, task-a60387aa','Status: ready, NOT SENT; live-session lookup failed DNS','',f"Plan paths: {Path.cwd()/base/'PLAN.md'} and {Path.cwd()/base/'PLAN.json'}",json.dumps(plan['counts']),'No render, no paid API. Existing media unchanged.','', '## Not checked / risk','']+['- '+r for r in risks]
report=['# REPORT task-a60387aa','','M1 planning deliverables completed; letter prepared, delivery blocked.','','## Files changed','','- PLAN.md: scene/shot plan, movers/reasons, rain classifications, flashback grades and risk section.','- PLAN.json: machine-readable equivalent, named-event anchors and existing reference inventory.','- CMO_LETTER.md: single unsent report letter with paths, counts and all risks.','- build_plan.py: documentation-only patch generator.','- REPORT.md: this report.','','## Validation performed','','- Read live PH brief (missing in worktree), GhostChannel DNA, rows, all 22 take texts, timeline and sample word/take metadata.','- Checked unique shot plate IDs, shot durations <=12 s, full timeline coverage including cards, three reasoned movers per scene, and source reference existence using local assertions.','- No media rendering or paid API; no media copied into git.','- Disk check: 11 GiB free rounded; exact byte recheck recorded in final validation output.','','## Limitations','','See PLAN.md section Not checked / risk. Timings are provisional and plates are not created. No visual/audio quality certification.','','## Blockers','','- Required recipient verification via bash scripts/live-sessions.sh failed DNS resolution. No org tools are available; no letter was sent. Launcher/CMO should deliver CMO_LETTER.md once the recipient can be verified.','- Asset creation and word alignment remain later milestones, outside planning-only authorization.','','## Skill learning','','- Existing words/c01.json uses fragmented Thai tokens and only c01-c07 files are present while rows/timeline contain c01-c22: never assume shared IDs imply take-aligned timings.','- Source c18 names lightning only; thunder must not be inferred from visual lightning.']
files={'PLAN.md':'\n'.join(md)+'\n','PLAN.json':json.dumps(plan,ensure_ascii=False,indent=2)+'\n','CMO_LETTER.md':'\n'.join(letter)+'\n','REPORT.md':'\n'.join(report)+'\n'}
print('*** Begin Patch')
for name,body in files.items():
    print('*** Add File: '+base+name)
    print('\n'.join('+'+line for line in body.splitlines()))
print('*** End Patch')
