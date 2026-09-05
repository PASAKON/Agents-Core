# S2H previz — THE COUPLE. Camera sits BEHIND the hero wall at the crack's own
# height, looking out down the gallery. The wall panels are hidden for the
# render so the crack reads as a black silhouette in the extreme foreground,
# with everyone in the room BEHIND it. That ordering is the whole point of the
# shot: the model keeps putting people in front of the crack and it is wrong.
import bpy, math
from math import radians as R
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 480          # 20s
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24
sc.timeline_markers.clear()                     # marker binds CAM_FLY4 otherwise
for o in bpy.data.objects:
    if o.name.startswith(("A_", "B_", "hvfly_tag", "Text.")):
        o.hide_render = o.hide_viewport = True
# hide the wall itself, keep the crack — the camera is inside the cavity
# CEO 2026-09-05: the crack comes OUT of the previz entirely. Its shape must
# come from the location plate, which is a photograph of the real break; a grey
# proxy drawn here is a crude approximation competing with that plate, and a
# video reference beats a still every time, so the proxy was winning and putting
# a machine-drawn star into the finished film. The previz now carries CAMERA and
# BLOCKING only.
for _c in [o for o in bpy.data.objects if o.name.startswith("crack_")]:
    _c.hide_render = _c.hide_viewport = True
for n in ("wall_hero_panel", "wall_crack_end"):
    ob = bpy.data.objects.get(n)
    if ob: ob.hide_render = ob.hide_viewport = True

exec(open(r"C:\Users\UsEr\Downloads\charlib.py").read())
col = sc.collection

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc); o = bpy.context.object; o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name+"_m"); m.use_nodes = False
    m.diffuse_color = color; o.data.materials.append(m); return o

# the couple, far RIGHT of frame as the CEO asked
wife    = spawn_char(col, "VISITOR_B", ( 1.85, -19.7), h=1.66, prefix="s2i")
# CEO 2026-09-04: the couple is TWO WOMEN. visitor_b (RUST) cries; collector_a
# (COBALT) is the partner who comforts her. The man in the maroon suit is not
# part of this couple. Same correction as s2h_previz.py.
partner = spawn_char(col, "COLLECTOR_A", ( 2.60, -19.5), h=1.70, prefix="s2i")
# Dupe well left, working, never crossing to them
dupe    = spawn_char(col, "DUPE",      (-2.6, -17.2), h=1.80, prefix="s2i")
build_cart(col, (-3.3, -16.6), prefix="s2i", with_painting=True)
cart = bpy.data.objects.get("s2i_cart_base")
if cart:
    cart.rotation_euler.z = R(90)
    for o in bpy.data.objects:
        if o.name.startswith("s2i_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2i_painting", (-3.3, -16.2, 1.35), (0.80,0.05,0.72), (0.45,0.45,0.45,1)).parent = cart

cam_d = bpy.data.cameras.new("CAM_S2I"); cam_d.lens = 21
cam = bpy.data.objects.new("CAM_S2I", cam_d); sc.collection.objects.link(cam); sc.camera = cam
# THE STUDENT, entering through the red door 43 m away. She cannot reach the
# crack in one shot — 43 m is 36 s of ordinary walking and the clip is 20 — so
# the scene jumps forward in time at 7s on the SAME camera, then cuts to the
# plaque at 13s.
student = spawn_char(col, "STUDENT", (0.0, 21.0), h=1.68, prefix="s2i")
tag_label(col, "STUDENT", student, cam, prefix="s2i") if False else None

# doors swing open as she arrives
dL, dR = bpy.data.objects.get("red_door_L"), bpy.data.objects.get("red_door_R")
for leaf, sign in ((dL, 1), (dR, -1)):
    if not leaf: continue
    leaf.rotation_mode = 'XYZ'
    for fr, ang in ((1, 0), (24, 0), (48, sign * 1.15), (480, sign * 1.15)):
        sc.frame_set(fr); leaf.rotation_euler.z = ang
        leaf.keyframe_insert("rotation_euler", frame=fr)

