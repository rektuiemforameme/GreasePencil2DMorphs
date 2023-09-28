import bpy
import math
from mathutils import Vector, Matrix
from bpy.props import IntProperty, EnumProperty, StringProperty
from ..utils import get_main_morph_node, get_tree
from ..utils_ops import run_ops_without_view_layer_update
from .ops import def_array_pos_to_def_frame_pos
from ..nodes.Input.node_ControlBase import GP2DMorphsNodeControlBase

class GP2DMORPHS_OT_update_nodes(bpy.types.Operator):
    bl_idname = "gp2dmorphs.update_nodes"    
    bl_label = "Update Nodes"
    bl_description = "Updates Nodes in Editor. Can take awhile. Patience is a virtue"
    bl_options = {'UNDO'}

    mode : EnumProperty(items = [('DYNAMIC', 'Dynamic', 'All or Selected', 'MOD_ARMATURE', 0), 
                                           ('GPFRAMES', 'GP Frames', 'GPencil Frames', 'ARMATURE_DATA',1),
                                           ('CONTROLS', 'Controls', 'Controls', 'ARMATURE_DATA',2),
                                           ('ALL', 'All Nodes', 'Update all Nodes', 'MOD_ARMATURE', 3),], name = "Mode", description = "")
    
    def execute(self, context):
        run_ops_without_view_layer_update(update_nodes,self,context,self.mode)
        context.view_layer.update()
        return {'FINISHED'}
    
class GP2DMORPHS_OT_remove_and_clean_up_nodes(bpy.types.Operator):
    bl_idname = "gp2dmorphs.remove_and_clean_up_nodes"    
    bl_label = "Delete and Clean Up"
    bl_description = "Removes all selected nodes, and cleans up after them. For controls, this means removing the bones associated with them"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        if context.area.ui_type == 'GP2DMorphsNodeTree' and (node_tree := context.space_data.edit_tree):
            original_active_obj = context.view_layer.objects.active
            original_mode = original_active_obj.mode             #Grab the current mode so we can switch back after
            for i in range(len(node_tree.nodes)-1,-1,-1):
                node = node_tree.nodes[i]
                if node.select:
                    node.clean_up()
                    node_tree.nodes.remove(node)
            context.view_layer.objects.active = original_active_obj
            bpy.ops.object.mode_set(mode=original_mode, toggle=False)
            context.view_layer.update()
            return {'FINISHED'}
        return {'CANCELLED'}
    
    @classmethod
    def poll(cls, context):
        return context.active_node is not None

