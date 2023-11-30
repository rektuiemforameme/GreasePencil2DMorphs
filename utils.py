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
    if hasattr(context,'active_node') and (n := context.active_node) and node_is_morph(n):
        return n
    if hasattr(context,'selected_nodes') and context.selected_nodes:
        for n in context.selected_nodes:
            if node_is_morph(n): 
                return n
    return None

def get_main_gp_morph_node(context=None):
    if context is None:
        context = bpy.context
    if hasattr(context,'active_node') and (n := context.active_node) and n.bl_idname == "GP2DMorphsNodeGP2DMorph":
        return n
    if hasattr(context,'selected_nodes') and context.selected_nodes:
        for n in context.selected_nodes:
            if n.bl_idname == "GP2DMorphsNodeGP2DMorph": 
                return n
    return None
#Returns the flipped name, or False if it can't be flipped
def get_flipped_name(n):
    if n[-1] == 'L':                            #Ends with L
        return n[:-1] + 'R'
    elif n[-1] == 'R':                          #Ends with R
        return n[:-1] + 'L'
    elif len(n) < 5:            #Not enough characters to have name.001 naming
        return False
    elif n[-4] == '.' and n[-3:].isdigit():     #Ends with numbered naming, eg .001 .002 etc
        if n[-5] == 'L':
            return n[:-5] + 'R' + n[-4:]
        elif n[-5] == 'R':
            return n[:-5] + 'L' + n[-4:]
    
    return False