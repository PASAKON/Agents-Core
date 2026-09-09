# S2AW / S2AP previz — THE INTERPRETATIONS, WES ANDERSON CUT (CTO 2026-09-10 02:10, CEO
# 01:55: "หลุดธีม Wes Anderson ไปหน่อย … ออกแบบมาให้ลงตัวที่สุด จะแยก Generate กี่คลิปก็ได้").
# Same wall-POV camera as S2N/S2AJ (the camera IS the break), but PLANIMETRIC: the five
# stand in ONE plane at EVEN spacing, centred on the red door, all facing the lens.
# MODE "AW": one locked 28 mm wide, 20 s, all five present from frame 1, no jump cuts;
#            heads turn in unison to each speaker (a small yaw on the head sphere is not
#            visible on a proxy, so the previz only fixes the marks and the frame).
# MODE "AP": five 3 s PORTRAITS, 15 s, one 85 mm camera per mark, marker-bound hard cuts;
#            each person centred, waist-up, the hall's one-point perspective behind them.
import bpy, math, os
from math import radians as R
MODE = os.environ.get("S2A_MODE", "AW")
sc = bpy.context.scene
FRAMES = 480 if MODE == "AW" else 360
sc.frame_start, sc.frame_end = 1, FRAMES
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24
sc.timeline_markers.clear()
for o in bpy.data.objects:
    if o.name.startswith(("A_", "B_", "hvfly_tag", "Text.")) or o.name in ("Cube", "Light"):
        o.hide_render = o.hide_viewport = True
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

# ONE plane, EVEN spacing 0.72 m, centred on x=0 (the red door's axis), 3.7 m from the lens.
ROW_Y = -19.90
row = [("COLLECTOR_A", -1.44, 1.68), ("STUDENT", -0.72, 1.70), ("VISITOR_B", 0.00, 1.66),
       ("VISITOR_A", 0.72, 1.78), ("CRITIC", 1.44, 1.64)]
obs = {}
for name, x, h in row:
    obs[name] = spawn_char(col, name, (x, ROW_Y), h=h, prefix="s2aw")
# Dupe dead centre far back under the door, mopping — the one symmetrical place for him
dupe = spawn_char(col, "DUPE", (0.0, -11.5), h=1.80, prefix="s2aw")
build_cart(col, (1.1, -11.9), prefix="s2aw", with_painting=True)
cart = bpy.data.objects.get("s2aw_cart_base")
if cart:
    for o in bpy.data.objects:
        if o.name.startswith("s2aw_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2aw_painting", (1.1, -11.5, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

WALL_CAM = (0.0, -23.60, 2.45)
if MODE == "AW":
    cam_d = bpy.data.cameras.new("CAM_S2AW"); cam_d.lens = 28
    cam = bpy.data.objects.new("CAM_S2AW", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = WALL_CAM; cam.rotation_euler = (R(80), 0, 0)
    for who, name, z in (("COBALT", "COLLECTOR_A", 2.00), ("STUDENT", "STUDENT", 2.20), ("FUR", "VISITOR_B", 2.00),
                         ("MAROON", "VISITOR_A", 2.20), ("CRITIC", "CRITIC", 2.00)):
        tag_label(col, who, obs[name], cam, z=z, size=0.16, prefix="s2aw")
    tag_label(col, "DUPE", dupe, cam, prefix="s2aw")
    OUT = r"C:\Users\UsEr\Downloads\S2AW-Render.MP4"; BLEND = r"C:\Users\UsEr\Downloads\S2AW_previz.blend"
else:
    # five portrait cameras at the wall, each aimed at one mark, 85 mm: waist-up, centred
    order = [("VISITOR_B", "FUR"), ("VISITOR_A", "MAROON"), ("CRITIC", "CRITIC"), ("STUDENT", "STUDENT"), ("COLLECTOR_A", "COBALT")]
    for i, (name, who) in enumerate(order):
        ob = obs[name]; x = ob.location.x; h = [r[2] for r in row if r[0] == name][0]
        cam_d = bpy.data.cameras.new(f"CAM_S2AP_{i+1}"); cam_d.lens = 70
        cam = bpy.data.objects.new(f"CAM_S2AP_{i+1}", cam_d); sc.collection.objects.link(cam)
        cam.location = (0.0, WALL_CAM[1], 1.45)                       # chest height: flat frontal
        aim_z = h - 0.15                                              # centre on the upper chest: air above the head, waist at the bottom
        dy = ROW_Y - WALL_CAM[1]; dx = x - 0.0
        yaw = -math.atan2(dx, dy)                                     # turn toward the mark
        pitch = math.atan2(aim_z - 1.45, math.hypot(dx, dy))
        cam.rotation_euler = (R(90) + pitch, 0, yaw)
        m = sc.timeline_markers.new(f"P{i+1}", frame=1 + i * 72); m.camera = cam
        if i == 0: sc.camera = cam
        # only the subject exists in its portrait: hide the other four, Dupe and the cart
        for other_name, other in obs.items():
            hid = other_name != name
            for fr in (1 + i * 72,):
                sc.frame_set(fr); other.hide_render = hid; other.hide_viewport = hid
                other.keyframe_insert("hide_render", frame=fr); other.keyframe_insert("hide_viewport", frame=fr)
        for extra in [dupe] + ([o for o in bpy.data.objects if o.name.startswith("s2aw_cart_") or o.name == "s2aw_painting"]):
            sc.frame_set(1); extra.hide_render = True; extra.hide_viewport = True
            extra.keyframe_insert("hide_render", frame=1); extra.keyframe_insert("hide_viewport", frame=1)
        t = tag_label(col, who, ob, cam, z=h + 0.22, size=0.09, prefix=f"s2ap{i}")
        for fr, hid in ((1, i != 0), (1 + i * 72, False), (1 + (i + 1) * 72, True)):
            if fr > FRAMES: continue
            sc.frame_set(fr); t.hide_render = hid; t.hide_viewport = hid
            t.keyframe_insert("hide_render", frame=fr); t.keyframe_insert("hide_viewport", frame=fr)
    OUT = r"C:\Users\UsEr\Downloads\S2AP-Render.MP4"; BLEND = r"C:\Users\UsEr\Downloads\S2AP_previz.blend"

for a, v in (("use_shadows", False), ("use_raytracing", False), ("use_fast_gi", False), ("taa_render_samples", 4)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = OUT
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
sc.frame_set(1)
bpy.ops.render.render(animation=True); print("RENDER-DONE", MODE)
