# S2H previz — THE COUPLE. Camera sits BEHIND the hero wall at the crack's own
# height, looking out down the gallery. The wall panels are hidden for the
# render so the crack reads as a black silhouette in the extreme foreground,
# with everyone in the room BEHIND it. That ordering is the whole point of the
# shot: the model keeps putting people in front of the crack and it is wrong.
import bpy, math
from math import radians as R
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 288          # 12s
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24
sc.timeline_markers.clear()                     # marker binds CAM_FLY4 otherwise
for o in bpy.data.objects:
    if o.name.startswith(("A_", "B_", "hvfly_tag", "Text.")):
        o.hide_render = o.hide_viewport = True
# hide the wall itself, keep the crack — the camera is inside the cavity
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

# the couple, far RIGHT of frame as the CEO asked
wife    = spawn_char(col, "VISITOR_B", ( 1.85, -19.7), h=1.66, prefix="s2h")
husband = spawn_char(col, "VISITOR_A", ( 2.60, -19.5), h=1.78, prefix="s2h")
# Dupe well left, working, never crossing to them
dupe    = spawn_char(col, "DUPE",      (-2.6, -17.2), h=1.80, prefix="s2h")
build_cart(col, (-3.3, -16.6), prefix="s2h", with_painting=True)
cart = bpy.data.objects.get("s2h_cart_base")
if cart:
    cart.rotation_euler.z = R(90)
    for o in bpy.data.objects:
        if o.name.startswith("s2h_cart_") and o is not cart:
            o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
    box("s2h_painting", (-3.3, -16.2, 1.35), (0.80,0.05,0.72), (0.45,0.45,0.45,1)).parent = cart

cam_d = bpy.data.cameras.new("CAM_S2H"); cam_d.lens = 21
cam = bpy.data.objects.new("CAM_S2H", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0.0, -22.45, 2.45)              # behind the wall, at crack height
cam.rotation_euler = (R(90), 0, 0)              # looking out along +y, down the hall
for who, ob in (("WIFE", wife), ("HUSBAND", husband), ("DUPE", dupe)):
    tag_label(col, who, ob, cam, prefix="s2h")

def key(o, fr, x, y, z=None):
    sc.frame_set(fr); o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

# the couple barely move — she is rooted, he closes the last half metre to her
key(wife, 1, 1.85, -19.7); key(wife, 288, 1.85, -19.7)
key(husband, 1, 2.75, -19.4); key(husband, 96, 2.30, -19.6); key(husband, 288, 2.30, -19.6)

# Dupe works his way slowly along, never toward them. 0.35 m/s — he is cleaning,
# not walking; the pace comes from the motion research, not from feel.
key(dupe, 1, -2.6, -17.2); key(dupe, 144, -1.9, -17.2); key(dupe, 288, -2.4, -17.2)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception: pass
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2H-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2H_previz.blend")
sc.frame_set(1)
print("cam", sc.camera.name, "markers", len(sc.timeline_markers))
bpy.ops.render.render(animation=True); print("RENDER-DONE")
