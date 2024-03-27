import bpy
from bpy.types import UIList
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy.app.handlers import persistent
from .props import GP2DMORPHS_EditorProps
from .draw_common import draw_def_array_frame_shortcuts, draw_options_mirror, draw_options_interpolate, draw_options_stroke_order
    
class NODE_UL_string_search(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        node = data
        row = layout.row(align=True)
        row.label(text="",icon='LAYER_ACTIVE' if node.list_index == index else 'LAYER_USED')
        if hasattr(node, 'props') and hasattr(node.props, 'mirror') and node.props.mirror:
            row.prop(item, 'mirror', toggle=True, icon_only=True, icon='MOD_MIRROR')
        if node.bl_idname == 'GP2DMorphsNodeGP2DMorph':
            row.prop_search(item, "name", node.obj.data, "layers", text="",icon='NONE')
        elif node.bl_idname == 'GP2DMorphsNodeBoneMorph':
            row.prop_search(item, "name", node.obj.data, "bones", text="",icon='NONE')

class GP2DMORPHSUIListItemString(bpy.types.PropertyGroup):
    name : StringProperty(name='Name')
    id : IntProperty()
    mirror : BoolProperty(default=True, name='Mirror', description="Mirrors this item in the morph")

class GP2DMORPHSPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Grease Pencil"

    @classmethod
    def poll(cls, context):
        ob = context.object
        return ob and (ob.type == 'GPENCIL' or ob.type == 'ARMATURE')

class GP2DMORPHS_PT_Options(GP2DMORPHSPanel, bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Grease Pencil 2D Morphs"
    bl_idname = "GP2DMORPHS_PT_Options"
        
    def draw(self, context):
        GP2DMORPHS_PT_OptionsSub.update_optionssub_class_vars(context)
        box = self.layout.box()
        if GP2DMORPHS_PT_OptionsSub.use_nodes:
            if GP2DMORPHS_PT_OptionsSub.active_node:
                box.label(text=(GP2DMORPHS_PT_OptionsSub.active_node.label if GP2DMORPHS_PT_OptionsSub.active_node.label != '' else GP2DMORPHS_PT_OptionsSub.active_node.name),icon='NODE')
            else:
                box.label(text="Active Node isn't a Morph",icon='ERROR')
        else:
            box.label(text='Not Using Nodes',icon='CANCEL')

class GP2DMORPHS_PT_OptionsSub(bpy.types.Panel):
    """Subpanel of the main GP2DMORPHS Panel"""
    bl_label = "Sub Panel"
    bl_idname = "GP2DMORPHS_PT_OptionsSub"
    bl_parent_id = "GP2DMORPHS_PT_Options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Grease Pencil"
    bl_options = {'DEFAULT_CLOSED'}
    use_nodes = False
    active_node = None
    GP2DMORPHSVars = None
    obj = None

    @staticmethod
    def update_optionssub_class_vars(context=None):
        if context is None:
            context = bpy.context
        areas  = [area for area in context.window.screen.areas if area.ui_type == 'GP2DMorphsNodeTree' and area.spaces.active.node_tree is not None]
        GP2DMORPHS_PT_OptionsSub.active_node = None
        GP2DMORPHS_PT_OptionsSub.use_nodes = False
        for a in areas:
            if a and (node_tree := a.spaces.active.edit_tree):
                GP2DMORPHS_PT_OptionsSub.use_nodes = True
                if (node_active := node_tree.nodes.active) and (node_active.bl_idname == 'GP2DMorphsNodeGP2DMorph' or node_active.bl_idname == 'GP2DMorphsNodeBoneMorph'):
                    GP2DMORPHS_PT_OptionsSub.active_node = node_active
                    break

        if GP2DMORPHS_PT_OptionsSub.active_node:
            GP2DMORPHS_PT_OptionsSub.GP2DMORPHSVars = GP2DMORPHS_PT_OptionsSub.active_node.props
            GP2DMORPHS_PT_OptionsSub.obj = GP2DMORPHS_PT_OptionsSub.active_node.obj
        else:
            obj_active = context.view_layer.objects.active
            GP2DMORPHS_PT_OptionsSub.GP2DMORPHSVars = obj_active.gp2dmorphs_panel_settings
            GP2DMORPHS_PT_OptionsSub.obj = obj_active

class GP2DMORPHS_PT_OptionsDefinedFrames(GP2DMORPHS_PT_OptionsSub):
    bl_label = "Defined Frames"
    bl_idname = "GP2DMORPHS_PT_OptionsDefinedFrames"

    def draw(self, context):
        layout = self.layout
        #Defined Array Dimensions
        morph_props = GP2DMORPHS_PT_OptionsSub.GP2DMORPHSVars
        layout.prop(morph_props, "def_frame_start", text="Starting Frame")
        row = layout.row(align=True)
        row.prop(morph_props, "def_frames_w", text="Width")
        row.prop(morph_props, "def_frames_h", text="Height")
        total_def_frames = morph_props.def_frames_w*morph_props.def_frames_h
        layout.label(text='Total Defined Frames ' + str(total_def_frames))
        draw_def_array_frame_shortcuts(context, layout, morph_props)

        if GP2DMORPHS_PT_OptionsSub.obj.type == 'GPENCIL':
            if GP2DMORPHS_PT_OptionsSub.active_node:
                n = GP2DMORPHS_PT_OptionsSub.active_node
                op_props = layout.operator("GP2DMORPHS.fill_defined_frames")
                op_props.def_frame_start, op_props.def_frames_w, op_props.def_frames_h = n.props.def_frame_start, n.props.def_frames_w, n.props.def_frames_h
                op_props.gp_obj_name, op_props.layer_name = n.obj.name, n.get_selected_name()
                op_props.props_set = True
            else:
                layout.operator("GP2DMORPHS.fill_defined_frames")

        #Mirror
        draw_options_mirror(context,layout,morph_props)

class GP2DMORPHS_PT_OptionsGeneratedFrames(GP2DMORPHS_PT_OptionsSub):
    bl_label = "Generated Frames"
    bl_idname = "GP2DMORPHS_PT_OptionsGeneratedFrames"

    def draw(self, context):
        layout = self.layout
        morph_props = GP2DMORPHS_PT_OptionsSub.GP2DMORPHSVars
        #Generated Array Dimensions
        total_def_frames = morph_props.def_frames_w*morph_props.def_frames_h
        row = layout.row()
        if morph_props.gen_frame_start < morph_props.def_frame_start+total_def_frames+morph_props.def_frames_h-1:      #If the gen start frame overlaps the defined frames, move it
            row.alert = True
        row.prop(morph_props, "gen_frame_start", text="Starting Frame")
        row = layout.row(align=True)
        row.prop(morph_props, "gen_frames_w", text="Width")
        row.prop(morph_props, "gen_frames_h", text="Height")
        layout.label(text='Total Generated Frames ' + str(morph_props.gen_frames_w*morph_props.gen_frames_h))
        #Interpolation
        draw_options_interpolate(context,layout,morph_props,node_name=GP2DMORPHS_PT_OptionsSub.active_node.name if GP2DMORPHS_PT_OptionsSub.use_nodes and GP2DMORPHS_PT_OptionsSub.active_node else '')
        #Stroke order settings
        draw_options_stroke_order(context,layout,morph_props)

        #Generation buttons
        if GP2DMORPHS_PT_OptionsSub.active_node is None:
            box = layout.box()
            row = box.row(align=True)
            row.prop(morph_props, "generate_frames_or_location", text="Frames", toggle=True)
            #if not GP2DMORPHS_PT_OptionsSub.use_nodes:
            row.prop(morph_props, "generate_control_or_rotation", text="Control", toggle=True)
            row.prop(morph_props, "generate_driver_or_scale", text="Driver", toggle=True)
            row = box.row()
            row.enabled = morph_props.generate_driver_or_scale or morph_props.generate_control_or_rotation or morph_props.generate_frames_or_location
            row.operator("GP2DMORPHS.generate_2d_morphs", text = "Generate")

    @classmethod
    def poll(cls, context):
        if GP2DMORPHS_PT_OptionsSub.active_node:
            return GP2DMORPHS_PT_OptionsSub.active_node.bl_idname == "GP2DMorphsNodeGP2DMorph" and GP2DMORPHS_PT_OptionsSub.active_node.obj
        else:
            ob = context.object
            return ob and ob.type == 'GPENCIL'

class GP2DMORPHS_PT_OptionsGeneratedBoneDrivers(GP2DMORPHS_PT_OptionsSub):
    bl_label = "Bone Transform Morphs"
    bl_idname = "GP2DMORPHS_PT_OptionsGeneratedBoneDrivers"

    def draw(self, context):
        layout = self.layout
        morph_props = GP2DMORPHS_PT_OptionsSub.GP2DMORPHSVars
        #Generation buttons
        box = layout.box()
        col = box.column()
        row = col.row(align=True)
        row.prop(morph_props, "generate_frames_or_location", text="Location", toggle=True)
        row.prop(morph_props, "generate_control_or_rotation", text="Rotation", toggle=True)
        row.prop(morph_props, "generate_driver_or_scale", text="Scale", toggle=True)
        if GP2DMORPHS_PT_OptionsSub.active_node is None:
            options_selected = morph_props.generate_driver_or_scale or morph_props.generate_control_or_rotation or morph_props.generate_frames_or_location
            row = col.row()
            row.enabled = options_selected
            row.operator("GP2DMORPHS.generate_2d_bone_morphs", text = "Create Drivers")
            row = col.row()
            row.enabled = options_selected
            row.operator("GP2DMORPHS.remove_morph_drivers", text = "Remove Drivers")

    @classmethod
    def poll(cls, context):
        if GP2DMORPHS_PT_OptionsSub.active_node:
            return GP2DMORPHS_PT_OptionsSub.active_node.bl_idname == "GP2DMorphsNodeBoneMorph" and GP2DMORPHS_PT_OptionsSub.active_node.obj
        else:
            ob = context.object
            return ob and ob.type == 'ARMATURE'
    
class GP2DMORPHS_PT_OptionsControl(GP2DMORPHS_PT_OptionsSub):
    bl_label = "Control"
    bl_idname = "GP2DMORPHS_PT_OptionsControl"

    def draw(self, context):
        layout = self.layout
        morph_props = GP2DMORPHS_PT_OptionsSub.GP2DMORPHSVars
        col = layout.column()
        col.prop(morph_props, "control_type", text="")
        if morph_props.control_type == 'BONE':
            col.prop(morph_props, "control_armature_x", text="", icon='ARMATURE_DATA')
            if morph_props.control_armature_x is not None:
                col.prop_search(morph_props, "control_bone_name_x", morph_props.control_armature_x.data, "bones", text="")
            col.prop(morph_props, "control_armature_y", text="", icon='ARMATURE_DATA')
            if morph_props.control_armature_y is not None:
                col.prop_search(morph_props, "control_bone_name_y", morph_props.control_armature_y.data, "bones", text="")

    @classmethod
    def poll(cls, context):
        return GP2DMORPHS_PT_OptionsSub.active_node is None
    
class GP2DMORPHS_PT_NodeTreeMorphMenu(bpy.types.Menu):
    bl_label = "Morph"
    bl_idname = "NODEGP2DMORPHS_MT_morph"

    def draw(self, context):
        layout = self.layout
        layout.operator("gp2dmorphs.create_controls_for_morphs", text="Create Location Control(s) for morph(s)", icon='ORIENTATION_VIEW').control_type = 'LOC'
        layout.operator("gp2dmorphs.create_controls_for_morphs", text="Create Rotation Control(s) for morph(s)", icon='DRIVER_ROTATIONAL_DIFFERENCE').control_type = 'ROT'
        layout.operator("gp2dmorphs.convert_defined_range")

    @classmethod
    def poll(cls, context):
        return context.area.ui_type == 'GP2DMorphsNodeTree' and context.space_data.node_tree

@persistent
def draw_node_editor_header_append(self, context):
    if context.area.ui_type == 'GP2DMorphsNodeTree' and context.space_data.node_tree:
        layout = self.layout
        GP2DMORPHSEditorProps = context.space_data.edit_tree.gp2dmorphs_editor_props
        layout.separator(factor=0.5)
        row = layout.row(align=True)
        row.operator("gp2dmorphs.update_nodes", text = "Update Nodes", icon='FILE_REFRESH')
        row.prop(GP2DMORPHSEditorProps,"update_gp_frames",text="",icon='DECORATE_KEYFRAME')
        row.prop(GP2DMORPHSEditorProps, "update_mirrors", text="", icon='MOD_MIRROR')
        row.prop(GP2DMORPHSEditorProps,"update_modifiers",text="",icon='MODIFIER')

        layout.prop(GP2DMORPHSEditorProps,"selected_only",text="",icon='RESTRICT_SELECT_OFF')
        
        row = layout.row(align=True)
        row.prop(GP2DMORPHSEditorProps,"preview_resolution",text="")
        lod_e_item = GP2DMORPHS_EditorProps.bl_rna.properties['level_of_detail'].enum_items[GP2DMORPHSEditorProps.level_of_detail]
        row.operator_menu_enum("gp2dmorphs.set_node_tree_lod","level_of_detail",text=lod_e_item.name,icon=lod_e_item.icon)
        mode_e_item = GP2DMORPHS_EditorProps.bl_rna.properties['mode'].enum_items[GP2DMORPHSEditorProps.mode]
        layout.operator_menu_enum("gp2dmorphs.set_node_tree_mode","mode",text=mode_e_item.name,icon=mode_e_item.icon)

@persistent
def draw_node_editor_node_menu(self, context):
    if context.area.ui_type == 'GP2DMorphsNodeTree' and context.space_data.node_tree:
        layout = self.layout
        layout.menu("NODEGP2DMORPHS_MT_morph")
        layout.operator("gp2dmorphs.flip_node_names", icon='MOD_MIRROR')
        layout.operator("gp2dmorphs.remove_and_clean_up_nodes", icon='PANEL_CLOSE')
        layout.separator()

@persistent
def draw_pose_append(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("gp2dmorphs.remove_morph_properties", icon='PANEL_CLOSE')

_classes = [
    NODE_UL_string_search,
    GP2DMORPHSUIListItemString,
    GP2DMORPHS_PT_Options,
    GP2DMORPHS_PT_OptionsDefinedFrames,
    GP2DMORPHS_PT_OptionsGeneratedFrames,
    GP2DMORPHS_PT_OptionsGeneratedBoneDrivers,
    GP2DMORPHS_PT_OptionsControl,
    GP2DMORPHS_PT_NodeTreeMorphMenu,
]
    
def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.NODE_HT_header.append(draw_node_editor_header_append)
    bpy.types.NODE_MT_node.append(draw_node_editor_node_menu)
    bpy.types.VIEW3D_MT_pose.append(draw_pose_append)

def unregister():
    for cls in _classes:
        bpy.utils.unregister_class(cls)
    bpy.types.NODE_HT_header.remove(draw_node_editor_header_append)  
    bpy.types.NODE_MT_node.remove(draw_node_editor_node_menu)
    bpy.types.VIEW3D_MT_pose.remove(draw_pose_append)          