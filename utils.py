import bpy

def node_is_morph(node):
    return node.bl_idname == "GP2DMorphsNodeGP2DMorph" or node.bl_idname == "GP2DMorphsNodeBoneMorph"

def node_is_control(node):
    return node.bl_idname == "GP2DMorphsNodeControlBase" or node.bl_idname == "GP2DMorphsNodeControlLocation" or node.bl_idname == "GP2DMorphsNodeControlRotation"

def get_tree(context=None):
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
    return None

def get_main_morph_node(context=None):
    if context is None:
        context = bpy.context
    if (n := context.active_node) and node_is_morph(n):
        return n
    for n in context.selected_nodes:
        if node_is_morph(n): 
            return n
    return None

def get_main_gp_morph_node(context=None):
    if context is None:
        context = bpy.context
    if (n := context.active_node) and n.bl_idname == "GP2DMorphsNodeGP2DMorph":
        return n
    for n in context.selected_nodes:
        if n.bl_idname == "GP2DMorphsNodeGP2DMorph": 
            return n
    return None