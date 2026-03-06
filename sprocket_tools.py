# __init__.py
import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, PointerProperty, EnumProperty, FloatProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel, AddonPreferences
import json
import platform
from pathlib import Path
import mathutils
import bmesh
from mathutils import Vector

def get_default_sprocket_path():
    system = platform.system()
    home = Path.home()

    if system == "Windows":
        return home / "Documents" / "My Games" / "Sprocket"
    else:
        return home / ".steam" / "steam" / "steamapps" / "compatdata" / "1674170" / "pfx" / "drive_c" / "users" / "steamuser" / "My Documents" / "My Games" / "Sprocket"

class SprocketPreferences(AddonPreferences):
    bl_idname = __package__

    sprocket_path: StringProperty(
        name="Sprocket Data Path",
        subtype='DIR_PATH',
        default=str(get_default_sprocket_path())
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "sprocket_path")

def get_sprocket_path(context):
    prefs = context.preferences.addons[__package__].preferences
    if prefs.sprocket_path:
        return Path(prefs.sprocket_path)
    return Path()

def get_factions(context):
    path = get_sprocket_path(context) / "Factions"
    if not path.exists():
        return []
    return [d.name for d in path.iterdir() if d.is_dir()]

class SprocketBlueprintItem(PropertyGroup):
    name: StringProperty(name="Name")
    path: StringProperty(name="Path")

class SprocketFactionItem(PropertyGroup):
    name: StringProperty(name="Name")

class SprocketSceneProps(PropertyGroup):
    faction: EnumProperty(
        name="Faction",
        items=lambda self, context: [(f, f, "") for f in get_factions(context)] if get_factions(context) else [("NONE", "No Factions Found", "")]
    )

    blueprints: CollectionProperty(type=SprocketBlueprintItem)
    blueprint_index: IntProperty(name="Blueprint Index")

    export_name: StringProperty(name="Export Name", default="Compartment")
    export_faction: EnumProperty(
        name="Export Faction",
        items=lambda self, context: [(f, f, "") for f in get_factions(context)] if get_factions(context) else [("NONE", "No Factions Found", "")]
    )

    thickness_default: FloatProperty(name="Default Thickness", default=1.0, min=0.0, max=65535.0)

class SPROCKET_UL_blueprint_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        layout.label(text=item.name)

class SPROCKET_OT_load_faction_blueprints(Operator):
    bl_idname = "sprocket.load_faction_blueprints"
    bl_label = "Load Faction Blueprints"

    def execute(self, context):
        props = context.scene.sprocket_props

        if props.faction == "NONE":
            return {'CANCELLED'}

        props.blueprints.clear()

        faction_path = get_sprocket_path(context) / "Factions" / props.faction / "Blueprints" / "Plate Structures"
        if not faction_path.exists():
            faction_path = get_sprocket_path(context) / "Factions" / props.faction / "Blueprints" / "Vehicles"

        if faction_path.exists():
            for bp in faction_path.glob("*.blueprint"):
                item = props.blueprints.add()
                item.name = bp.stem
                item.path = str(bp)

        return {'FINISHED'}

class SPROCKET_OT_import_blueprint(Operator):
    bl_idname = "sprocket.import_blueprint"
    bl_label = "Import Blueprint"

    filepath: StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        props = context.scene.sprocket_props

        if props.blueprint_index >= 0 and props.blueprint_index < len(props.blueprints):
            bp = props.blueprints[props.blueprint_index]
            self.filepath = bp.path
        else:
            self.report({'ERROR'}, "No blueprint selected")
            return {'CANCELLED'}

        if not self.filepath or not Path(self.filepath).exists():
            self.report({'ERROR'}, "Blueprint not found")
            return {'CANCELLED'}

        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)

            import_mesh(context, data, Path(self.filepath).stem)
            self.report({'INFO'}, f"Imported {Path(self.filepath).stem}")
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}

def import_mesh(context, data, name):
    mesh_data = parse_mesh_data(data)

    bm = bmesh.new()

    raw_verts = []
    positions = mesh_data['mesh']['vertices']
    for i in range(0, len(positions), 3):
        x, y, z = -positions[i], positions[i+1], positions[i+2]
        co = mathutils.Vector((x, z, y))
        raw_verts.append(co)

    vert_remap = {}
    unique_verts = []
    for i, co in enumerate(raw_verts):
        key = (round(co.x, 6), round(co.y, 6), round(co.z, 6))
        if key in vert_remap:
            vert_remap[i] = vert_remap[key]
        else:
            vert_remap[i] = len(unique_verts)
            unique_verts.append(co)

    verts = []
    for co in unique_verts:
        verts.append(bm.verts.new(co))

    bm.verts.ensure_lookup_table()

    thickness_layer = bm.faces.layers.float.new("sprocket_thickness")
    mode_layer = bm.faces.layers.int.new("sprocket_thicken_mode")

    faces_data = mesh_data['mesh']['faces']
    for face_data in faces_data:
        face_verts = []
        for vi in face_data['v']:
            remapped = vert_remap.get(vi, vi)
            if 0 <= remapped < len(verts):
                face_verts.append(verts[remapped])

        if len(face_verts) >= 3:
            try:
                face_verts.reverse()
                face = bm.faces.new(face_verts)

                thicknesses = face_data.get('t', [1])
                if thicknesses:
                    face[thickness_layer] = thicknesses[0] / 100.0

                tm = face_data.get('tm', 16843009)
                face[mode_layer] = tm
            except:
                pass

    bm.normal_update()

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    context.collection.objects.link(obj)

    return obj

