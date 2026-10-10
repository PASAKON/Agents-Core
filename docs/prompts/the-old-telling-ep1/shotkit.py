"""Helpers shared by the ACT 4, 5 and 6 shot lists of The Old Telling EP1 (data only, no I/O, no paid call).

Called by act4_shots.py, act5_shots.py, act6_shots.py (each does `from shotkit import *`) and read by build_act456.py through those files.
Every shot is one dict in the same shape build_act3.py used: key, title, sec, refs, refover, line, header, heading, frame, beats, sound, crit, hold.
CEO 2026-10-10: 'ทำ ARCT 4-6 ต่อได้เลย อณุมติ CU เพิ่มอีก 200'.
"""

CAVERN = {"STAIR": "@STAIR: THE CAVERN LOOK ONLY: the wet dark rough-cut rock, the cold mist and the cold verdigris light of THE STAIR's cavern. Take nothing else from it: no stair, no steps, no daylight opening."}
COLD = "There is no warm light at all: the only light is a faint cold verdigris glow."
EMBER = "The only warm light is a low ember glow on the horizon and on the nearest edges of things; everything else is cold verdigris and grey."

# one description per recurring person who has no entity of ours (kept word for word across shots so the look repeats)
WOMEN = ("adult women of Thrace in long ankle-length wool dresses of muted ochre and grey-green, a spotted fawn skin draped over one shoulder, "
         "wreaths of ivy in their hair and long wooden staffs wound with ivy; no bare skin shown except hands and faces, faces in shadow or backlit")
BOATMAN = "a tall hooded boatman in a long dark robe, his face in deep shadow, standing at the stern of a long narrow black wooden boat and holding a long pole"


def hdr(sec, cam):
    return f"{sec}s · 1080p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS. Camera {cam}; no zoom, no cut."


def snd(place, extra="No voices, no speech, no singing."):
    return f"overall_soundscape: only the sounds of the place: {place}. {extra}\nnon_diegetic_music: none."


def shot(key, title, sec, refs, line, cam, heading, frame, beats, sound, negs, hold, refover=None):
    """hold = seconds (number) at which the final '[Xs] Hold' beat sits; the closing negation names the same second."""
    d = dict(key=key, title=title, sec=sec, refs=refs, line=line, header=hdr(sec, cam), heading=heading, frame=frame, beats=beats, sound=sound,
             crit="CRITICAL NEGATIVES: " + ", ".join(negs) + f", nothing new starts after {hold} seconds.", hold=f"{hold}s")
    if refover:
        d["refover"] = refover
    return d
