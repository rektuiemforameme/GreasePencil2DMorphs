import bpy
from . import ops, ui, props

bl_info = {
    "name": "Grease Pencil 2D Morph Generator",
    "author": "Matt Thompson",
    "version": (1, 0),
    "blender": (3, 5, 1),
    "location": "View3D > N sidebar",
    "description": "Generates 2D Morph frames from given frames.",
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