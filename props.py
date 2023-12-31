import bpy
from bpy.props import IntProperty, FloatProperty, BoolProperty, EnumProperty, StringProperty, PointerProperty

class GP2DMORPHS_OpProps(bpy.types.PropertyGroup):
    #Frame Generation
    def_frame_start: IntProperty(name="def_frame_start", default = 0, description="The starting frame for the user-defined frames")
    def_frames_w: IntProperty(name="def_frames_w", default = 3, description="The width of the '2D array' of user-defined frames",min=1)
    def_frames_h: IntProperty(name="def_frames_h", default = 3, description="The height of the '2D array' of user-defined frames",min=1)
    gen_frame_start: IntProperty(name="gen_frame_start", default = 100, description="The starting frame for the generated frames")
    gen_frames_w: IntProperty(name="gen_frames_w", default = 33, description="The width of the '2D array' of generated frames",min=1)
    gen_frames_h: IntProperty(name="gen_frames_h", default = 33, description="The height of the '2D array' of generated frames",min=1)
    generate_frames_or_location: BoolProperty(name="generate_frames_or_location", default = True, description="Generate interpolated Frames from user-defined frames")
    generate_control_or_rotation: BoolProperty(name="generate_control_or_rotation", default = True, description="Generate Control Objects")
    generate_driver_or_scale: BoolProperty(name="generate_driver_or_scale", default = True, description="Generate Driver from Control to Generated frames")
    #Interpolation
    interpolate: BoolProperty(name="interpolate", default = True, description="Interpolate between defined frames. Without this, the addon will not generate any new frames and just reorganize the defined frames into the positions they would be in when generated.")
    
    interp_type_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['type'].enum_items if ot.identifier != 'CUSTOM']
    interp_type_left : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the left direction")
    interp_type_right : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the right direction")
    interp_type_up : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the up direction")
    interp_type_down : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the down direction")
    interp_easing_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['easing'].enum_items if ot.identifier != 'AUTO']
    interp_easing_left : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the left direction")
    interp_easing_right : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the right direction")
    interp_easing_up : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the up direction")
    interp_easing_down : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the down direction")

    stroke_order_changes: BoolProperty(name="Stroke Order Changes", default = False, description="The order of strokes in some frames can change. Slower, but necessary if the stroke order changes")
    stroke_order_change_offset_factor_horizontal : FloatProperty(name="Stroke Order Change Offset Factor Horizontal", default=0.5, 
                                                                        description="Factor for the distance between two frames that new interpolated stroke orders should change on the horizontal axis",
                                                                        min=0,max=1)
    stroke_order_change_offset_factor_vertical : FloatProperty(name="Stroke Order Change Offset Factor Vertical", default=0.5, 
                                                                        description="Factor for the distance between two frames that new interpolated stroke orders should change on the vertical axis",
                                                                        min=0,max=1)
    #Control
    control_type : EnumProperty(name="Control Type", items = [('OBJECT',"Object",""),('BONE',"Armature Bone","")], default='BONE', description="Type of control to use")
    control_armature_x : PointerProperty(name="Control Armature X", type=bpy.types.Object, poll=lambda self, obj: obj.type == 'ARMATURE', description="The armature to add or find control bones in for the X axis of the morph")
    control_bone_name_x : StringProperty(name="Control Bone X", default='',description="The bone to use as a control for the X axis of the morph")
    control_bone_transform_type_x : StringProperty(name="Control Bone Transform Type X", default='LOC_X',description="The transform component of the control to use for the X axis of the morph")
    control_range_start_x : FloatProperty(name="Control Range Start Y", default=-180, 
                                                                        description="The value that will represent '0' in the control driver. Mostly used for rotation controls",
                                                                        min=-180,max=180)
    control_range_end_x : FloatProperty(name="Control Range End Y", default=180, 
                                                                        description="The value that will represent '1' in the control driver. Mostly used for rotation controls",
                                                                        min=-180,max=180)
    control_range_flip_x : BoolProperty(name="Rotation Range Flip",default=False,description="Rotation Range should go counter-clockwise instead of clockwise")
    control_armature_y : PointerProperty(name="Control Armature Y", type=bpy.types.Object, poll=lambda self, obj: obj.type == 'ARMATURE', description="The armature to add or find control bones in for the Y axis of the morph")
    control_bone_name_y : StringProperty(name="Control Bone Y", default='',description="The bone to use as a control for the Y axis of the morph")
    control_bone_transform_type_y : StringProperty(name="Control Bone Transform Type Y", default='LOC_Z',description="The transform component of the control to use for the Y axis of the morph")
    control_range_start_y : FloatProperty(name="Control Range Start X", default=-180, 
                                                                        description="The value that will represent '0' in the control driver. Mostly used for rotation controls",
                                                                        min=-180,max=180)
    control_range_end_y : FloatProperty(name="Control Range End X", default=180, 
                                                                        description="The value that will represent '1' in the control driver. Mostly used for rotation controls",
                                                                        min=-180,max=180)
    control_range_flip_y : BoolProperty(name="Rotation Range Flip",default=False,description="Rotation Range should go counter-clockwise instead of clockwise")
    use_layer_pass: BoolProperty(name="Use Layer Pass Index", default = False, 
                                           description="If true, Morph Node will use one Time Offset with the layer pass index of the first layer instead of one for each layer in the morph. In order for this to work, all layers in the morph need to have the same Pass Index")

class GP2DMORPHS_EditorProps(bpy.types.PropertyGroup):
    previous_anim_frame : IntProperty()
    preview_resolution: IntProperty(default = 17, description="The maximum width or height of any morph in the tree while in Preview mode",min=1)
    selected_only: BoolProperty(name="Only Update Selected", default = True, description="Only update selected nodes")
    update_gp_frames: BoolProperty(name="Update GPencil Frames", default = True, description="Update GPencil Morph frames when updating")
    update_modifiers: BoolProperty(name="Update Modifiers and Drivers", default = True, description="Update modifiers and drivers when updating")
    mode : EnumProperty(items = [('EDIT', 'Edit', 'Editing Rig', 'MOD_ARMATURE', 0), 
                                ('ANIMATE', 'Animate', 'Animating Rig', 'ARMATURE_DATA',1)], name = "Mode", description = "")
    level_of_detail : EnumProperty(items = [('PREVIEW', 'Preview', 'Lower number of frames for performance while editing', 'MESH_PLANE', 0), 
                                            ('RENDER', 'Render', 'High number of frames for smooth transitions', 'VIEW_ORTHO',1)], default='RENDER', 
                                            name = "Level of Detail", description = "A small number of frames for less lag, or a large number for smoother transitions")

_classes = [
    GP2DMORPHS_OpProps,
    GP2DMORPHS_EditorProps
]
    
def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.gp2dmorphs_panel_settings = PointerProperty(type=GP2DMORPHS_OpProps)
    

def unregister():
    for cls in _classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.gp2dmorphs_panel_settings
    