def parse_mesh_data(data):
    if 'v' in data and isinstance(data['v'], str):
        return {
            'version': data.get('v', '0.2'),
            'name': data.get('name', ''),
            'smoothAngle': data.get('smoothAngle', 0),
            'gridSize': data.get('gridSize', 1),
            'format': data.get('format', 'freeform'),
            'mesh': {
                'majorVersion': data.get('mesh', {}).get('majorVersion', 0),
                'minorVersion': data.get('mesh', {}).get('minorVersion', 3),
                'vertices': data.get('mesh', {}).get('vertices', []),
                'edges': data.get('mesh', {}).get('edges', []),
                'edgeFlags': data.get('mesh', {}).get('edgeFlags', []),
                'faces': data.get('mesh', {}).get('faces', [])
            },
            'rivets': data.get('rivets', {'profiles': [], 'nodes': []})
        }
    else:
        return {
            'version': '0.2',
            'name': '',
            'smoothAngle': 0,
            'gridSize': 1,
            'format': 'freeform',
            'mesh': {
                'majorVersion': 0,
                'minorVersion': 3,
                'vertices': [],
                'edges': [],
                'edgeFlags': [],
                'faces': []
            },
            'rivets': {'profiles': [], 'nodes': []}
        }

class SPROCKET_OT_export_compartment(Operator):
    bl_idname = "sprocket.export_compartment"
    bl_label = "Export Compartment"

    def execute(self, context):
        props = context.scene.sprocket_props
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh selected")
            return {'CANCELLED'}

        if props.export_faction == "NONE":
            self.report({'ERROR'}, "No faction selected")
            return {'CANCELLED'}

        name = props.export_name
        if not name:
            name = obj.name

        try:
            mesh_data = export_mesh(obj, props)

            faction_path = get_sprocket_path(context) / "Factions" / props.export_faction / "Blueprints" / "Plate Structures"
            faction_path.mkdir(parents=True, exist_ok=True)

            filepath = faction_path / f"{name}.blueprint"

            with open(filepath, 'w') as f:
                json.dump(mesh_data, f, indent=2)

            self.report({'INFO'}, f"Exported to {filepath}")
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}

def export_mesh(obj, props):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()

    position_to_index = {}
    vertices = []
    face_remaps = []

    for poly in mesh.polygons:
        if len(poly.vertices) > 4:
            continue

        remapped = []
        for vi in poly.vertices:
            v = mesh.vertices[vi]
            key = (round(-v.co.x, 6), round(v.co.z, 6), round(v.co.y, 6))
            if key not in position_to_index:
                position_to_index[key] = len(vertices) // 3
                vertices.extend([key[0], key[1], key[2]])
            remapped.append(position_to_index[key])
        face_remaps.append(remapped)

    eval_obj.to_mesh_clear()

    faces = []
    edge_map = {}
    face_idx = 0

    for remapped in face_remaps:
        face_data = {'v': remapped, 't': [], 'tm': 16843009, 'te': 0}
        t = int(props.thickness_default)
        face_data['t'] = [t] * len(remapped)
        faces.append(face_data)

        for i in range(len(remapped)):
            va = remapped[i]
            vb = remapped[(i + 1) % len(remapped)]
            key = tuple(sorted([va, vb]))
            if key not in edge_map:
                edge_map[key] = []
            edge_map[key].append((face_idx, i))

        face_idx += 1

    edges = []
    edge_flags = []

    for (va, vb), _ in edge_map.items():
        edges.extend([vb, va])
        edge_flags.append(0)

    mesh_data = {
        'v': '0.2',
        'name': obj.name,
        'smoothAngle': 0,
        'gridSize': 1,
        'format': 'freeform',
        'mesh': {
            'majorVersion': 0,
            'minorVersion': 3,
            'vertices': vertices,
            'edges': edges,
            'edgeFlags': edge_flags,
            'faces': faces
        },
        'rivets': {
            'profiles': [{'model': 0, 'spacing': 0.1, 'diameter': 0.05, 'height': 0.025, 'padding': 0.4}],
            'nodes': []
        }
    }

    return mesh_data

class SPROCKET_PT_import_panel(Panel):
    bl_label = "Sprocket Import"
    bl_idname = "SPROCKET_PT_import_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sprocket'

    def draw(self, context):
        layout = self.layout
        props = context.scene.sprocket_props

        row = layout.row(align=True)
        row.prop(props, "faction")
        row.operator("sprocket.load_faction_blueprints", text="", icon='FILE_REFRESH')

        layout.operator("sprocket.load_faction_blueprints")

        layout.template_list("SPROCKET_UL_blueprint_list", "", props, "blueprints", props, "blueprint_index")

        layout.operator("sprocket.import_blueprint")

class SPROCKET_PT_export_panel(Panel):
    bl_label = "Sprocket Export"
    bl_idname = "SPROCKET_PT_export_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sprocket'

    def draw(self, context):
        layout = self.layout
        props = context.scene.sprocket_props

        layout.prop(props, "export_faction")
        layout.prop(props, "export_name")
        layout.prop(props, "thickness_default")

        layout.operator("sprocket.export_compartment")

classes = [
    SprocketPreferences,
    SprocketBlueprintItem,
    SprocketFactionItem,
    SprocketSceneProps,
    SPROCKET_UL_blueprint_list,
    SPROCKET_OT_load_faction_blueprints,
    SPROCKET_OT_import_blueprint,
    SPROCKET_OT_export_compartment,
    SPROCKET_PT_import_panel,
    SPROCKET_PT_export_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.sprocket_props = PointerProperty(type=SprocketSceneProps)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.sprocket_props

if __name__ == "__main__":
    register()
