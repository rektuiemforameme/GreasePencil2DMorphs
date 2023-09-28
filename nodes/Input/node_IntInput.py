import bpy
from bpy.props import IntProperty
from ..BASE.node_base import GP2DMorphsNodeBase


def update_node(self, context):
    self.execute_tree()

def update_attached_nodes(self,context):
    linked_input_skts = self.get_linked_inputs()
    for output_inputs in linked_input_skts:
        list_output = output_inputs[0]
        if list_output:
            for list_input in output_inputs[1]:
                if list_input.bl_idname == 'GP2DMorphsNodeLinkedPropSocket':
                    list_input.set_value(self.default_value)

class GP2DMorphsNodeIntInput(GP2DMorphsNodeBase):
    bl_idname = 'GP2DMorphsNodeIntInput'
    bl_label = 'Int Input'

    default_value: IntProperty(update=update_attached_nodes)

    def init(self, context):
        self.create_output('GP2DMorphsNodeSocketIntOverZero', 'output', "Output")

    def draw_buttons(self, context, layout):
        layout.prop(self, 'default_value', text='')

    def process(self, context, id, path):
        self.outputs[0].set_value(self.default_value)
    
    def update(self):
        update_attached_nodes(self,bpy.context)

def register():
    bpy.utils.register_class(GP2DMorphsNodeIntInput)


def unregister():
    bpy.utils.unregister_class(GP2DMorphsNodeIntInput)
