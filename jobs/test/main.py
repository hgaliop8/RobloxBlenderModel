"""Test de l'installation : une main stylisée en chair (sous-surface), rendu Cycles + export GLB/FBX."""
import bpy, sys, os, time, math, platform

out = sys.argv[sys.argv.index('--') + 1]
os.makedirs(out, exist_ok=True)
t0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# modèle : singe subdivisé + doigts en métaballes converties, pour tester modificateurs et conversions
bpy.ops.mesh.primitive_monkey_add(size=1.2, location=(0, 0, 0.6))
mk = bpy.context.object
mod = mk.modifiers.new('sub', 'SUBSURF'); mod.levels = 2; mod.render_levels = 3
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.new('Chair'); mat.use_nodes = True
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.42, 0.36, 0.32, 1)
bsdf.inputs['Subsurface Weight'].default_value = 0.35
bsdf.inputs['Subsurface Radius'].default_value = (0.6, 0.25, 0.12)
bsdf.inputs['Subsurface Scale'].default_value = 0.08
bsdf.inputs['Roughness'].default_value = 0.45
noise = mat.node_tree.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 40
bump = mat.node_tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.25
mat.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
mat.node_tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
mk.data.materials.append(mat)

bpy.ops.mesh.primitive_plane_add(size=10)
fl = bpy.context.object
fm = bpy.data.materials.new('Sol'); fm.use_nodes = True
fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.05, 0.05, 0.055, 1)
fl.data.materials.append(fm)

bpy.ops.object.light_add(type='AREA', location=(2.5, -2.5, 3.5)); L = bpy.context.object
L.data.energy = 600; L.data.size = 1.5; L.rotation_euler = (math.radians(50), 0, math.radians(45))
bpy.ops.object.light_add(type='POINT', location=(-1.2, 2.0, 1.4)); R = bpy.context.object
R.data.energy = 150; R.data.color = (0.6, 0.75, 1.0)

bpy.ops.object.camera_add(location=(0, -4.2, 1.6)); cam = bpy.context.object
cam.rotation_euler = (math.radians(80), 0, 0); sc.camera = cam
w = bpy.data.worlds.new('W'); w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.004, 0.005, 0.007, 1)
sc.world = w

sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 96
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 960, 540
sc.view_settings.view_transform = 'AgX'
sc.render.filepath = os.path.join(out, 'rendu.png')
bpy.ops.render.render(write_still=True)
t_render = time.time() - t0

bpy.ops.object.select_all(action='DESELECT'); mk.select_set(True); bpy.context.view_layer.objects.active = mk
bpy.ops.export_scene.gltf(filepath=os.path.join(out, 'test.glb'), use_selection=True, export_apply=True)
bpy.ops.export_scene.fbx(filepath=os.path.join(out, 'test.fbx'), use_selection=True, use_mesh_modifiers=True)

with open(os.path.join(out, 'info.txt'), 'w') as f:
    f.write(f'blender {bpy.app.version_string}\npython {platform.python_version()}\ncpu {os.cpu_count()}\n'
            f'rendu_s {t_render:.1f}\ntotal_s {time.time() - t0:.1f}\n')
print('OK', bpy.app.version_string)
