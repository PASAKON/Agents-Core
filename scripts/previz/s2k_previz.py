# S2K previz — THE GROUP. Same wall-POV camera as S2H/S2I: the crack sits in the
# extreme foreground and everyone in the room is behind it, by construction.
# Four visitors now, held at the positions they arrived in, plus Dupe still
# cleaning and still glancing over.
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
# CEO 2026-09-05: the crack comes OUT of the previz entirely. Its shape must
# come from the location plate, which is a photograph of the real break; a grey
# proxy drawn here is a crude approximation competing with that plate, and a
# video reference beats a still every time, so the proxy was winning and putting
# a machine-drawn star into the finished film. The previz now carries CAMERA and
# BLOCKING only.
for _c in [o for o in bpy.data.objects if o.name.startswith("crack_")]:
    _c.hide_render = _c.hide_viewport = True
for n in ("wall_hero_panel", "wall_crack_end"):
    ob = bpy.data.objects.get(n)
    if ob: ob.hide_render = ob.hide_viewport = True

exec(open(r"C:\Users\UsEr\Downloads\charlib.py").read())
col = sc.collection

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc); o = bpy.context.object; o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name+"_m"); m.use_nodes = False
    m.diffuse_color = color; o.data.materials.append(m); return o

# CEO: nobody lines up smartly. Gaps are UNEVEN and depths differ, and the
# couple stand close together while everyone else keeps ordinary distance.
# Reading right to left across the frame:
# CEO 2026-09-04: the couple is TWO WOMEN. char_woman (COBALT) is the partner
# who comforts; visitor_b (RUST) is the one crying. That frees visitor_a, the
# man in the maroon suit, to be the lone browser deep in the background who has
# not joined the group at all.
CAST = [
    ("CRITIC",      3.05, -20.15, 1.64),  # the Chinese woman, hard right
    ("STUDENT",     1.55, -19.05, 1.68),  # 1.50 m gap, and a metre nearer
    ("COLLECTOR_A", 0.25, -19.90, 1.70),  # 1.30 m gap — the partner, in cobalt
    ("VISITOR_B",  -0.35, -19.65, 1.66),  # 0.60 m — the one crying, close to her
]
people = {}
for name, x, y, h in CAST:
    people[name] = spawn_char(col, name, (x, y), h=h, prefix="s2k")

# the man in the maroon suit, still browsing, far off and barely readable
browser = spawn_char(col, "VISITOR_A", (-4.1, -6.0), h=1.76, prefix="s2k")

dupe = spawn_char(col, "DUPE", (-2.75, -17.2), h=1.80, prefix="s2k")
build_cart(col, (-3.45, -16.6), prefix="s2k", with_painting=True)
cart = bpy.data.objects.get("s2k_cart_base")
if cart:
    cart.rotation_euler.z = R(90)
    for o in bpy.data.objects:
        if o.name.startswith("s2k_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2k_painting", (-3.45, -16.2, 1.35), (0.80,0.05,0.72), (0.45,0.45,0.45,1)).parent = cart

cam_d = bpy.data.cameras.new("CAM_S2K"); cam_d.lens = 21
cam = bpy.data.objects.new("CAM_S2K", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0.0, -22.45, 2.45)
cam.rotation_euler = (R(90), 0, 0)
for n, ob in list(people.items()) + [("DUPE", dupe), ("BROWSER", browser)]:
    tag_label(col, n, ob, cam, prefix="s2k")

def key(o, fr, x, y):
    sc.frame_set(fr); o.location = (x, y, o.location.z)
    o.keyframe_insert("location", frame=fr)

# the four hold position — small shifts of weight only, no walking
for name, x, y, _ in CAST:
    o = people[name]
    key(o, 1, x, y); key(o, 144, x + 0.06, y); key(o, 288, x - 0.04, y)

# Dupe keeps working his own patch and never joins them. 0.35 m/s.
key(dupe, 1, -2.75, -17.2); key(dupe, 144, -2.20, -17.2); key(dupe, 288, -2.60, -17.2)

# he drifts along the far wall, never toward them — 0.4 m/s, browsing
key(browser, 1, -4.1, -6.0); key(browser, 288, -4.1, -10.8)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2K-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2K_previz.blend")
sc.frame_set(1); print("cam", sc.camera.name)
bpy.ops.render.render(animation=True); print("RENDER-DONE")