class GP2DMORPHS_OT_create_controls_for_morphs(bpy.types.Operator):
    bl_idname = "gp2dmorphs.create_controls_for_morphs"    
    bl_label = "Create control(s) for morph(s)"
    bl_description = "Creates controls for selected morph nodes and attaches them"
    bl_options = {'UNDO'}

    control_type : EnumProperty(items = [('LOC', 'Location', 'Location Control', 'TRANSFORM_ORIGINS', 0), 
                                           ('ROT', 'Rotation', 'Rotation Control', 'DRIVER_ROTATIONAL_DIFFERENCE', 1)], name = "Type", description = "Type of Control to generate for Morphs")
    
    def execute(self, context):
        run_ops_without_view_layer_update(self.run,context)
        context.view_layer.update()
        return {'FINISHED'}


    def run(self,context):
        node_tree = context.space_data.edit_tree
        original_cursor_location = context.scene.cursor.location.copy()
        original_active_obj = context.view_layer.objects.active
        original_mode = original_active_obj.mode             #Grab the current mode so we can switch back after
        if node_tree is None:
            self.report({'ERROR'}, "No Node Tree Found")
            return
        control_armature = None 
        for node in context.selected_nodes:
            if node.bl_idname == 'GP2DMorphsNodeBoneMorph' or node.bl_idname == 'GP2DMorphsNodeGP2DMorph':  #For some reason this isn't working -> issubclass(type(node),GP2DMorphsNodeMorphBase): 
                skts = node.get_connected_xy_sockets()
                if skts[0] is None or skts[1] is None:    #This morph has at least one input without a control attached
                    node.update_props()
                    new_ctrl_nodes = list()
                    match self.control_type:
                        case 'LOC':
                            c = node_tree.nodes.new("GP2DMorphsNodeControlLocation")
                            c.location = node.location - Vector((200,0))
                            if node.props.gen_frames_w > 1 and skts[0] is None:
                                node_tree.links.new(c.outputs['LOC_X'],node.inputs['input_x'])
                            if node.props.gen_frames_h > 1 and skts[1] is None:
                                node_tree.links.new(c.outputs['LOC_Y'],node.inputs['input_y'])
                            new_ctrl_nodes.append(c)
                        case 'ROT':
                            if node.props.gen_frames_w > 1 and skts[0] is None:
                                c = node_tree.nodes.new("GP2DMorphsNodeControlRotation")
                                c.location = node.location - Vector((200,0))
                                node_tree.links.new(c.outputs['ROT_Z'],node.inputs['input_x'])
                                new_ctrl_nodes.append(c)
                            if node.props.gen_frames_h > 1 and skts[1] is None:
                                c = node_tree.nodes.new("GP2DMorphsNodeControlRotation")
                                c.location = node.location - Vector((200,120))
                                node_tree.links.new(c.outputs['ROT_Z'],node.inputs['input_y'])
                                new_ctrl_nodes.append(c)
                    for c in new_ctrl_nodes:
                        if node.label != "":
                            c.label = node.label
                        if c.update_control(context, control_armature):
                            context.scene.cursor.location += Vector((1.3,0,0))
                        if c.obj is not None:
                            control_armature = c.obj
                        #c.update() #Seems like it's going to get updated anyway?

        context.scene.cursor.location = original_cursor_location
        context.view_layer.objects.active = original_active_obj
        bpy.ops.object.mode_set(mode=original_mode, toggle=False)

    @classmethod
    def poll(cls, context):
        return get_main_morph_node(context) is not None

class GP2DMORPHS_OT_set_node_tree_lod(bpy.types.Operator):
    bl_idname = "gp2dmorphs.set_node_tree_lod"    
    bl_label = "Set Node Tree Level of Detail"
    bl_description = "Set Node Tree Level of Detail. Uses the 'Only Update Selected' setting, so if that is enabled then this operator will only change the LoD for selected nodes. Can take a long time going from Preview to Render, because it has to regenerate all morphs at full frame resolution"
    bl_options = {'UNDO'}

    level_of_detail : EnumProperty(items = [('PREVIEW', 'Preview', 'Lower number of frames for performance while editing', 'MESH_PLANE', 0), 
                                                   ('RENDER', 'Render', 'High number of frames for smooth transitions', 'VIEW_ORTHO',1)], 
                                                   name = "Level of Detail", 
                                                   description = "A small number of frames for less lag, or a large number for smoother transitions")
    
    def execute(self, context):
        GP2DMORPHSEditorProps = context.space_data.edit_tree.gp2dmorphs_editor_props
        if GP2DMORPHSEditorProps.level_of_detail != self.level_of_detail or self.level_of_detail == 'PREVIEW':
            GP2DMORPHSEditorProps.level_of_detail = self.level_of_detail
            run_ops_without_view_layer_update(update_nodes,self,context,'GPFRAMES')
            context.view_layer.update()
            #bpy.ops.gp2dmorphs.update_nodes(mode='GPFRAMES')
        return {'FINISHED'}
    
