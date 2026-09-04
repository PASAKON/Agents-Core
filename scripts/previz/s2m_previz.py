# S2M previz — THE REGISTRAR. Same wall-cavity camera as S2L, and every one of
# the five is on the exact x/y S2L left them on, so the two clips cut together
# with nobody moving across the join. Only the REGISTRAR is new: he walks down
# the hall with his ledger, comes round to the group's LEFT so he faces them
# without ever crossing in front of the crack, delivers the welcome, takes the
# WOMAN's offer, and turns to go.
#
# Why he arrives on the left and stops at the group's own depth: the five face
# the crack, which means they face the lens. Anyone addressing them has to be
# beside them, not behind them, or they would all have to turn their backs to
# camera to listen.
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
for n in ("wall_hero_panel", "wall_crack_end"):
    ob = bpy.data.objects.get(n)
    if ob: ob.hide_render = ob.hide_viewport = True


# ---- the crack, scaled 1.5x IN THE PREVIZ ONLY (CEO 2026-09-04 halved it
# from 3x: big enough to say WHERE the break is, small enough that the model
# is not tempted to copy this crude grey shape instead of the real Element). At true size it is 0.34 m of
# hairline sticks 1.78 m from the lens, and it renders as a small dark mark
# that the eye reads as being on the far wall. That misreading is precisely the
# failure this whole camera exists to prevent — the model keeps staging people
# in front of the break. A previz is a depth diagram, not a beauty render, so
# the break is drawn big enough that its position in front of everybody is
# unmistakable. The true shape and size come from the Element in the prompt.
_piv = (0.0, -21.82, 2.45)
for _o in bpy.data.objects:
    if _o.name.startswith("crack_"):
        _o.location = tuple(_piv[i] + (_o.location[i] - _piv[i]) * 1.5 for i in range(3))
        _o.scale = tuple(v * 1.5 for v in _o.scale)

exec(open(r"C:\Users\UsEr\Downloads\charlib.py").read())
col = sc.collection

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc); o = bpy.context.object; o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name+"_m"); m.use_nodes = False
    m.diffuse_color = color; o.data.materials.append(m); return o

# ---- the five, exactly where S2L ended. Do not tidy these numbers.
woman   = spawn_char(col, "COLLECTOR_A",     (-1.60, -19.95), h=1.68, prefix="s2m")
student = spawn_char(col, "STUDENT", ( -0.45, -19.72), h=1.70, prefix="s2m")
wifeB   = spawn_char(col, "VISITOR_B", ( 0.40, -19.88), h=1.66, prefix="s2m")
manA    = spawn_char(col, "VISITOR_A", ( 1.05, -19.55), h=1.78, prefix="s2m")
critic  = spawn_char(col, "CRITIC",  ( 1.80, -19.95), h=1.64, prefix="s2m")
dupe    = spawn_char(col, "DUPE",      (-2.40, -17.20), h=1.80, prefix="s2m")
regis   = spawn_char(col, "REGISTRAR", (-5.00,  -8.00), h=1.80, prefix="s2m")
build_cart(col, (-3.30, -16.60), prefix="s2m", with_painting=True)
cart = bpy.data.objects.get("s2m_cart_base")
if cart:
    cart.rotation_euler.z = R(90)
    for o in bpy.data.objects:
        if o.name.startswith("s2m_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2m_painting", (-3.30, -16.20, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

cam_d = bpy.data.cameras.new("CAM_S2M"); cam_d.lens = 28
cam = bpy.data.objects.new("CAM_S2M", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0.0, -23.60, 2.45)
cam.rotation_euler = (R(80), 0, 0)   # 10 deg down; the crack is at 2.45 m, above their heads


for who, ob in (("WOMAN", woman), ("STUDENT", student), ("WIFE", wifeB),
                ("MAN_A", manA), ("CRITIC", critic), ("DUPE", dupe), ("REGISTRAR", regis)):
    tag_label(col, who, ob, cam, prefix="s2m")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# REGISTRAR: (-5.00,-8.00) -> (-3.20,-19.00) is 11.13 m. At 1.20 m/s that is
# 9.3 s = 223 frames — an ordinary unhurried walk, which is the whole character:
# he is welcoming guests, not responding to anything yet. He speaks while he
# walks. At 18 s he turns to leave and the clip cuts before he has gone.
key(regis, 1,   -5.00,  -8.00)
key(regis, 223, -3.20, -19.00)
key(regis, 432, -3.20, -19.00)
key(regis, 480, -3.45, -18.55)     # the first half-step away, no more

# the five hold. Only the WOMAN turns, and a turn is not a translation, so she
# keeps her exact mark — the model gets the turn from the prompt, not from here.
for ob, x, y in ((woman, -1.60, -19.95), (student, -0.45, -19.72),
                 (wifeB, 0.40, -19.88), (manA, 1.05, -19.55), (critic, 1.80, -19.95)):
    key(ob, 1, x, y); key(ob, 480, x, y)

key(dupe, 1, -2.40, -17.20); key(dupe, 240, -2.05, -17.20); key(dupe, 480, -2.35, -17.20)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2M-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2M_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
