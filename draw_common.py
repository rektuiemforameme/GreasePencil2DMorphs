from math import floor
from .preferences import get_pref
#Defined Array Frame shortcuts
def draw_def_array_frame_shortcuts(context, layout, props):
    box = layout.box()
    dw, dh = props.def_frames_w, props.def_frames_h
    direction_horizontal = props.mirror_direction == 'LEFT' or props.mirror_direction == 'RIGHT'
    if not props.mirror or not get_pref().use_custom_draw_def_grid_mirrored or (direction_horizontal and dw == 1) or (not direction_horizontal and dh == 1):
        col = box.column(align=True)
        for y in range(dh-1,-1,-1):
            row = col.row(align=True)
            for x in range(dw):
                f = props.def_frame_start + y*(dw+1) + x   #The frame that this button and position in the defined 'array' represents and links to
                op_props = row.operator("GP2DMORPHS.set_frame_by_defined_pos", text = str(f), depress = f==context.scene.frame_current)
                op_props.pos_x, op_props.pos_y = x, y
                op_props.def_frame_start, op_props.def_frames_w = props.def_frame_start, dw
    elif direction_horizontal:
        odd_cols = props.def_frames_w % 2 == 1
        row = box.row()
        col_l = row.column(align=True)
        col_c = row.column(align=True) if odd_cols else col_l
        col_r = row.column(align=True)
        for y in range(dh-1,-1,-1):
            row_l = col_l.row(align=True)
            row_c = col_c.row(align=True)  if odd_cols else row_l
            row_r = col_r.row(align=True)
            for x in range(dw):
                grid_side = -1 if (x < floor(dw/2)) else 1 if x >= (dw/2) else 0
                row = row_l if grid_side == -1 else row_r if grid_side == 1 else row_c
                f = props.def_frame_start + y*(dw+1) + x   #The frame that this button and position in the defined 'array' represents and links to
                if ((props.mirror_direction == 'LEFT' and grid_side == -1) or
                                          (props.mirror_direction == 'RIGHT' and grid_side == 1)):
                    op_props = row.operator("GP2DMORPHS.set_frame_by_defined_pos", text = str(f), icon = 'MOD_MIRROR', depress = f==context.scene.frame_current)
                else:
                    op_props = row.operator("GP2DMORPHS.set_frame_by_defined_pos", text = str(f), depress = f==context.scene.frame_current)
                op_props.pos_x, op_props.pos_y = x, y
                op_props.def_frame_start, op_props.def_frames_w = props.def_frame_start, dw
    else:               # Mirror Up or Down
        col = box.column(align=True)
        for y in range(dh-1,-1,-1):
            if (dh%2==1 and y == floor(dh/2)) or y == floor(dh/2)-1:
                col = box.column(align=True)
            row = col.row(align=True)
            for x in range(dw):
                f = props.def_frame_start + y*(dw+1) + x   #The frame that this button and position in the defined 'array' represents and links to
                if ((props.mirror_direction == 'DOWN' and y < floor(dh/2)) or
                                          (props.mirror_direction == 'UP' and y >= (dh/2))):
                    op_props = row.operator("GP2DMORPHS.set_frame_by_defined_pos", text = str(f), icon = 'MOD_MIRROR', depress = f==context.scene.frame_current)
                else:
                    op_props = row.operator("GP2DMORPHS.set_frame_by_defined_pos", text = str(f), depress = f==context.scene.frame_current)
                op_props.pos_x, op_props.pos_y = x, y
                op_props.def_frame_start, op_props.def_frames_w = props.def_frame_start, dw

