# S2SB previz — THE REVERSE. Same scene, same marks, camera moved OUT of
# the wall and into the gallery behind the group, looking back at the broken
# wall. Everyone watching the break now has their back to us; who turns and
# who does not is decided by what each of them is doing, not by a rule.
# CEO 2026-09-04: every scene gets both angles, sixteen in total.
#
# Same locked frame as S2R so the two cut together with nobody moving across
# the join: Carrington left, the Madame right, Valder centre, the room banked
# behind them. The voice arrives from the far end of the hall before anybody
# can see who owns it, every head turns away from us to look up the gallery,
# and there she is — a very old woman in a powered wheelchair, tiny at the
# vanishing point.
#
# THE JOKE IS THE SPEED, so the speed is the one number in this file that
# matters: 0.25 m/s, which is five metres in the whole twenty seconds. She is
# still a long way off when the clip ends. Two of the watchers give up and
# leave, walking out past the lens, which is only funny because she has visibly
# barely moved.
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

# ---- everyone exactly where S2R left them
gent   = spawn_char(col, "GENTLEMAN",  (-2.10, -3.00), h=1.79, prefix="s2sb")
bguard = spawn_char(col, "BODYGUARD",  (-3.10, -2.10), h=1.94, prefix="s2sb")
madame = spawn_char(col, "PARROT",     ( 2.15, -3.20), h=1.72, prefix="s2sb")
valder = spawn_char(col, "VALDER",     ( 0.00, -1.55), h=1.86, prefix="s2sb")
regis  = spawn_char(col, "REGISTRAR",  (-2.75, -5.50), h=1.80, prefix="s2sb")
watchers = {}
for name, x, y, h in (("GUARD_V1",    -1.70,  0.10, 1.84),
                      ("GUARD_V2",     1.75,  0.20, 1.76),
                      ("COLLECTOR_A", -2.95, -0.70, 1.68),
                      ("STUDENT",     -1.05, -0.55, 1.70),
                      ("VISITOR_B",    1.15, -0.60, 1.66),
                      ("VISITOR_A",    2.95, -0.80, 1.78),
                      ("CRITIC",       3.60, -1.80, 1.64)):
    watchers[name] = spawn_char(col, name, (x, y), h=h, prefix="s2sb")
dupe = spawn_char(col, "DUPE", (-4.30, 1.60), h=1.80, prefix="s2sb")
build_cart(col, (-4.95, 2.30), prefix="s2sb", with_painting=True)
cart = bpy.data.objects.get("s2sb_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s2sb_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2sb_painting", (-4.95, 2.70, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# ---- the grandmother. SEATED, so the proxy is short, and she rides a chair
# built as an empty with a seat slab and two wheels parented to it. Everything
# hangs off the chair root, which is the thing that gets keyed — parent first,
# position after, so the chair and the woman can never drift apart.
chair = bpy.data.objects.new("s2sb_chair_root", None)
sc.collection.objects.link(chair)
chair.location = (0.30, 16.00, 0.0)
seat = box("s2sb_chair_seat", (0, 0, 0), (0.62, 0.70, 0.10), (0.10, 0.10, 0.12, 1))
back = box("s2sb_chair_back", (0, 0, 0), (0.62, 0.08, 0.55), (0.10, 0.10, 0.12, 1))
whL  = box("s2sb_chair_whl",  (0, 0, 0), (0.06, 0.56, 0.56), (0.05, 0.05, 0.05, 1))
whR  = box("s2sb_chair_whr",  (0, 0, 0), (0.06, 0.56, 0.56), (0.05, 0.05, 0.05, 1))
for ob, loc in ((seat, (0, 0, 0.47)), (back, (0, -0.31, 0.78)),
                (whL, (-0.34, 0, 0.28)), (whR, (0.34, 0, 0.28))):
    ob.parent = chair; ob.location = loc          # identity inverse = chair space
gran = spawn_char(col, "GRANDMOTHER", (0.30, 16.00), h=1.05, prefix="s2sb")
gran.parent = chair
gran.location = (0.0, 0.0, 0.52)                  # sitting on the seat

cam_d = bpy.data.cameras.new("CAM_S2SB"); cam_d.lens = 35
cam = bpy.data.objects.new("CAM_S2SB", cam_d); sc.collection.objects.link(cam); sc.camera = cam
# B ANGLE (CEO 2026-09-04): the far end, 180 deg opposite the A camera, and the
# one place this angle beats its A twin outright. The grandmother sits at y=16
# and the whole party is 19 m beyond her at y=-3, so from here we are BEHIND
# HER: her back and her chair fill the near foreground, and the entire room is
# small and far away, facing her. We hear a hundred million from a few feet away
# and watch it land on twelve people down the hall.
# Measured 2026-09-04: hall interior y -22.10..+22.10, red-door end wall at 21.90.
# 22.00 was inside that wall and rendered solid brown. 20.80 clears it by 1.1 m and
# still sits 4.8 m behind the grandmother at y=16.
cam.location = (0.30, 20.80, 1.66)
cam.rotation_euler = (R(92), 0, R(180))    # looking back down the hall along -y
cam_d.lens = 30                            # match the A angle
for who, ob in (("GENTLEMAN", gent), ("MADAME", madame), ("VALDER", valder),
                ("GRANDMOTHER", gran), ("REGISTRAR", regis), ("DUPE", dupe)):
    tag_label(col, who, ob, cam, prefix="s2sb")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# 5.0 m in 20 s = 0.25 m/s. A normal walk is 1.2-1.4; this is a fifth of that,
# and it has to be visibly, painfully slow or the scene has no joke in it.
key(chair, 1,   0.30, 16.00)
key(chair, 480, 0.30, 11.00)

# the principals do not move at all — they are waiting, which is the point
for ob, x, y in ((gent, -2.10, -3.00), (bguard, -3.10, -2.10), (madame, 2.15, -3.20),
                 (valder, 0.00, -1.55), (regis, -2.75, -5.50)):
    key(ob, 1, x, y); key(ob, 480, x, y)

# TWO PEOPLE GIVE UP AND LEAVE, walking out past the lens in the last third.
# 1.3 m/s, an ordinary unhurried walk — they are bored, not fleeing.
st = watchers["STUDENT"]
key(st, 1,   -1.05, -0.55); key(st, 300, -1.05, -0.55)
key(st, 480, -1.55, -8.40)
vb = watchers["VISITOR_B"]
key(vb, 1,    1.15, -0.60); key(vb, 348,  1.15, -0.60)
key(vb, 480,  1.70, -6.90)
for name in ("GUARD_V1", "GUARD_V2", "COLLECTOR_A", "VISITOR_A", "CRITIC"):
    ob = watchers[name]
    x, y = ob.location.x, ob.location.y
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
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2SB-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2SB_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
