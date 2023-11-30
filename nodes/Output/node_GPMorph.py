import bpy
from bpy.props import PointerProperty, BoolProperty
from ..Output.node_MorphBase import GP2DMorphsNodeMorphBase
from ...operators.ops import generate_2d_morphs_with_pg, update_gp_time_offset_and_driver
from ...utils import get_flipped_name

class GP2DMorphsNodeGP2DMorph(GP2DMorphsNodeMorphBase):
    bl_idname = "GP2DMorphsNodeGP2DMorph"
    bl_label = 'GPencil Morph'
    bl_icon = 'GP_MULTIFRAME_EDITING'

    obj : PointerProperty(name="GPencil", type=bpy.types.Object, poll=lambda self, o: o.type == 'GPENCIL', description="The Grease Pencil Object that contains the layer(s) to be morphed")
    lock_morph : BoolProperty(name="Lock Morph",default=False,description="Lock Morph so that its frames won't get updated when other nodes get updated")

    def init(self, context):
        node_tree = self.get_tree(context)
        col_purple=(0.9,0.2,1)
        col_aqua=(0.4,1,1)
        self.create_input('GP2DMorphsNodeLinkedPropSocket', 'def_frames_w', 'Defined Frames Width',socket_color=col_purple,default_value=3)
        self.create_input('GP2DMorphsNodeLinkedPropSocket', 'def_frames_h', 'Defined Frames Height',socket_color=col_aqua,default_value=3)
        self.create_input('GP2DMorphsNodeLinkedPropSocket', 'gen_frames_w', 'Generated Frames Width',socket_color=col_purple,default_value=33)
        self.create_input('GP2DMorphsNodeLinkedPropSocket', 'gen_frames_h', 'Generated Frames Height',socket_color=col_aqua,default_value=33)
        for node in node_tree.nodes:
            if node.bl_idname == self.bl_idname and node.obj:
                self.obj = node.obj
                break
        
        if self.obj is None:
            for o in bpy.data.objects:
                if o and o.type == 'GPENCIL':
                    self.obj = o
                    break
        self.add_to_name_list()
        super().init(context)

    def draw_buttons(self, context, layout):
        layout.prop(self, "obj", text="", icon='GREASEPENCIL')
        super().draw_buttons(context,layout)
            
        
    def draw_buttons_ext(self, context, layout):
        super().draw_buttons_ext(context,layout)
        if self.obj:
            l_name = self.get_selected_name()
            op_props = layout.operator("GP2DMORPHS.fill_defined_frames")
            op_props.def_frame_start, op_props.def_frames_w, op_props.def_frames_h = self.props.def_frame_start, self.props.def_frames_w, self.props.def_frames_h
            op_props.gp_obj_name, op_props.layer_name = self.obj.name, l_name
            op_props.props_set = True

            layout.prop(self.props, "gen_frame_start", text="Gen Starting Frame")
            layout.prop(self.props,"use_layer_pass")
            box = layout.box()
            col = box.column()
            col.prop(self.props, "interpolate", text="Interpolate")

            if self.props.interpolate:
                row = layout.row()
                row.label(icon='IPO_EASE_IN_OUT')
                row.operator_menu_enum("GP2DMORPHS.set_all_interp_types","type", text="Set All").node_name = self.name
                if self.props.interp_type_left != 'LINEAR' or self.props.interp_type_right != 'LINEAR' or self.props.interp_type_up != 'LINEAR' or self.props.interp_type_down != 'LINEAR':
                    row.operator_menu_enum("GP2DMORPHS.set_all_interp_easings","easing", text="Set All").node_name = self.name
                
                if self.props.gen_frames_h > 1:
                    row = layout.row()
                    row.label(text="",icon='TRIA_UP')
                    row.prop(self.props, "interp_type_up", text="")
                    if self.props.interp_type_up == 'CUSTOM':
                        row.label(text=":(",icon='ERROR')
                    elif self.props.interp_type_up != 'LINEAR':
                        row.prop(self.props, "interp_easing_up", text="")

                    if self.props.def_frames_h > 2:
                        row = layout.row()
                        row.label(text="",icon='TRIA_DOWN')
                        row.prop(self.props, "interp_type_down", text="")
                        if self.props.interp_type_down == 'CUSTOM':
                            row.label(text=":(",icon='ERROR')
                        elif self.props.interp_type_down != 'LINEAR':
                            row.prop(self.props, "interp_easing_down", text="")
                if self.props.gen_frames_w > 1:
                    if self.props.def_frames_w > 2:
                        row = layout.row()
                        row.label(text="",icon='TRIA_LEFT')
                        row.prop(self.props, "interp_type_left", text="")
                        if self.props.interp_type_left == 'CUSTOM':
                            row.label(text=":(",icon='ERROR')
                        elif self.props.interp_type_left != 'LINEAR':
                            row.prop(self.props, "interp_easing_left", text="")

                    row = layout.row()
                    row.label(text="",icon='TRIA_RIGHT')
                    row.prop(self.props, "interp_type_right", text="")
                    if self.props.interp_type_right == 'CUSTOM':
                        row.label(text=":(",icon='ERROR')
                    elif self.props.interp_type_right != 'LINEAR':
                        row.prop(self.props, "interp_easing_right", text="")

            #Stroke order settings
            box = layout.box()
            box.prop(self.props, "stroke_order_changes", text="Stroke Order Changes")
            if self.props.stroke_order_changes:
                box.label(text="Order change offset factor")
                row = box.row()
                h,v = self.props.def_frames_w > 1, self.props.def_frames_h > 1
                if h:
                    row.prop(self.props, "stroke_order_change_offset_factor_horizontal", text="Horizontal" if v else "")
                if v:
                    row.prop(self.props, "stroke_order_change_offset_factor_vertical", text="Vertical" if h else "")

    def generate(self, context):
        self.update_props()
        if self.lock_morph or self.obj is None or len(self.name_list) == 0:
            return
        node_tree = self.get_tree()
        if node_tree is None:
            return
        editor_props = node_tree.gp2dmorphs_editor_props
        original_gen_w, original_gen_h = self.props.gen_frames_w, self.props.gen_frames_h
        if editor_props.level_of_detail == 'PREVIEW':
            self.props.gen_frames_w, self.props.gen_frames_h = min(self.props.gen_frames_w, editor_props.preview_resolution), min(self.props.gen_frames_h, editor_props.preview_resolution)
        generate_2d_morphs_with_pg(self.props,self.name,self.get_pass_index(),False,False,editor_props.mode)
        self.props.gen_frames_w, self.props.gen_frames_h = original_gen_w, original_gen_h

    def update_props(self):
        super().update_props()
        if node_tree := self.get_tree():
            editor_props = node_tree.gp2dmorphs_editor_props
            self.props.generate_frames_or_location = editor_props.update_gp_frames
            self.props.generate_driver_or_scale = editor_props.update_modifiers

    def update_drivers(self):
        if node_tree := self.get_tree():
            editor_props = node_tree.gp2dmorphs_editor_props
            original_gen_w, original_gen_h = self.props.gen_frames_w, self.props.gen_frames_h
            if editor_props.level_of_detail == 'PREVIEW':
                self.props.gen_frames_w, self.props.gen_frames_h = min(self.props.gen_frames_w, editor_props.preview_resolution), min(self.props.gen_frames_h, editor_props.preview_resolution)
            ctrl_objs = self.get_control_bones()
            if self.props.use_layer_pass:
                update_gp_time_offset_and_driver(self.props,self.obj,ctrl_objs[0],ctrl_objs[1],[n.name for n in self.name_list if n.name != ''],
                                                 self.get_pass_index(),editor_props.mode,False,self.get_morph_name()+"TO")
            else:
                for n in self.name_list:
                    if self.obj.data.layers.get(n.name):
                        update_gp_time_offset_and_driver(self.props,self.obj,ctrl_objs[0],ctrl_objs[1],[n.name],-1,editor_props.mode,False)
            self.props.gen_frames_w, self.props.gen_frames_h = original_gen_w, original_gen_h

    def set_mode(self, mode):
        if self.obj:
            if self.props.use_layer_pass:    #Use the pass index to toggle the modifier
                layer = self.obj.data.layers.get(self.get_first_nonblank_name())
                if layer is None:   return
                pindex = layer.pass_index
                for m in self.obj.grease_pencil_modifiers:
                    if m.type == 'GP_TIME':
                        if pindex == m.layer_pass:
                            m.show_viewport = mode == 'ANIMATE'
                            return
            else:                       #Use the layer(s) to toggle the modifier(s)
                mod_view = mode == 'ANIMATE'
                name_list_names = [item.name for item in self.name_list]
                for m in self.obj.grease_pencil_modifiers:
                    if m.type == 'GP_TIME':
                        if m.layer in name_list_names:
                            m.show_viewport = mod_view
    
    def get_pass_index(self):
        if self.props.use_layer_pass:
            for n in self.name_list:
                if layer := self.obj.data.layers.get(n.name):
                    return layer.pass_index
        return -1

    def get_timeoffset_modifier(self, layer_name = ''):
        if layer_name == '':
            layer_name = self.get_first_nonblank_name()
        layer = self.obj.data.layers.get(layer_name)
        if self.obj is None or layer is None: return None
        if self.props.use_layer_pass:    #Use the pass index to find the modifier
            pindex = layer.pass_index
            for m in self.obj.grease_pencil_modifiers:
                if m.type == 'GP_TIME':
                    if pindex == m.layer_pass:
                        return m
        else:                       #Use the layer to find the modifier
            for m in self.obj.grease_pencil_modifiers:
                if m.type == 'GP_TIME':
                    if m.layer == layer_name:
                        return m
        return None
    
    def add_to_name_list(self,given_name=''):
        if not super().add_to_name_list(given_name) and self.obj:
            context = bpy.context
            node_tree = context.space_data.edit_tree
             
            #List of layers in other nodes, so we don't default to one of them
            other_layers = [n.name
            for node in node_tree.nodes
                if (hasattr(node, 'obj') and node.obj and node.obj == self.obj and node.bl_idname == self.bl_idname)
                    for n in node.name_list
                        if n.name != ""]
            
            gp = self.obj.data
            if len(self.name_list) > 1: #There are already layers in the list. Find the last one, and try to add the layer that is next in line.
                last_layer_index = 0
                for n in reversed(self.name_list):
                    if n.name != '':
                        try:
                            last_layer_index = gp.layers.find(n.name)
                            if last_layer_index == -1: continue
                            for li in range(last_layer_index+1,len(gp.layers)): #Try going forwards
                                if gp.layers[li].info not in other_layers:
                                    self.name_list[len(self.name_list)-1].name = gp.layers[li].info
                                    return
                            for li in range(last_layer_index-1,-1,-1):          #Backwards
                                if gp.layers[li].info not in other_layers:
                                    self.name_list[len(self.name_list)-1].name = gp.layers[li].info
                                    return
                        except ValueError:
                            continue
            
            for l in gp.layers:
                if l.info not in other_layers:
                    self.name_list[len(self.name_list)-1].name = l.info
                    return
                
    def flip_names(self):
        if super().flip_names() and self.obj:
            gp = self.obj.data
            for n in self.name_list:
                new_name = get_flipped_name(n.name)
                if new_name is not False and new_name in gp.layers:
                    n.name = new_name

def register():
    bpy.utils.register_class(GP2DMorphsNodeGP2DMorph)


def unregister():
    bpy.utils.unregister_class(GP2DMorphsNodeGP2DMorph)