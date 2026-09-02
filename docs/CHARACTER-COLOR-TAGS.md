# «Sorry, Sir» — Blender proxy colour tags (CEO-approved system, 2026-08-31)

One colour per character, NO colour shared between different characters.
Exception (CEO): characters that are legitimately identical multiples share
one colour (the two Valder guards). Every proxy also carries a floating name
tag. These exact colour words go into every prompt's POSITION MAP so Seedance
maps each proxy to its Element:
"the <COLOUR> figure labelled <NAME> = @<element_id>".

| Colour tag | RGB (previz) | Character | Element ID |
|---|---|---|---|
| WHITE | 0.97 0.97 0.97 | Dupe, the cleaner | @project_absence_char_cleaner_c |
| MAGENTA | 0.85 0.15 0.60 | Valder | @project_absence_char_valder |
| NAVY ×2 | 0.10 0.10 0.32 | Valder's two guards (identical pair — shared by rule) | @project_absence_char_guard_valder_two |
| GOLD | 0.85 0.65 0.10 | The gold-toothed gentleman | @gentleman_e |
| CHARCOAL | 0.22 0.22 0.24 | The gentleman's one private bodyguard | @project_absence_char_guard_private |
| BLACK | 0.04 0.04 0.05 | The registrar | @project_absence_char_registrar_b |
| PLUM | 0.45 0.10 0.40 | The art critic | @project_absence_char_critic_b |
| DARK GREEN | 0.05 0.30 0.10 | The elderly man (A1) | @project_absence_char_oldman |
| ORANGE | 0.90 0.45 0.05 | Visitor A (S4/S17 man) | @project_absence_char_visitor_a |
| RUST | 0.55 0.25 0.10 | Visitor B (rust fur) | @project_absence_char_visitor_b |
| OLIVE | 0.42 0.40 0.12 | The husband | @project_absence_char_husband |
| LIME | 0.60 0.90 0.10 | The art student | @project_absence_char_student_c |
| COBALT | 0.12 0.25 0.80 | Collector A, the woman in cobalt | @project_absence_char_woman |
| CYAN | 0.05 0.75 0.80 | The parrot woman | @project_absence_char_woman_c |
| LIGHT GREY | 0.72 0.72 0.70 | The grandmother (+ wheelchair proxy) | @project_absence_char_grandmother |
| SLATE | 0.35 0.45 0.58 | The workman (S14/S16) | @project_absence_char_workman |
| MAROON | 0.40 0.08 0.12 | Press A | @project_absence_char_press_a |
| CORAL | 0.95 0.50 0.45 | Press B | @project_absence_char_press_b |
| TEAL | 0.06 0.35 0.38 | Dupe rich (S18, teal suit) | @project_absence_char_cleaner_rich |
| BURNT ORANGE (prop) | 0.72 0.30 0.05 | Dupe's trolley — mops, orange bucket, cream bottles, step ladder, gold V front, EMPTY rack pre-S2 | @project_absence_prop_cart / @prop_cart_b (painting rides it from S2 on) |

Rules bound to this system (every @Video 1 prompt):
- POSITION MAP lists every figure: colour word + name label + element id.
- "EVERY CHARACTER APPEARS EXACTLY ONCE — one proxy, one person, never both a
  mapped character AND a leftover grey figure" + `no proxy rendered as an extra
  person`.
- Continuity: each scene previz ENDS with characters at recorded positions;
  the next contiguous scene STARTS them there (ending positions logged per
  scene in PREVIZ-INDEX.md).
- Nobody stands idle: every present character carries a scene-appropriate
  activity in both the previz motion and the prompt beats.
