import bpy
from bpy.props import IntProperty, StringProperty, BoolProperty
from bpy.types import UIList


class NODE_UL_string_ui_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(0.2)
        split.label(str(item.id))
        split.prop(item, "name", text="", emboss=False, translate=False, icon='BORDER_RECT')
        #col.prop_search(GP2DMORPHSVars, "control_bone_name", GP2DMORPHSVars.control_armature.data, "bones", text="")

class StringUIListItem(bpy.types.PropertyGroup):
    name : StringProperty()
    id : IntProperty()
    mirror : BoolProperty(default=True)


def register():
    bpy.utils.register_class(NODE_UL_string_ui_list)
    bpy.utils.register_class(StringUIListItem)

def unregister():
    bpy.utils.unregister_class(NODE_UL_string_ui_list)
    bpy.utils.unregister_class(StringUIListItem)