# Patient zéro — logo 3D : le virus ouvre la gueule et croque l'écran, « PZ » brille au fond.
# Lancer :  blender -b -P blender_logo.py -- <sortie.png> [taille]
import bpy, bmesh, math, sys
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = args[0] if args else '//blender-virus.png'
SIZE = int(args[1]) if len(args) > 1 else 1024

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try: sc.render.engine = eng; break
    except Exception: pass
sc.render.resolution_x = sc.render.resolution_y = SIZE
sc.render.film_transparent = False
sc.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
sc.view_settings.look = 'None'

def mat(name, col, rough=.4, metal=0., emit=None, strength=0.):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = strength
    return m

BLACK = mat('virus', (.012, .012, .014), .28, .35)
BONE  = mat('dents', (.78, .72, .58), .5)
GLOW  = mat('pz', (1, .95, .8), .3, emit=(1, .78, .45), strength=14)
GORGE = mat('gorge', (.0, .0, .0), 1., emit=(.05, .0, .0), strength=.1)

def link(o):
    bpy.context.collection.objects.link(o); return o

def mesh_from_bm(name, bm, m):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(m); return o

R = 1.6
# --- mâchoires : une icosphère coupée en deux, chaque moitié pivote autour d'une charnière à l'arrière
def jaw(name, upper):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=R)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=upper, clear_outer=not upper)
    return mesh_from_bm(name, bm, BLACK)
up, lo = jaw('machoire_haut', True), jaw('machoire_bas', False)
for o in (up, lo):
    o.modifiers.new('epaisseur', 'SOLIDIFY').thickness = .12

hingeU = link(bpy.data.objects.new('charniere_haut', None)); hingeU.location = (0, 1.15, 0)
hingeL = link(bpy.data.objects.new('charniere_bas', None)); hingeL.location = (0, 1.15, 0)
for o, h in ((up, hingeU), (lo, hingeL)):
    o.parent = h; o.location = (0, -1.15, 0)

def cone(loc, direction, r, depth, m, parent, verts=4):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=0, depth=depth, location=loc)
    c = bpy.context.active_object
    c.rotation_euler = Vector(direction).normalized().to_track_quat('Z', 'Y').to_euler()
    for p in c.data.polygons: p.use_smooth = False
    c.data.materials.append(m)
    mw = c.matrix_world.copy(); c.parent = parent; c.matrix_world = mw
    return c

# --- pointes du virus, sur toute la coque
ico = bmesh.new(); bmesh.ops.create_icosphere(ico, subdivisions=1, radius=1)
for v in ico.verts:
    n = v.co.normalized()
    if abs(n.z) < .12: continue
    if n.y < -.55 and abs(n.z) < .5: continue  # pas de pointe dans l'ouverture
    par = up if n.z > 0 else lo
    cone(n * R * 1.0 + n * .42, n, .21, 1.0, BLACK, par)
ico.free()

# --- dents le long des deux mâchoires, côté caméra
for k in range(11):
    a = math.radians(205 + k * 13)
    p = Vector((math.cos(a) * R * .93, math.sin(a) * R * .93, 0))
    if p.y > -.25: continue
    cone(p + Vector((0, 0, .02)), (0, .15, -1), .13, .5 + .15 * (k % 2), BONE, up, 5)
    cone(p - Vector((0, 0, .02)), (0, .15, 1), .12, .42 + .12 * ((k + 1) % 2), BONE, lo, 5)

# --- ouverture de la gueule
hingeU.rotation_euler.x = math.radians(-34)
hingeL.rotation_euler.x = math.radians(24)

# --- le fond de la gorge et « PZ » qui brille dedans
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1.05, location=(0, .75, 0))
link_g = bpy.context.active_object; link_g.data.materials.append(GORGE)

# plaque « PZ » façon logo B, rouge foncé, tenue au fond de la gueule
import os
PLQ = bpy.data.materials.new('plaque'); PLQ.use_nodes = True
pn = PLQ.node_tree; pb = pn.nodes['Principled BSDF']
tex = pn.nodes.new('ShaderNodeTexImage')
tex.image = bpy.data.images.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plaque-pz.png'))
pn.links.new(tex.outputs['Color'], pb.inputs['Base Color'])
pn.links.new(tex.outputs['Color'], pb.inputs['Emission Color'])
pb.inputs['Emission Strength'].default_value = .22; pb.inputs['Roughness'].default_value = .35
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -.45, .12), rotation=(math.radians(90), math.radians(180), 0))
pl = bpy.context.active_object; pl.scale = (1.3, 1.3, .06)
bpy.ops.object.transform_apply(scale=True)
pl.data.materials.append(PLQ)
# UV : chaque face reçoit l'image entière
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.reset(); bpy.ops.object.mode_set(mode='OBJECT')

# langue : charnue, brillante, avec un sillon au milieu et des papilles
TONGUE = bpy.data.materials.new('langue'); TONGUE.use_nodes = True
tn = TONGUE.node_tree; tb = tn.nodes['Principled BSDF']
tb.inputs['Base Color'].default_value = (.36, .025, .03, 1); tb.inputs['Roughness'].default_value = .18
try: tb.inputs['Subsurface Weight'].default_value = .25; tb.inputs['Subsurface Radius'].default_value = (.6, .1, .1)
except Exception: pass
nz = tn.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 90
bump = tn.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .6
tn.links.new(nz.outputs['Fac'], bump.inputs['Height']); tn.links.new(bump.outputs['Normal'], tb.inputs['Normal'])
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=1)
for v in bm.verts:
    x, y, z = v.co
    y *= 1.5; x *= .72 * (1 - .25 * max(0, -y))      # s'affine vers la pointe
    z *= .22
    if z > 0: z -= .07 * math.exp(-(x / .12) ** 2)     # sillon central
    z += .32 * max(0, -y - .5) ** 2                   # la pointe remonte
    v.co = (x, y, z)
