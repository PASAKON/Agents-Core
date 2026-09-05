# S2N previz — FIVE MILLION. Same wall-cavity camera and the same five on the
# same marks as S2L/S2M, so the cut is invisible. The GENTLEMAN and his
# BODYGUARD come in through the side door on the right and STOP just inside —
# he does not walk to anybody, he waits to be received, which is the whole
# character. The REGISTRAR crosses the hall to him.
#
# Why the side door and not the far red door: the hall is 43 m. A man entering
# at the vanishing point cannot be met and spoken to twice inside 20 s at any
# human walking speed — that arithmetic already forced a cutaway in S2I. The
# side door puts him 16.6 m from the registrar, which the registrar covers in
# 8.7 s at a hurrying 1.9 m/s and leaves 6 s for the two lines.
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

# ---- the five, exactly where S2M left them. Do not tidy these numbers.
woman   = spawn_char(col, "COLLECTOR_A",     (-1.60, -19.95), h=1.68, prefix="s2n")
student = spawn_char(col, "STUDENT", ( -0.45, -19.72), h=1.70, prefix="s2n")
wifeB   = spawn_char(col, "VISITOR_B", ( 0.40, -19.88), h=1.66, prefix="s2n")
manA    = spawn_char(col, "VISITOR_A", ( 1.05, -19.55), h=1.78, prefix="s2n")
critic  = spawn_char(col, "CRITIC",  ( 1.80, -19.95), h=1.64, prefix="s2n")
dupe    = spawn_char(col, "DUPE",      (-2.35, -17.20), h=1.80, prefix="s2n")
regis   = spawn_char(col, "REGISTRAR", (-3.20, -19.00), h=1.80, prefix="s2n")
gent    = spawn_char(col, "GENTLEMAN", ( 5.60,  -1.60), h=1.79, prefix="s2n")
guard   = spawn_char(col, "BODYGUARD", ( 5.95,  -0.90), h=1.94, prefix="s2n")
build_cart(col, (-3.30, -16.60), prefix="s2n", with_painting=True)
cart = bpy.data.objects.get("s2n_cart_base")
if cart:
    cart.rotation_euler.z = R(90)
    for o in bpy.data.objects:
        if o.name.startswith("s2n_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2n_painting", (-3.30, -16.20, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

# the side door they come through — a leaf hinged on its upstream edge so the
# swing reads, at the right wall about 18 m short of the hero wall
door = box("s2n_sidedoor", (5.90, -2.00, 1.35), (0.10, 1.30, 2.70), (0.32, 0.10, 0.10, 1))
door.location = (5.90, -2.65, 1.35)
piv = bpy.data.objects.new("s2n_door_piv", None); sc.collection.objects.link(piv)
piv.location = (5.90, -3.30, 0.0)
door.parent = piv; door.matrix_parent_inverse = piv.matrix_world.inverted()
piv.rotation_mode = 'XYZ'
for fr, ang in ((1, 0), (10, 0), (34, R(78)), (480, R(78))):
    sc.frame_set(fr); piv.rotation_euler.z = ang
    piv.keyframe_insert("rotation_euler", frame=fr)

cam_d = bpy.data.cameras.new("CAM_S2N"); cam_d.lens = 28
cam = bpy.data.objects.new("CAM_S2N", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0.0, -23.60, 2.45)
cam.rotation_euler = (R(80), 0, 0)   # 10 deg down; the crack is at 2.45 m, above their heads


for who, ob in (("WOMAN", woman), ("STUDENT", student), ("WIFE", wifeB),
                ("MAN_A", manA), ("CRITIC", critic), ("DUPE", dupe),
                ("REGISTRAR", regis), ("GENTLEMAN", gent), ("BODYGUARD", guard)):
    tag_label(col, who, ob, cam, prefix="s2n")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# GENTLEMAN: three steps in from the door and then he stops, for good. 2.1 m at
# 0.85 m/s = 2.5 s. A man who has just said a number does not walk toward
# anyone; he waits. The BODYGUARD shadows him and stops a pace behind.
key(gent, 1,  5.60, -1.60); key(gent, 24, 5.60, -1.60)
key(gent, 84, 4.30, -3.00); key(gent, 480, 4.30, -3.00)
key(guard, 1, 5.95, -0.90); key(guard, 34, 5.95, -0.90)
key(guard, 96, 5.25, -2.15); key(guard, 480, 5.25, -2.15)

# REGISTRAR: leaves the group at 5 s and covers 16.6 m at 1.90 m/s — hurrying,
# not running, which is 8.7 s = 209 frames. He arrives at 13.7 s and the two
# lines fill the rest. At 19.5 s he turns; the clip cuts before the step lands.
key(regis, 1,   -3.20, -19.00); key(regis, 120, -3.20, -19.00)
key(regis, 329,  2.95,  -3.80); key(regis, 468,  2.95,  -3.80)
key(regis, 480,  2.65,  -4.35)     # the turn begins, nothing more

# the five hold their marks; heads turn, and a turn is not a translation
for ob, x, y in ((woman, -1.60, -19.95), (student, -0.45, -19.72),
                 (wifeB, 0.40, -19.88), (manA, 1.05, -19.55), (critic, 1.80, -19.95)):
    key(ob, 1, x, y); key(ob, 480, x, y)

key(dupe, 1, -2.35, -17.20); key(dupe, 240, -2.00, -17.20); key(dupe, 480, -2.30, -17.20)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2N-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2N_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