class GP2DMORPHS_OT_set_node_tree_mode(bpy.types.Operator):
    bl_idname = "gp2dmorphs.set_node_tree_mode"    
    bl_label = "Set Node Tree Mode"
    bl_description = "Sets the mode for either editing morph frames, or animating/testing controls"
    bl_options = {'UNDO'}

    mode : EnumProperty(items = [('EDIT', 'Edit', 'Editing Rig', 'MOD_ARMATURE', 0), 
                                           ('ANIMATE', 'Animate', 'Animating Rig', 'ARMATURE_DATA',1)], name = "Mode", description = "")
    
    def execute(self, context):
        node_tree = get_tree(context)
        if node_tree is None:
            self.report({'ERROR'}, "No Node Tree Found")
            return
        GP2DMORPHSEditorProps = node_tree.gp2dmorphs_editor_props
        edit_frame = -2
        change = GP2DMORPHSEditorProps.mode != self.mode    #Changing to a different mode
        if change and self.mode == 'EDIT': #If we're going from animation mode to edit
            GP2DMORPHSEditorProps.previous_anim_frame = context.scene.frame_current
            edit_frame = -1
        GP2DMORPHSEditorProps.mode = self.mode
        for node in node_tree.nodes:
            match node.bl_idname:
                case 'GP2DMorphsNodeGP2DMorph':             #Morph      GPencil
                    node.set_mode(self.mode)
                    if edit_frame == -1:
                        dw, dh = node.props.def_frames_w, node.props.def_frames_h
                        edit_frame = def_array_pos_to_def_frame_pos(math.floor(dw/2),math.floor(dh/2),node.props.def_frame_start,dw)    #The center frame of the morph
                case 'GP2DMorphsNodeBoneMorph':             #Morph      GPencil
                    node.set_mode(self.mode)
                    if edit_frame == -1:
                        dw, dh = node.props.def_frames_w, node.props.def_frames_h
                        edit_frame = def_array_pos_to_def_frame_pos(math.floor(dw/2),math.floor(dh/2),node.props.def_frame_start,dw)    #The center frame of the morph
        if change:  #If the mode is changing, set the frame
            if self.mode == 'ANIMATE':
                context.scene.frame_set(GP2DMORPHSEditorProps.previous_anim_frame)  #Go back to where we were animating before
            elif edit_frame > -1:
                context.scene.frame_set(edit_frame)                                 #Go to the center frame of the first morph node. 
        return {'FINISHED'}

class GP2DMORPHS_OT_set_ctrl_skt_range(bpy.types.Operator):
    bl_idname = "gp2dmorphs.set_ctrl_skt_range"    
    bl_label = "Set Control Socket Range"
    bl_description = "Sets either the Start or End angle for the current Control socket to the current rotation of the control bone"
    bl_options = {'UNDO'}
    node_name : StringProperty()
    socket_name : StringProperty()
    control_armature_name : StringProperty()
    control_bone_name : StringProperty()
    index : IntProperty() #0 = Range Start, 1 = Range End
    def execute(self, context):
        if (node_tree := get_tree(context)) and (node := node_tree.nodes.get(self.node_name)) and issubclass(type(node),GP2DMorphsNodeControlBase):
            skt = node.outputs.get(self.socket_name)
            if skt:
                control_armature = bpy.data.objects.get(self.control_armature_name)
                if control_armature is not None:
                    bone = control_armature.pose.bones.get(self.control_bone_name)
                    if bone is not None:
                        comp_index = 0 if skt.default_value[-1] == 'X' else 1 if skt.default_value[-1] == 'Y' else 2
                        if bone.rotation_mode == 'AXIS_ANGLE':
                            angle, *axis = bone.rotation_axis_angle
                            val = math.degrees(Matrix.Rotation(angle, 4, axis).to_euler()[comp_index])
                        else:
                            val = math.degrees(bone.rotation_quaternion.to_euler()[comp_index] if bone.rotation_mode=='QUATERNION' else
                                                bone.rotation_euler[comp_index])
                        if self.index == 0:
                            skt.range_start = val
                        else:
                            skt.range_end = val
                        return{'FINISHED'}
        return{'CANCELLED'}
    
class GP2DMORPHS_OT_switch_ctrl_skt_range_values(bpy.types.Operator):
    bl_idname = "gp2dmorphs.switch_ctrl_skt_range_values"    
    bl_label = "Switch Control Socket Range Values"
    bl_description = "Sets Range Start to Range End, and sets Range End to Range Start"
    bl_options = {'UNDO'}
    node_name: StringProperty()
    socket_name : StringProperty()
    def execute(self, context):
        if (node_tree := get_tree(context)) and (node := node_tree.nodes.get(self.node_name)) and issubclass(type(node),GP2DMorphsNodeControlBase):
            skt = node.outputs.get(self.socket_name)
            if skt:
                skt.range_start, skt.range_end = skt.range_end, skt.range_start
                return{'FINISHED'}
        return{'CANCELLED'}

