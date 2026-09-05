# S2L previz — THE COLLECTOR ARRIVES. Camera sits BEHIND the hero wall at the
# crack's own height, looking out down the gallery. The wall panels are hidden
# for the render so the crack reads as a black silhouette in the extreme
# foreground with everyone in the room BEHIND it. That ordering is the whole
# point: the model keeps putting people in front of the crack and it is wrong.
#
# The scene: WOMAN (blue coat) walks in from deep in the hall and joins the
# group at the crack. VISITOR_A, who has been browsing in the background since
# S2I, finally drifts over and joins too — so the clip ENDS on the five the CEO
# named, standing at the crack, unevenly spaced, not in a smart row.
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
# hide the wall itself, keep the crack — the camera is inside the cavity
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

# ---- the group at the crack. x/y carried forward from S2H + S2I unchanged, so
# the cut between scenes does not move anybody. Gaps are 1.60 / 1.70 / 0.75 /
# 0.95 and depths run -19.45 to -19.95 — deliberately uneven, per the CEO's
# "do not stand smart, uneven gaps".
woman   = spawn_char(col, "COLLECTOR_A",     (-1.45,  -4.00), h=1.68, prefix="s2l")  # walks in
student = spawn_char(col, "STUDENT", ( -0.45, -19.72), h=1.70, prefix="s2l")
wifeB   = spawn_char(col, "VISITOR_B", ( 0.40, -19.88), h=1.66, prefix="s2l")
manA    = spawn_char(col, "VISITOR_A", ( 4.60,  -7.50), h=1.78, prefix="s2l")  # joins
critic  = spawn_char(col, "CRITIC",  ( 1.80, -19.95), h=1.64, prefix="s2l")
dupe    = spawn_char(col, "DUPE",      (-2.60, -17.20), h=1.80, prefix="s2l")
build_cart(col, (-3.30, -16.60), prefix="s2l", with_painting=True)
cart = bpy.data.objects.get("s2l_cart_base")
if cart:
    cart.rotation_euler.z = R(90)
    for o in bpy.data.objects:
        if o.name.startswith("s2l_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2l_painting", (-3.30, -16.20, 1.35), (0.80, 0.05, 0.72), (0.45, 0.45, 0.45, 1)).parent = cart

cam_d = bpy.data.cameras.new("CAM_S2L"); cam_d.lens = 28
cam = bpy.data.objects.new("CAM_S2L", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0.0, -23.60, 2.45)              # behind the wall, at crack height
cam.rotation_euler = (R(80), 0, 0)   # 10 deg down; the crack is at 2.45 m, above their heads              # looking out along +y, down the hall


for who, ob in (("WOMAN", woman), ("STUDENT", student), ("WIFE", wifeB),
                ("MAN_A", manA), ("CRITIC", critic), ("DUPE", dupe)):
    tag_label(col, who, ob, cam, prefix="s2l")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# WOMAN: 15.95 m at 1.10 m/s = 14.5 s = 348 frames. Speed drives the frame
# count, never the other way round — see the motion research. She then stands
# and does not move again: the reaction is held, not walked off.
key(woman, 1,   -1.45,  -4.00)
key(woman, 348, -1.60, -19.95)
key(woman, 480, -1.60, -19.95)

# VISITOR_A leaves the background at 2s and takes 16 s to cover 12.1 m —
# 0.76 m/s, an elderly man still looking at things on the way, not walking to
# somewhere. He is the last to arrive, which is what makes the five complete.
key(manA, 1,    4.60,  -7.50)
key(manA, 48,   4.60,  -7.50)
key(manA, 432,  1.05, -19.55)
key(manA, 480,  1.05, -19.55)

# the three already at the crack barely move — a shift of weight, nothing more
key(student, 1,  -0.45, -19.72); key(student, 480,  -0.45, -19.72)
key(wifeB,   1,  0.40, -19.88); key(wifeB,   480,  0.40, -19.88)
key(critic,  1,  1.80, -19.95); key(critic,  240,  1.68, -19.90); key(critic, 480, 1.80, -19.95)

# Dupe works his way slowly along, never toward them. 0.35 m/s — he is cleaning,
# not walking; the pace comes from the motion research, not from feel.
key(dupe, 1, -2.60, -17.20); key(dupe, 240, -1.90, -17.20); key(dupe, 480, -2.40, -17.20)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2L-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2L_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
