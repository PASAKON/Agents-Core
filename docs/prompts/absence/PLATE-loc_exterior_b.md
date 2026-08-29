# PLATE — `loc_exterior_b` · THE BACK OF THE MUSEUM
The old `project_absence_loc_exterior` is terminally **"Not eligible"** in the
composer's reference picker — dimmed, no remediation control — which blocks
**S13a and S13b**. This replaces it under a NEW name (never re-point an
existing Element; it silently serves the old asset).

## ⚠️ UPLOAD THIS REFERENCE — CEO's instruction
`docs/prompts/absence/REF-museum-exterior-front.png`

> "คุณต้องใส่ REF ของ Museum ไปด้วย Model จะได้ Generate มุมข้างๆ ได้เหมือนจริง"

It is the museum's grand FRONT in four views. We are generating the same
building's BACK, so the model needs to see what building it is: cream
limestone cladding in smooth curved streamline-moderne masses, polished
chromium trumpet columns (the same family as the interior), a gold V, pink
terrazzo paving. Without it the model invents an unrelated loading dock.

Attach `@loc_hall_big_e` as well, for the film's material and light language.

## The prompt
```
16:9 landscape, 2K. THE SERVICE SIDE OF THE MUSEUM IN THE REFERENCE IMAGE —
the same building, the same cream limestone cladding, the same smooth curved
streamline-moderne massing, seen from BEHIND, where nobody photographs it.

KEEP SAME the building's material: KEEP SAME the cream limestone, KEEP SAME
the curved wall forms, KEEP SAME the architectural period. This is the back
of THAT building, not a different one.

Here the cladding gives way to plain unpainted concrete: exposed pipework
running along the wall, a heavy steel service door, a small delivery bay with
a raised concrete loading edge, two ordinary plastic bins parked against the
wall. Warm afternoon light, long low-angle shadows across the ground.

Photographed, not rendered: fine film grain, realistic architectural
photography, slightly desaturated concrete against warm golden light. Empty,
quiet, utilitarian — the opposite of the grand front in the reference.

NO PEOPLE. NO FIGURES. NO SILHOUETTES.
```

NEGATIVE: no people, no figures, no silhouettes, no faces, no hands, no cars,
no landscaping, no signage, no logos, no readable text, no graffiti, no modern
glass, no ornate architecture, no columns, no marble, no red carpet, no grand
entrance, no gold V on this side, no HDR, no CGI sheen, no night, no darkness,
no rain.

## After it exists
Repoint `s13-the-back-door.txt` from `@project_absence_loc_exterior` to the new
Element, then fire S13a and S13b.
