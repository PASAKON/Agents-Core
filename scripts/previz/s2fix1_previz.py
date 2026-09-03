# S2-Fix1 previz — camera grammar: locked wide / fast zoom to crack /
# tilt down to plaque / CUT close shock / CUT wide exit / CUT final crack+plaque
import bpy, math
from math import radians as R

sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 480
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24

# hide other scenes' stage dressing (A_* = interview set, B_* = hammer room, text tags)
for o in bpy.data.objects:
    if o.name.startswith(("A_", "B_", "hvfly_tag", "Text.")):
        o.hide_render = True
        o.hide_viewport = True

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name + "_m")
    m.use_nodes = False
    m.diffuse_color = color
    o.data.materials.append(m)
    return o

def cyl(name, loc, r, h, color):
    bpy.ops.mesh.primitive_cylinder_add(location=loc, radius=r, depth=h)
    o = bpy.context.object
    o.name = name
    m = bpy.data.materials.new(name + "_m")
    m.use_nodes = False
    m.diffuse_color = color
    o.data.materials.append(m)
    return o

WHITE  = (0.92, 0.92, 0.92, 1)
ORANGE = (0.72, 0.28, 0.06, 1)
GREY   = (0.45, 0.45, 0.45, 1)

# proxies
dupe  = cyl("P_dupe", (1.15, -21.2, 0.9), 0.22, 1.8, WHITE)
head  = cyl("P_dupe_head", (1.15, -21.2, 1.95), 0.16, 0.3, WHITE)
cartb = box("P_cart_body", (2.15, -20.55, 0.55), (0.9, 0.6, 0.8), ORANGE)
cartr = box("P_cart_rack", (2.15, -20.15, 0.55), (0.9, 0.08, 0.6), ORANGE)
ptg   = box("P_painting", (0.0, -21.70, 3.05), (0.80, 0.05, 0.72), GREY)
ptg.rotation_euler = (0, R(4), 0)          # hangs crooked over the future crack

def key(o, fr, loc=None, rot=None):
    sc.frame_set(fr)
    if loc: o.location = loc
    if rot: o.rotation_euler = rot
    o.keyframe_insert("location", frame=fr)
    o.keyframe_insert("rotation_euler", frame=fr)

# ---- painting action ----
key(ptg, 1,   (0.0, -21.70, 3.05), (0, R(4), 0))
key(ptg, 120, (0.0, -21.70, 3.05), (0, R(4), 0))
key(ptg, 168, (0.0, -21.70, 3.05), (0, 0, 0))          # straightened at ~7s
key(ptg, 191, (0.0, -21.70, 3.05), (0, 0, 0))
key(ptg, 200, (0.0, -21.62, 0.42), (R(-8), 0, 0))       # dropped, leaning on floor
key(ptg, 335, (0.0, -21.62, 0.42), (R(-8), 0, 0))
key(ptg, 336, (2.15, -20.12, 0.85), (0, 0, 0))          # racked on the cart (same size!)
key(ptg, 408, (2.15,  -7.6,  0.85), (0, 0, 0))          # rides away with the cart

# ---- dupe + cart exit ----
for o, x in ((dupe, 1.15), (head, 1.15)):
    z = o.location.z
    key(o, 1,   (x, -21.2, z)); key(o, 335, (x, -21.2, z))
    key(o, 336, (x, -20.9, z)); key(o, 408, (2.15, -7.9, z))
for o in (cartb, cartr):
    z = o.location.z; y0 = o.location.y
    key(o, 1, (2.15, y0, z)); key(o, 335, (2.15, y0, z)); key(o, 408, (2.15, y0 + 13.0, z))

# ---- the camera ----
# hall_v41 carries timeline markers that BIND cameras per frame — they override
# scene.camera during render, which is why the first build came out of CAM_FLY4.
print("markers before:", [(m.name, m.frame, m.camera.name if m.camera else None)
                          for m in sc.timeline_markers])
sc.timeline_markers.clear()

cam_d = bpy.data.cameras.new("CAM_S2FIX1")
cam = bpy.data.objects.new("CAM_S2FIX1", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
LEVEL = (R(90), 0, R(180))   # looking straight down -y

def ckey(fr, loc, rot, lens):
    sc.frame_set(fr)
    cam.location = loc; cam.rotation_euler = rot; cam_d.lens = lens
    cam.keyframe_insert("location", frame=fr)
    cam.keyframe_insert("rotation_euler", frame=fr)
    cam_d.keyframe_insert("lens", frame=fr)

WIDE  = ((0, -14.6, 1.40), LEVEL, 28)
CRACK = ((0, -19.80, 3.05), LEVEL, 70)
PLAQ  = ((0, -19.80, 3.05), (R(45.0), 0, R(180)), 85)   # tilt derived: 45.0 deg down
SHOCK = ((1.15, -19.70, 1.85), LEVEL, 85)
FINAL = ((0, -19.40, 2.05), LEVEL, 25)

ckey(1,   *WIDE)            # [0-8s] locked wide
ckey(191, *WIDE)
ckey(216, *CRACK)           # [8-9s] fast push-zoom to the crack
ckey(240, *CRACK)           # hold
ckey(264, *PLAQ)            # [10-11s] tilt down to the plaque
ckey(287, *PLAQ)            # hold
ckey(288, *SHOCK)           # [12s] CUT — shock close-up
ckey(335, *SHOCK)
ckey(336, *WIDE)            # [14s] CUT — wide again, he loads and flees, camera stays
ckey(407, *WIDE)
ckey(408, *FINAL)           # [17s] CUT — straight-on: crack above, plaque below
ckey(480, *FINAL)

# ---- fast render settings ----
for attr, val in (("use_shadows", False), ("use_raytracing", False),
                  ("use_gtao", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, attr, val)
    except Exception as e: print("eevee attr skip:", attr, e)
# Blender 5.x: video lives behind image_settings.media_type
try:
    sc.render.image_settings.media_type = "VIDEO"
    print("media_type set VIDEO")
except Exception as e:
    print("media_type unavailable:", e)
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"
sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"
sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2Fix1-Render.MP4"

bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2Fix1_previz.blend")
sc.frame_set(1)
print("render camera =", sc.camera.name, "markers =", len(sc.timeline_markers))
bpy.ops.render.render(animation=True)
print("RENDER-DONE")