me = bpy.data.meshes.new('langue'); bm.to_mesh(me); bm.free()
tg = link(bpy.data.objects.new('langue', me)); tg.data.materials.append(TONGUE)
for p in me.polygons: p.use_smooth = True
tg.location = (0, -1.2, -.82); tg.rotation_euler.x = math.radians(30); tg.scale = (.62, .62, .7)
sub = tg.modifiers.new('lisse', 'SUBSURF'); sub.levels = sub.render_levels = 1

# --- pattes qui viennent agripper l'écran (vers les coins de l'image)
def seg(a, b, r, m):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=d.length, location=(a + b) / 2)
    c = bpy.context.active_object; c.rotation_euler = d.normalized().to_track_quat('Z', 'Y').to_euler(); c.data.materials.append(m)
    for p in c.data.polygons: p.use_smooth = False
for sx in (-1, 1):
    for sz in (-1, 1):
        root = (sx * 1.2, -.1, sz * .6); knee = (sx * 3.0, -1.4, sz * 2.3); tip = (sx * 2.1, -4.7, sz * 1.75)
        seg(root, knee, .14, BLACK); seg(knee, tip, .11, BLACK)
        cone(Vector(tip) + (Vector(tip) - Vector(knee)).normalized() * .25, Vector(tip) - Vector(knee), .12, .5, BLACK, None)
# 4 pattes de plus, pliées en trois, qui sortent sur les côtés
for sx in (-1, 1):
    for sz in (-1, 1):
        pts = [(sx * 1.4, .1, sz * .3), (sx * 3.3, -.3, sz * 1.25), (sx * 4.0, -2.2, sz * .9), (sx * 3.4, -4.4, sz * .35)]
        for a, b, r in zip(pts, pts[1:], (.13, .11, .09)): seg(a, b, r, BLACK)
        for p in pts[1:3]:
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=.15, location=p); bpy.context.active_object.data.materials.append(BLACK)
        cone(Vector(pts[3]) + (Vector(pts[3]) - Vector(pts[2])).normalized() * .22, Vector(pts[3]) - Vector(pts[2]), .1, .45, BLACK, None)

# --- décor : le carrelage jauni des Poolrooms, flou au loin
TILE = bpy.data.materials.new('carrelage'); TILE.use_nodes = True
nt = TILE.node_tree; bsdf = nt.nodes['Principled BSDF']
br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0; br.squash = 1
br.inputs['Color1'].default_value = (.62, .57, .42, 1); br.inputs['Color2'].default_value = (.56, .51, .37, 1)
br.inputs['Mortar'].default_value = (.42, .39, .3, 1); br.inputs['Scale'].default_value = 6; br.inputs['Mortar Size'].default_value = .025
br.inputs['Brick Width'].default_value = .5; br.inputs['Row Height'].default_value = .5
nt.links.new(br.outputs['Color'], bsdf.inputs['Base Color']); bsdf.inputs['Roughness'].default_value = .25
bpy.ops.mesh.primitive_plane_add(size=26, location=(0, 6, 0), rotation=(math.radians(90), 0, 0)); bpy.context.active_object.data.materials.append(TILE)
bpy.ops.mesh.primitive_plane_add(size=26, location=(0, -2, -3.4)); bpy.context.active_object.data.materials.append(TILE)

# --- caméra et lumières
cam = link(bpy.data.objects.new('cam', bpy.data.cameras.new('cam')))
cam.location = (0, -8.4, 1.5); cam.rotation_euler = (math.radians(80), 0, 0); cam.data.lens = 46
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 7.4; cam.data.dof.aperture_fstop = 1.8
sc.camera = cam
def light(kind, loc, energy, col, size=1.):
    l = bpy.data.lights.new(kind + str(len(bpy.data.lights)), kind); l.energy = energy; l.color = col
    if kind == 'AREA': l.size = size
    o = link(bpy.data.objects.new(l.name, l)); o.location = loc
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
light('AREA', (-4.5, -5.5, 5.5), 900, (1, .9, .72), 4)
light('AREA', (4.5, 3.5, 3.5), 900, (.7, .85, 1), 3)
light('POINT', (0, -1.6, .3), 18, (1, .55, .35))
w = bpy.data.worlds.new('monde'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (.08, .07, .05, 1); sc.world = w

# halo lumineux autour du « PZ » (compositeur)
sc.use_nodes = True; ct = sc.node_tree
for n in list(ct.nodes): ct.nodes.remove(n)
rl = ct.nodes.new('CompositorNodeRLayers'); gl = ct.nodes.new('CompositorNodeGlare'); co = ct.nodes.new('CompositorNodeComposite')
try: gl.glare_type = 'FOG_GLOW'
except Exception: pass
for attr, val in (('threshold', 1.0), ('size', 7), ('quality', 'HIGH')):
    try: setattr(gl, attr, val)
    except Exception: pass
ct.links.new(rl.outputs['Image'], gl.inputs['Image']); ct.links.new(gl.outputs['Image'], co.inputs['Image'])
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('RENDU OK', OUT)
