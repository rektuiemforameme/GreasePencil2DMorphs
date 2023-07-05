import bpy

class GP2DMORPHSPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Grease Pencil"

    @classmethod
    def poll(cls, context):
        ob = context.object
        return ob and ob.type == 'GPENCIL'

class GP2DMORPHS_PT_Options(GP2DMORPHSPanel, bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Grease Pencil 2D Morphs"
    bl_idname = "GP2DMORPHS_PT_Options"
        
    def draw(self, context):
        #Nothing
        return
        
class GP2DMORPHS_PT_OptionsDefinedFrames(bpy.types.Panel):
    """Subpanel of the main GP2DMORPHS Panel"""
    bl_label = "Defined Frames"
    bl_idname = "GP2DMORPHS_PT_OptionsDefinedFrames"
    bl_parent_id = "GP2DMORPHS_PT_Options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Grease Pencil"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        layout = self.layout
        #Defined Array Dimensions
        #box = layout.box()
        col = layout.column()
        col.prop(GP2DMORPHSVars, "def_frame_start", text="Starting Frame")
        col.label(text='Array Size')
        row = col.row()
        row.prop(GP2DMORPHSVars, "def_frames_w", text="Width")
        row.prop(GP2DMORPHSVars, "def_frames_h", text="Height")
        total_def_frames = GP2DMORPHSVars.def_frames_w*GP2DMORPHSVars.def_frames_h
        col.label(text='Total Defined Frames ' + str(total_def_frames))
        box = col.box()
        #Defined Array Frame shortcuts
        for y in range(GP2DMORPHSVars.def_frames_h-1,-1,-1):
            row = box.row()
            for x in range(GP2DMORPHSVars.def_frames_w):
                f = GP2DMORPHSVars.def_frame_start + y*(GP2DMORPHSVars.def_frames_w+1) + x   #The frame that this button and position in the defined 'array' represents and links to
                props = row.operator("GP2DMORPHS.set_frame_by_defined_pos", text = str(f), depress = f==context.scene.frame_current)
                props.pos_x, props.pos_y = x, y
        col.operator("GP2DMORPHS.fill_defined_frames")

class GP2DMORPHS_PT_OptionsGeneratedFrames(bpy.types.Panel):
    """Subpanel of the main GP2DMORPHS Panel"""
    bl_label = "Generated Frames"
    bl_idname = "GP2DMORPHS_PT_OptionsGeneratedFrames"
    bl_parent_id = "GP2DMORPHS_PT_Options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Grease Pencil"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        layout = self.layout
        #Generated Array Dimensions
        col = layout.column()
        total_def_frames = GP2DMORPHSVars.def_frames_w*GP2DMORPHSVars.def_frames_h
        row = col.row()
        if GP2DMORPHSVars.gen_frame_start < GP2DMORPHSVars.def_frame_start+total_def_frames+GP2DMORPHSVars.def_frames_h-1:      #If the gen start frame overlaps the defined frames, move it
            row.alert = True
        row.prop(GP2DMORPHSVars, "gen_frame_start", text="Starting Frame")
        col.label(text='Array Size')
        row = col.row()
        row.prop(GP2DMORPHSVars, "gen_frames_w", text="Width")
        row.prop(GP2DMORPHSVars, "gen_frames_h", text="Height")
        col.label(text='Total Generated Frames ' + str(GP2DMORPHSVars.gen_frames_w*GP2DMORPHSVars.gen_frames_h))
        #Interpolation
        box = layout.box()
        col = box.column()
        col.prop(GP2DMORPHSVars, "interpolate", text="Interpolate")

        if GP2DMORPHSVars.interpolate:
            row = col.row()
            row.label(icon='IPO_EASE_IN_OUT')
            row.operator_menu_enum("GP2DMORPHS.set_all_interp_types","type", text="Set All")
            if GP2DMORPHSVars.interp_type_left != 'LINEAR' or GP2DMORPHSVars.interp_type_right != 'LINEAR' or GP2DMORPHSVars.interp_type_up != 'LINEAR' or GP2DMORPHSVars.interp_type_down != 'LINEAR':
                row.operator_menu_enum("GP2DMORPHS.set_all_interp_easings","easing", text="Set All")
            
            if GP2DMORPHSVars.gen_frames_h > 1:
                row = col.row()
                row.label(text="",icon='TRIA_UP')
                row.prop(GP2DMORPHSVars, "interp_type_up", text="")
                if GP2DMORPHSVars.interp_type_up == 'CUSTOM':
                    row.label(text=":(",icon='ERROR')
                elif GP2DMORPHSVars.interp_type_up != 'LINEAR':
                    row.prop(GP2DMORPHSVars, "interp_easing_up", text="")

                if GP2DMORPHSVars.def_frames_h > 2:
                    row = col.row()
                    row.label(text="",icon='TRIA_DOWN')
                    row.prop(GP2DMORPHSVars, "interp_type_down", text="")
                    if GP2DMORPHSVars.interp_type_down == 'CUSTOM':
                        row.label(text=":(",icon='ERROR')
                    elif GP2DMORPHSVars.interp_type_down != 'LINEAR':
                        row.prop(GP2DMORPHSVars, "interp_easing_down", text="")
            if GP2DMORPHSVars.gen_frames_w > 1:
                if GP2DMORPHSVars.def_frames_w > 2:
                    row = col.row()
                    row.label(text="",icon='TRIA_LEFT')
                    row.prop(GP2DMORPHSVars, "interp_type_left", text="")
                    if GP2DMORPHSVars.interp_type_left == 'CUSTOM':
                        row.label(text=":(",icon='ERROR')
                    elif GP2DMORPHSVars.interp_type_left != 'LINEAR':
                        row.prop(GP2DMORPHSVars, "interp_easing_left", text="")

                row = col.row()
                row.label(text="",icon='TRIA_RIGHT')
                row.prop(GP2DMORPHSVars, "interp_type_right", text="")
                if GP2DMORPHSVars.interp_type_right == 'CUSTOM':
                    row.label(text=":(",icon='ERROR')
                elif GP2DMORPHSVars.interp_type_right != 'LINEAR':
                    row.prop(GP2DMORPHSVars, "interp_easing_right", text="")

        #Stroke order settings
        box = layout.box()
        col = box.column()
        col.prop(GP2DMORPHSVars, "stroke_order_changes", text="Stroke Order Changes")
        if GP2DMORPHSVars.stroke_order_changes:
            col.label(text="Order change offset factor")
            row = col.row()
            h,v = GP2DMORPHSVars.def_frames_w > 1, GP2DMORPHSVars.def_frames_h > 1
            if h:
                row.prop(GP2DMORPHSVars, "stroke_order_change_offset_factor_horizontal", text="Horizontal" if v else "")
            if v:
                row.prop(GP2DMORPHSVars, "stroke_order_change_offset_factor_vertical", text="Vertical" if h else "")

        #Generation buttons
        box = layout.box()
        col = box.column()
        row = col.row()
        row.prop(GP2DMORPHSVars, "generate_frames", text="Frames")
        row.prop(GP2DMORPHSVars, "generate_control", text="Control")
        row.prop(GP2DMORPHSVars, "generate_driver", text="Driver")
        col.operator("GP2DMORPHS.generate_2d_morphs", text = "Generate")

class GP2DMORPHS_PT_OptionsControl(bpy.types.Panel):
    """Subpanel of the main GP2DMORPHS Panel"""
    bl_label = "Control"
    bl_idname = "GP2DMORPHS_PT_OptionsControl"
    bl_parent_id = "GP2DMORPHS_PT_Options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Grease Pencil"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        layout = self.layout
        col = layout.column()
        col.prop(GP2DMORPHSVars, "control_type", text="Type")
        if GP2DMORPHSVars.control_type == 'BONE':
            col.prop(GP2DMORPHSVars, "control_armature", text="Armature", icon='ARMATURE_DATA')
        

_classes = [
    GP2DMORPHS_PT_Options,
    GP2DMORPHS_PT_OptionsDefinedFrames,
    GP2DMORPHS_PT_OptionsGeneratedFrames,
    GP2DMORPHS_PT_OptionsControl
]
    
def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in _classes:
        bpy.utils.unregister_class(cls)                       