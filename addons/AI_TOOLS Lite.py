bl_info = {
    "name": "AI_TOOLS Lite",
    "author": "AI3DCNC",
    "version": (0, 2, 2),
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar > AI_TOOLS Lite",
    "description": "Lite UI for JSON export/import (meters, 3dp) and a DXF QA stub.",
    "category": "System",
}

import bpy
import json
import os
import sys
import subprocess
from typing import Optional

# -------------------------------
# Paths & helpers
# -------------------------------
_DEF_EXPORT = os.path.join(os.path.expanduser('~'), 'BLENDER_EXPORT')


def _mod_id() -> str:
    return __package__ or __name__


def _get_prefs(ctx) -> Optional[bpy.types.AddonPreferences]:
    ad = ctx.preferences.addons.get(_mod_id())
    return getattr(ad, 'preferences', None)


def _open_dir(path: str):
    os.makedirs(path, exist_ok=True)
    try:
        if os.name == 'nt':
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
    except Exception as e:
        print(f"[SUMMARY] open_dir failed: {e}")


# -------------------------------
# Preferences
# -------------------------------
class AITLITE_Prefs(bpy.types.AddonPreferences):
    bl_idname = _mod_id()

    export_dir: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Export Dir",
        subtype='DIR_PATH',
        default=_DEF_EXPORT,
    )
    import_dir: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Import Dir",
        subtype='DIR_PATH',
        default=_DEF_EXPORT,
    )

    def draw(self, ctx):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Defaults (meters, 3dp)")
        col.prop(self, 'export_dir')
        col.prop(self, 'import_dir')
        row = col.row(align=True)
        row.operator('aitlite.open_export_dir', text='Open Export Dir', icon='FILE_FOLDER')
        row.operator('aitlite.open_import_dir', text='Open Import Dir', icon='FILE_FOLDER')


# -------------------------------
# Panel
# -------------------------------
class AITLITE_PT(bpy.types.Panel):
    bl_idname = "AITLITE_PT_main"
    bl_label = "AI_TOOLS Lite"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AI_TOOLS Lite"

    @classmethod
    def poll(cls, ctx):
        return True

    def draw(self, ctx):
        layout = self.layout
        prefs = _get_prefs(ctx)
        col = layout.column(align=True)

        col.operator('aitlite.export_min_sample', icon='EXPORT')
        col.operator('aitlite.import_json', icon='IMPORT')
        col.operator('aitlite.write_dxf_stub', icon='FILE')  # safe icon name

        col.separator()
        if prefs:
            col.prop(prefs, 'export_dir')
            col.prop(prefs, 'import_dir')
            row = col.row(align=True)
            row.operator('aitlite.open_export_dir', text='Open Export Dir', icon='FILE_FOLDER')
            row.operator('aitlite.open_import_dir', text='Open Import Dir', icon='FILE_FOLDER')
        else:
            col.label(text="Set paths in Preferences > Add-ons > AI_TOOLS Lite")


# -------------------------------
# Operators
# -------------------------------
class AITLITE_OT_export_min(bpy.types.Operator):
    bl_idname = 'aitlite.export_min_sample'
    bl_label = 'Export min_scene_export.json'

    def invoke(self, ctx, ev):
        return self.execute(ctx)

    def execute(self, ctx):
        prefs = _get_prefs(ctx)
        base = prefs.export_dir if prefs else _DEF_EXPORT
        try:
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, 'min_scene_export.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(_MIN_SCENE, f, indent=2)
            self.report({'INFO'}, f'Wrote {path}')
            print(f"[SUMMARY] min_scene_export -> {path}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'WARNING'}, f'Export failed: {e}')
            return {'CANCELLED'}


class AITLITE_OT_import(bpy.types.Operator):
    bl_idname = 'aitlite.import_json'
    bl_label = 'Import JSON (noop lite)'

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')  # type: ignore[valid-type]
    filter_glob: bpy.props.StringProperty(default='*.json', options={'HIDDEN'})  # type: ignore[valid-type]

    def invoke(self, ctx, ev):
        prefs = _get_prefs(ctx)
        base = prefs.import_dir if prefs else _DEF_EXPORT
        os.makedirs(base, exist_ok=True)
        self.filepath = os.path.join(base, 'min_scene_export.json')
        ctx.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, ctx):
        try:
            if not os.path.isfile(self.filepath):
                self.report({'WARNING'}, 'Invalid file path')
                return {'CANCELLED'}
            with open(self.filepath, 'r', encoding='utf-8') as f:
                json.load(f)
            print(f"[SUMMARY] (lite) parsed JSON OK: {os.path.basename(self.filepath)}")
        except Exception as e:
            self.report({'WARNING'}, f"Parse failed: {e}")
        return {'FINISHED'}


