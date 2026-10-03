# -*- coding: utf-8 -*-
"""Shared blocks for «ขายชื่อ» EP1 (film 5) ACT1-3 data files: cast, wardrobe, voices,
languages, locations, negatives, and the script parser. Each ep5-ACTn.data.py imports this
file by path and adds only its own _META (who, where, when, the English action) and props.

The dialogue and its per-line direction are read from docs/scripts/ep5-khaichue-EP1-SCRIPT-v1.md
at import time, so the script the CEO reads and the prompts the runner fires cannot disagree.
Plates: docs/ops/briefs/ep5-plates-round1.json. States: docs/scripts/ep5-CAST-STATES.md.
"""
import re
from pathlib import Path

STYLE = ("Contemporary Thai realist drama, vertical 9:16, shot on 35mm, bright natural "
         "daylight in an urban fresh market and neighborhood soi in central Thailand, "
         "strong expressive acting, faces clearly readable.")
# Overflow acting (CEO 2026-09-27, story skill §Overflow acting): the one ensemble rule for every shot.
STYLE_ACTING = (STYLE + " Big, lively, theatrical Thai lakorn acting with no dead moments: from the "
                "first frame to the last, every person in frame keeps moving and keeps doing their own "
                "task; whoever is listening reacts with face, hands and body to every phrase and never "
                "stands still waiting for their turn.")

_SRI = ("a hardworking Thai woman of forty-eight with sun-kissed golden-tan skin, plump full "
        "cheeks, sharp dark eyes with fine laugh lines at the corners, dark black hair tied back "
        "in a neat low bun wrapped with an orange floral cloth band, wearing no glasses")
_TON = ("a handsome Thai young man of nineteen with rustic down-to-earth good looks, a lean athletic "
        "build from mechanical labor, sun-tanned golden-brown skin, thick straight dark eyebrows, "
        "warm expressive dark almond-shaped eyes, short black hair with tapered sides, a strong "
        "jawline, a subtle hint of a small single canine snaggletooth when he smiles, and fingertips "
        "permanently stained with dark engine grease around the cuticles")
_BOY = ("a stocky Thai man of twenty-eight with a slight paunch, round face, an undercut hairstyle "
        "slicked back with wet-look pomade, gold-rimmed sunglasses pushed up on top of his head, a "
        "thick gold chain necklace around his neck, a gold wristwatch, wearing a short-sleeved rayon "
        "camp shirt printed with a bold yellow-and-black tiger stripe pattern with top buttons open, "
        "dark tailored trousers and black leather loafers, chewing gum")
_FON = ("a slender Thai young woman of twenty-three with a delicate oval face, clear skin with no "
        "makeup, dark hair pulled back into a sleek smooth high ponytail, soft gentle dark eyes, "
        "wearing a button-down short-sleeved mint-green cotton shirt, dark grey slim trousers, "
        "flat black shoes and a small black crossbody sling bag")
_COL = ("a weathered Thai man of forty-five with flat impassive features, wearing a navy-blue baseball "
        "cap with no logo, a plain brown short-sleeved polo shirt with no badge and no insignia, "
        "dark brown trousers, a black canvas zippered waist pouch buckled around his waist, and "
        "worn black slip-on shoes")
_FRI = ("a lean Thai young man of nineteen with short black hair tipped with bleached-gold highlights, "
        "lively dark eyes, wearing a plain cobalt-blue sleeveless basketball jersey with white trim and "
        "no numbers, dark sports shorts, and blue rubber flip-flops")

CHAR = {
    "sri": ("@sri__face",
            _SRI + ", wearing a papaya-orange vendor apron with a deep front pocket over a plain cream "
            "short-sleeved cotton blouse with sleeves rolled up, a dark floral tube skirt and worn rubber flip-flops",
            "The woman in the papaya-orange apron"),
    "sri_noapron": ("@sri__face",
                    _SRI + ", wearing a plain cream short-sleeved cotton blouse with rolled-up sleeves, "
                    "a dark floral tube skirt and worn rubber flip-flops with no apron",
                    "The woman in the cream blouse"),
    "ton": ("@ton__face",
            _TON + ", wearing a plain heather-grey crewneck T-shirt with light oil smudges near the hem, "
            "faded dark blue jeans, worn dark canvas sneakers, and a folded red cotton work rag tucked into his back right pocket",
            "The young man in the grey T-shirt"),
    "boy": ("@boy__face", _BOY, "The man in the tiger-print shirt"),
    "fon": ("@fon__face", _FON, "The young woman in the mint-green shirt"),
    "col": ("@collector__face", _COL, "The man in the navy-blue cap"),
    "fri": ("@friend__face", _FRI, "The young man in the basketball jersey"),
}

WARDROBE = {
    "sri": "@sri__apron",
    "sri_noapron": "@sri__noapron",
    "ton": "@ton__work",
    "boy": "@boy__tiger",
    "fon": "@fon__mint",
    "col": "@collector__work",
    "fri": "@friend__jersey",
}

# Timbre, pitch and age ONLY (CMO_Standard_Story_ThaiMoralDrama §Emotion rule 3).
_V = "(prompt only, no bound voice)"
VOICE = {
    "sri": (_V, "the warm mid-pitched voice of a Thai woman of forty-eight with a slight vendor huskiness"),
    "sri_noapron": (_V, "the warm mid-pitched voice of a Thai woman of forty-eight with a slight vendor huskiness"),
    "ton": (_V, "the clear light tenor voice of a Thai man of nineteen"),
    "boy": (_V, "the loud nasal baritone voice of a Thai man of twenty-eight with a Bangkok street accent"),
    "fon": (_V, "the soft low alto voice of a Thai woman of twenty-three"),
    "col": (_V, "the flat dry baritone voice of a Thai man of forty-five"),
    "fri": (_V, "the fast bright tenor voice of a Thai man of nineteen"),
}