WALLPOV = ((0.0, -22.45, 2.45), (R(90), 0, 0), 21)       # A + C: crack in foreground
COUPLE  = ((4.9, -16.2, 1.62), None, 34)                 # B: cutaway, aimed at the wife
PLAQUE  = ((1.35, -20.55, 1.35), (R(84), 0, R(203)), 80) # D: off-axis so she does not block it
DUPECU  = ((-0.9, -14.4, 1.70), None, 55)                # E: Dupe, aimed at him
cam.location, cam.rotation_euler = WALLPOV[0], WALLPOV[1]
for who, ob in (("WIFE", wife), ("PARTNER", partner), ("DUPE", dupe), ("STUDENT", student)):
    tag_label(col, who, ob, cam, prefix="s2i")

# aim helpers — hand-typed euler angles have missed three times tonight
_aimW = bpy.data.objects.new("AIM_WIFE", None); sc.collection.objects.link(_aimW)
_aimW.parent = wife; _aimW.location = (0, 0, 0.55)
_aimD = bpy.data.objects.new("AIM_DUPE", None); sc.collection.objects.link(_aimD)
_aimD.parent = dupe; _aimD.location = (0, 0, 0.60)
_trk = cam.constraints.new('TRACK_TO'); _trk.track_axis = 'TRACK_NEGATIVE_Z'; _trk.up_axis = 'UP_Y'
_trk.influence = 0.0

def ckey(fr, spec):
    loc, rot, lens = spec
    _trk.target = _aimW if spec is COUPLE else (_aimD if spec is DUPECU else None)
    _trk.influence = 1.0 if _trk.target else 0.0
    sc.frame_set(fr)
    _trk.keyframe_insert("influence", frame=fr)
    if _trk.target: _trk.keyframe_insert("target", frame=fr) if False else None
    cam.location = loc
    if rot: cam.rotation_euler = rot
    cam.data.lens = lens
    cam.keyframe_insert("location", frame=fr)
    if rot: cam.keyframe_insert("rotation_euler", frame=fr)
    cam.data.keyframe_insert("lens", frame=fr)
# five shots. The cutaway at 6s is what makes the geometry work: she needs
# 36 s to cross 43 m and the clip is 20, so we leave her mid-walk and come back
# when she has arrived.
ckey(1,   WALLPOV); ckey(143, WALLPOV)    # A  0.0-6.0s  door opens, she enters far off
ckey(144, COUPLE);  ckey(239, COUPLE)     # B  6.0-10.0s cutaway: Dupe + the crying wife
ckey(240, WALLPOV); ckey(383, WALLPOV)    # C 10.0-16.0s she is at the crack, and speaks
ckey(384, PLAQUE);  ckey(431, PLAQUE)     # D 16.0-18.0s the 2,000,000 insert
ckey(432, DUPECU);  ckey(480, DUPECU)     # E 18.0-20.0s Dupe, looking at the lot of them

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# the couple barely move — she is rooted, he closes the last half metre to her
key(wife, 1, 1.85, -19.7); key(wife, 288, 1.85, -19.7)
key(partner, 1, 2.75, -19.4); key(partner, 96, 2.30, -19.6); key(partner, 288, 2.30, -19.6)

# Dupe works his way slowly along, never toward them. 0.35 m/s — he is cleaning,
# not walking; the pace comes from the motion research, not from feel.
key(dupe, 1, -2.6, -17.2); key(dupe, 240, -1.9, -17.2); key(dupe, 480, -2.4, -17.2)

# the student. 0-7s she is far off by the door; at frame 168 the scene jumps
# forward in time and she is already close, walking the last stretch to the
# crack, arriving at 13s. 1.2 m/s throughout.
key(student, 1,   0.0, 21.0)
key(student, 48,  0.0, 21.0)          # the doors open
key(student, 143, 0.0, 16.3)          # 4.7 m walked when we cut away
key(student, 144, 0.0, -14.5)         # the cutaway covers the rest of the hall
key(student, 240, 0.0, -19.9)         # back on her: arrived at the crack
key(student, 480, 0.0, -19.9)         # and she stays there

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2I-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2I_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
