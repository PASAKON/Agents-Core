# S2D previz — three locked shots, cut at 7s and 10s.
#  1  0-7s   locked wide on the hero wall; cart in from the left, Dupe looks in
#  2  7-10s  from INSIDE the wall — handled as a black frame in previz; the real
#             shot is a generated plate, so this only holds the timing
#  3 10-20s  locked behind Dupe, looking down the gallery; door, guest, fake clean
import bpy, math
from math import radians as R

sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 480
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24
sc.timeline_markers.clear()                       # hall_v41 binds CAM_FLY4 otherwise
for o in bpy.data.objects:
    if o.name.startswith(("A_", "B_", "hvfly_tag", "Text.")):
        o.hide_render = o.hide_viewport = True

exec(open(r"C:\Users\UsEr\Downloads\charlib.py").read())
col = sc.collection

def box(name, loc, dim, color):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object; o.name = name
    o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    m = bpy.data.materials.new(name+"_m"); m.use_nodes = False
    m.diffuse_color = color; o.data.materials.append(m); return o

dupe = spawn_char(col, "DUPE", (0.9, -20.6), h=1.8, prefix="s2d")
build_cart(col, (2.4, -20.4), prefix="s2d", with_painting=True)
cart = bpy.data.objects.get("s2d_cart_base")
for o in bpy.data.objects:
    if o.name.startswith("s2d_cart_") and o is not cart:
        o.parent = cart; o.matrix_parent_inverse = cart.matrix_world.inverted()
box("s2d_painting", (2.4, -20.0, 1.35), (0.80, 0.05, 0.72), (0.45,0.45,0.45,1)).parent = cart
guest = spawn_char(col, "OLDMAN", (-1.6, 20.5), h=1.70, prefix="s2d")
guest.hide_render = guest.hide_viewport = True   # not in the room until the door opens

# the red door swings open as he enters — two leaves, hinged at their outer edges
dL, dR = bpy.data.objects.get("red_door_L"), bpy.data.objects.get("red_door_R")
for leaf, sign in ((dL, 1), (dR, -1)):
    if not leaf: continue
    leaf.rotation_mode = 'XYZ'
    for fr, ang in ((1, 0), (276, 0), (300, sign * 1.15), (480, sign * 1.15)):
        sc.frame_set(fr); leaf.rotation_euler.z = ang
        leaf.keyframe_insert("rotation_euler", frame=fr)

cam_d = bpy.data.cameras.new("CAM_S2D"); cam = bpy.data.objects.new("CAM_S2D", cam_d)
sc.collection.objects.link(cam); sc.camera = cam
tag_label(col, "DUPE", dupe, cam, prefix="s2d")
tag_label(col, "OLDMAN", guest, cam, prefix="s2d")
tag_label(col, "CART", cart, cam, z=1.4, prefix="s2d")

def ckey(fr, loc, rot, lens):
    sc.frame_set(fr); cam.location = loc; cam.rotation_euler = rot; cam_d.lens = lens
    cam.keyframe_insert("location", frame=fr); cam.keyframe_insert("rotation_euler", frame=fr)
    cam_d.keyframe_insert("lens", frame=fr)

WALL  = ((0, -15.6, 1.45), (R(90), 0, R(180)), 30)     # shot 1, straight on the wall
INSIDE= ((0.6, -21.86, 2.45), (R(96), 0, 0), 28)       # shot 2, at the crack looking out and down
BEHIND= ((0.9, -21.75, 2.30), (R(80), 0, 0), 24)       # shot 3, behind him looking up the gallery

ckey(1, *WALL);   ckey(167, *WALL)
ckey(168, *INSIDE); ckey(239, *INSIDE)
ckey(240, *BEHIND); ckey(480, *BEHIND)

def key(o, fr, x, y, z=None):
    sc.frame_set(fr)
    o.location = (x, y, o.location.z if z is None else z)
    o.keyframe_insert("location", frame=fr)

Z0 = dupe.location.z          # standing height of the proxy

# Dupe: wheels in from the left, steps to the wall, then turns and fake-cleans
key(dupe, 1, -4.6, -20.6); key(dupe, 120, 0.6, -20.6); key(dupe, 140, 0.6, -21.35)
# three hops at the wall — he is too short for a crack at z=2.45 and never
# quite gets his eye to it. up-down-up-down-up-down, 12 frames each way.
for base in (146, 152, 158):                        # all three land before the cut at 167
    key(dupe, base,     0.6, -21.35, Z0)
    key(dupe, base + 3, 0.6, -21.35, Z0 + 0.52)
    key(dupe, base + 6, 0.6, -21.35, Z0)
key(dupe, 288, 0.6, -21.35, Z0); key(dupe, 300, 0.9, -21.05, Z0)
key(dupe, 480, 0.9, -21.05, Z0)
zc = cart.location.z
key(cart, 1, -3.1, -20.4); key(cart, 120, 2.4, -20.4); key(cart, 480, 2.4, -20.4)
p = bpy.data.objects["s2d_painting"]
# guest: enters far end at 12s, drifts down the hall
for fr, vis in ((1, True), (287, True), (288, False)):
    sc.frame_set(fr)
    guest.hide_render = guest.hide_viewport = vis
    guest.keyframe_insert("hide_render", frame=fr)
    guest.keyframe_insert("hide_viewport", frame=fr)
key(guest, 1, -1.6, 20.5); key(guest, 287, -1.6, 20.5)
key(guest, 300, -1.6, 18.0); key(guest, 580, -1.2, 4.0)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"
except Exception as e: print("media_type:", e)
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2D-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2D_previz.blend")
sc.frame_set(1)
print("render camera =", sc.camera.name, "markers =", len(sc.timeline_markers))
bpy.ops.render.render(animation=True)
print("RENDER-DONE")