class AITLITE_OT_dxf(bpy.types.Operator):
    bl_idname = 'aitlite.write_dxf_stub'
    bl_label = 'Write QA DXF (stub)'

    def execute(self, ctx):
        prefs = _get_prefs(ctx)
        base = prefs.export_dir if prefs else _DEF_EXPORT
        path = os.path.join(base, 'qa_panel.dxf')
        _write_min_dxf(path)
        self.report({'INFO'}, f'Wrote {path}')
        print(f"[SUMMARY] dxf_stub -> {path}")
        return {'FINISHED'}


class AITLITE_OT_open_export(bpy.types.Operator):
    bl_idname = 'aitlite.open_export_dir'
    bl_label = 'Open Export Dir'

    def execute(self, ctx):
        prefs = _get_prefs(ctx)
        base = prefs.export_dir if prefs else _DEF_EXPORT
        _open_dir(base)
        return {'FINISHED'}


class AITLITE_OT_open_import(bpy.types.Operator):
    bl_idname = 'aitlite.open_import_dir'
    bl_label = 'Open Import Dir'

    def execute(self, ctx):
        prefs = _get_prefs(ctx)
        base = prefs.import_dir if prefs else _DEF_EXPORT
        _open_dir(base)
        return {'FINISHED'}


# -------------------------------
# Minimal scene JSON (meters, 3dp)
# -------------------------------
_MIN_SCENE_JSON = r'''
{
  "scene_view": {"cameras": [{"name": "Cam", "transform": {}}], "lights": [{"name": "Key", "type": "AREA", "energy": 800.0, "transform": {}}], "meta": {"units": "m"}},
  "materials": {"materials": [{"name": "Mat_A"}, {"name": "Mat_B"}], "meta": {"units": "m"}},
  "mesh": {"meshes": [{"object_name": "Cube", "collection_path": ["Root"], "transform": {}, "world_matrix": [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1], "dimensions": {"local": [], "world": []}, "vertices": [], "materials": ["Mat_A"], "triangles": []}], "meta": {"units": "m"}},
  "collections": {"collections": [{"name": "Root", "path": ["Root"], "children": [], "items": {}, "flags": {}}], "meta": {"units": "m"}},
  "geometry_nodes": {"groups": [], "overrides": [], "meta": {"units": "m"}},
  "bool_ops": {"targets": [], "meta": {"units": "m"}}
}
'''
_MIN_SCENE = json.loads(_MIN_SCENE_JSON)


# -------------------------------
# DXF stub (ASCII, minimal entities)
# -------------------------------

def _write_min_dxf(path: str):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='ascii') as f:
        f.write("0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nTABLES\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n")
        # panel outer (unit square) on CUT_OUTER
        f.write("0\nLWPOLYLINE\n8\nCUT_OUTER\n90\n4\n70\n1\n10\n0\n20\n0\n10\n1\n20\n0\n10\n1\n20\n1\n10\n0\n20\n1\n")
        # one drill (circle)
        f.write("0\nCIRCLE\n8\nDRILL\n10\n0.100\n20\n0.100\n40\n0.005\n")
        # one slot (polyline)
        f.write("0\nLWPOLYLINE\n8\nSLOT\n90\n2\n70\n0\n10\n0.200\n20\n0.200\n10\n0.250\n20\n0.200\n")
        f.write("0\nENDSEC\n0\nEOF\n")


# -------------------------------
# Registration
# -------------------------------
_classes = (
    AITLITE_Prefs,
    AITLITE_PT,
    AITLITE_OT_export_min,
    AITLITE_OT_import,
    AITLITE_OT_dxf,
    AITLITE_OT_open_export,
    AITLITE_OT_open_import,
)


def register():
    for c in _classes:
        try:
            bpy.utils.register_class(c)
        except Exception as e:
            print(f"[SUMMARY] register failed: {c.__name__}: {e}")
    print("[SUMMARY] AI_TOOLS Lite registered")


def unregister():
    for c in reversed(_classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception as e:
            print(f"[SUMMARY] unregister failed: {c.__name__}: {e}")
    print("[SUMMARY] AI_TOOLS Lite unregistered")