def draw_options_mirror(context, layout, props):
    box = layout.box()
    row = box.row()
    row.prop(props, "mirror")
    row.label(icon='MOD_MIRROR')
    if props.mirror:
        split = box.split(factor=0.4)
        col_labels = split.column()
        col_props = split.column()
        # Direction
        direction_error = ('H' if ((props.mirror_direction=='LEFT' or props.mirror_direction=='RIGHT') and props.def_frames_w == 1) else
                            'V' if ((props.mirror_direction=='UP' or props.mirror_direction=='DOWN') and props.def_frames_h == 1) else
                            '')
        if direction_error != '':
            col_labels.alert = True
            col_props.alert = True
        col_labels.label(text="Mirror Direction")
        col_props.prop(props, 'mirror_direction', text='')
        if direction_error != '':
            box.label(text="Horizontal mirrors won't work with vertical morphs" if direction_error == 'H' else "Vertical mirrors won't work with horizontal morphs", icon='ERROR')
            split = box.split(factor=0.4)
            col_labels = split.column()
            col_props = split.column()
        # Axis
        col_labels.label(text="Flip Axis")
        row = col_props.row(align=True)
        # Pivot Point
        col_mode_labels = col_labels.column(align=True)
        col_mode_props = col_props.column(align=True)
        row.prop(props, 'mirror_use_axis_x', text='X', toggle=True)
        row.prop(props, 'mirror_use_axis_y', text='Y', toggle=True)
        row.prop(props, 'mirror_use_axis_z', text='Z', toggle=True)
        col_mode_labels.label(text="Pivot Point")
        col_mode_props.prop(props, 'mirror_point_mode', text='')
        if props.mirror_point_mode == 'CUSTOM':
            for i,v in enumerate(('x','y','z')):
                if props['mirror_use_axis_' + v]:
                    col_mode_props.prop(props, 'mirror_custom_point',text=v.upper(),index=i)
        # Layer Pairs
        col_labels.label(text="")   #Spacer
        col_props.prop(props, 'mirror_paired_layers', text='Paired Layers')
        
def draw_options_interpolate(context, layout, props, node_name = ''):
    box = layout.box()
    col = box.column()
    row = col.row()
    row.prop(props, "interpolate", text="Interpolate")
    row.label(icon='IPO_EASE_IN_OUT')
    if props.interpolate:
        row = col.row(align=True)
        row.label(icon='IPO_EASE_IN_OUT')
        if node_name != '':
            row.operator_menu_enum("GP2DMORPHS.set_all_interp_types","type", text="Set All").node_name = node_name
        else:
            row.operator_menu_enum("GP2DMORPHS.set_all_interp_types","type", text="Set All")
        if props.interp_type_left != 'LINEAR' or props.interp_type_right != 'LINEAR' or props.interp_type_up != 'LINEAR' or props.interp_type_down != 'LINEAR':
            if node_name != '':
                row.operator_menu_enum("GP2DMORPHS.set_all_interp_easings","easing", text="Set All").node_name = node_name
            else:
                row.operator_menu_enum("GP2DMORPHS.set_all_interp_easings","easing", text="Set All")
        
        if props.gen_frames_h > 1:
            row = col.row(align=True)
            row.label(text="",icon='TRIA_UP')
            row.prop(props, "interp_type_up", text="")
            if props.interp_type_up == 'CUSTOM':
                row.label(text=":(",icon='ERROR')
            elif props.interp_type_up != 'LINEAR':
                row.prop(props, "interp_easing_up", text="")

            if props.def_frames_h > 2:
                row = col.row(align=True)
                row.label(text="",icon='TRIA_DOWN')
                row.prop(props, "interp_type_down", text="")
                if props.interp_type_down == 'CUSTOM':
                    row.label(text=":(",icon='ERROR')
                elif props.interp_type_down != 'LINEAR':
                    row.prop(props, "interp_easing_down", text="")
        if props.gen_frames_w > 1:
            if props.def_frames_w > 2:
                row = col.row(align=True)
                row.label(text="",icon='TRIA_LEFT')
                row.prop(props, "interp_type_left", text="")
                if props.interp_type_left == 'CUSTOM':
                    row.label(text=":(",icon='ERROR')
                elif props.interp_type_left != 'LINEAR':
                    row.prop(props, "interp_easing_left", text="")

            row = col.row(align=True)
            row.label(text="",icon='TRIA_RIGHT')
            row.prop(props, "interp_type_right", text="")
            if props.interp_type_right == 'CUSTOM':
                row.label(text=":(",icon='ERROR')
            elif props.interp_type_right != 'LINEAR':
                row.prop(props, "interp_easing_right", text="")
                
def draw_options_stroke_order(context, layout, props):
    box = layout.box()
    box.prop(props, "stroke_order_changes", text="Stroke Order Changes")
    if props.stroke_order_changes:
        box.label(text="Order change offset factor")
        row = box.row(align=True)
        h,v = props.def_frames_w > 1, props.def_frames_h > 1
        if h:
            row.prop(props, "stroke_order_change_offset_factor_horizontal", text="H" if v else '')
        if v:
            row.prop(props, "stroke_order_change_offset_factor_vertical", text="V" if h else '')