class GP2DMORPHS_OT_add_transform_output(bpy.types.Operator):
    bl_idname = "gp2dmorphs.add_transform_output"    
    bl_label = "Add Transform Output Socket"
    bl_description = "Adds a transform output socket to the node"
    bl_options = {'UNDO'}
    node_name: StringProperty()
    def execute(self, context):
        if (node_tree := get_tree(context)) and (node := node_tree.nodes.get(self.node_name)) and issubclass(type(node),GP2DMorphsNodeControlBase):
            type_to_add = 'LOC_X'
            # transform_types = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.types.DriverTarget.bl_rna.properties['transform_type'].enum_items if ot.identifier != '']
            transform_types = ['LOC_X','LOC_Y','LOC_Z','ROT_X','ROT_Y','ROT_Z','SCALE_X','SCALE_Y','SCALE_Z']
            current_types = [o.default_value for o in node.outputs]
            if len(current_types) > 0:
                last_type = current_types[-1]
                try:
                    last_index = transform_types.index(last_type)
                    if last_index < len(transform_types)-1:
                        type_to_add = transform_types[last_index+1]
                except ValueError:
                    pass
            output = node.outputs.new('GP2DMorphsNodeTransformChannelSocket', type_to_add)
            output.default_value = type_to_add
            output.init()
            return{'FINISHED'}
        return{'CANCELLED'}
    
class GP2DMORPHS_OT_remove_transform_output(bpy.types.Operator):
    bl_idname = "gp2dmorphs.remove_transform_output"    
    bl_label = "Remove Transform Output Socket"
    bl_description = "Removes the transform output socket from the node"
    bl_options = {'UNDO'}
    node_name: StringProperty()
    socket_name : StringProperty()
    def execute(self, context):
        if (node_tree := get_tree(context)) and (node := node_tree.nodes.get(self.node_name)) and issubclass(type(node),GP2DMorphsNodeControlBase):
            node.remove_output(self.socket_name)
            node.update_shape()
            return{'FINISHED'}
        return{'CANCELLED'}

class GP2DMORPHS_OT_add_selected_bones_to_morph_node(bpy.types.Operator):
    bl_idname = "gp2dmorphs.add_selected_bones_to_morph_node"    
    bl_label = "Add Selected Bones To Morph Node"
    bl_description = "Adds the current selected bones to the list in the morph node"
    bl_options = {'UNDO'}
    node_name: StringProperty()
    def execute(self, context):
        if (node_tree := get_tree(context)) and (node := node_tree.nodes.get(self.node_name)) and node.bl_idname == "GP2DMorphsNodeBoneMorph" and node.obj:
            for b in node.obj.data.bones:
                if b.select:
                    node.add_to_name_list(b.name)
            return{'FINISHED'}
        return{'CANCELLED'}
#Thanks to Diego Gangl and the tutorial at https://sinestesia.co/blog/tutorials/using-uilists-in-blender/ for these UIList operators
class LIST_OT_NewItem(bpy.types.Operator): 
    #Add a new item to the list.
    bl_idname = "gp2dmorphs.ui_list_new_item" 
    bl_label = "Add a new item"
    node_name: StringProperty()
    def execute(self, context):
        if (node_tree := get_tree(context)) and (node := node_tree.nodes.get(self.node_name)):
            node.add_to_name_list()
            return{'FINISHED'}
        return{'CANCELLED'}
    
class LIST_OT_DeleteItem(bpy.types.Operator): 
    #Delete the selected item from the list. 
    bl_idname = "gp2dmorphs.ui_list_delete_item" 
    bl_label = "Deletes an item"
    node_name: StringProperty()
    def execute(self, context):
        if (node_tree := get_tree(context)) and (node := node_tree.nodes.get(self.node_name)):
            op_list = node.name_list
            index = node.list_index 
            op_list.remove(index) 
            node.list_index = min(max(0, index - 1), len(op_list) - 1) 
            return{'FINISHED'}
        return{'CANCELLED'}
    
