import bpy
from bpy.props import BoolProperty, StringProperty, PointerProperty
from ..BASE.node_base import GP2DMorphsNodeBase
from ..Output.node_MorphBase import GP2DMorphsNodeMorphBase
from ...operators.ops import get_or_create_control, update_ctrl_bone

def update_node(self, context):
    self.execute_tree()

def update_bone(self, context):
    update_attached_morphs(context)
    self.update_shape()

def update_attached_morphs(self,context):
    if self.obj is None or self.bone_name == '':    return
    linked_input_skts = self.get_linked_inputs(skts_fake_dict=[])
    for output_inputs in linked_input_skts:
        list_output = output_inputs[0]
        if list_output:
            for list_input in output_inputs[1]:
                skt_node = list_input.node
                if skt_node and issubclass(type(skt_node),GP2DMorphsNodeMorphBase):
                    skt_node.update_props_from_control(list_input,self,list_output)
                    skt_node.update_drivers()

class GP2DMorphsNodeControlBase(GP2DMorphsNodeBase):
    bl_idname = 'GP2DMorphsNodeControlBase'
    bl_label = 'Base Control'
    bl_icon = 'DRIVER'

    obj : PointerProperty(name="Armature", type=bpy.types.Object, poll=lambda self, obj: obj.type == 'ARMATURE', description="The armature to add or find control bones in")
    bone_name : StringProperty(name="Bone", default='',update=update_attached_morphs,description="The bone to use as a control")
    use_custom_shapes : BoolProperty(name="Use Custom Shapes",default=True,description="Pose Bones will have Custom Shapes applied to them that correspond to their control")
    use_control_constraints : BoolProperty(name="Use Control Constraints",default=True,description="Knob Pose Bone will have constraints applied to it to limit its movement depending on the type of control")

    def init(self, context):
        if context is None:
            context = bpy.context   #The passed context was sometimes None...
        node_tree = self.get_tree(context)
        #Try to find an armature to use
        for node in node_tree.nodes:
            if (issubclass(type(node),GP2DMorphsNodeControlBase)) and node.obj is not None:
                self.obj = node.obj
                break
        if self.obj is None:
            for o in bpy.data.objects:
                if o is not None and o.type == 'ARMATURE':
                    self.obj = o
                    break
        
    def draw_buttons(self, context, layout):
        op_props = layout.operator("gp2dmorphs.add_transform_output",text='',icon='ADD')
        op_props.node_name = self.name
        col = layout.column(align=True)
        col.prop(self, "obj", text="", icon='ARMATURE_DATA')
        if self.obj is not None:
            col.prop_search(self, "bone_name", self.obj.data, "bones", text="")

    def draw_buttons_ext(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "use_custom_shapes", text="Custom Shapes", toggle=True)
        row.prop(self, "use_control_constraints", text="Constraints", toggle=True)
        ctrl_defined = self.obj and self.obj.pose.bones.get(self.bone_name)
        for out in self.outputs:
            out.draw_buttons_ext(context, layout, ctrl_defined)

    def update_shape(self):
        if self.obj and self.obj.name in bpy.data.objects and self.bone_name != '':
            b = self.obj.pose.bones.get(self.bone_name)
            if b:
                trans_limits = self.get_transform_limits()
                
                if trans_limits['L'] or trans_limits['R'] or trans_limits['S']:
                    update_ctrl_bone(b,trans_limits,self.use_custom_shapes,self.use_control_constraints)
    #returns True if a new control was created
    def update_control(self, context, arm_obj=None):
        if self.obj and self.obj.pose.bones.get(self.bone_name):
            return False      #References are good. Nothing to see here.
        trans_limits = self.get_transform_limits()
        control_name = self.bone_name
        if control_name == "":
            if self.label != "":
                control_name = self.label
            else:
                control_name = self.name
        if self.obj is None and arm_obj and arm_obj.type == 'ARMATURE':
            self.obj = arm_obj
        b = get_or_create_control('BONE',control_name,
                                self.obj.name if self.obj else "",
                                self.use_custom_shapes,self.use_control_constraints,trans_limits)
        if b:
            self.obj = b.id_data
            self.bone_name = b.name
        return True
    
    def clean_up(self):
        if self.obj:
            original_object_selected = self.obj.select_get()
            if not original_object_selected:
                self.obj.select_set(True)
            bpy.context.view_layer.objects.active = self.obj
            original_mode = self.obj.mode
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
            if(ctrl_bone := self.obj.data.edit_bones.get(self.bone_name)):
                if (base_bone := ctrl_bone.parent) and len(base_bone.name) >= 4 and base_bone.name[:-4] == ctrl_bone.name[:-4]:
                    self.obj.data.edit_bones.remove(base_bone)
                self.obj.data.edit_bones.remove(ctrl_bone)
            self.obj.select_set(original_object_selected)
            bpy.ops.object.mode_set(mode=original_mode, toggle=False)
        return super().clean_up()
    
    def get_transform_limits(self):
        trans_limits = {'L':None,'R':None,'S':None}    #Components of Loc,Rot,Scale that are needed.
                
        for out in self.outputs:    #Find out which transform components we're using
            trans_type = out.default_value[0]
            if trans_limits[trans_type] is None:
                trans_limits[trans_type] = {'X':None,'Y':None,'Z':None}
            trans_limits[trans_type][out.default_value[-1]] = (-0.5,0.5) if trans_type == 'L' else (out.range_start,out.range_end) if trans_type == 'R' else (0,2)#default_value[0] will be in ('L','R','S'), and default_value[-1] will be in ('X','Y','Z')
        return trans_limits
    
def register():
    bpy.utils.register_class(GP2DMorphsNodeControlBase)

def unregister():
    bpy.utils.unregister_class(GP2DMorphsNodeControlBase)