import bpy
from ..Input.node_ControlBase import GP2DMorphsNodeControlBase

def update_node(self, context):
    self.execute_tree()

class GP2DMorphsNodeControlLocation(GP2DMorphsNodeControlBase):
    bl_idname = 'GP2DMorphsNodeControlLocation'
    bl_label = 'Location Control'

    def init(self, context):
        context = bpy.context   #The passed context was sometimes None... 
        super().init(context)
        out = self.create_output('GP2DMorphsNodeTransformChannelSocket', 'LOC_X', "Location X", default_value='LOC_X')
        out.init()
        out = self.create_output('GP2DMorphsNodeTransformChannelSocket', 'LOC_Y', "Location Y", default_value='LOC_Y')
        out.init()

def register():
    bpy.utils.register_class(GP2DMorphsNodeControlLocation)


def unregister():
    bpy.utils.unregister_class(GP2DMorphsNodeControlLocation)