LANG = {
    "sri": "standard Central Thai with an everyday market vendor cadence",
    "sri_noapron": "standard Central Thai with an everyday market vendor cadence",
    "ton": "standard Central Thai with an everyday youth cadence",
    "boy": "standard Central Thai with a Bangkok street slang cadence",
    "fon": "standard Central Thai with a soft polite cadence",
    "col": "standard Central Thai with a flat businesslike cadence",
    "fri": "standard Central Thai with a fast casual youth cadence",
}

_MARKET_STALL = ("an open-air daytime som-tam stall in a Thai fresh market: a wooden counter under a "
                 "large orange canvas umbrella, a large brown glazed clay mortar with a wooden pestle, "
                 "baskets of green papayas, chilies and limes, an insulated red ice box, red plastic stools, "
                 "adjacent stalls empty with bare tables")
_MARKET_ROAD = ("the roadside asphalt curb in front of the open-air fresh market during the day, with "
                "the market's orange awnings visible behind")
_MARKET_BACK = ("the quiet narrow service walkway behind the market stalls during the day, with stacks "
                "of empty red and blue plastic crates piled against a concrete wall")
_REPAIR_SOI = ("a roadside repair spot in a neighborhood soi under a large shady tamarind tree during "
               "the day, with a blue plastic tarpaulin overhead, a wooden bench, hanging inner tubes and tires, "
               "a round metal water basin, and an oily concrete ground")
_PICKUP_CAB = ("the interior cabin of a four-door pickup truck parked on the street in broad daylight: "
               "dark fabric front bucket seats and rear bench, steering wheel on the right, a closed plastic "
               "center console box with a hinged lid between the front seats, daylight through the windows, "
               "all digital displays dark and inactive")

LOC = {
    "market_stall": ("@market__stall", _MARKET_STALL),
    "market_road": ("@market__road", _MARKET_ROAD),
    "market_back": ("@market__back", _MARKET_BACK),
    "repair_soi": ("@repair__soi", _REPAIR_SOI),
    "pickup_cab": ("@pickup__cab", _PICKUP_CAB),
}

NOT = {
    "nosubs": "No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame.",
    "nologo": "Every vehicle, machine, card, container and object is completely plain: no brand names, "
              "no logos, no badges, no stickers, no letters and no numbers anywhere.",
    "nocash": "Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.",
    "noscreen": "Every smartphone screen is turned away from the camera or dark: no numbers, no readable text, "
                "no app interfaces, no chat messages and no notifications are visible on any screen.",
    "noextra": "Nobody else is in the frame: no passers-by, no customers, no crowds, no children; at most "
               "three people in the shot.",
    "nouniform": "Nobody wears a uniform, an official badge, a lanyard, police insignia or government emblems.",
    "daylight": "The scene is lit entirely by bright natural daytime sunlight, with no night lighting, "
                "no darkness and no neon glow.",
}

PROP_FOR_NOT = {}

_NAME = {
    "sri": "แม่ศรี",
    "sri_noapron": "แม่ศรี",
    "ton": "ต้น",
    "boy": "บอย",
    "fon": "ฝน",
    "col": "คนเก็บค่าแผง",
    "fri": "เพื่อนต้น",
}

T1 = "the morning, bright natural morning sunlight in dry weather"
T2 = "the late morning, bright sunny late morning light"
T3 = "the early afternoon, bright hot midday sunlight, one o'clock"
T4 = "the mid-afternoon, hot bright afternoon sun, three o'clock"
T5 = "the late afternoon, warm bright late afternoon sunlight"


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from SCRIPT-v1 (S1-68)
    and the EP3 closing script (S69-78); the two files never share a shot number."""
    text = "\n".join(Path(__file__).with_name(f).read_text(encoding="utf-8")
                     for f in ("ep5-khaichue-EP1-SCRIPT-v1.md", "ep5-EP3-SCRIPT-v1.md"))
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r"^### SHOT (\d+) ", ln)
        if m:
            cur = int(m.group(1))
            out[cur] = []
            continue
        m = re.match(r'^\*\*บทพูด\*\* (\S+) `"(.+)"` — (.+)$', ln)
        if m and cur is not None:
            out[cur].append((m.group(1), m.group(3).strip(), m.group(2)))
    return out


def build_shots(meta):
    lines = _lines_from_script()
    shots = []
    for n in sorted(meta):
        secs, framing, chars, loc, tod, action, nots = meta[n]
        spoken = []
        for who, direction, line in lines.get(n, []):
            key = next((c for c in chars if _NAME.get(c) == who), None)
            if key is None:
                raise SystemExit(f"shot {n}: speaker {who} is not in the shot's cast {chars}")
            spoken.append((key, direction, line))
        shots.append((n, secs, framing, chars, loc, tod, action, spoken, nots))
    return shots


def apply_directions(shots, direction):
    """Overflow acting: replace every spoken direction with the (shot, speaker) entry in `direction`.
    Strict: a spoken line with no entry stops the build, so no line is left at the script's flat reading."""
    out = []
    for (n, secs, framing, chars, loc, tod, action, spoken, nots) in shots:
        missing = [k for k, _d, _l in spoken if (n, k) not in direction]
        if missing:
            raise SystemExit(f"shot {n}: no overflow-acting direction for {missing}")
        spoken = [(k, direction[(n, k)], line) for k, _d, line in spoken]
        out.append((n, secs, framing, chars, loc, tod, action, spoken, nots))
    return out
