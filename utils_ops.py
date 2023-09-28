import bpy
#This function is thanks to Tomreggae from https://blender.stackexchange.com/questions/204636/moving-gpencil-frames-in-time-with-python-causes-viewport-issues
def refresh_GP_dopesheet(context=None) :  
    if context is None:
        context = bpy.context
    #dirty way to force blender to refresh frames indices in grease pencil dopesheet
    if context.object.type == 'GPENCIL' :
        cur_areatype = str(context.area.type)
        context.area.type = 'DOPESHEET_EDITOR'
        cur_space_mode = str(context.area.spaces[0].mode)
        context.area.spaces[0].mode = 'GPENCIL'
        bpy.ops.action.mirror(type = 'XAXIS')
        bpy.ops.action.mirror(type = 'XAXIS')
        context.area.spaces[0].mode = cur_space_mode
        context.area.type = cur_areatype

#This function is thanks to scurest from https://blender.stackexchange.com/questions/7358/python-performance-with-blender-operators. I just adjusted it to take parameters.
def run_ops_without_view_layer_update(func,*args):
    from bpy.ops import _BPyOpsSubModOp

    view_layer_update = _BPyOpsSubModOp._view_layer_update

    def dummy_view_layer_update(context):
        pass

    try:
        _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update

        func(*args)

    finally:
        _BPyOpsSubModOp._view_layer_update = view_layer_update