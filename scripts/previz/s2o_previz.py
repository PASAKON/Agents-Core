# S2O previz — VALDER ARRIVES. This one leaves the wall cavity, and it has to.
# The CEO's note is that DUPE alone reacts and you can read the fear on his
# face; at 16 m on a 21 mm lens from inside the wall he is four pixels of white
# uniform, so the shot moves to his side of the room. Camera sits low and
# behind him looking back UP the hall: Dupe is 4.4 m away and large, and Valder
# enters at the vanishing point behind him and walks toward us for 18 s.
#
# Everyone else keeps the exact marks S2N left them on, whether or not they are
# in frame, so the next scene inherits a stage that has not shifted.
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
# NOTE: the wall is NOT hidden here. This camera is in the room, not in the
# cavity, so the hero wall belongs in shot as an ordinary wall.

exec(open(r"C:\Users\UsEr\Downloads\charlib.py").read())
col = sc.collection

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc); o = bpy.context.object; o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name+"_m"); m.use_nodes = False
    m.diffuse_color = color; o.data.materials.append(m); return o

dupe    = spawn_char(col, "DUPE",      (-2.30, -17.20), h=1.80, prefix="s2o")
valder  = spawn_char(col, "VALDER",    ( 0.00,  20.50), h=1.86, prefix="s2o")
guardL  = spawn_char(col, "GUARD_V1", (-1.10,  21.30), h=1.84, prefix="s2o")
guardR  = spawn_char(col, "GUARD_V2", ( 1.10,  21.30), h=1.76, prefix="s2o")
gent    = spawn_char(col, "GENTLEMAN", ( 5.00,  -3.00), h=1.79, prefix="s2o")
bguard  = spawn_char(col, "BODYGUARD", ( 5.95,  -2.15), h=1.94, prefix="s2o")
regis   = spawn_char(col, "REGISTRAR", ( 3.05,  -4.35), h=1.80, prefix="s2o")
# the five hold their marks off-frame, for continuity into S2P
woman   = spawn_char(col, "COLLECTOR_A",     (-1.45, -19.95), h=1.68, prefix="s2o")
student = spawn_char(col, "STUDENT", ( 0.15, -19.75), h=1.70, prefix="s2o")
wifeB   = spawn_char(col, "VISITOR_B", ( 1.85, -19.70), h=1.66, prefix="s2o")
manA    = spawn_char(col, "VISITOR_A", ( 2.60, -19.45), h=1.78, prefix="s2o")
critic  = spawn_char(col, "CRITIC",  ( 3.55, -19.85), h=1.64, prefix="s2o")
build_cart(col, (-3.30, -16.60), prefix="s2o", with_painting=True)
cart = bpy.data.objects.get("s2o_cart_base")
if cart:
    cart.rotation_euler.z = R(90)
    for o in bpy.data.objects:
        if o.name.startswith("s2o_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2o_painting", (-3.30, -16.20, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

cam_d = bpy.data.cameras.new("CAM_S2O"); cam_d.lens = 28
cam = bpy.data.objects.new("CAM_S2O", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (-3.20, -20.80, 1.60)   # 3.7 m behind Dupe, on his own line
# AIM WITH A CONSTRAINT, NOT WITH TYPED EULERS. Hand-typed angles have missed
# on this project four times; a TRACK_TO at a fixed empty has never missed.
aim = bpy.data.objects.new("s2o_aim", None); sc.collection.objects.link(aim)
aim.parent = dupe
aim.location = (0.0, 0.0, 0.55)               # locked to Dupe himself
trk = cam.constraints.new('TRACK_TO'); trk.target = aim
trk.track_axis = 'TRACK_NEGATIVE_Z'; trk.up_axis = 'UP_Y'

for who, ob in (("DUPE", dupe), ("VALDER", valder), ("GUARD_L", guardL),
                ("GUARD_R", guardR), ("GENTLEMAN", gent), ("BODYGUARD", bguard),
                ("REGISTRAR", regis)):
    tag_label(col, who, ob, cam, prefix="s2o")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# VALDER: 23.0 m from the far doors to (3.80,-2.20) across frames 24-456, which
# is 18.0 s at 1.28 m/s — the unhurried stride of a man who owns the building,
# quicker than the elderly visitors because he carries no cane and never stops.
key(valder, 1,   0.00, 20.50); key(valder, 24,  0.00, 20.50)
key(valder, 456, 3.80, -2.20); key(valder, 480, 3.80, -2.20)
# the two uniformed guards stay a pace and a half behind him the whole way
key(guardL, 1, -1.10, 21.30); key(guardL, 24, -1.10, 21.30)
key(guardL, 456, 2.55, -0.95); key(guardL, 480, 2.55, -0.95)
key(guardR, 1,  1.10, 21.30); key(guardR, 24,  1.10, 21.30)
key(guardR, 456, 5.05, -1.15); key(guardR, 480, 5.05, -1.15)

# DUPE: he is the only one who moves at all, and only by turning — a turn is
# not a translation, so he holds his mark and the prompt carries the reaction.
key(dupe, 1, -2.30, -17.20); key(dupe, 480, -2.30, -17.20)

# everybody else is frozen exactly where S2N left them
for ob, x, y in ((gent, 5.00, -3.00), (bguard, 5.95, -2.15), (regis, 3.05, -4.35),
                 (woman, -1.45, -19.95), (student, 0.15, -19.75),
                 (wifeB, 1.85, -19.70), (manA, 2.60, -19.45), (critic, 3.55, -19.85)):
    key(ob, 1, x, y); key(ob, 480, x, y)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2O-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2O_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
