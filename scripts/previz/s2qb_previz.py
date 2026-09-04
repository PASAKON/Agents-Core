# S2QB previz — THE REVERSE. Same scene, same marks, camera moved OUT of
# the wall and into the gallery behind the group, looking back at the broken
# wall. Everyone watching the break now has their back to us; who turns and
# who does not is decided by what each of them is doing, not by a rule.
# CEO 2026-09-04: every scene gets both angles, sixteen in total.
# showing Carrington the room, and the CEO's note is that she walks in like a
# model on a runway. That solves the geometry problem the rest of this film has
# fought all night: the hall is 43 m long, and for once the LENGTH IS THE POINT.
# She walks it, straight down the middle, toward a locked camera on a long lens,
# and the whole party stands aside and watches her come.
#
# 20 m at 1.0 m/s fills the twenty seconds exactly — a deliberate unhurried
# runway pace, slower than an ordinary 1.2-1.4 m/s walk because she is being
# looked at and knows it.
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

# ---- the party, parted to BOTH SIDES so the centre of the hall is empty.
# That empty corridor is the runway, and it is the only reason the shot reads.
# x is kept beyond +/-2.2 so nobody drifts into her lane.
madame = spawn_char(col, "PARROT",      ( 0.35,  19.00), h=1.72, prefix="s2qb")
LEFT = [("VALDER",      -2.60,  2.60, 1.86),
        ("GENTLEMAN",   -3.45,  1.30, 1.79),
        ("BODYGUARD",   -4.20,  0.40, 1.94),
        ("GUARD_V1",    -2.90, -0.60, 1.84),
        ("REGISTRAR",   -3.70, -1.70, 1.80)]
RIGHT = [("COLLECTOR_A", 2.70,  2.20, 1.68),
         ("CRITIC",      3.55,  1.10, 1.64),
         ("VISITOR_B",   2.85,  0.10, 1.66),
         ("VISITOR_A",   3.60, -0.90, 1.78),
         ("STUDENT",     2.60, -1.90, 1.70),
         ("GUARD_V2",    3.90, -2.80, 1.76)]
standing = []
for name, x, y, h in LEFT + RIGHT:
    standing.append(spawn_char(col, name, (x, y), h=h, prefix="s2qb"))
# Dupe far back on the left with his cart, still not part of anything
dupe = spawn_char(col, "DUPE", (-4.60, -5.40), h=1.80, prefix="s2qb")
build_cart(col, (-5.20, -6.10), prefix="s2qb", with_painting=True)
cart = bpy.data.objects.get("s2qb_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s2qb_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2qb_painting", (-5.20, -5.70, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# ---- the camera. 50 mm, locked, low-ish, dead centre of the corridor and
# level. A long lens is what makes a runway read: it compresses the hall, holds
# her the same size for longer than the eye expects, and then she arrives all
# at once. A wide lens here would make her a dot that suddenly balloons.
cam_d = bpy.data.cameras.new("CAM_S2QB"); cam_d.lens = 35
cam = bpy.data.objects.new("CAM_S2QB", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0.20, -13.60, 1.72)        # in the hall, behind the group
cam.rotation_euler = (R(92), 0, R(180))    # looking BACK at the wall along -y
for who, ob in ([("MADAME", madame), ("DUPE", dupe)] +
                [(n, o) for (n, _, _, _), o in zip(LEFT + RIGHT, standing)]):
    tag_label(col, who, ob, cam, prefix="s2qb")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# 20.0 m at 1.00 m/s = 20 s = the whole clip. She never stops and never speeds
# up; she ends about 3 m from the lens, which on a 50 is a chest-up frame.
key(madame, 1,   0.35, 19.00)
key(madame, 480, 0.35, -1.00)

# nobody else moves a step. Heads turn, and a turn is not a translation.
for ob in standing:
    x, y = ob.location.x, ob.location.y
    key(ob, 1, x, y); key(ob, 480, x, y)
key(dupe, 1, -4.60, -5.40); key(dupe, 240, -4.30, -5.40); key(dupe, 480, -4.55, -5.40)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2QB-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2QB_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
