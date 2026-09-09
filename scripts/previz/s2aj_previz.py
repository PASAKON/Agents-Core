# S2AJ previz — THE INTERPRETATIONS, JUMP CUT (CEO 2026-09-09 18:40). Wall-POV
# camera and marks from S2N (same cavity camera, same row in front of the break,
# no crack proxy per the 2026-09-05 ruling — camera and blocking only). ONE locked
# angle, five JUMP CUTS in time: nobody is ever seen entering; at each cut the
# next person is simply already standing on their mark. Fill LEFT to RIGHT, no
# wider than the red door. Beats (unequal, by line length):
#   0-4s   OLDMAN alone (already there from S3b)
#   4-9s   + VISITOR_B (chestnut fur)      9-15s + CRITIC
#   15-20s + STUDENT                        20-25s the four argue at once (bob)
#   25-30s + COLLECTOR_A (cobalt) — the others go still.
import bpy, math
from math import radians as R
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 720          # 30s
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

OFF = 40.0   # parked off-screen until the beat
row = [("OLDMAN",      -1.60, -19.95, 1.76,   1),
       ("VISITOR_B",   -0.75, -19.88, 1.66,  97),
       ("CRITIC",       0.10, -19.95, 1.64, 217),
       ("STUDENT",      0.95, -19.72, 1.70, 361),
       ("COLLECTOR_A",  1.80, -19.90, 1.68, 601)]
obs = {}
for name, x, y, h, beat in row:
    ob = spawn_char(col, name, (OFF if beat > 1 else x, y), h=h, prefix="s2aj")
    obs[name] = ob
    if beat > 1:
        sc.frame_set(1); ob.location = (OFF, y, ob.location.z); ob.keyframe_insert("location", frame=1)
        sc.frame_set(beat - 1); ob.location = (OFF, y, ob.location.z); ob.keyframe_insert("location", frame=beat - 1)
        sc.frame_set(beat); ob.location = (x, y, ob.location.z); ob.keyframe_insert("location", frame=beat)
    else:
        sc.frame_set(1); ob.location = (x, y, ob.location.z); ob.keyframe_insert("location", frame=1)
    sc.frame_set(720); ob.location = (x, y, ob.location.z); ob.keyframe_insert("location", frame=720)
# the four argue at once, 20-25s: a small alternating bob on each of them
for k, name in enumerate(("OLDMAN", "VISITOR_B", "CRITIC", "STUDENT")):
    ob = obs[name]; z0 = ob.location.z; x, y = [r for r in row if r[0] == name][0][1:3]
    for i, fr in enumerate(range(481, 601, 8)):
        sc.frame_set(fr); ob.location = (x, y, z0 + (0.04 if (i + k) % 2 == 0 else 0.0)); ob.keyframe_insert("location", frame=fr)
    sc.frame_set(606); ob.location = (x, y, z0); ob.keyframe_insert("location", frame=606)
# Dupe far back with his cart, cleaning, never part of the row
dupe = spawn_char(col, "DUPE", (-2.35, -17.20), h=1.80, prefix="s2aj")
build_cart(col, (-3.30, -16.60), prefix="s2aj", with_painting=True)
cart = bpy.data.objects.get("s2aj_cart_base")
if cart:
    cart.rotation_euler.z = R(90)
    for o in bpy.data.objects:
        if o.name.startswith("s2aj_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2aj_painting", (-3.30, -16.20, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# constant interpolation so an arrival is a jump, not a slide
def all_fcurves(act):
    fl = getattr(act, "fcurves", None)
    if fl is not None:
        yield from fl; return
    for layer in getattr(act, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                yield from cb.fcurves
for ob in list(obs.values()):
    ad = ob.animation_data
    if ad and ad.action:
        for fc in all_fcurves(ad.action):
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'

cam_d = bpy.data.cameras.new("CAM_S2AJ"); cam_d.lens = 28
cam = bpy.data.objects.new("CAM_S2AJ", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0.0, -23.60, 2.45)
cam.rotation_euler = (R(80), 0, 0)
for who, name in (("OLD MAN", "OLDMAN"), ("FUR", "VISITOR_B"), ("CRITIC", "CRITIC"), ("STUDENT", "STUDENT"), ("COBALT", "COLLECTOR_A")):
    tag_label(col, who, obs[name], cam, prefix="s2aj")
tag_label(col, "DUPE", dupe, cam, prefix="s2aj")

for a, v in (("use_shadows", False), ("use_raytracing", False), ("use_fast_gi", False), ("taa_render_samples", 4)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
sc.render.engine = 'BLENDER_EEVEE'
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2AJ-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2AJ_previz.blend")
sc.frame_set(1)
bpy.ops.render.render(animation=True); print("RENDER-DONE")