class LIST_OT_MoveItem(bpy.types.Operator): 
    #Move an item in the list. 
    bl_idname = "gp2dmorphs.ui_list_move_item" 
    bl_label = "Move an item in the list" 
    direction : EnumProperty(items=(('UP', 'Up', ""), ('DOWN', 'Down', ""),)) 
    node_name: StringProperty()
    def execute(self, context):
        if (node_tree := get_tree(context)) and (node := node_tree.nodes.get(self.node_name)):
            op_list = node.name_list
            index = node.list_index 
            neighbor = index + (-1 if self.direction == 'UP' else 1) 
            op_list.move(neighbor, index)
            list_length = len(op_list) - 1 # (index starts at 0) 
            new_index = index + (-1 if self.direction == 'UP' else 1) 
            node.list_index = max(0, min(new_index, list_length))
            return{'FINISHED'}
        return{'CANCELLED'}

def update_nodes(self,context,mode='ALL'):
    node_tree = context.space_data.edit_tree
    if node_tree is None:
        self.report({'ERROR'}, "No Node Tree Found")
        return
    if len(node_tree.nodes) == 0:
        self.report({'ERROR'}, "No Nodes. Nothing to update")
        return
    GP2DMORPHSEditorProps = node_tree.gp2dmorphs_editor_props
    original_active_obj = context.view_layer.objects.active
    original_mode = original_active_obj.mode             #Grab the current mode so we can switch back after
    original_cursor_location = context.scene.cursor.location.copy()
    controls, morphs_gp, morphs_bones = list(),list(),list()
    for node in node_tree.nodes:
        if not GP2DMORPHSEditorProps.selected_only or node.select:
            match node.bl_idname:
                case 'GP2DMorphsNodeControlLocation':       #Control    Location
                    controls.append(node)
                case 'GP2DMorphsNodeControlRotation':       #Control    Rotation
                    controls.append(node)
                case 'GP2DMorphsNodeGP2DMorph':             #Morph      GPencil
                    morphs_gp.append(node)
                case 'GP2DMorphsNodeBoneMorph':             #Morph      GPencil
                    morphs_bones.append(node)
    default_control_armature = None             
    did_something = False
    if mode != 'GPFRAMES':
        for c in controls:
            if c.update_control(context,default_control_armature):
                context.scene.cursor.location += Vector((1.3,0,0))
            if c.obj is not None:
                default_control_armature = c.obj
        for m in morphs_bones:
            m.generate(context)
        if len(controls) > 0 or len(morphs_bones) > 0:  did_something = True
    for m in morphs_gp:
        m.generate(context)
    if len(morphs_gp) > 0:  did_something = True
    if not did_something:
        self.report({'ERROR'}, 
        "Nothing updated. Likely, 'Only Update Selected' is enabled in the node editor header, but there aren't any valid nodes for the operation that are selected")
    else:       #Make everything go back to the way it was before
        context.scene.cursor.location = original_cursor_location
        context.view_layer.objects.active = original_active_obj
        bpy.ops.object.mode_set(mode=original_mode, toggle=False)
    
_classes = [
    LIST_OT_NewItem,
    LIST_OT_DeleteItem,
    LIST_OT_MoveItem,
    GP2DMORPHS_OT_add_selected_bones_to_morph_node,
    GP2DMORPHS_OT_update_nodes,
    GP2DMORPHS_OT_remove_and_clean_up_nodes,
    GP2DMORPHS_OT_create_controls_for_morphs,
    GP2DMORPHS_OT_set_ctrl_skt_range,
    GP2DMORPHS_OT_switch_ctrl_skt_range_values,
    GP2DMORPHS_OT_add_transform_output,
    GP2DMORPHS_OT_remove_transform_output,
    GP2DMORPHS_OT_set_node_tree_lod,
    GP2DMORPHS_OT_set_node_tree_mode
]
    
def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in _classes:
        bpy.utils.unregister_class(cls)