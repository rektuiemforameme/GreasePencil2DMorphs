import bpy
from bpy.props import StringProperty
from ._runtime import (runtime_info, cache_node_dependants, cache_executed_nodes,
                       logger, MeasureTime)
from ...utils import get_flipped_name


# some method comes from rigging_nodes
class GP2DMorphsNodeBase(bpy.types.Node):
    bl_label = "GP2DMorphsNodeBase"

    last_ex_id: StringProperty()

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname in {'GP2DMorphsNodeTree', 'GP2DMorphsNodeTreeGroup'}

    ## BASE METHOD
    #########################################

    def copy(self, node):
        self.flip_names()
        self.width = node.width

    def free(self):
        pass

    def clean_up(self):
        self.free()

    ## INITIAL METHOD
    #########################################

    def create_input(self, socket_type, socket_name, socket_label, socket_color=None, default_value=None, editable=True):
        if self.inputs.get(socket_name):
            return None

        input = self.inputs.new(socket_type, socket_name)
        input.text = socket_label
        input.editable=editable
        if socket_color: input.socket_color = socket_color
        if default_value: input.default_value = default_value
        return input

    def remove_input(self, socket_name):
        input = self.inputs.get(socket_name)
        if input:
            self.inputs.remove(input)

    def create_output(self, socket_type, socket_name, socket_label, socket_color=None, default_value=None):
        if self.outputs.get(socket_name):
            return None

        output = self.outputs.new(socket_type, socket_name)
        output.text = socket_label
        if socket_color: output.socket_color = socket_color
        if default_value: output.default_value = default_value
        return output

    def remove_output(self, socket_name):
        output = self.outputs.get(socket_name)
        if output:
            self.outputs.remove(output)

    ## STATE METHOD
    #########################################

    def draw_buttons(self, context, layout):
        pass

    ## UPDATE METHOD
    #########################################

    # This is build-in method
    def update(self):
        if runtime_info['updating'] is True:
            return

    def get_dependant_nodes(self):
        #returns the nodes connected to the inputs of this node
        dep_tree = cache_node_dependants.setdefault(self.id_data, {})

        if self in dep_tree:
            return dep_tree[self]
        nodes = []
        for input in self.inputs:
            connected_socket = input.connected_socket
            if connected_socket and connected_socket not in nodes:
                nodes.append(connected_socket.node)
        dep_tree[self] = nodes
        return nodes
    #returns a pseudo dictionary (actually a list of [output_skt,[input_skts]]) 
    def get_linked_inputs(self,n=None,skts_fake_dict=[],is_reroute=False):
        if n is None:
            n = self
        i = len(skts_fake_dict)
        for out in n.outputs:
            if not is_reroute:
                skts_fake_dict.append([out,[]])
            for l in out.links:
                if l.to_node.bl_rna.name == 'Reroute':
                    self.get_linked_inputs(l.to_node,skts_fake_dict,True)
                else:
                    skts_fake_dict[i][1].append(l.to_socket)
            if not is_reroute:
                i += 1
        return skts_fake_dict

    def path_to_node(self, path):
        node_tree = bpy.data.node_groups.get(path[0])
        for x in path[1:-1]:
            node_tree = node_tree.nodes.get(x).node_tree
        node = node_tree.nodes.get(path[-1])
        return node

    def get_tree(self,context=None):
        if context is None:
            context = bpy.context
        if context.area.ui_type == 'GP2DMorphsNodeTree':
            return context.space_data.edit_tree
        else:
            areas  = [area for area in context.window.screen.areas if area.ui_type == 'GP2DMorphsNodeTree' and area.spaces.active.node_tree is not None]
            for a in areas:
                if a is not None:
                    node_tree = a.spaces.active.edit_tree
                    if node_tree is not None:
                        return node_tree

    def flip_names(self):
        n = get_flipped_name(self.label)
        if n is not False:
            self.label = n
            return True
        return False

def register():
    bpy.utils.register_class(GP2DMorphsNodeBase)


def unregister():
    bpy.utils.unregister_class(GP2DMorphsNodeBase)
