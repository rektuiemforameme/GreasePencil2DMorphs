import bpy
import gpu
from gpu_extras.batch import batch_for_shader

overlay_handler = None

class OverlayHandler:
    def __init__(self, context):
       self.handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback, (), 'WINDOW', 'POST_VIEW')

    def clean(self):
        if self.handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')

    def draw_callback(self):
        from bpy import context
        overlay = context.area.spaces.active.overlay
        scene = context.scene
        obj = context.object
        if not overlay.show_overlays or obj is None or obj.mode != 'EDIT_GPENCIL':
            return
        
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        if scene.gp2dmorphs_use_mirror_excluded_strokes:
            coords = []
            gp = obj.data


            coords = [(1, 1, 1), (-2, 0, 0), (-2, -1, 3), (0, 1, 1)]
            batch = batch_for_shader(shader, 'LINES', {"pos": coords})
            shader.bind()
            shader.uniform_float("color", (1, 0, 0, scene.gp2dmorphs_mirror_excluded_strokes_opacity))
            batch.draw(shader)
        gpu.state.blend_set('NONE')

def make_draw_class():
    global overlay_handler
    overlay_handler = OverlayHandler(bpy.context)

def unregister():
    global overlay_handler
    if overlay_handler:
        overlay_handler.clean()

