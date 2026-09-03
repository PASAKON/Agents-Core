# S2P previz — THE TOUR. The first moving camera in the film, and the CEO asked
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
    ("VALDER",    3.20, +2.40, 1.86),
    ("GUARD_V1", 2.45, +3.10, 1.84),
    ("GUARD_V2", 4.60, +1.90, 1.76),
    ("GENTLEMAN", 3.90, +1.50, 1.79),
    ("BODYGUARD", 4.70, +0.70, 1.94),
    ("REGISTRAR", 3.40, -0.10, 1.80),
    ("COLLECTOR_A",     2.90, -0.90, 1.68),
    ("CRITIC",  3.70, -1.80, 1.64),
    ("VISITOR_B", 2.70, -2.50, 1.66),
    ("VISITOR_A", 3.50, -3.20, 1.78),
    ("STUDENT", 2.60, -4.10, 1.70),
    ("DUPE",      2.20, -5.40, 1.80),
]
people = []
for name, x, dy, h in LINE:
    ob = spawn_char(col, name, (x, BASE + dy), h=h, prefix="s2p")
    people.append((ob, x, dy))
build_cart(col, (1.45, BASE - 6.20), prefix="s2p", with_painting=True)
cart = bpy.data.objects.get("s2p_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s2p_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2p_painting", (1.45, BASE - 5.80, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# ---- the tracking camera. 35 mm at ~13 m covers 14.4 m along the walking axis
# and the procession spans 7.8 m, so nobody clips out at either end.
cam_d = bpy.data.cameras.new("CAM_S2P"); cam_d.lens = 35
cam = bpy.data.objects.new("CAM_S2P", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.rotation_euler = (R(90), 0, R(-90))         # (90,0,0) looks +Y; -90 about Z swings it to +X
cam.location = (-10.50, BASE - 1.00, 1.70)

for ob, _, _ in people:
    tag_label(col, ob.name.split("_", 1)[-1], ob, cam, prefix="s2p")

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
    key(cart, 1,   1.45, BASE - 6.20)
    key(cart, 480, 1.45, BASE - 6.20 + TRAVEL)

sc.frame_set(1);   cam.location = (-10.50, BASE - 1.00, 1.70)
cam.keyframe_insert("location", frame=1)
sc.frame_set(480); cam.location = (-10.50, BASE - 1.00 + TRAVEL, 1.70)
cam.keyframe_insert("location", frame=480)

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
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2P-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2P_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
