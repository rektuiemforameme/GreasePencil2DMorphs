import bpy
from bpy.props import IntProperty, BoolProperty

class GP2DMORPHS_Panel_Settings(bpy.types.PropertyGroup):
    def_frame_start: IntProperty(name="def_frame_start", default = 0, description="The starting frame for the user-defined frames")
    def_frames_w: IntProperty(name="def_frames_w", default = 3, description="The width of the '2D array' of user-defined frames",min=1)
    def_frames_h: IntProperty(name="def_frames_h", default = 3, description="The height of the '2D array' of user-defined frames",min=1)
    gen_frame_start: IntProperty(name="gen_frame_start", default = 100, description="The starting frame for the generated frames")
    gen_frames_w: IntProperty(name="gen_frames_w", default = 21, description="The width of the '2D array' of generated frames",min=1)
    gen_frames_h: IntProperty(name="gen_frames_h", default = 21, description="The height of the '2D array' of generated frames",min=1)
    generate_frames: BoolProperty(name="generate_frames", default = True, description="Generate interpolated Frames from user-defined frames")
    generate_control: BoolProperty(name="generate_control", default = True, description="Generate Control Objects")
    generate_driver: BoolProperty(name="generate_driver", default = True, description="Generate Driver from Control to Generated frames")

    interpolate: BoolProperty(name="interpolate", default = True, description="Interpolate between defined frames. Without this, the addon will not generate any new frames and just reorganize the defined frames into the positions they would be in when generated.")
    
    interp_type_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['type'].enum_items if ot.identifier != 'CUSTOM']
    interp_type_left : bpy.props.EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the left direction")
    interp_type_right : bpy.props.EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the right direction")
    interp_type_up : bpy.props.EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the up direction")
    interp_type_down : bpy.props.EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the down direction")
    interp_easing_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['easing'].enum_items if ot.identifier != 'AUTO']
    interp_easing_left : bpy.props.EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the left direction")
    interp_easing_right : bpy.props.EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the right direction")
    interp_easing_up : bpy.props.EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the up direction")
    interp_easing_down : bpy.props.EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the down direction")

    stroke_order_changes: BoolProperty(name="Stroke Order Changes", default = False, description="The order of strokes in some frames can change. Slower, but necessary if the stroke order changes")
    stroke_order_change_offset_factor_horizontal : bpy.props.FloatProperty(name="Stroke Order Change Offset Factor Horizontal", default=0.5, 
                                                                        description="Factor for the distance between two frames that new interpolated stroke orders should change on the horizontal axis",
                                                                        min=0,max=1)
    stroke_order_change_offset_factor_vertical : bpy.props.FloatProperty(name="Stroke Order Change Offset Factor Vertical", default=0.5, 
                                                                        description="Factor for the distance between two frames that new interpolated stroke orders should change on the vertical axis",
                                                                        min=0,max=1)
    
    control_type : bpy.props.EnumProperty(name="Control Type", items = [('OBJECT',"Object",""),('BONE',"Armature Bone","")], default='BONE', description="Type of control to use")
    control_armature : bpy.props.PointerProperty(name="Control Armature", type=bpy.types.Object, poll=lambda self, obj: obj.type == 'ARMATURE', description="The armature to add or find control bones in")

_classes = [
    GP2DMORPHS_Panel_Settings
]
    
def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gp2dmorphs_panel_settings = bpy.props.PointerProperty(
        type=GP2DMORPHS_Panel_Settings
    )

def unregister():
    for cls in _classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gp2dmorphs_panel_settings
    