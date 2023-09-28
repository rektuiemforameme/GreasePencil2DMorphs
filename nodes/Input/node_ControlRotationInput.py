import bpy
from ..Input.node_ControlBase import GP2DMorphsNodeControlBase

class GP2DMorphsNodeControlRotation(GP2DMorphsNodeControlBase):
    bl_idname = 'GP2DMorphsNodeControlRotation'
    bl_label = 'Rotation Control'

    def init(self, context):
        context = bpy.context   #The passed context was sometimes None... 
        super().init(context)
        out = self.create_output('GP2DMorphsNodeTransformChannelSocket', 'ROT_Z', "Rotation Z", default_value='ROT_Z')
        out.init()

def register():
    bpy.utils.register_class(GP2DMorphsNodeControlRotation)


def unregister():
    bpy.utils.unregister_class(GP2DMorphsNodeControlRotation)
