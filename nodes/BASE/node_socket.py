import bpy
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty, EnumProperty, StringProperty
from mathutils import Vector

from ._runtime import cache_socket_links, cache_socket_variables
from..Output.node_MorphBase import GP2DMorphsNodeMorphBase


# some method from rigging_node
class SocketBase():
    compatible_sockets = []

    # reroute method
    ###########################
    @property
    def connected_socket(self):
        '''
        Returns connected socket

        It takes O(len(nodetree.links)) time to iterate thought the links to check the connected socket
        To avoid doing the look up every time, the connections are cached in a dictionary
        The dictionary is emptied whenever a socket/connection/node changes in the nodetree
        accessing links Takes O(len(nodetree.links)) time.
        '''

        def set_valid(socket, is_valid=False):
            if socket.links:
                socket.links[0].is_valid = is_valid

        _nodetree_socket_connections = cache_socket_links.setdefault(self.id_data, {})
        _connected_socket = _nodetree_socket_connections.get(self, None)

        if _connected_socket:
            return _connected_socket

        socket = self

        if socket.is_output:
            while socket.is_linked and socket.links[0].to_node.bl_rna.name == 'Reroute':
                socket = socket.links[0].to_node.outputs[0]
            if socket.is_linked:
                _connected_socket = socket.links[0].to_socket

        else:
            while socket.is_linked and socket.links[0].from_node.bl_rna.name == 'Reroute':
                socket = socket.links[0].from_socket
            if socket.is_linked:
                _connected_socket = socket.links[0].from_socket

                # set link
                if not socket.is_socket_compatible(_connected_socket):
                    set_valid(socket, False)

        cache_socket_links[self.id_data][self] = _connected_socket

        return _connected_socket
    
    def get_linked_inputs(self,out=None):
        if out is None:
            out = self
        skts = []
        for l in out.links:
            if l.to_node.bl_rna.name == 'Reroute':
                for o in l.to_node.outputs:
                    skts += self.get_linked_inputs(o)
            else:
                skts.append(l.to_socket)
        return skts

    # UI display
    ###################

    # Link valid
    def is_socket_compatible(self, other_socket):
        if other_socket.bl_idname == 'NodeSocketVirtual':
            return True
        return other_socket.bl_idname == self.bl_idname or other_socket.bl_idname in self.compatible_sockets

    @property
    def ui_value(self):
        '''use for output ui display'''
        val = self.get_value()
        if val is None: return 'None'

        if isinstance(val, bpy.types.Object) or isinstance(val, bpy.types.Material) or isinstance(val, bpy.types.World):
            return val.name
        elif isinstance(val, str) or isinstance(val, int):
            return f'{val}'
        elif isinstance(val, float):
            return f'{round(val, 2)}'
        elif isinstance(val, tuple) or isinstance(val, Vector):
            d_val = [round(num, 2) for num in list(val)]
            return f'{d_val}'
        elif isinstance(val, bool):
            return 'True' if val else 'False'
        else:
            return f'{val}'

    # set and get method
    #########################

    def set_value(self, value):
        '''Sets the value of an output socket'''
        cache_socket_variables.setdefault(self.id_data, {})[self] = value

    def get_self_value(self):
        '''returns the stored value of an output socket'''
        val = cache_socket_variables.setdefault(self.id_data, {}).get(self, None)
        return val

    def get_value(self):
        '''
        if the socket is an output it returns the stored value of that socket
        if the socket is an input:
            if it's connected, it returns the value of the connected output socket
            if it's not it returns the default value of the socket
        '''
        _value = ''
        if not self.is_output:
            connected_socket = self.connected_socket

            if not connected_socket:
                _value = self.default_value
            else:
                _value = connected_socket.get_self_value()
        else:
            _value = self.get_self_value()

        return _value

def update_node(self, context):
    try:
        self.node.execute_tree()
    except Exception as e:
        print(e)

