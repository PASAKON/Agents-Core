# S3A previz — THE FIRST CUSTOMER, take 2 (CTO 2026-09-10 01:05 after take 1's shot 2 drifted
# into an over-the-shoulder). 10 s = 240 frames, ONE hard cut at 5 s, two LOCKED cameras bound
# by timeline markers:
#   SHOT 1 (frames 1-120)   CAM_A at the near end of the hall, waist height, straight down the
#                           axis to the red doors (y=+21.9). The old man appears inside the door
#                           at 1 s and walks a few steps in, stops at 4 s. Dupe mid-distance, mopping.
#   SHOT 2 (frames 121-240) CAM_B side-on, bolted between the near columns (x=-2.8, y=4.0),
#                           looking +X. The old man walks THROUGH the frame left→right at ~1.2 m/s
#                           past a plinth and a vitrine; Dupe deep behind, still, watching.
import bpy, math
from math import radians as R
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 240
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

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# ---- people
oldman = spawn_char(col, "OLDMAN", (0.0, 22.6), h=1.78, prefix="s3a")   # parked behind the end wall
dupe   = spawn_char(col, "DUPE",   (0.6, 9.0),  h=1.80, prefix="s3a")
build_cart(col, (1.3, 8.2), prefix="s3a", with_painting=True)
cart = bpy.data.objects.get("s3a_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s3a_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s3a_painting", (1.3, 7.65, 0.40), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# shot 1: door → a few steps in → stop
key(oldman, 1,   0.0, 22.6)
key(oldman, 24,  0.0, 22.6)
key(oldman, 30,  0.0, 21.2)          # through the door
key(oldman, 96,  0.0, 18.6)          # stops just inside, looks the hall over
key(oldman, 120, 0.0, 18.6)
# shot 2: side-on, walks through the frame left (+Y) → right (-Y)
key(oldman, 121, 0.8, 6.9)
key(oldman, 240, 0.8, 1.1)
# Dupe: shot 1 mid-distance mopping (tiny bob), shot 2 deep behind the man, still
key(dupe, 1,   0.6, 9.0); key(dupe, 120, 0.6, 9.0)
key(dupe, 121, 3.0, 5.2); key(dupe, 240, 3.0, 5.2)
if cart:
    key(cart, 1, 1.3, 8.2); key(cart, 120, 1.3, 8.2)
    key(cart, 121, 3.0, 3.9); key(cart, 240, 3.0, 3.9)

# shot-2 dressing: a white plinth with a bronze and a glass vitrine on the near side
box("s3a_plinth",  (1.7, 5.4, 0.50), (0.50, 0.50, 1.00), (0.92, 0.92, 0.90, 1))
box("s3a_bronze",  (1.7, 5.4, 1.22), (0.30, 0.30, 0.44), (0.35, 0.25, 0.12, 1))
box("s3a_vitrine", (1.7, 2.4, 0.80), (0.60, 0.60, 1.60), (0.75, 0.85, 0.90, 0.6))

# ---- cameras
camA_d = bpy.data.cameras.new("CAM_S3A_A"); camA_d.lens = 35
camA = bpy.data.objects.new("CAM_S3A_A", camA_d); sc.collection.objects.link(camA)
camA.location = (0.0, 0.0, 1.10); camA.rotation_euler = (R(90), 0, 0)          # looks +Y down the axis
camB_d = bpy.data.cameras.new("CAM_S3A_B"); camB_d.lens = 28
camB = bpy.data.objects.new("CAM_S3A_B", camB_d); sc.collection.objects.link(camB)
camB.location = (-2.8, 4.0, 1.30); camB.rotation_euler = (R(90), 0, R(-90))     # looks +X, between the near columns
sc.camera = camA
mA = sc.timeline_markers.new("SHOT1", frame=1);   mA.camera = camA
mB = sc.timeline_markers.new("SHOT2", frame=121); mB.camera = camB

# labels: one set per camera, shown only in its own shot
def shot_labels(cam, first, last, z_old, z_dupe, tag):
    for ob, txt, z in ((oldman, "OLDMAN", z_old), (dupe, "DUPE", z_dupe)):
        t = tag_label(col, txt, ob, cam, z=z, size=0.22, prefix=f"s3a{tag}")
        for fr, hid in ((1, first != 1), (first, False), (last + 1, True)):
            if fr > 240: continue
            sc.frame_set(fr); t.hide_render = hid; t.hide_viewport = hid
            t.keyframe_insert("hide_render", frame=fr); t.keyframe_insert("hide_viewport", frame=fr)
shot_labels(camA, 1, 120, 2.05, 2.05, "A")
shot_labels(camB, 121, 240, 2.05, 2.35, "B")

def all_fcurves(act):
    fl = getattr(act, "fcurves", None)
    if fl is not None:
        for fc in fl: yield fc
        return
    for layer in getattr(act, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                for fc in cb.fcurves: yield fc
for ob in [oldman, dupe] + ([cart] if cart else []):
    ad = ob.animation_data
    if not ad or not ad.action: continue
    for fc in all_fcurves(ad.action):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
# the 120→121 jump must be a hard cut, not a slide: CONSTANT on the last shot-1 key
for ob in [oldman, dupe] + ([cart] if cart else []):
    ad = ob.animation_data
    if not ad or not ad.action: continue
    for fc in all_fcurves(ad.action):
        for kp in fc.keyframe_points:
            if abs(kp.co.x - 120) < 0.5: kp.interpolation = 'CONSTANT'

for a, v in (("use_shadows", False), ("use_raytracing", False), ("use_fast_gi", False), ("taa_render_samples", 4)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S3A-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S3A_previz.blend")
sc.frame_set(1)
bpy.ops.render.render(animation=True); print("RENDER-DONE")
