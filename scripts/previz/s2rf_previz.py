# S2R-F previz — THE BATTLE, FACES (five-strip split). Built on the S2R staging:
# same room, same twelve people in the same places. Five CLOSE-UP cameras, one
# per bid (GENTLEMAN / PARROT / GENTLEMAN / PARROT / GENTLEMAN), each rendered as a
# 256x720 still; then the master camera renders the FULL SHOT (frames 361-480,
# 15-20s) with the room's startle and Valder's happy rock. The strips are
# composed on the Mac with ffmpeg (active strip bright, others dim).
import bpy, math, os
from math import radians as R
sc = bpy.context.scene
OUT = r"C:\Users\UsEr\Downloads\S2RF_seq"
os.makedirs(OUT, exist_ok=True)
sc.frame_start, sc.frame_end = 1, 480
sc.render.fps = 24
sc.timeline_markers.clear()
for o in bpy.data.objects:
    if o.name.startswith(("A_", "B_", "hvfly_tag", "Text.")) or o.name in ("Cube", "Light"):
        o.hide_render = o.hide_viewport = True

exec(open(r"C:\Users\UsEr\Downloads\charlib.py").read())
col = sc.collection

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc); o = bpy.context.object; o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name+"_m"); m.use_nodes = False
    m.diffuse_color = color; o.data.materials.append(m); return o

gent   = spawn_char(col, "GENTLEMAN",  (-2.10, -3.00), h=1.79, prefix="s2rf")
bguard = spawn_char(col, "BODYGUARD",  (-3.10, -2.10), h=1.94, prefix="s2rf")
madame = spawn_char(col, "PARROT",     ( 2.15, -3.20), h=1.72, prefix="s2rf")
valder = spawn_char(col, "VALDER",     ( 0.00, -1.55), h=1.86, prefix="s2rf")
regis  = spawn_char(col, "REGISTRAR",  (-3.40, -5.60), h=1.80, prefix="s2rf")
crowd = [("GUARD_V1",    -1.70,  0.10, 1.84),
         ("GUARD_V2",     1.75,  0.20, 1.76),
         ("COLLECTOR_A", -2.95, -0.70, 1.68),
         ("STUDENT",     -1.05, -0.55, 1.70),
         ("VISITOR_B",    1.15, -0.60, 1.66),
         ("VISITOR_A",    2.95, -0.80, 1.78),
         ("CRITIC",       3.60, -1.80, 1.64)]
crowd_obs = []
for name, x, y, h in crowd:
    crowd_obs.append(spawn_char(col, name, (x, y), h=h, prefix="s2rf"))
dupe = spawn_char(col, "DUPE", (-4.30, 1.60), h=1.80, prefix="s2rf")
build_cart(col, (-4.95, 2.30), prefix="s2rf", with_painting=True)
cart = bpy.data.objects.get("s2rf_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s2rf_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2rf_painting", (-4.95, 2.70, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# ---- master camera (the S2R see-saw view)
cam_d = bpy.data.cameras.new("CAM_S2RF"); cam_d.lens = 30
cam = bpy.data.objects.new("CAM_S2RF", cam_d); sc.collection.objects.link(cam)
cam.location = (0.00, -11.40, 1.66); cam.rotation_euler = (R(88), 0, 0)
for who, ob in (("GENTLEMAN", gent), ("MADAME", madame), ("VALDER", valder),
                ("REGISTRAR", regis), ("BODYGUARD", bguard), ("DUPE", dupe)):
    tag_label(col, who, ob, cam, prefix="s2rf")

# ---- five close-up cameras: 85mm one metre in front of the bidder's head
def closeup_cam(name, ob, h):
    cd = bpy.data.cameras.new(name); cd.lens = 85; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
    c = bpy.data.objects.new(name, cd); sc.collection.objects.link(c)
    x, y = ob.location.x, ob.location.y
    c.location = (x, y - 2.10, h + 0.06); c.rotation_euler = (R(90), 0, 0)
    return c
cams = [closeup_cam("CAM_CU1", gent, 1.79), closeup_cam("CAM_CU2", madame, 1.72),
        closeup_cam("CAM_CU3", gent, 1.79), closeup_cam("CAM_CU4", madame, 1.72),
        closeup_cam("CAM_CU5", gent, 1.79)]

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# nobody walks; everyone holds through the strips (1-360)
for ob, x, y in ((gent, -2.10, -3.00), (bguard, -3.10, -2.10), (madame, 2.15, -3.20), (regis, -3.40, -5.60), (dupe, -4.30, 1.60)):
    key(ob, 1, x, y); key(ob, 360, x, y); key(ob, 480, x, y)
for (name, x, y, _), ob in zip(crowd, crowd_obs):
    key(ob, 1, x, y); key(ob, 360, x, y)
# THE STARTLE at 15.4s (frame 370): watchers, guards, registrar and Dupe hop 10cm and settle
for ob in crowd_obs + [regis, bguard, dupe]:
    z0 = ob.location.z; x, y = ob.location.x, ob.location.y
    key(ob, 368, x, y, z0); key(ob, 372, x, y, z0 + 0.10); key(ob, 378, x, y, z0)
    key(ob, 480, x, y, z0)
# VALDER delighted: rocks foot to foot from 15.8s to the end
key(valder, 1, 0.00, -1.55); key(valder, 360, 0.00, -1.55); key(valder, 378, 0.00, -1.55)
for i, fr in enumerate(range(390, 481, 12)):
    key(valder, fr, (0.22 if i % 2 == 0 else -0.22), -1.58)
# the registrar's pen stops: he leans back a touch
key(regis, 390, -3.55, -5.70); key(regis, 480, -3.55, -5.70)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("use_fast_gi", False), ("taa_render_samples", 4)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
sc.render.engine = 'BLENDER_EEVEE'
sc.render.use_simplify = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"

# 1) the five close-up stills at 256x720
sc.render.resolution_x, sc.render.resolution_y = 256, 720
sc.render.resolution_percentage = 100
sc.frame_set(1)
for i, c in enumerate(cams, 1):
    sc.camera = c
    sc.render.filepath = os.path.join(OUT, "strip_%d.png" % i)
    bpy.ops.render.render(write_still=True)
    print("STILL-DONE", i)
import sys
if '--stills-only' in sys.argv:
    print('RENDER-DONE'); raise SystemExit
# 2) the full shot, frames 361-480 at 1280x720
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.camera = cam
sc.frame_start, sc.frame_end = 361, 480
sc.render.filepath = os.path.join(OUT, "full_")
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2RF_previz.blend")
bpy.ops.render.render(animation=True)
print("RENDER-DONE")
