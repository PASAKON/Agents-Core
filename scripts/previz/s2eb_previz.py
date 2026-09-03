# S2Eb previz — THE FAKE CLEANING, IN THE COLONNADE.
# Two faults in the S2E previz this replaces:
#  1. Dupe's proxy (pale cylinder + dome) read as an extra CHROMIUM COLUMN
#     standing in the middle of the room. Fixed by giving him a clearly
#     non-column silhouette and standing him against depth, not a blank wall.
#  2. It still showed the crack and plaque, which S2Eb must not contain at all.
import bpy, math
from math import radians as R
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 288
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24
sc.timeline_markers.clear()
for o in bpy.data.objects:
    if o.name.startswith(("A_", "B_", "hvfly_tag", "Text.")):
        o.hide_render = o.hide_viewport = True
# S2Eb contains NO crack and NO plaque — hide them so the previz cannot suggest them
for o in bpy.data.objects:
    if o.name.startswith("crack_") or o.name == "plaque":
        o.hide_render = o.hide_viewport = True

exec(open(r"C:\Users\UsEr\Downloads\charlib.py").read())
col = sc.collection

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc); o = bpy.context.object; o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name+"_m"); m.use_nodes = False
    m.diffuse_color = color; o.data.materials.append(m); return o

# Dupe stands in the colonnade beside a column, between two of them so his own
# silhouette cannot be mistaken for one.
dupe = spawn_char(col, "DUPE", (-2.1, -4.0), h=1.80, prefix="s2eb")
# Break the plain-cylinder read that made him look like a chromium column.
# Parenting WITHOUT matrix_parent_inverse makes .location a LOCAL offset — the
# trap this project's own skill documents, and which I walked into by setting
# world coordinates on the first attempt.
for nm, loc, dim in (("s2eb_dupe_shoulders", (0.0, 0.0, 0.72), (0.66, 0.30, 0.15)),
                     ("s2eb_dupe_armL",      (-0.30, 0.10, 0.42), (0.14, 0.14, 0.62)),
                     ("s2eb_dupe_armR",      (0.34, 0.16, 0.40), (0.14, 0.14, 0.58)),
                     ("s2eb_dupe_cloth",     (0.46, 0.30, 0.46), (0.24, 0.05, 0.24)),
                     ("s2eb_dupe_cap",       (0.0, 0.06, 1.06), (0.40, 0.40, 0.07))):
    o = box(nm, (0, 0, 0), dim, (0.97, 0.97, 0.97, 1))
    o.parent = dupe
    o.location = loc

build_cart(col, (-2.9, -3.1), prefix="s2eb", with_painting=True)
cart = bpy.data.objects.get("s2eb_cart_base")
if cart:
    cart.rotation_euler.z = R(90)
    for o in bpy.data.objects:
        if o.name.startswith("s2eb_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2eb_painting", (-2.9, -2.7, 1.35), (0.80,0.05,0.72), (0.45,0.45,0.45,1)).parent = cart

oldman = spawn_char(col, "OLDMAN", (1.9, 6.0), h=1.70, prefix="s2eb")

cam_d = bpy.data.cameras.new("CAM_S2EB"); cam_d.lens = 35
cam = bpy.data.objects.new("CAM_S2EB", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (1.6, -7.6, 1.66)
_aim = bpy.data.objects.new("AIM_DUPE", None); sc.collection.objects.link(_aim)
_aim.parent = dupe; _aim.location = (0, 0, 0.62)
_t = cam.constraints.new('TRACK_TO'); _t.target = _aim
_t.track_axis = 'TRACK_NEGATIVE_Z'; _t.up_axis = 'UP_Y'
tag_label(col, "DUPE", dupe, cam, prefix="s2eb")
tag_label(col, "OLDMAN", oldman, cam, prefix="s2eb")

def key(o, fr, x, y):
    sc.frame_set(fr); o.location = (x, y, o.location.z)
    o.keyframe_insert("location", frame=fr)

# he works his patch — a small sideways shift around the column, nothing more
key(dupe, 1, -2.1, -4.0); key(dupe, 144, -1.85, -4.0); key(dupe, 288, -2.15, -4.0)
# the old man crosses behind him at 0.95 m/s, the previz-readable walk
key(oldman, 1, 1.9, 6.0); key(oldman, 288, 1.9, -5.4)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2Eb-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2Eb_previz.blend")
sc.frame_set(1); print("cam", sc.camera.name)
bpy.ops.render.render(animation=True); print("RENDER-DONE")
