import bpy
from bpy.props import PointerProperty
from ...props import GP2DMORPHS_EditorProps
from ._runtime import cache_node_dependants, cache_socket_links
from ._runtime import runtime_info


# some method comes from rigging_nodes
class NodeTreeBase(bpy.types.NodeTree):
    def get_other_socket(self, socket):
        '''
        Returns connected socket

        It takes O(len(nodetree.links)) time to iterate thought the links to check the connected socket
        To avoid doing the look up every time, the connections are cached in a dictionary
        The dictionary is emptied whenever a socket/connection/node changes in the nodetree
        '''
        # accessing links Takes O(len(nodetree.links)) time.
        _nodetree_socket_connections = cache_socket_links.setdefault(self, {})
        _connected_socket = _nodetree_socket_connections.get(socket, None)

        if _connected_socket:
            return _connected_socket

        socket = socket
        if socket.is_output:
            while socket.links and socket.links[0].to_node.bl_rna.name == 'Reroute':
                socket = socket.links[0].to_node.outputs[0]
            if socket.links:
                _connected_socket = socket.links[0].to_socket
        else:
            while socket.links and socket.links[0].from_node.bl_rna.name == 'Reroute':
                socket = socket.links[0].from_node.inputs[0]
            if socket.links:
                _connected_socket = socket.links[0].from_socket

        cache_socket_links[self][socket] = _connected_socket
        return _connected_socket

    def update(self):
        '''Called when the nodetree sockets or links change, socket pair cache is cleared here'''
        if not runtime_info['executing']:
            if self in cache_socket_links:
                del cache_socket_links[self]
            # if self in cache_tree_portals:
            #     del cache_tree_portals[self]
            if self in cache_node_dependants:
                del cache_node_dependants[self]
        else:
            print('TRIED TO UPDATE TREE, BUT ITS EXECUTING')
        # change the socket of the reroute nodes
        # for node in self.nodes:
        #     if node.bl_idname == 'NodeReroute':
        #         connected = self.get_other_socket(node.inputs[0])
        #         if connected and connected.bl_idname != node.inputs[0].bl_idname:
        #             new_input = node.inputs.new(connected.bl_idname, '')
        #             # new_input.init_from_socket(connected.node, connected)
        #             new_output = node.outputs.new(connected.bl_idname, '')
        #             # new_output.init_from_socket(connected.node, connected)
        #             self.relink_socket(node.inputs[0], new_input)
        #             self.relink_socket(node.outputs[0], new_output)

        #             node.inputs.remove(node.inputs[0])
        #             node.outputs.remove(node.outputs[0])

    def relink_socket(self, old_socket, new_socket):
        '''Utility function to relink sockets'''
        if not old_socket.is_output and not new_socket.is_output and old_socket.links:
            self.links.new(old_socket.links[0].from_socket, new_socket)
            self.links.remove(old_socket.links[0])
        elif old_socket.is_output and new_socket.is_output and old_socket.links:
            links = list(old_socket.links[:])
            for link in links:
                self.links.new(new_socket, link.to_socket)
                # self.links.remove(link)

    def execute(self, context):
        pass


class GP2DMorphsNodeTree(NodeTreeBase):
    bl_idname = 'GP2DMorphsNodeTree'
    bl_label = 'GP Morphs Node Editor'
    bl_icon = 'GP_MULTIFRAME_EDITING'

    gp2dmorphs_editor_props : PointerProperty(
        type=GP2DMORPHS_EditorProps
    )


class GP2DMorphsNodeTreeGroup(NodeTreeBase):
    bl_idname = 'GP2DMorphsNodeTreeGroup'
    bl_label = "GP2DMorphs Node (groups)"
    bl_icon = 'NODETREE'

    @classmethod
    def poll(cls, context):
        return False


        

def register():
    bpy.utils.register_class(GP2DMorphsNodeTree)
    bpy.utils.register_class(GP2DMorphsNodeTreeGroup)


def unregister():
    bpy.utils.unregister_class(GP2DMorphsNodeTree)
    bpy.utils.unregister_class(GP2DMorphsNodeTreeGroup)
