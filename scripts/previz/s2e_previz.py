# S2E previz — THE FAKE CLEANING. One locked camera on Dupe. His hands work the
# wall; his eyes never go near what they are doing. He stares straight past it.
import bpy, math
from math import radians as R
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 288          # 12s
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24
sc.timeline_markers.clear()
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

dupe = spawn_char(col, "DUPE", (0.9, -21.05), h=1.8, prefix="s2e")
build_cart(col, (2.4, -20.4), prefix="s2e", with_painting=True)
cart = bpy.data.objects.get("s2e_cart_base")
for o in bpy.data.objects:
    if o.name.startswith("s2e_cart_") and o is not cart:
        o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
box("s2e_painting", (2.4, -20.0, 1.35), (0.80,0.05,0.72), (0.45,0.45,0.45,1)).parent = cart
guest = spawn_char(col, "OLDMAN", (-1.4, 6.0), h=1.70, prefix="s2e")

cam_d = bpy.data.cameras.new("CAM_S2E"); cam_d.lens = 32
cam = bpy.data.objects.new("CAM_S2E", cam_d); sc.collection.objects.link(cam); sc.camera = cam
# three-quarter on Dupe from the room side: we see his face AND the wall he is
# pretending to clean, so the lie is visible in one frame
cam.location = (4.4, -18.2, 1.70)
# aim with a constraint instead of guessed euler angles — the first pass at this
# put both new cameras into a side wall and rendered flat brown
_aim = bpy.data.objects.new("AIM_DUPE", None)
sc.collection.objects.link(_aim)
_aim.parent = dupe
_aim.location = (-0.5, -0.4, 0.55)
_c = cam.constraints.new('TRACK_TO'); _c.target = _aim
_c.track_axis = 'TRACK_NEGATIVE_Z'; _c.up_axis = 'UP_Y'
tag_label(col, "DUPE", dupe, cam, prefix="s2e")
tag_label(col, "OLDMAN", guest, cam, prefix="s2e")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)
# he barely moves — small drift along the wall as the cloth works
key(dupe, 1, 0.9, -21.05); key(dupe, 144, 0.75, -21.05); key(dupe, 288, 0.95, -21.05)
# the old man crosses behind him, which is what his eyes are actually following
key(guest, 1, -1.4, 8.0); key(guest, 303, -1.4, -4.0)
sc.frame_end = 288

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2E-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2E_previz.blend")
sc.frame_set(1); print("cam", sc.camera.name)
bpy.ops.render.render(animation=True); print("RENDER-DONE")
