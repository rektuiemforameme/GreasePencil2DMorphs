import bpy
from . import ops, ui, props

bl_info = {
    "name": "Grease Pencil 2D Morphs",
    "author": "Matt Thompson",
    "version": (1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > N sidebar",
    "description": "Generates 2D Morph frames from user defined frames and manipulate them with controls and drivers.",
    "warning": "",
    "doc_url": "",
    "category": "Grease Pencil",
}
    
def register():
    props.register()
    ops.register()
    ui.register()

def unregister():
    props.unregister()
    ops.unregister()
    ui.unregister()

if __name__ == "__main__":
    register()