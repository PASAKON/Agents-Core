# CEO 2026-09-04: the crack sits too high. Measure plaque centre -> crack centre
# and move the whole crack DOWN by 30% of that distance.
import bpy
BLEND = r"C:\Users\UsEr\Downloads\SorrySir_hall_v41.blend"
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene

plaque = bpy.data.objects["plaque"]
pieces = [o for o in bpy.data.objects if o.name.startswith("crack_")]
core = bpy.data.objects["crack_core"]
gap = core.location.z - plaque.location.z
drop = gap * 0.30
print("plaque z=%.3f  crack centre z=%.3f  gap=%.3f  drop 30%%=%.3f" %
      (plaque.location.z, core.location.z, gap, drop))
for o in pieces:
    o.location.z -= drop
bpy.context.view_layer.update()
print("crack centre now z=%.3f   new gap=%.3f" % (core.location.z, core.location.z - plaque.location.z))

# one still from the shot-1 camera so the CEO can judge before any animation
sc.timeline_markers.clear()
for o in bpy.data.objects:
    if o.name.startswith(("A_", "B_", "hvfly_tag", "Text.")):
        o.hide_render = o.hide_viewport = True
import math
cam_d = bpy.data.cameras.new("CAM_STILL"); cam_d.lens = 30
cam = bpy.data.objects.new("CAM_STILL", cam_d); sc.collection.objects.link(cam)
sc.camera = cam
cam.location = (0, -15.6, 1.45)
cam.rotation_euler = (math.radians(90), 0, math.radians(180))
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
for a, v in (("use_shadows", False), ("use_raytracing", False), ("taa_render_samples", 16)):
    try: setattr(sc.eevee, a, v)
    except Exception: pass
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = r"C:\Users\UsEr\Downloads\crack-lowered.png"
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("STILL-DONE + MASTER-SAVED")
