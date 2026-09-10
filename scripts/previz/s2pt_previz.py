# S2PT previz — THE TOUR, TOGETHER (CEO 2026-09-09 20:20: repair of Draft 5 3:18-3:52,
# clip A of two). Same Wes Anderson lateral track as S2P — camera square to the group,
# looking +X, dollying +Y at exactly their speed — but the cast is now the six the CEO
# named and nobody else: Valder leading, Carrington at his shoulder, Carrington's
# bodyguard a pace behind him, Valder's two guards a pace and a half back, and DUPE
# three metres behind the last of them pushing the cart. No registrar, no visitors.
# The mustard armchair on its blue rug slides into frame at ~13s (the chair line) and
# is level with Valder at ~16s.
import bpy, math
from math import radians as R
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 480          # 20s
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24
sc.timeline_markers.clear()
for o in bpy.data.objects:
    if o.name.startswith(("A_", "B_", "hvfly_tag", "Text.", "crack_")) or o.name in ("Cube", "Light"):
        o.hide_render = o.hide_viewport = True

exec(open(r"C:\Users\UsEr\Downloads\charlib.py").read())
col = sc.collection

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc); o = bpy.context.object; o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name+"_m"); m.use_nodes = False
    m.diffuse_color = color; o.data.materials.append(m); return o

BASE = -12.0
# (name, x = depth from the lens, dy = position along the walk, height)
LINE = [
    ("VALDER",    1.60, +2.40, 1.86),
    ("GENTLEMAN", 2.30, +1.60, 1.79),   # Carrington, at his shoulder, half a step back
    ("BODYGUARD", 3.10, +0.60, 1.94),   # a pace behind his employer
    ("GUARD_V1",  1.00, +0.80, 1.84),   # tall and thin
    ("GUARD_V2",  2.40, -0.30, 1.76),   # short and heavy
    ("DUPE",     -0.15, -2.90, 1.80),   # BEHIND his cart and pushing it — the cart leads him by 0.7 m.
                                        # x MATCHES the cart's x: at 0.60 he sat 0.75 m deeper than it and
                                        # the cart hid him completely from this side-on camera (measured
                                        # 2026-09-10: DUPE screen 0.76/0.32 depth 6.00 behind cart depth 5.25).
                                        # CEO 2026-09-10: takes 1-3 all had Dupe walking AHEAD of the cart
                                        # because this dy used to be -2.90 while the cart sat at -3.60.
                                        # Dupe must always be the SMALLER dy of the two — the party walks +Y.
                                        # First attempt swapped the two values and pushed Dupe OFF FRAME at
                                        # -3.60 (only his label rendered). So the CART moved forward to -2.20
                                        # instead and Dupe kept -2.90, his known in-frame mark.
]
people = []
for name, x, dy, h in LINE:
    ob = spawn_char(col, name, (x, BASE + dy), h=h, prefix="s2pt")
    people.append((ob, x, dy))
build_cart(col, (-0.15, BASE - 2.20), prefix="s2pt", with_painting=True)
cart = bpy.data.objects.get("s2pt_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s2pt_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2pt_painting", (-0.15, BASE - 1.80, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# the mustard armchair on its blue rug, against the far side of the hall (x=3.6, behind
# the far column line). Fixed objects enter at the frame's LEFT edge and drift right as
# the camera tracks +Y: this one enters at ~9.6s, passes Valder's line at ~12s and sits
# centre-left, between the party and the far wall, through the chair lines (13-19s).
CHAIR_Y = BASE + 12.6
box("s2pt_rug",   (3.60, CHAIR_Y, 0.01), (1.60, 2.00, 0.02), (0.10, 0.18, 0.45, 1))
box("s2pt_chair", (3.60, CHAIR_Y, 0.45), (0.80, 0.80, 0.90), (0.85, 0.62, 0.10, 1))

cam_d = bpy.data.cameras.new("CAM_S2PT"); cam_d.lens = 28
cam = bpy.data.objects.new("CAM_S2PT", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.rotation_euler = (R(90), 0, R(-90))         # looks +X across the hall; the walk (+Y) runs frame-right to frame-left
CAM0 = (-5.40, BASE - 0.90, 1.70)
cam.location = CAM0

for (ob, _, _), z in zip(people, (2.20, 2.50, 2.20, 2.50, 2.20, 2.20)):   # staggered so the tags stay legible
    tag_label(col, ob.name.split("_", 1)[-1], ob, cam, z=z, size=0.22, prefix="s2pt")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

TRAVEL = 14.0                                   # 0.70 m/s tour pace, as S2P
for ob, x, dy in people:
    key(ob, 1,   x, BASE + dy)
    key(ob, 480, x, BASE + dy + TRAVEL)
if cart:
    key(cart, 1,   -0.15, BASE - 2.20)
    key(cart, 480, -0.15, BASE - 2.20 + TRAVEL)
sc.frame_set(1);   cam.location = CAM0;                                    cam.keyframe_insert("location", frame=1)
sc.frame_set(480); cam.location = (CAM0[0], CAM0[1] + TRAVEL, CAM0[2]);   cam.keyframe_insert("location", frame=480)

def all_fcurves(act):
    fl = getattr(act, "fcurves", None)
    if fl is not None:
        for fc in fl: yield fc
        return
    for layer in getattr(act, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                for fc in cb.fcurves: yield fc
for ob in [p[0] for p in people] + [cam] + ([cart] if cart else []):
    ad = ob.animation_data
    if not ad or not ad.action: continue
    for fc in all_fcurves(ad.action):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'

for a, v in (("use_shadows", False), ("use_raytracing", False), ("use_fast_gi", False), ("taa_render_samples", 4)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2PT-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2PT_previz.blend")
sc.frame_set(1)
bpy.ops.render.render(animation=True); print("RENDER-DONE")
