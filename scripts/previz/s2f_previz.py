# S2F previz — THE OLD MAN LOOKS. He walks the gallery, stops at a work, looks,
# nods, moves on. Dupe is not in this scene at all.
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

guest = spawn_char(col, "OLDMAN", (-2.0, 10.0), h=1.70, prefix="s2f")

cam_d = bpy.data.cameras.new("CAM_S2F"); cam_d.lens = 42
cam = bpy.data.objects.new("CAM_S2F", cam_d); sc.collection.objects.link(cam); sc.camera = cam
# locked three-quarter across the hall: he moves through frame, pieces on the
# left wall behind him, the colonnade receding
cam.location = (2.6, 4.5, 1.70)
# aim with a constraint instead of guessed euler angles — the first pass at this
# put both new cameras into a side wall and rendered flat brown
_aim = bpy.data.objects.new("AIM_GUEST", None)
sc.collection.objects.link(_aim)
_aim.parent = guest
_aim.location = (0, 0, 0.75)
_c = cam.constraints.new('TRACK_TO'); _c.target = _aim
_c.track_axis = 'TRACK_NEGATIVE_Z'; _c.up_axis = 'UP_Y'
tag_label(col, "OLDMAN", guest, cam, prefix="s2f")

def key(o, fr, x, y):
    sc.frame_set(fr); o.location = (x, y, o.location.z); o.keyframe_insert("location", frame=fr)
# walk, stop and look, walk, stop and look — the pauses are the nods
key(guest, 1, -2.0, 9.50)
key(guest, 77, -2.0, 6.50)
key(guest, 123, -2.0, 6.50)
key(guest, 211, -2.0, 3.00)
key(guest, 250, -2.0, 3.00)
key(guest, 288, -2.0, 1.50)

sc.frame_end = 288

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2F-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2F_previz.blend")
sc.frame_set(1); print("cam", sc.camera.name)
bpy.ops.render.render(animation=True); print("RENDER-DONE")
