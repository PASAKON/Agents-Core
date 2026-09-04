# S2PB previz — THE REVERSE. Same scene, same marks, camera moved OUT of
# the wall and into the gallery behind the group, looking back at the broken
# wall. Everyone watching the break now has their back to us; who turns and
# who does not is decided by what each of them is doing, not by a rule.
# CEO 2026-09-04: every scene gets both angles, sixteen in total.
# for it by name: a Wes Anderson lateral track. The camera sits square to the
# group, looks along +X, and dollies alongside them at exactly their own speed
# so they stay locked in frame while the gallery streams past behind. Flat on,
# no perspective drift, no reframing, no easing at either end — a lateral track
# that accelerates reads as a handheld follow and loses the whole effect.
#
# Everyone is on the marks S2O left them on at frame 1 and then walks together.
# Valder leads and narrates to the room; he only ever turns to the GENTLEMAN.
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

exec(open(r"C:\Users\UsEr\Downloads\charlib.py").read())
col = sc.collection

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc); o = bpy.context.object; o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name+"_m"); m.use_nodes = False
    m.diffuse_color = color; o.data.materials.append(m); return o

# ---- the procession. y is the walking axis, so these offsets are what spreads
# them ACROSS the frame; x is depth from the lens and is staggered so they do
# not read as a single flat rank. Valder is at the head, the GENTLEMAN at his
# shoulder because he is the only one being spoken to, Dupe trailing far back
# with the cart because he is staff and was never invited.
BASE = -12.0
LINE = [
    ("VALDER", 1.60, +2.40, 1.86),
    ("GUARD_V1", 0.85, +3.10, 1.84),
    ("GUARD_V2", 3.00, +1.90, 1.76),
    ("GENTLEMAN", 2.30, +1.50, 1.79),
    ("BODYGUARD", 3.10, +0.70, 1.94),
    ("REGISTRAR", 1.80, -0.10, 1.80),
    ("COLLECTOR_A", 1.30, -0.90, 1.68),
    ("CRITIC", 2.10, -1.80, 1.64),
    ("VISITOR_B", 1.10, -2.50, 1.66),
    ("VISITOR_A", 1.90, -3.20, 1.78),
    ("STUDENT", 1.00, -4.10, 1.70),
    ("DUPE", 0.60, -5.40, 1.80),
]
people = []
for name, x, dy, h in LINE:
    ob = spawn_char(col, name, (x, BASE + dy), h=h, prefix="s2pb")
    people.append((ob, x, dy))
build_cart(col, (-0.15, BASE - 6.20), prefix="s2pb", with_painting=True)
cart = bpy.data.objects.get("s2pb_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s2pb_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2pb_painting", (-0.15, BASE - 5.80, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# ---- the tracking camera. 35 mm at ~13 m covers 14.4 m along the walking axis
# and the procession spans 7.8 m, so nobody clips out at either end.
cam_d = bpy.data.cameras.new("CAM_S2PB"); cam_d.lens = 35
cam = bpy.data.objects.new("CAM_S2PB", cam_d); sc.collection.objects.link(cam); sc.camera = cam
# B ANGLE (CEO 2026-09-04): the far end, 180 deg opposite the A camera, and
# LOCKED. The tour walks 14 m from BASE toward +y, so the camera stands behind
# where they start and they walk AWAY down the room — backs the whole clip,
# which is what the CEO asked this angle for. A camera facing the broken wall
# lost them inside four seconds.
cam.location = (0.20, BASE - 7.00, 1.70)   # 7 m behind the head of the procession
cam.rotation_euler = (R(90), 0, 0)         # level, looking along +y after them

for ob, _, _ in people:
    tag_label(col, ob.name.split("_", 1)[-1], ob, cam, prefix="s2pb")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# 14.0 m over 20 s = 0.70 m/s. A tour pace: slower than an ordinary walk
# because the whole group keeps half-stopping to look at what he is pointing
# at. Everyone and the camera advance by the identical amount, which is what
# holds the group still in frame while the room slides.
TRAVEL = 14.0
for ob, x, dy in people:
    key(ob, 1,   x, BASE + dy)
    key(ob, 480, x, BASE + dy + TRAVEL)
if cart:
    key(cart, 1,   -0.15, BASE - 6.20)
    key(cart, 480, -0.15, BASE - 6.20 + TRAVEL)

# NO CAMERA KEYFRAMES ON THE B ANGLE. The A version tracks with the group; this
# one is locked and lets them walk out of it. Leaving the old keyframes here is
# what made the first B render come back as a copy of the A shot.

# LINEAR on everything. Blender's default bezier eases in and out of every
# channel, and an eased lateral track is the one thing that cannot look like
# Wes Anderson — the move has to start at speed and stop at speed.
def all_fcurves(act):
    """Blender 5.2 actions are SLOTTED: the flat `action.fcurves` list is gone
    and raises AttributeError. Curves now live at
    action.layers[].strips[].channelbags[].fcurves. Handle both so this script
    still runs on an older Blender."""
    fl = getattr(act, "fcurves", None)
    if fl is not None:
        for fc in fl:
            yield fc
        return
    for layer in getattr(act, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                for fc in cb.fcurves:
                    yield fc

for ob in [p[0] for p in people] + [cam] + ([cart] if cart else []):
    ad = ob.animation_data
    if not ad or not ad.action: continue
    for fc in all_fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2PB-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2PB_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