class GP2DMorphsNodeSocket(bpy.types.NodeSocket, SocketBase):
    bl_idname = 'GP2DMorphsNodeSocket'
    bl_label = 'GP2DMorphsNodeSocket'

    socket_color : FloatVectorProperty(default=(0.5,0.5,0.5))

    compatible_sockets = []
    text : StringProperty(default='')
    default_value : IntProperty(default=0, update=update_node)

    @property
    def display_name(self):
        label = self.name
        if self.text != '':
            label = self.text
        # if self.is_output:
        #     label += ': ' + self.ui_value
        return label

    def draw(self, context, layout, node, text):
        col = layout.column(align=1)
        if self.is_linked or self.is_output:
            layout.label(text=self.display_name)
        else:
            col.prop(self, 'default_value', text=self.display_name)  # column for vector

    def draw_color(self, context, node):
        return (self.socket_color[0],self.socket_color[1],self.socket_color[2],1)

# Socket Classes
################
# Input socket whose property is linked to a property in the node's property group. The name of the socket needs to be the same as the name of the linked property.
class GP2DMorphsNodeLinkedPropSocket(GP2DMorphsNodeSocket):
    bl_idname = 'GP2DMorphsNodeLinkedPropSocket'
    bl_label = 'GP2DMorphsNodeLinkedPropSocket'
    
    def draw(self, context, layout, node, text):
        col = layout.column(align=1)
        if self.is_linked or self.is_output:
            layout.label(text=self.display_name)
        else:
            col.prop(self.node.props, self.name, text=self.display_name)  # column for vector

    def get_value(self):
        '''
        if the socket is an output it returns the stored value of that socket
        if the socket is an input:
            if it's connected, it returns the value of the connected output socket
            if it's not, it returns the value of the linked property
        '''
        _value = ''
        if self.is_output:      #Output
            _value = self.get_self_value()
        else:                   #Input
            connected_socket = self.connected_socket
            if connected_socket:
                _value = connected_socket.get_self_value()
            else:
                _value = getattr(self.node.props,self.name)
            

        return _value

    def set_value(self, value):
        setattr(self.node.props,self.name,value)
        cache_socket_variables.setdefault(self.id_data, {})[self] = value   #Not sure we need this. 

class GP2DMorphsNodeNonValueSocket(GP2DMorphsNodeSocket):
    bl_idname = 'GP2DMorphsNodeNonValueSocket'
    bl_label = 'GP2DMorphsNodeNonValueSocket'

    compatible_sockets = ['GP2DMorphsNodeTransformChannelSocket']

    def __init__(self):
        super().__init__()
        self.display_shape = 'DIAMOND'

    def draw(self, context, layout, node, text):
        layout.label(text=self.display_name)

def update_trans_skt(self,context):
    ax = self.default_value[-1]
    self.socket_color=(context.preferences.themes[0].user_interface.axis_x if ax == 'X' else 
                    context.preferences.themes[0].user_interface.axis_y if ax == 'Y' else 
                    context.preferences.themes[0].user_interface.axis_z if ax == 'Z' else 
                    (0,0,0))
    self.node.update_shape()
    update_attached_morphs(self,context)

def update_attached_morphs(self,context):
    linked_input_skts = self.get_linked_inputs()
    for list_input in linked_input_skts:
        skt_node = list_input.node
        if skt_node and issubclass(type(skt_node),GP2DMorphsNodeMorphBase):
            skt_node.update_props_from_control(list_input,self.node,self)
            skt_node.update_drivers()

