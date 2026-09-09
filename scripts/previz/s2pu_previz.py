# S2PU previz — ARE YOU FOLLOWING US (CEO 2026-09-09 20:20: repair of Draft 5 3:18-3:52,
# clip B of two; the CEO chose the side-on LOCKED angle). Camera static, square to the
# hall, looking +X — the S2P camera without its move. The six walk in from frame-right
# (from -Y) and stop in front of the hanging fish trap by 3s: Valder facing it at the
# left, Carrington at his shoulder, the bodyguard behind him, the two guards a pace and
# a half back, and DUPE with the cart at the right, two and a half metres behind the
# last guard. Valder turns to Dupe at 9s ("Are you following us with that?"); Dupe
# freezes (12s), then at 14s swings the cart a quarter turn to the wall and mops right
# there. Nothing else moves. No blush.
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

Y0 = 4.65                                       # marks centre on y=4.0, midway between the near columns at y=2 and y=6
WALK = 3.0                                      # they walk in over the first 3s from 3 m to the right
# (name, x = depth from the lens, dy = final mark along the hall, height)
MARKS = [
    ("VALDER",    1.60, +1.80, 1.86),
    ("GENTLEMAN", 2.30, +1.00, 1.79),
    ("BODYGUARD", 3.10, +0.10, 1.94),
    ("GUARD_V1",  1.00, -0.20, 1.84),
    ("GUARD_V2",  2.40, -1.10, 1.76),
    ("DUPE",      0.60, -2.50, 1.80),
]
people = []
for name, x, dy, h in MARKS:
    ob = spawn_char(col, name, (x, Y0 + dy - WALK), h=h, prefix="s2pu")
    people.append((ob, x, dy))
CART0 = (-0.15, Y0 - 3.10)
build_cart(col, (CART0[0], CART0[1] - WALK), prefix="s2pu", with_painting=True)
cart = bpy.data.objects.get("s2pu_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s2pu_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2pu_painting", (CART0[0], CART0[1] - WALK + 0.40, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# the fish trap: a woven oval hanging on wires at head height, far side of the hall,
# where Valder faces it.
bpy.ops.mesh.primitive_uv_sphere_add(location=(4.20, Y0 + 3.50, 2.00)); trap = bpy.context.object   # clear of Valder's head in the side-on view
trap.name = "s2pu_trap"; trap.scale = (0.45, 0.80, 0.55)
mt = bpy.data.materials.new("s2pu_trap_m"); mt.use_nodes = False; mt.diffuse_color = (0.55, 0.38, 0.15, 1)
trap.data.materials.append(mt)
box("s2pu_trap_wire", (4.20, Y0 + 3.50, 3.30), (0.02, 0.02, 1.60), (0.3, 0.3, 0.3, 1))

cam_d = bpy.data.cameras.new("CAM_S2PU"); cam_d.lens = 28
cam = bpy.data.objects.new("CAM_S2PU", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.rotation_euler = (R(90), 0, R(-90))         # looks +X; LOCKED for the whole clip
cam.location = (-5.40, 4.00, 1.70)              # between two near columns (x=-3.5, y=2 and 6): no column in the foreground

for (ob, _, _), z in zip(people, (2.20, 2.50, 2.20, 2.50, 2.20, 2.20)):   # staggered so the tags stay legible
    tag_label(col, ob.name.split("_", 1)[-1], ob, cam, z=z, size=0.22, prefix="s2pu")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# walk in over 0-3s (frames 1-72), then hold on the marks
for ob, x, dy in people:
    key(ob, 1,  x, Y0 + dy - WALK)
    key(ob, 72, x, Y0 + dy)
    key(ob, 480, x, Y0 + dy)
if cart:
    key(cart, 1,  CART0[0], CART0[1] - WALK)
    key(cart, 78, CART0[0], CART0[1])           # the cart stops last, a quarter second after Dupe
    key(cart, 336, CART0[0], CART0[1])
    # 14s: Dupe swings the cart a quarter turn to face the near wall and mops there
    sc.frame_set(336); cart.rotation_euler = (0, 0, 0);     cart.keyframe_insert("rotation_euler", frame=336)
    sc.frame_set(360); cart.rotation_euler = (0, 0, R(90)); cart.keyframe_insert("rotation_euler", frame=360)
    key(cart, 480, CART0[0], CART0[1])
dupe = people[-1][0]
key(dupe, 336, 0.60, Y0 - 2.50)
key(dupe, 360, 0.20, Y0 - 2.10)                 # steps to the turned cart's side, mopping
key(dupe, 480, 0.20, Y0 - 2.10)

def all_fcurves(act):
    fl = getattr(act, "fcurves", None)
    if fl is not None:
        for fc in fl: yield fc
        return
    for layer in getattr(act, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                for fc in cb.fcurves: yield fc
for ob in [p[0] for p in people] + ([cart] if cart else []):
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
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2PU-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2PU_previz.blend")
sc.frame_set(1)
bpy.ops.render.render(animation=True); print("RENDER-DONE")
