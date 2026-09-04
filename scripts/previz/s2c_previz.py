# S2C previz — the pacing. ONE locked camera, no moves at all.
# Dupe paces left/right, exits, comes back, freezes for the PA, exits for good,
# leaving the audience alone with the cart.
import bpy, math
from math import radians as R

sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 480          # 20s @ 24fps
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24

# hall_v41 holds a marker binding CAM_FLY4 — it overrides scene.camera on render
sc.timeline_markers.clear()
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

# the cart is PARKED and never moves — it is what the audience is left with
cart = build_cart(col, (2.75, -12.30), prefix="s2c", with_painting=True)
cart_root = bpy.data.objects.get("s2c_cart_base")
for o in bpy.data.objects:
    if o.name.startswith("s2c_cart_") and o is not cart_root:
        o.parent = cart_root; o.matrix_parent_inverse = cart_root.matrix_world.inverted()
# the painting rides in the rack at the size it had on the wall
box("s2c_painting", (2.75, -11.90, 1.35), (0.80, 0.05, 0.72), (0.45,0.45,0.45,1)).parent = cart_root

dupe = spawn_char(col, "DUPE", (0.0, -14.3), h=1.8, prefix="s2c")

cam_d = bpy.data.cameras.new("CAM_S2C"); cam_d.lens = 24
cam = bpy.data.objects.new("CAM_S2C", cam_d); sc.collection.objects.link(cam)
sc.camera = cam
# looking UP the hall, away from the crack: chair+rug at y=-9, the trap hanging
# at y=-13, the vessel at y=-6, the study on the +x wall, millstone far off.
cam.location = (0.0, -17.4, 1.55)
cam.rotation_euler = (R(90), 0, 0)             # locked, level, looking along +y
tag_label(col, "DUPE", dupe, cam, prefix="s2c")
tag_label(col, "CART", cart_root, cam, z=1.4, prefix="s2c")

def key(o, fr, x, y=-14.3):
    sc.frame_set(fr); o.location = (x, y, o.location.z)
    o.keyframe_insert("location", frame=fr)

# ---- the pacing, all of it lateral, all of it hurried ----
# frames: 24 = 1s. Off-frame is roughly |x| > 3.4 at this lens and distance.
PACE = [
    # CEO 2026-09-05: HE WALKS, SLOWLY. He does not run at any point.
    #
    # The old table said "hurried" in its comments while the prompt said "no
    # running" in its negatives, and the motion said something else again.
    # Measured: seven of its eleven segments were over 2.0 m/s, where people
    # stop walking and break into a run, and one was 5.67 m/s, a sprint. The
    # model takes motion from the video reference, so the reference beat the
    # words and Dupe ran.
    #
    # Every segment below is at or under 0.84 m/s. Ordinary walking is about
    # 1.3-1.4 m/s, so this is deliberately SLOWER than a normal walk — the pace
    # of a worried man going back and forth, not a man hurrying anywhere.
    #
    # The agitation comes from everything except his legs — breath, hands, jaw,
    # eyes — which is what the prompt carries.
    #
    # DROPPED: the mid-scene exit at 5s and return at 7s. At walking pace he
    # cannot cross to off-frame and come back before the PA at 10s; it only fit
    # before because he was running. He now paces the whole first ten seconds,
    # stops dead for the announcement, paces again, and walks out for good at
    # the end. Off-frame is roughly |x| > 3.4 at this lens and distance.
    (1,    0.0), (60,  -2.0), (145,  0.6), (200, -1.2), (243,  0.3),
    (336,  0.3),                                          # frozen for the PA, 10.1s to 14.0s
    (396, -1.6), (436, -2.9),                             # pacing again, drifting left
    (480, -3.9),                                          # walks out left, clear by ~frame 458
]
for fr, x in PACE:
    key(dupe, fr, x)

for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 8)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
try: sc.render.image_settings.media_type = "VIDEO"        # Blender 5.x gate
except Exception as e: print("media_type:", e)
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "HIGH"; sc.render.ffmpeg.audio_codec = "NONE"
sc.render.filepath = r"C:\Users\UsEr\Downloads\S2C-Render.MP4"
bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\UsEr\Downloads\S2C_previz.blend")
sc.frame_set(1)
print("render camera =", sc.camera.name, "markers =", len(sc.timeline_markers))
bpy.ops.render.render(animation=True)
print("RENDER-DONE")
