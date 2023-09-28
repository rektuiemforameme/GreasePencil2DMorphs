import bpy
from bpy.props import PointerProperty, IntProperty, CollectionProperty
from ..BASE.node_base import GP2DMorphsNodeBase
from ...props import GP2DMORPHS_OpProps
from ...ui import GP2DMORPHSUIListItemString

class GP2DMorphsNodeMorphBase(GP2DMorphsNodeBase):
    bl_idname = "GP2DMorphsNodeMorphBase"
    bl_label = 'Morph Base'
    bl_icon = 'GP_MULTIFRAME_EDITING'

    props: PointerProperty(type=GP2DMORPHS_OpProps)

    obj : PointerProperty(name="GPencil", type=bpy.types.Object, poll=lambda self, o: o.type == 'GPENCIL', description="The Grease Pencil Object that contains the layer(s) to be morphed")
    list_index : IntProperty()
    name_list : CollectionProperty(type=GP2DMORPHSUIListItemString)

    def init(self, context):
        if context is None: #This happens sometimes, not sure why
            context=bpy.context
        self.width = 200
        self.props.control_type = 'BONE'
        self.props.generate_control_or_rotation = False
        self.create_input('GP2DMorphsNodeNonValueSocket', 'input_x', 'Input X',socket_color=context.preferences.themes[0].user_interface.axis_x)
        self.create_input('GP2DMorphsNodeNonValueSocket', 'input_y', 'Input Y',socket_color=context.preferences.themes[0].user_interface.axis_y)

    def draw_buttons(self, context, layout):
        #####Layer Name List#####
        if self.obj is not None:
            row = layout.row()
            row.template_list("NODE_UL_string_search", "", self, "name_list", self, "list_index", rows=1)
            #ADD and REMOVE
            col = row.column(align=True)
            col.operator('gp2dmorphs.ui_list_new_item', text='',icon='ADD').node_name = self.name
            col.operator('gp2dmorphs.ui_list_delete_item', text='',icon='REMOVE').node_name = self.name
            if self.bl_idname == "GP2DMorphsNodeBoneMorph":
                col.operator('gp2dmorphs.add_selected_bones_to_morph_node', text='',icon='RESTRICT_SELECT_OFF').node_name = self.name
            #MOVE 
            if len(self.name_list) > 1:
                col.separator()
                op_props = col.operator('gp2dmorphs.ui_list_move_item', text='',icon='TRIA_UP')
                op_props.direction = 'UP'
                op_props.node_name = self.name
                op_props = col.operator('gp2dmorphs.ui_list_move_item', text='',icon='TRIA_DOWN')
                op_props.direction = 'DOWN'
                op_props.node_name = self.name

    
    def draw_buttons_ext(self, context, layout):
        layout.prop(self.props, "def_frame_start", text="Starting Frame")
        l_name = self.get_selected_name()
        if self.obj is not None and l_name != '':
            box = layout.box()
            #Defined Array Frame shortcuts
            col = box.column(align=True)
            for y in range(self.props.def_frames_h-1,-1,-1):
                row = col.row(align=True)
                for x in range(self.props.def_frames_w):
                    f = self.props.def_frame_start + y*(self.props.def_frames_w+1) + x   #The frame that this button and position in the defined 'array' represents and links to
                    op_props = row.operator("GP2DMORPHS.set_frame_by_defined_pos", text = str(f), depress = f==context.scene.frame_current)
                    op_props.pos_x, op_props.pos_y = x, y
                    op_props.def_frame_start, op_props.def_frames_w = self.props.def_frame_start, self.props.def_frames_w
    #Handle new control being connected     TODO: Figure out why the hell this doesn't work. Any attempt to access link.to_socket or link.from_socket, or the sockets from the nodes given, will error
    # def insert_link(self, link):
    #     from ..Input.node_ControlBase import GP2DMorphsNodeControlBase  #I don't like this any more than you do
    #     self_skt = link.to_socket
    #     if self_skt.bl_idname == 'GP2DMorphsNodeNonValueSocket':  #The socket connected to is either the X or Y input, so update the control
    #         ctrl_skt = link.from_socket
    #         while ctrl_skt.is_linked and ctrl_skt.links[0].from_node.bl_rna.name == 'Reroute':
    #             ctrl_skt = ctrl_skt.links[0].from_socket
    #         if ctrl_skt and issubclass(type(ctrl_skt.node),GP2DMorphsNodeControlBase):
    #             self.update_props_from_control(self_skt,ctrl_skt.node,ctrl_skt)
    #             self.update_drivers()
    #I don't like using this because update() is called on all nodes, not just the nodes that are changed so it's slower since unnecessary nodes are updated. Should replace with the above instert_link if it can work
    def update(self):
        self.update_props()
        self.update_drivers()
    
    def update_props(self):
        props = self.props
        xy_sockets = self.get_connected_xy_sockets()
        skt_x = xy_sockets[0]
        if skt_x is not None:
            ctrl_node_x = skt_x.node
            props.control_armature_x = ctrl_node_x.obj
            props.control_bone_name_x = ctrl_node_x.bone_name
            if skt_x.bl_idname == 'GP2DMorphsNodeTransformChannelSocket':
                props.control_bone_transform_type_x = skt_x.default_value
                props.control_range_start_x, props.control_range_end_x = skt_x.range_start, skt_x.range_end
                props.control_range_flip_x = skt_x.range_flip
        skt_y = xy_sockets[1]
        if skt_y is not None:
            ctrl_node_y = skt_y.node
            props.control_armature_y = ctrl_node_y.obj
            props.control_bone_name_y = ctrl_node_y.bone_name
            if skt_y.bl_idname == 'GP2DMorphsNodeTransformChannelSocket':
                props.control_bone_transform_type_y = skt_y.default_value
                props.control_range_start_y, props.control_range_end_y = skt_y.range_start, skt_y.range_end
                props.control_range_flip_y = skt_y.range_flip

    def update_props_from_control(self,self_skt,ctrl_node,ctrl_skt):
        if self_skt and ctrl_node and ctrl_skt:
            props = self.props
            if self_skt.identifier[-1] == 'x':
                props.control_armature_x = ctrl_node.obj
                props.control_bone_name_x = ctrl_node.bone_name
                if ctrl_skt.bl_idname == 'GP2DMorphsNodeTransformChannelSocket':
                    props.control_bone_transform_type_x = ctrl_skt.default_value
                    props.control_range_start_x, props.control_range_end_x = ctrl_skt.range_start, ctrl_skt.range_end
                    props.control_range_flip_x = ctrl_skt.range_flip
            else:                       #Y
                props.control_armature_y = ctrl_node.obj
                props.control_bone_name_y = ctrl_node.bone_name
                if ctrl_skt.bl_idname == 'GP2DMorphsNodeTransformChannelSocket':
                    props.control_bone_transform_type_y = ctrl_skt.default_value
                    props.control_range_start_y, props.control_range_end_y = ctrl_skt.range_start, ctrl_skt.range_end
                    props.control_range_flip_y = ctrl_skt.range_flip

    def update_drivers(self):
        pass    #Define in children

    def get_ctrlskt_connected_to(self,input_name):
        from ..Input.node_ControlBase import GP2DMorphsNodeControlBase  #I don't like this any more than you do
        connected_skt = self.inputs[input_name].connected_socket
        if connected_skt is not None:
            input_node = connected_skt.node
            if issubclass(type(input_node),GP2DMorphsNodeControlBase):
                return connected_skt
        return None

    def get_connected_xy_sockets(self):
        return (self.get_ctrlskt_connected_to("input_x"),self.get_ctrlskt_connected_to("input_y"))
    
    def has_connected_xy_socket(self):
        connected_skt_y = self.get_ctrlskt_connected_to("input_x")
        if connected_skt_y is not None:
            return True
        connected_skt_y = self.get_ctrlskt_connected_to("input_y")
        if connected_skt_y is not None:
            return True
        return False
    
    def get_control_bones(self):
        return (self.props.control_armature_x.pose.bones.get(self.props.control_bone_name_x) if self.props.control_armature_x else None,
                self.props.control_armature_y.pose.bones.get(self.props.control_bone_name_y) if self.props.control_armature_y else None)
    
    def get_morph_name(self):
        if self.label != "":
            return self.label
        n = ""
        if self.obj is not None:
            n += self.obj.name
        for nli in self.name_list:
            if nli.name != '':
                n += nli.name
                break
        return n

    def add_to_name_list(self,given_name=''):
        context = bpy.context
        node_tree = context.space_data.edit_tree
        self.name_list.add()
        if given_name != '':
            self.name_list[len(self.name_list)-1].name = given_name
            return True
        return False

    def get_selected_name(self):
        n = ''
        if self.list_index < len(self.name_list):
            n = self.name_list[self.list_index].name
        if n == '':
            return self.get_first_nonblank_name()
        return n
        
    def get_first_nonblank_name(self):
        for name_item in self.name_list:
            if name_item.name != '':
                return name_item.name
        return ''

def register():
    bpy.utils.register_class(GP2DMorphsNodeMorphBase)


def unregister():
    bpy.utils.unregister_class(GP2DMorphsNodeMorphBase)