class GP2DMorphsNodeTransformChannelSocket(GP2DMorphsNodeSocket):
    bl_idname = 'GP2DMorphsNodeTransformChannelSocket'
    bl_label = 'GP2DMorphsNodeTransformChannelSocket'

    compatible_sockets = [GP2DMorphsNodeNonValueSocket.bl_idname]
    default_value : EnumProperty(name="Transform Channel", 
                                 items = [('LOC_X','X Location','','EMPTY_ARROWS',0),('LOC_Y','Y Location','','EMPTY_ARROWS',1),('LOC_Z','Z Location','','EMPTY_ARROWS',2),None,
                                          ('ROT_X','X Rotation','','ORIENTATION_GIMBAL',3),('ROT_Y','Y Rotation','','ORIENTATION_GIMBAL',4),('ROT_Z','Z Rotation','','ORIENTATION_GIMBAL',5),None,
                                          ('SCALE_X','X Scale','','MOD_LENGTH',6),('SCALE_Y','Y Scale','','MOD_LENGTH',7),('SCALE_Z','Z Scale','','MOD_LENGTH',8)
                                          ],
                                #  items = [(ot.identifier, ot.name, ot.description, 'EMPTY_ARROWS' if ot.identifier[0] == 'L' else 'ORIENTATION_GIMBAL' if ot.identifier[0] == 'R' else 'MOD_LENGTH', ot.value) for ot in bpy.types.DriverTarget.bl_rna.properties['transform_type'].enum_items 
                                #           if ot.identifier != 'ROT_W' and ot.identifier != 'SCALE_AVG'], 
                                 update=update_trans_skt,description="Transform channel to use")
    range_start : FloatProperty(name="Range Start",update=update_attached_morphs,default=180, 
                                                                        description="The angle (in degrees) that will represent '0' in the control driver")
    range_end : FloatProperty(name="Range End",update=update_attached_morphs,default=-180, 
                                                                        description="The angle (in degrees) that will represent '1' in the control driver")
    range_flip : BoolProperty(name="Range Flip",update=update_attached_morphs,default=True,description="Rotation Range should go the opposite way from start to end")
    
    def init(self):
        self.display_shape = 'DIAMOND'
        update_trans_skt(self,bpy.context)

    #This seems to get called every frame V
    # def __init__(self):
    #     self.display_shape = 'DIAMOND'

    def draw(self, context, layout, node, text):
        row = layout.row(align=True)
        op_props = row.operator("gp2dmorphs.remove_transform_output",text='',icon='PANEL_CLOSE')
        op_props.node_name, op_props.socket_name = self.node.name,self.name
        row.prop(self, 'default_value',text='')
    #To be called from the node
    def draw_buttons_ext(self, context, layout, ctrl_defined=True):
        box = layout.box()
        box.prop(self, "default_value",text='')
        trans_type = self.default_value[0]
        if trans_type == 'R':   #Rotation
            row = box.row(align=True)
            if ctrl_defined:
                op_props = row.operator("gp2dmorphs.set_ctrl_skt_range",text='',icon='DUPLICATE')
                op_props.node_name, op_props.socket_name, op_props.control_armature_name, op_props.control_bone_name = self.node.name,self.name,self.node.obj.name,self.node.bone_name
                op_props.index = 0
            row.prop(self, "range_start",text="")
            op_props = row.operator("gp2dmorphs.switch_ctrl_skt_range_values",text='', icon='UV_SYNC_SELECT')
            op_props.node_name, op_props.socket_name = self.node.name,self.name
            row.prop(self, "range_end",text="")
            if ctrl_defined:
                op_props = row.operator("gp2dmorphs.set_ctrl_skt_range",text='',icon='DUPLICATE')
                op_props.node_name, op_props.socket_name, op_props.control_armature_name, op_props.control_bone_name = self.node.name,self.name,self.node.obj.name,self.node.bone_name
                op_props.index = 1
            box.prop(self,"range_flip",text="Flip Direction",icon = 'LOOP_BACK' if self.range_flip else 'LOOP_FORWARDS')

class GP2DMorphsNodeSocketIntOverZero(GP2DMorphsNodeSocket, SocketBase):
    bl_idname = 'GP2DMorphsNodeSocketIntOverZero'
    bl_label = 'GP2DMorphsNodeSocketIntOverZero'

    socket_color = (0, 0.9, 0.1)
    compatible_sockets = [GP2DMorphsNodeLinkedPropSocket.bl_idname]
    default_value: IntProperty(default=0, update=update_node, min=1)

classes = (
    GP2DMorphsNodeSocket,
    GP2DMorphsNodeLinkedPropSocket,
    GP2DMorphsNodeTransformChannelSocket,
    GP2DMorphsNodeNonValueSocket,
    GP2DMorphsNodeSocketIntOverZero,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
