import bpy
import math
from bpy.props import PointerProperty, BoolProperty
from ..Output.node_MorphBase import GP2DMorphsNodeMorphBase
from ...operators.ops import generate_2d_bone_morphs_with_pg, create_driver_variable_expression
from ...utils import get_flipped_name

class GP2DMorphsNodeBone2DMorph(GP2DMorphsNodeMorphBase):
    bl_idname = "GP2DMorphsNodeBoneMorph"
    bl_label = 'Bone Morph'
    bl_icon = 'CON_SPLINEIK'

    obj : PointerProperty(name="Armature", type=bpy.types.Object, poll=lambda self, obj: obj.type == 'ARMATURE', description="The armature to add or find bones to morph in")
    lock_morph : BoolProperty(name="Lock Morph",default=False,description="Lock Morph so that its transform data won't get updated when other nodes get updated")
    
    def init(self, context):
        context = bpy.context
        node_tree = self.get_tree(context)
        col_purple=(0.9,0.2,1)
        col_aqua=(0.4,1,1)
        self.create_input('GP2DMorphsNodeLinkedPropSocket', 'def_frames_w', 'Defined Frames Width',socket_color=col_purple,default_value=3)
        self.create_input('GP2DMorphsNodeLinkedPropSocket', 'def_frames_h', 'Defined Frames Height',socket_color=col_aqua,default_value=3)

        for node in node_tree.nodes:
            if node.bl_idname == 'GP2DMorphsNodeBoneMorph' and node.obj is not None:
                self.obj = node.obj
                break
        if self.obj is None:
            for o in bpy.data.objects:
                if o is not None and o.type == 'ARMATURE':
                    self.obj = o
                    break
        self.add_to_name_list()
        super().init(context)

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "obj", text="", icon='ARMATURE_DATA')
        super().draw_buttons(context,layout) 
        row = layout.row(align=True)
        row.prop(self.props, "generate_frames_or_location", text="Location", toggle=True)
        row.prop(self.props, "generate_control_or_rotation", text="Rotation", toggle=True)
        row.prop(self.props, "generate_driver_or_scale", text="Scale", toggle=True)
        
    def draw_buttons_ext(self, context, layout):
        super().draw_buttons_ext(context,layout)
        box = layout.box()
        row = box.row(align=True)
        row.prop(self.props, "generate_frames_or_location", text="Location", toggle=True)
        row.prop(self.props, "generate_control_or_rotation", text="Rotation", toggle=True)
        row.prop(self.props, "generate_driver_or_scale", text="Scale", toggle=True)

    def generate(self, context):
        self.update_props()
        if self.lock_morph or self.obj is None or len(self.name_list) == 0:
            return
        node_tree = self.get_tree(context)
        editor_props = node_tree.gp2dmorphs_editor_props
        name_list_names = [list_item.name for list_item in self.name_list]  #I make good variable names, I swear
        original_selected_state = list()
        for b in self.obj.data.bones:
            original_selected_state.append((b,b.select))
            b.select = b.name in name_list_names
        generate_2d_bone_morphs_with_pg(self.props,self.obj.name,False,False,False,editor_props.mode)
        for select_state in original_selected_state:
            select_state[0].select = select_state[1]
        #self.set_mode(editor_props.mode)

    def update_drivers(self):
        if self.obj is not None:
            ctrl_obj_x, ctrl_obj_y = None, None
            if self.props.control_armature_x:
                ctrl_obj_x = self.props.control_armature_x.pose.bones.get(self.props.control_bone_name_x)
            if self.props.control_armature_y:
                ctrl_obj_y = self.props.control_armature_y.pose.bones.get(self.props.control_bone_name_y)
            need_x, need_y = ctrl_obj_x is not None, ctrl_obj_y is not None
            driver_var_x = create_driver_variable_expression("varX",self.props.control_bone_transform_type_x[:3],
                                                              math.radians(self.props.control_range_start_x),math.radians(self.props.control_range_end_x),self.props.control_range_flip_x)
            driver_var_y = create_driver_variable_expression("varY",self.props.control_bone_transform_type_y[:3],
                                                              math.radians(self.props.control_range_start_y),math.radians(self.props.control_range_end_y),self.props.control_range_flip_y)
            old_driver_var_x_expr, old_driver_var_y_expr = '',''
            for name_list_item in self.name_list:
                bone = self.obj.pose.bones.get(name_list_item.name)
                rot_var_name = ("rotation_quaternion" if bone.rotation_mode=='QUATERNION' else
                            "rotation_axis_angle" if bone.rotation_mode=='AXIS_ANGLE' else
                            "rotation_euler")
                rot_len = len(rot_var_name)
                for fc in self.obj.animation_data.drivers:  #F Curves
                    # a data path looks like this: 'pose.bones["Bone.002"].scale'
                    # search for the full bone name including the quotation marks!
                    if ('"%s"' % name_list_item.name) in fc.data_path:
                        if fc.data_path[-8:] == 'location' or fc.data_path[-rot_len:] == rot_var_name or fc.data_path[-5:] == 'scale':
                            driver = fc.driver
                            expr = driver.expression
                            var_x = driver.variables.get('varX')
                            var_y = driver.variables.get('varY')

                            if need_x:
                                if var_x is None:
                                    var_x = driver.variables.new()
                                    var_x.type='TRANSFORMS'
                                    var_x.name="varX"
                                    var_x.targets[0].transform_space = 'LOCAL_SPACE'
                                if var_x.targets[0].transform_type != self.props.control_bone_transform_type_x:
                                    var_x.targets[0].transform_type = self.props.control_bone_transform_type_x
                                    if old_driver_var_x_expr == '':
                                        i = expr.find("varX")
                                        i_start, i_end = i - 1, i + 3
                                        parentheses = 0
                                        while i_start > 0 and (c := expr[i_start]) != ',': 
                                            if c == '(':
                                                parentheses += 1
                                            elif c == ')':
                                                parentheses -= 1
                                            i_start -= 1
                                        i_start += 1
                                        while i_end < len(expr) - 1 and parentheses > 0: 
                                            c = expr[i_end]
                                            if c == '(':
                                                parentheses += 1
                                            elif c == ')':
                                                parentheses -= 1
                                            i_end += 1
                                        if i_start > 1 and i_end < len(expr):
                                            old_driver_var_x_expr = expr[i_start:i_end]
                                            expr = expr[:i_start] + driver_var_x + expr[i_end:]
                                    else:
                                        i_start = expr.find(old_driver_var_x_expr)
                                        if i != -1:
                                            expr = expr[:i_start] + driver_var_x + expr[i_start+len(old_driver_var_x_expr):]
                                var_x.targets[0].id = ctrl_obj_x.id_data
                                var_x.targets[0].bone_target = ctrl_obj_x.name
                            elif var_x:
                                var_x.targets[0].bone_target = ''
                            if need_y:
                                if var_y is None:
                                    var_y = driver.variables.new()
                                    var_y.type='TRANSFORMS'
                                    var_y.name="varY"
                                    var_y.targets[0].transform_space = 'LOCAL_SPACE'
                                if var_y.targets[0].transform_type != self.props.control_bone_transform_type_y:
                                    var_y.targets[0].transform_type = self.props.control_bone_transform_type_y
                                    if old_driver_var_y_expr == '':
                                        i = expr.find("varY")
                                        i_start, i_end = i - 1, i + 3
                                        parentheses = 0
                                        while i_start > 0 and (c := expr[i_start]) != ',': 
                                            if c == '(':
                                                parentheses += 1
                                            elif c == ')':
                                                parentheses -= 1
                                            i_start -= 1
                                        i_start += 1
                                        while i_end < len(expr) - 1 and parentheses > 0: 
                                            c = expr[i_end]
                                            if c == '(':
                                                parentheses += 1
                                            elif c == ')':
                                                parentheses -= 1
                                            i_end += 1
                                        if i_start > 1 and i_end < len(expr):
                                            old_driver_var_y_expr = expr[i_start:i_end]
                                            expr = expr[:i_start] + driver_var_y + expr[i_end:]
                                    else:
                                        i_start = expr.find(old_driver_var_y_expr)
                                        if i != -1:
                                            expr = expr[:i_start] + driver_var_y + expr[i_start+len(old_driver_var_y_expr):]
                                var_y.targets[0].id = ctrl_obj_y.id_data
                                var_y.targets[0].bone_target = ctrl_obj_y.name
                            elif var_y:
                                var_y.targets[0].bone_target = ''
                            driver.expression = expr

    def set_mode(self, mode):
        if self.obj is not None:
            driver_mute = mode == 'EDIT'
            for name_list_item in self.name_list:
                bone = self.obj.pose.bones.get(name_list_item.name)
                rot_var_name = ("rotation_quaternion" if bone.rotation_mode=='QUATERNION' else
                            "rotation_axis_angle" if bone.rotation_mode=='AXIS_ANGLE' else
                            "rotation_euler")
                rot_len = len(rot_var_name)
                for fc in self.obj.animation_data.drivers:  #F Curves
                    if ('"%s"' % name_list_item.name) in fc.data_path:
                        if fc.data_path[-8:] == 'location':
                            if self.props.generate_frames_or_location:
                                fc.mute = driver_mute
                        elif fc.data_path[-rot_len:] == rot_var_name:
                            if self.props.generate_control_or_rotation:
                                fc.mute = driver_mute
                        elif fc.data_path[-5:] == 'scale':
                            if self.props.generate_driver_or_scale:
                                fc.mute = driver_mute

    def add_to_name_list(self, given_name=''):
        if not super().add_to_name_list(given_name):
            if self.obj:
                context = bpy.context
                node_tree = context.space_data.edit_tree
                other_bones = list()   #List of layers in other nodes, so we don't default to one of them
                for node in node_tree.nodes:
                    if node.bl_idname == "GP2DMorphsNodeBoneMorph" and node.obj and node.obj == self.obj:
                        for n in node.name_list:
                            if n.name != "":
                                other_bones.append(n.name)
                for l in self.obj.pose.bones:
                    if l.name not in other_bones:
                        self.name_list[len(self.name_list)-1].name = l.name
                        break

    def flip_names(self):
        if super().flip_names() and self.obj:
            for n in self.name_list:
                new_name = get_flipped_name(n.name)
                if new_name is not False and new_name in self.obj.pose.bones:
                    n.name = new_name

def register():
    bpy.utils.register_class(GP2DMorphsNodeBone2DMorph)


def unregister():
    bpy.utils.unregister_class(GP2DMorphsNodeBone2DMorph)