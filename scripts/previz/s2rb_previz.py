# S2RB previz — THE REVERSE. Same scene, same marks, camera moved OUT of
# the wall and into the gallery behind the group, looking back at the broken
# wall. Everyone watching the break now has their back to us; who turns and
# who does not is decided by what each of them is doing, not by a rule.
# CEO 2026-09-04: every scene gets both angles, sixteen in total.
# this file exists to lock: the two bidders face each other across the room,
# VALDER STANDS IN THE MIDDLE, the registrar cannot write fast enough, and the
# audience heads swing left, right, left, following whoever just said a number.
#
# So the camera looks straight down the hall and the frame is built as a
# see-saw: Carrington hard left, the Madame hard right, Valder dead centre
# between and slightly behind them, everyone else banked further back on both
# sides. Nobody in this scene walks anywhere — the whole event is heads and
# voices, which means the previz's only job is to fix WHO IS WHERE and to keep
# the two bidders far enough apart that a head-turn between them reads as a
# turn rather than a glance.
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

# ---- the see-saw. 5.2 m between the two bidders: wide enough that the room
# has to physically turn to follow them, narrow enough that a 35 mm at 7 m
# holds both plus Valder between.
gent   = spawn_char(col, "GENTLEMAN",  (-2.10, -3.00), h=1.79, prefix="s2rb")
bguard = spawn_char(col, "BODYGUARD",  (-3.10, -2.10), h=1.94, prefix="s2rb")
madame = spawn_char(col, "PARROT",     ( 2.15, -3.20), h=1.72, prefix="s2rb")
valder = spawn_char(col, "VALDER",     ( 0.00, -1.55), h=1.86, prefix="s2rb")
regis  = spawn_char(col, "REGISTRAR",  (-3.40, -5.60), h=1.80, prefix="s2rb")
# the audience, banked behind the bidders on both sides so their heads swing
# across the lens rather than away from it
crowd = [("GUARD_V1",    -1.70,  0.10, 1.84),
         ("GUARD_V2",     1.75,  0.20, 1.76),
         ("COLLECTOR_A", -2.95, -0.70, 1.68),
         ("STUDENT",     -1.05, -0.55, 1.70),
         ("VISITOR_B",    1.15, -0.60, 1.66),
         ("VISITOR_A",    2.95, -0.80, 1.78),
         ("CRITIC",       3.60, -1.80, 1.64)]
for name, x, y, h in crowd:
    spawn_char(col, name, (x, y), h=h, prefix="s2rb")
dupe = spawn_char(col, "DUPE", (-4.30, 1.60), h=1.80, prefix="s2rb")
build_cart(col, (-4.95, 2.30), prefix="s2rb", with_painting=True)
cart = bpy.data.objects.get("s2rb_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s2rb_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2rb_painting", (-4.95, 2.70, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

cam_d = bpy.data.cameras.new("CAM_S2RB"); cam_d.lens = 35
cam = bpy.data.objects.new("CAM_S2RB", cam_d); sc.collection.objects.link(cam); sc.camera = cam
# B ANGLE (CEO 2026-09-04): the far end, 180 deg opposite the A camera. The
# bidders stand at y=-3; from this side Carrington reads on the RIGHT and the
# Madame on the LEFT, mirrored from the A angle, Valder still between them, all
# three seen from behind. Dupe sits at y=1.6 and lands in the near foreground,
# watching the whole thing over their heads. A camera facing the broken wall
# gave an empty wall — nobody in this scene is anywhere near it.
cam.location = (0.00, 7.00, 1.66)
cam.rotation_euler = (R(92), 0, R(180))    # looking back down the hall along -y
cam_d.lens = 30                            # match the A angle
for who, ob in (("GENTLEMAN", gent), ("MADAME", madame), ("VALDER", valder),
                ("REGISTRAR", regis), ("BODYGUARD", bguard), ("DUPE", dupe)):
    tag_label(col, who, ob, cam, prefix="s2rb")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# NOBODY WALKS. The bidders hold their ground, which is the point — this is a
# fight conducted entirely with numbers. Only two small moves exist:
# the registrar edges toward whoever is winning, and Valder shifts his weight
# between them like an umpire who cannot help himself.
for ob, x, y in ((gent, -2.10, -3.00), (bguard, -3.10, -2.10), (madame, 2.15, -3.20)):
    key(ob, 1, x, y); key(ob, 480, x, y)
key(valder, 1,   0.00, -1.55)
key(valder, 168, -0.35, -1.60)      # leans toward Carrington's side
key(valder, 312,  0.40, -1.62)      # then toward hers
key(valder, 480,  0.00, -1.55)
key(regis, 1,   -3.40, -5.60)
key(regis, 240, -3.05, -5.45)       # drifts in, trying to keep up
key(regis, 480, -2.75, -5.50)

for name, x, y, _ in crowd:
    ob = bpy.data.objects.get(f"s2rb_{name}")
    if ob:
        key(ob, 1, x, y); key(ob, 480, x, y)
key(dupe, 1, -4.30, 1.60); key(dupe, 480, -4.30, 1.60)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2RB-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2RB_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
