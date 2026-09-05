# Rebuild the hero-wall crack to CRACK-CANON.md.
#
# What was there: crack_core, a 45mm CUBE, plus FIVE two-segment arms each made
# of a uniform-width box. Rendered as a square with five straight bars, which is
# what Seedance copied into the film — a video reference beats prose, so the
# canon text never had a chance.
#
# What canon actually specifies: a solid arrowhead-shaped blade pointing DOWN
# with a hooked spur off its upper right and a notch at its upper left, and
# FOUR arms that thicken, thin, kink, carry beads and throw one barb.
import bpy, bmesh, math

BLEND = r"C:\Users\UsEr\Downloads\SorrySir_hall_v41.blend"
bpy.ops.wm.open_mainfile(filepath=BLEND)

CX, CY, CZ = 0.000, -21.820, 2.450     # keep the crack exactly where it sits
THICK = 0.012

old = [o for o in bpy.data.objects if o.name.startswith("crack_")]
mat = None
for o in old:
    if o.data.materials and mat is None:
        mat = o.data.materials[0]
print("removing %d old crack pieces (mat=%s)" % (len(old), mat.name if mat else None))
for o in old:
    bpy.data.objects.remove(o, do_unlink=True)
if mat is None:
    mat = bpy.data.materials.new("crack_black")
    mat.use_nodes = False
    mat.diffuse_color = (0.01, 0.01, 0.01, 1.0)

def make(name, loops):
    """loops: list of [(x,z), ...] outlines in the wall plane, local to centre."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for pts in loops:
        vs = [bm.verts.new((x, -THICK / 2, z)) for x, z in pts]
        bm.faces.new(vs)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = (CX, CY, CZ)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    m = ob.modifiers.new("solid", 'SOLIDIFY'); m.thickness = THICK
    return ob

def strip(name, path):
    """path: [(x, z, halfwidth), ...] — a tapered ribbon that can kink and bead."""
    left, right = [], []
    for i, (x, z, w) in enumerate(path):
        if i == 0:      dx, dz = path[1][0] - x, path[1][2 - 1] - z
        elif i == len(path) - 1: dx, dz = x - path[i-1][0], z - path[i-1][1]
        else:           dx, dz = path[i+1][0] - path[i-1][0], path[i+1][1] - path[i-1][1]
        L = math.hypot(dx, dz) or 1.0
        nx, nz = -dz / L, dx / L
        left.append((x + nx * w, z + nz * w))
        right.append((x - nx * w, z - nz * w))
    return make(name, [left + right[::-1]])

# --- the blade: arrowhead pointing DOWN, notch at upper left
# It must read as a piece of wall that has come away, not as the junction the
# arms happen to meet at, so it is deliberately large against them.
make("crack_core", [[
    (-0.050,  0.048),   # top left
    (-0.034,  0.030),   # into THE NOTCH
    (-0.026,  0.046),   # back out of it
    ( 0.052,  0.050),   # top right, where the spur leaves
    ( 0.034, -0.006),   # right side falling inward
    ( 0.010, -0.058),   # THE POINT
    (-0.026, -0.008),   # left side rising back
]])

# --- the hooked spur off the upper right: leaves, bends back on itself, stops
strip("crack_spur", [
    (0.052, 0.046, 0.0110), (0.076, 0.058, 0.0090), (0.092, 0.074, 0.0075),
    (0.090, 0.090, 0.0060), (0.074, 0.096, 0.0048), (0.058, 0.086, 0.0016),
])

# --- ARM 1 · 12 o'clock, leaning left, one oval bead a third up, hairline end
strip("crack_arm_12", [
    (-0.010, 0.046, 0.0080), (-0.014, 0.072, 0.0050), (-0.008, 0.085, 0.0100),
    (-0.011, 0.105, 0.0046), (-0.015, 0.140, 0.0028), (-0.019, 0.170, 0.0008),
])
# --- ARM 2 · 1:30, longest and heaviest, lumpy, kinks once about halfway
strip("crack_arm_0130", [
    (0.050, 0.044, 0.0105), (0.072, 0.062, 0.0074), (0.082, 0.072, 0.0110),
    (0.098, 0.098, 0.0065), (0.135, 0.113, 0.0092), (0.168, 0.140, 0.0048),
    (0.196, 0.162, 0.0014),
])
# --- ARM 3 · 9:30, shallow down-left, beaded, thinner, fine point
strip("crack_arm_0930", [
    (-0.042, 0.010, 0.0076), (-0.070, -0.002, 0.0048), (-0.086, -0.010, 0.0082),
    (-0.115, -0.018, 0.0038), (-0.148, -0.026, 0.0012),
])
# --- ARM 4 · 4:30 off the blade's point, kinks, throws a barb, tapers to a needle
strip("crack_arm_0430", [
    (0.010, -0.056, 0.0085), (0.032, -0.078, 0.0060), (0.046, -0.078, 0.0068),
    (0.056, -0.104, 0.0048), (0.086, -0.134, 0.0050), (0.108, -0.152, 0.0030),
    (0.126, -0.170, 0.0010),
])
# --- the barb thrown off arm 4 near its end
strip("crack_arm_0430_barb", [
    (0.086, -0.134, 0.0038), (0.104, -0.126, 0.0026), (0.120, -0.124, 0.0008),
])

bpy.context.view_layer.update()
pieces = [o for o in bpy.data.objects if o.name.startswith("crack_")]
xs = [v[0] for o in pieces for v in [(o.location.x + c[0], 0, 0) for c in [(0,0,0)]]]
print("=== NEW CRACK: %d pieces ===" % len(pieces))
for o in sorted(pieces, key=lambda x: x.name):
    print("  %-24s dim=(%.3f, %.3f, %.3f)" % (o.name, *o.dimensions))
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("saved", BLEND)
