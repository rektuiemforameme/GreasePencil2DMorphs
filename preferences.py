import bpy
import rna_keymap_ui
from bpy.props import StringProperty

from . import __folder_name__


def get_pref():
    return bpy.context.preferences.addons.get(__folder_name__).preferences


class GP2DMorphs_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    custom_shapes_collection : StringProperty(name="Custom Shapes Collection Name", default='Custom Shapes',
                                              description="The name of the collection to put control custom shape meshes in. Use 'None' to put them in the current collection")

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'custom_shapes_collection')
        self.drawKeymap(context) #Maybe some day I'll get around to looking into this

    def drawKeymap(self,context):
        col = self.layout.box().column()
        col.label(text="Keymap", icon="KEYINGSET")
        km = None
        wm = context.window_manager
        kc = wm.keyconfigs.user

        old_km_name = ""
        get_kmi_l = []

        for km_add, kmi_add in addon_keymaps:
            for km_con in kc.keymaps:
                if km_add.name == km_con.name:
                    km = km_con
                    break
            
            for kmi_con in km.keymap_items:
                if kmi_add.idname == kmi_con.idname and kmi_add.name == kmi_con.name:
                    get_kmi_l.append((km, kmi_con))

        get_kmi_l = sorted(set(get_kmi_l), key=get_kmi_l.index)

        for km, kmi in get_kmi_l:
            if not km.name == old_km_name:
                col.label(text=str(km.name), icon="DOT")

            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)

            old_km_name = km.name


addon_keymaps = []


def add_keymap():
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
        kmi = km.keymap_items.new("gp2dmorphs.remove_and_clean_up_nodes", 'X', 'PRESS', shift=True)
        addon_keymaps.append((km, kmi))


def remove_keymap():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)

    addon_keymaps.clear()


def register():
    bpy.utils.register_class(GP2DMorphs_Preferences)
    add_keymap()


def unregister():
    bpy.utils.unregister_class(GP2DMorphs_Preferences)
    remove_keymap()
