import bpy
import math
import bl_math
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty, EnumProperty, StringProperty
from bpy.app.handlers import persistent
from ..preferences import get_pref
from ..utils import get_tree,get_main_gp_morph_node
from ..utils_ops import run_ops_without_view_layer_update, refresh_GP_dopesheet

class GP2DMORPHS_OT_generate_2d_morphs(bpy.types.Operator):
    bl_idname = "gp2dmorphs.generate_2d_morphs"    
    bl_label = "Generate 2D Morphs"
    bl_description = "Using predefined frames made by the user, creates a 'grid' of interpolated frames and a Time Offset Modifier, Control and Driver to manipulate the frames"
    bl_options = {'UNDO'}

    props_set: BoolProperty(name="props_set", default = False)
    # Frames
    def_frame_start: IntProperty(name="def_frame_start", default = 0, description="The starting frame for the user-defined frames")
    def_frames_w: IntProperty(name="def_frames_w", default = 3, description="The width of the '2D array' of user-defined frames",min=1)
    def_frames_h: IntProperty(name="def_frames_h", default = 3, description="The height of the '2D array' of user-defined frames",min=1)
    gen_frame_start: IntProperty(name="gen_frame_start", default = 100, description="The starting frame for the generated frames")
    gen_frames_w: IntProperty(name="gen_frames_w", default = 21, description="The width of the '2D array' of generated frames",min=1)
    gen_frames_h: IntProperty(name="gen_frames_h", default = 21, description="The height of the '2D array' of generated frames",min=1)
    generate_frames: BoolProperty(name="generate_frames", default = True, description="Generate interpolated Frames from user-defined frames")
    generate_control: BoolProperty(name="generate_control", default = True, description="Generate Control Objects")
    generate_driver: BoolProperty(name="generate_driver", default = True, description="Generate Driver from Control to Generated frames")
    # Mirror
    mirror: BoolProperty(name="Mirror", default=False, description="""Duplicate and Flip user-defined frames to the opposite side of the user-defined array of morph frames. Useful for things such as head turns, so that you only need to create defined frames for the character looking from straight ahead to the right and the addon will generate the frames for looking to the left""")
    mirror_paired_layers: BoolProperty(name="Paired Layers", default=False, description="Some layers in this morph are mirror opposites of each other, and the mirror operation should treat the strokes in these layers as if they are pairs of the corresponding strokes in the paired layer. Paired layers must have the same name, with one character different at the end. For example, 'EyeL' and 'EyeR'")
    mirror_point_mode: EnumProperty(items=[('OBJ_ORIGIN', 'Object Origin', "Use this Object's Origin as the point to flip strokes across", 'OBJECT_ORIGIN', 0),
                                      ('LAYER_TRANSFORM', 'Layer Transform', "Use the first Layer's Transform as the point to flip strokes across", 'TRANSFORM_ORIGINS', 1),
                                      ('AXIS', 'Axis', "Use a Grid Axis as the point to flip strokes across", 'EMPTY_AXIS', 2),
                                      ('CUSTOM', 'Custom Point', "Use a Custom point as the point to flip strokes across", 'CON_LOCLIMIT', 3)],
                               name="Mirror Point Mode", description="")
    mirror_use_axis_x: BoolProperty(name='Mirror Axis Use X', description="Flip strokes in each mirrored frame on the X axis", default=True)
    mirror_use_axis_y: BoolProperty(name='Mirror Axis Use Y', description="Flip strokes in each mirrored frame on the Y axis", default=False)
    mirror_use_axis_z: BoolProperty(name='Mirror Axis Use Z', description="Flip strokes in each mirrored frame on the Z axis", default=False)
    mirror_direction: EnumProperty(items=[('LEFT', 'Right to Left',"Replace user-defined frames on the left side of the morph with flipped user-defined frames from the right side",'BACK', 0),
                                           ('RIGHT', 'Left to Right',"Replace user-defined frames on the right side of the morph with flipped user-defined frames from the left side",'FORWARD', 1),
                                          ('DOWN', 'Top to Bottom',"Replace user-defined frames on the bottom side of the morph with flipped user-defined frames from the top side", 'SORT_ASC', 2),
                                           ('UP', 'Bottom to Top', "Replace user-defined frames on the top side of the morph with flipped user-defined frames from the bottom side",'SORT_DESC', 3)],
                                    name="Mirror Point Mode", description="")
    mirror_custom_point : FloatVectorProperty(name="Custom Point", description="The local point to mirror strokes across", subtype='XYZ')
    # Interpolation
    interpolate: BoolProperty(name="interpolate", default = True, description="Interpolate between defined frames. Without this, the addon will not generate any new frames and just reorganize the defined frames into the positions they would be in when generated.")
    
    interp_type_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['type'].enum_items if ot.identifier != 'CUSTOM']
    interp_type_left : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the left direction")
    interp_type_right : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the right direction")
    interp_type_up : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the up direction")
    interp_type_down : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the down direction")
    interp_easing_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['easing'].enum_items if ot.identifier != 'AUTO']
    interp_easing_left : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the left direction")
    interp_easing_right : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the right direction")
    interp_easing_up : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the up direction")
    interp_easing_down : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the down direction")
    # Stroke Order
    stroke_order_changes: BoolProperty(name="Stroke Order Changes", default = False, description="The order of strokes in some frames can change. Slower, but necessary if the stroke order changes")
    stroke_order_change_offset_factor_horizontal : FloatProperty(name="Stroke Order Change Offset Factor Horizontal", default=0.5, 
                                                                        description="Factor for the distance between two frames that new interpolated stroke orders should change on the horizontal axis",
                                                                        min=0,max=1)
    stroke_order_change_offset_factor_vertical : FloatProperty(name="Stroke Order Change Offset Factor Vertical", default=0.5, 
                                                                        description="Factor for the distance between two frames that new interpolated stroke orders should change on the vertical axis",
                                                                        min=0,max=1)
    # Control
    control_type : EnumProperty(name="Control Type", items = [('OBJECT',"Object",""),('BONE',"Armature Bone","")], default='BONE', description="Type of control to use")
    control_armature_x = None
    control_armature_name_x : StringProperty(name="Control Armature X", default='',description="The armature that has the bone to use as a control for the X axis of the morph")
    control_bone_name_x : StringProperty(name="Control Bone X", default='',description="The bone to use as a control for the X axis of the morph")
    control_bone_transform_type_x : StringProperty(name="Control Bone Transform Type X", default='LOC_X',description="The transform component of the control to use for the X axis of the morph")
    control_range_start_x : FloatProperty(name="Control Range Start X", default=-180, 
                                                                        description="The value that will represent '0' in the control driver. Mostly used for rotation controls")
    control_range_end_x : FloatProperty(name="Control Range End X", default=180, 
                                                                        description="The value that will represent '1' in the control driver. Mostly used for rotation controls")
    control_range_flip_x : BoolProperty(name="Rotation Range Flip",default=False,description="Rotation Range should go counter-clockwise instead of clockwise")
    
    control_armature_y = None
    control_armature_name_y : StringProperty(name="Control Armature Y", default='',description="The armature that has the bone to use as a control for the Y axis of the morph")
    control_bone_name_y : StringProperty(name="Control Bone Y", default='',description="The bone to use as a control for the Y axis of the morph")
    control_bone_transform_type_y : StringProperty(name="Control Bone Transform Type Y", default='LOC_Y',description="The transform component of the control to use for the Y axis of the morph")
    control_range_start_y : FloatProperty(name="Control Range Start Y", default=-180, 
                                                                        description="The value that will represent '0' in the control driver. Mostly used for rotation controls")
    control_range_end_y : FloatProperty(name="Control Range End Y", default=180, 
                                                                        description="The value that will represent '1' in the control driver. Mostly used for rotation controls")
    control_range_flip_y : BoolProperty(name="Rotation Range Flip",default=False,description="Rotation Range should go counter-clockwise instead of clockwise")

    gp_obj = None
    gp_obj_name : StringProperty()
    layers = None
    layers_mirror = None    #Layers that should be mirrored
    pass_index: IntProperty(default=-2)
    use_custom_shapes : BoolProperty(name="Use Custom Shapes",default=True,description="Pose Bones will have Custom Shapes applied to them that correspond to their control")
    use_control_constraints : BoolProperty(name="Use Control Constraints",default=True,description="Knob Pose Bone will have constraints applied to it to limit its movement depending on the type of control")
    mode : StringProperty(default='ANIMATE')
    node_name: StringProperty(default='')
    node = None

    def execute(self, context):
        run_ops_without_view_layer_update(self.run,context)
        context.view_layer.update()
        return {'FINISHED'}

    def run(self,context):
        original_active_obj = context.view_layer.objects.active
        original_mode = original_active_obj.mode             #Grab the current mode so we can switch back after
        original_frame = bpy.context.scene.frame_current
        if self.node_name != '':
            node_tree = get_tree(context)
            if node_tree is None:   return {'CANCELLED'}
            self.node = node_tree.nodes.get(self.node_name)
            if self.node is None or self.node.bl_idname != 'GP2DMorphsNodeGP2DMorph':   return {'CANCELLED'}
            self.gp_obj = self.node.obj
            self.layers = [l for name_item in self.node.name_list if (name_item.name != '' and (l := self.gp_obj.data.layers.get(name_item.name)))]
            if self.mirror:
                self.layers_mirror = {l:name_item.mirror for name_item in self.node.name_list if (name_item.name != '' and (l := self.gp_obj.data.layers.get(name_item.name)))}

        if self.props_set:  #Properties have already been set. Just need to set the two pointers for controls
            self.control_armature_x = bpy.data.objects.get(self.control_armature_name_x)
            self.control_armature_y = bpy.data.objects.get(self.control_armature_name_y)
        else:               #Properties haven't been set. Use the props from the node, or the panel settings.
            if self.node:
                self.set_props(self.node.props)
                self.pass_index = self.node.get_pass_index()
                self.control_armature_x = bpy.data.objects.get(self.control_armature_name_x)
                self.control_armature_y = bpy.data.objects.get(self.control_armature_name_y)
            else:
                self.set_props(original_active_obj.gp2dmorphs_panel_settings)
        
        if self.gp_obj is None: return {'CANCELLED'}

        if self.mirror:
            pass
        if self.generate_frames:
            generate_morph_frames(self,context)
        ctrl_objs = list((None, None))
        if self.generate_control:
            trans_limits = {'L':None,'R':None,'S':None}    #Components of Loc,Rot,Scale that are needed.
            if self.gen_frames_w > 1:
                trans_type = self.control_bone_transform_type_x[0]
                trans_limits[trans_type] = {'X':None,'Y':None,'Z':None}
                trans_limits[trans_type][self.control_bone_transform_type_x[-1]] = (-0.5,0.5) if trans_type != 'R' else (self.control_range_start_x,self.control_range_end_x)
            if self.gen_frames_h > 1:
                trans_type = self.control_bone_transform_type_y[0]
                if trans_limits[trans_type] is None:
                    trans_limits[trans_type] = {'X':None,'Y':None,'Z':None}
                trans_limits[trans_type][self.control_bone_transform_type_y[-1]] = (-0.5,0.5) if trans_type != 'R' else (self.control_range_start_y,self.control_range_end_y)
            ctrl_objs[0] = get_or_create_control(self.control_type,
                                           self.gp_obj.name + self.gp_obj.data.layers.active.info + "Control" if (self.control_type=='OBJECT' or self.control_bone_name_x=='' ) else self.control_bone_name_x,
                                           self.control_armature_name_x,self.use_custom_shapes,self.use_control_constraints, trans_limits)
            ctrl_objs[1] = (get_or_create_control(self.control_type,
                                           self.gp_obj.name + self.gp_obj.data.layers.active.info + "Control" if (self.control_type=='OBJECT' or self.control_bone_name_y=='' ) else self.control_bone_name_y,
                                        self.control_armature_name_y,self.use_custom_shapes,self.use_control_constraints, trans_limits) 
                                        if self.control_armature_name_y != self.control_armature_name_x or self.control_bone_name_y != self.control_bone_name_x else ctrl_objs[0])
        else:
            ctrl_objs[0] = get_control(self.control_type,
                                           self.gp_obj.name + self.gp_obj.data.layers.active.info + "Control" if (self.control_type=='OBJECT' or self.control_bone_name_x=='' ) else self.control_bone_name_x,
                                           self.control_armature_name_x)
            ctrl_objs[1] = get_control(self.control_type,
                                           self.gp_obj.name + self.gp_obj.data.layers.active.info + "Control" if (self.control_type=='OBJECT' or self.control_bone_name_y=='' ) else self.control_bone_name_y,
                                           self.control_armature_name_y)
            
        if self.generate_driver:
            self.generate_time_offset_and_driver(context, ctrl_objs)
        context.view_layer.objects.active = original_active_obj
        bpy.ops.object.mode_set(mode=original_mode, toggle=False)
        bpy.context.scene.frame_current = original_frame
    
    #Yes, this is a duplicate of the function below 'update_gp_time_offset_and_driver' except using self props instead of a PropertyGroup parameter. The only way around this I saw was to give the other function an ungodly number of parameters which I didn't want to do, so here we are.
    def generate_time_offset_and_driver(self, context, ctrl_objs):
        x_comp, y_comp = '',''
        if ctrl_objs[0]:
            range_start, range_end = math.radians(self.control_range_start_x), math.radians(self.control_range_end_x)
            var_x = create_driver_variable_expression("varX",self.control_bone_transform_type_x[:3],range_start,range_end,self.control_range_flip_x)
            x_comp = ("+round(" + var_x + "*" + str(self.gen_frames_w-1) + ")")
        if ctrl_objs[1]:
            range_start, range_end = math.radians(self.control_range_start_y), math.radians(self.control_range_end_y)
            var_y = create_driver_variable_expression("varY",self.control_bone_transform_type_y[:3],range_start,range_end,self.control_range_flip_y)
            y_comp = ("+round(" + var_y + "*" + str(self.gen_frames_h-1) + ")*" + str(self.gen_frames_w+1))
        expr = (str(self.gen_frame_start) + x_comp + y_comp)    #Driver Expression. It's the same for all modifiers
        if self.pass_index > -1:    #Use the pass index
            mod_name = (self.node.get_morph_name() + 'TO') if self.node else ''
            mod = update_gp_time_offset_modifier(self.gp_obj,[l.info for l in self.layers if l],mod_name,self.pass_index,self.mode)
            driver = create_ctrl_driver(bpy.context,ctrl_objs[0],ctrl_objs[1],mod,"offset",
                                            control_transform_type_x=self.control_bone_transform_type_x,control_transform_type_y=self.control_bone_transform_type_y) #mode should be ANIMATE no matter what because the driver doesn't care for GP Morphs
            driver.expression = expr
        else:                       #Use the layer(s)
            mod_name = (self.node.get_morph_name() + 'TO') if self.node and len(self.layers) < 2 else ''
            for layer in self.layers:
                mod = update_gp_time_offset_modifier(self.gp_obj,[layer.info],mod_name,self.pass_index,self.mode)
                driver = create_ctrl_driver(bpy.context,ctrl_objs[0],ctrl_objs[1],mod,"offset",
                                                control_transform_type_x=self.control_bone_transform_type_x,control_transform_type_y=self.control_bone_transform_type_y) #mode should be ANIMATE no matter what because the driver doesn't care for GP Morphs
                driver.expression = expr
    
    #I'm not any happier about this than you are.
    def set_props(self, pg):
        self.def_frame_start=pg.def_frame_start
        self.def_frames_w=pg.def_frames_w
        self.def_frames_h=pg.def_frames_h
        self.gen_frame_start=pg.gen_frame_start
        self.gen_frames_w=pg.gen_frames_w
        self.gen_frames_h=pg.gen_frames_h
        self.generate_frames=pg.generate_frames_or_location
        self.generate_control=pg.generate_control_or_rotation
        self.generate_driver=pg.generate_driver_or_scale
        self.interpolate=pg.interpolate
        self.interp_type_left=pg.interp_type_left
        self.interp_type_right=pg.interp_type_right
        self.interp_type_up=pg.interp_type_up
        self.interp_type_down=pg.interp_type_down
        self.interp_easing_left=pg.interp_easing_left
        self.interp_easing_right=pg.interp_easing_right
        self.interp_easing_up=pg.interp_easing_up
        self.interp_easing_down=pg.interp_easing_down
        self.stroke_order_changes=pg.stroke_order_changes
        self.stroke_order_change_offset_factor_horizontal=pg.stroke_order_change_offset_factor_horizontal
        self.stroke_order_change_offset_factor_vertical=pg.stroke_order_change_offset_factor_vertical
        self.control_type=pg.control_type
        self.control_armature_name_x='' if pg.control_armature_x is None else pg.control_armature_x.name
        self.control_bone_name_x=pg.control_bone_name_x
        self.control_bone_transform_type_x=pg.control_bone_transform_type_x
        self.control_range_start_x=pg.control_range_start_x
        self.control_range_end_x=pg.control_range_end_x
        self.control_range_flip_x=pg.control_range_flip_x
        self.control_armature_name_y='' if pg.control_armature_y is None else pg.control_armature_y.name
        self.control_bone_name_y=pg.control_bone_name_y
        self.control_bone_transform_type_y=pg.control_bone_transform_type_y
        self.control_range_start_y=pg.control_range_start_y
        self.control_range_end_y=pg.control_range_end_y
        self.control_range_flip_y=pg.control_range_flip_y
        if self.node:
            self.gp_obj = self.node.obj
            self.layers = [l for name_item in self.node.name_list if (name_item.name != '' and (l := self.gp_obj.data.layers.get(name_item.name)))]
        else:
            self.gp_obj = bpy.context.view_layer.objects.active
            self.layers = [self.gp_obj.data.layers.active]      

class GP2DMORPHS_OT_convert_defined_range(bpy.types.Operator):
    bl_idname = "gp2dmorphs.convert_defined_range"
    bl_label = "Convert Defined Range"
    bl_description = "Convert the defined frames in a GP morph to a different resolution. For example, changing a 3x3 array to 5x5, or vice versa"
    bl_options = {'UNDO'}

    props_set: BoolProperty(name="props_set", default = False)

    #Frame Generation
    def_frame_start: IntProperty(name="def_frame_start", default = 0, description="The starting frame for the user-defined frames")
    def_frames_w: IntProperty(name="def_frames_w", default = 3, description="The old width of the '2D array' of user-defined frames",min=1)
    def_frames_h: IntProperty(name="def_frames_h", default = 3, description="The old height of the '2D array' of user-defined frames",min=1)
    gen_frame_start: IntProperty(name="gen_frame_start", default = 10000, description="The starting frame for the generated frames")
    gen_frames_w: IntProperty(name="gen_frames_w", default = 5, description="The new width of the '2D array' of user-defined frames",min=1)
    gen_frames_h: IntProperty(name="gen_frames_h", default = 5, description="The new height of the '2D array' of user-defined frames",min=1)
    #Interpolation
    interpolate: BoolProperty(name="interpolate", default = True, description="Interpolate between defined frames. Without this, the addon will not generate any new frames and just reorganize the defined frames into the positions they would be in when generated.")
    
    interp_type_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['type'].enum_items if ot.identifier != 'CUSTOM']
    interp_type_left : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the left direction")
    interp_type_right : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the right direction")
    interp_type_up : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the up direction")
    interp_type_down : EnumProperty(name="Interpolation Type", items = interp_type_enum, description="Interpolation Type in the down direction")
    interp_easing_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['easing'].enum_items if ot.identifier != 'AUTO']
    interp_easing_left : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the left direction")
    interp_easing_right : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the right direction")
    interp_easing_up : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the up direction")
    interp_easing_down : EnumProperty(name="Interpolation Easing", default='EASE_OUT', items = interp_easing_enum, description="Interpolation Easing in the down direction")

    stroke_order_changes: BoolProperty(name="Stroke Order Changes", default = False, description="The order of strokes in some frames can change. Slower, but necessary if the stroke order changes")
    stroke_order_change_offset_factor_horizontal : FloatProperty(name="Stroke Order Change Offset Factor Horizontal", default=0.5, 
                                                                        description="Factor for the distance between two frames that new interpolated stroke orders should change on the horizontal axis",
                                                                        min=0,max=1)
    stroke_order_change_offset_factor_vertical : FloatProperty(name="Stroke Order Change Offset Factor Vertical", default=0.5, 
                                                                        description="Factor for the distance between two frames that new interpolated stroke orders should change on the vertical axis",
                                                                        min=0,max=1)
    gp_obj = None
    gp_obj_name : StringProperty()
    layers = None
    node_tree = None
    node = None

    def execute(self, context):
        run_ops_without_view_layer_update(self.run,context)
        context.view_layer.update()
        return {'FINISHED'}

    def run(self,context):
        original_active_obj = context.view_layer.objects.active
        original_mode = original_active_obj.mode             #Grab the current mode so we can switch back after
        original_frame = bpy.context.scene.frame_current
        
        for node in context.selected_nodes:
            if node.bl_idname == "GP2DMorphsNodeGP2DMorph": 
                self.node = node
                self.gp_obj = node.obj
                if self.gp_obj is None: continue
                self.layers = [l for name_item in node.name_list if (name_item.name != '' and (l := self.gp_obj.data.layers.get(name_item.name)))]

                self.props = node.props if node else original_active_obj.gp2dmorphs_panel_settings
        
                generate_morph_frames(self,context)
                def_frame_end = def_array_pos_to_def_frame_pos(self.def_frames_w-1,self.def_frames_h-1,self.def_frame_start,self.def_frames_w)
                gen_frame_end = gen_array_pos_to_gen_frame_pos(self.gen_frames_w-1,self.gen_frames_h-1,self.gen_frame_start,self.gen_frames_w)
                for layer in self.layers:
                    for frame in layer.frames:
                        if frame.frame_number >= self.def_frame_start and frame.frame_number <= def_frame_end:      #Remove old defined frames
                            layer.frames.remove(frame)
                        elif frame.frame_number >= self.gen_frame_start and frame.frame_number <= gen_frame_end:    #Move new defined frames into position and make them keyframes
                            frame.frame_number = self.def_frame_start + (frame.frame_number - self.gen_frame_start)
                            frame.keyframe_type = 'KEYFRAME'
                    
                #Change the morph's defined frames to match
                node.inputs['def_frames_w'].set_value(self.gen_frames_w)
                node.inputs['def_frames_h'].set_value(self.gen_frames_h)
            elif node.bl_idname == "GP2DMorphsNodeBoneMorph":
                pass #Cries in Not Implemented
        
        context.view_layer.objects.active = original_active_obj
        bpy.ops.object.mode_set(mode=original_mode, toggle=False)
        bpy.context.scene.frame_current = original_frame

    def invoke(self, context, event):
        self.node_tree = get_tree(context)
        self.node = get_main_gp_morph_node(context)
        if self.node_tree is None or self.node is None:
            self.report({'ERROR'}, "No Node Tree Found")
            return
        self.set_props(self.node.props)
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Convert to:")
        row = layout.row(align=True)
        row.prop(self, "gen_frames_w", text="Width")
        row.prop(self, "gen_frames_h", text="Height")
        box = layout.box()
        col = box.column()
        col.prop(self, "interpolate", text="Interpolate")

        if self.interpolate:
            row = layout.row()
            row.label(icon='IPO_EASE_IN_OUT')
            row.operator_menu_enum("GP2DMORPHS.set_all_interp_types","type", text="Set All").node_name = self.name
            if self.interp_type_left != 'LINEAR' or self.interp_type_right != 'LINEAR' or self.interp_type_up != 'LINEAR' or self.interp_type_down != 'LINEAR':
                row.operator_menu_enum("GP2DMORPHS.set_all_interp_easings","easing", text="Set All").node_name = self.name
            
            if self.gen_frames_h > 1:
                row = layout.row()
                row.label(text="",icon='TRIA_UP')
                row.prop(self, "interp_type_up", text="")
                if self.interp_type_up == 'CUSTOM':
                    row.label(text=":(",icon='ERROR')
                elif self.interp_type_up != 'LINEAR':
                    row.prop(self, "interp_easing_up", text="")

                if self.def_frames_h > 2:
                    row = layout.row()
                    row.label(text="",icon='TRIA_DOWN')
                    row.prop(self, "interp_type_down", text="")
                    if self.interp_type_down == 'CUSTOM':
                        row.label(text=":(",icon='ERROR')
                    elif self.interp_type_down != 'LINEAR':
                        row.prop(self, "interp_easing_down", text="")
            if self.gen_frames_w > 1:
                if self.def_frames_w > 2:
                    row = layout.row()
                    row.label(text="",icon='TRIA_LEFT')
                    row.prop(self, "interp_type_left", text="")
                    if self.interp_type_left == 'CUSTOM':
                        row.label(text=":(",icon='ERROR')
                    elif self.interp_type_left != 'LINEAR':
                        row.prop(self, "interp_easing_left", text="")

                row = layout.row()
                row.label(text="",icon='TRIA_RIGHT')
                row.prop(self, "interp_type_right", text="")
                if self.interp_type_right == 'CUSTOM':
                    row.label(text=":(",icon='ERROR')
                elif self.interp_type_right != 'LINEAR':
                    row.prop(self, "interp_easing_right", text="")

        #Stroke order settings
        box = layout.box()
        box.prop(self, "stroke_order_changes", text="Stroke Order Changes")
        if self.stroke_order_changes:
            box.label(text="Order change offset factor")
            row = box.row()
            h,v = self.def_frames_w > 1, self.def_frames_h > 1
            if h:
                row.prop(self, "stroke_order_change_offset_factor_horizontal", text="Horizontal" if v else "")
            if v:
                row.prop(self, "stroke_order_change_offset_factor_vertical", text="Vertical" if h else "")
    
    @classmethod
    def poll(cls, context):
        return get_main_gp_morph_node(context) is not None
    
    #I'm not any happier about this than you are.
    def set_props(self, pg):
        self.def_frame_start=pg.def_frame_start
        self.def_frames_w=pg.def_frames_w
        self.def_frames_h=pg.def_frames_h
        self.gen_frames_w=self.def_frames_w*2-1
        self.gen_frames_h=self.def_frames_h*2-1
        self.interpolate=pg.interpolate
        self.interp_type_left=pg.interp_type_left
        self.interp_type_right=pg.interp_type_right
        self.interp_type_up=pg.interp_type_up
        self.interp_type_down=pg.interp_type_down
        self.interp_easing_left=pg.interp_easing_left
        self.interp_easing_right=pg.interp_easing_right
        self.interp_easing_up=pg.interp_easing_up
        self.interp_easing_down=pg.interp_easing_down
        self.stroke_order_changes=pg.stroke_order_changes
        self.stroke_order_change_offset_factor_horizontal=pg.stroke_order_change_offset_factor_horizontal
        self.stroke_order_change_offset_factor_vertical=pg.stroke_order_change_offset_factor_vertical
        if self.node:
            self.gp_obj = self.node.obj
            self.layers = [l for name_item in self.node.name_list if (name_item.name != '' and (l := self.gp_obj.data.layers.get(name_item.name)))]
        else:
            self.gp_obj = bpy.context.view_layer.objects.active
            self.layers = [self.gp_obj.data.layers.active] 

class GP2DMORPHS_OT_generate_2d_bone_morphs(bpy.types.Operator):
    bl_idname = "gp2dmorphs.generate_2d_bone_morphs"    
    bl_label = "Generate 2D Bone Morphs"
    bl_description = "Using predefined frames made by the user, creates a 'grid' of interpolated frames and a Time Offset Modifier, Control and Driver to manipulate the frames"
    bl_options = {'UNDO'}

    props_set: BoolProperty(name="props_set", default = False)

    def_frame_start: IntProperty(name="def_frame_start", default = 0, description="The starting frame for the user-defined frames")
    def_frames_w: IntProperty(name="def_frames_w", default = 3, description="The width of the '2D array' of user-defined frames",min=1)
    def_frames_h: IntProperty(name="def_frames_h", default = 3, description="The height of the '2D array' of user-defined frames",min=1)

    generate_control: BoolProperty(default = True)
    generate_location: BoolProperty(default = True)
    generate_rotation: BoolProperty(default = True)
    generate_scale: BoolProperty(default = True)

    control_type : EnumProperty(name="Control Type", items = [('OBJECT',"Object",""),('BONE',"Armature Bone","")], default='BONE', description="Type of control to use")
    control_armature_x = None
    control_armature_name_x : StringProperty(name="Control Armature X", default='',description="The armature that has the bone to use as a control for the X axis of the morph")
    control_bone_name_x : StringProperty(name="Control Bone X", default='',description="The bone to use as a control for the X axis of the morph")
    control_bone_transform_type_x : StringProperty(name="Control Bone Transform Type X", default='LOC_X',description="The transform component of the control to use for the X axis of the morph")
    control_range_start_x : FloatProperty(name="Control Range Start X", default=-180, 
                                                                        description="The value that will represent '0' in the control driver. Mostly used for rotation controls")
    control_range_end_x : FloatProperty(name="Control Range End X", default=180, 
                                                                        description="The value that will represent '1' in the control driver. Mostly used for rotation controls")
    control_range_flip_x : BoolProperty(name="Rotation Range Flip",default=False,description="Rotation Range should go counter-clockwise instead of clockwise")
    
    control_armature_y = None
    control_armature_name_y : StringProperty(name="Control Armature Y", default='',description="The armature that has the bone to use as a control for the Y axis of the morph")
    control_bone_name_y : StringProperty(name="Control Bone Y", default='',description="The bone to use as a control for the Y axis of the morph")
    control_bone_transform_type_y : StringProperty(name="Control Bone Transform Type Y", default='LOC_Y',description="The transform component of the control to use for the Y axis of the morph")
    control_range_start_y : FloatProperty(name="Control Range Start Y", default=-180, 
                                                                        description="The value that will represent '0' in the control driver. Mostly used for rotation controls")
    control_range_end_y : FloatProperty(name="Control Range End Y", default=180, 
                                                                        description="The value that will represent '1' in the control driver. Mostly used for rotation controls")
    control_range_flip_y : BoolProperty(name="Rotation Range Flip",default=False,description="Rotation Range should go counter-clockwise instead of clockwise")

    morph_armature_obj = None
    morph_armature_obj_name : StringProperty()
    use_custom_shapes : BoolProperty(name="Use Custom Shapes",default=True,description="Pose Bones will have Custom Shapes applied to them that correspond to their control")
    use_control_constraints : BoolProperty(name="Use Control Constraints",default=True,description="Knob Pose Bone will have constraints applied to it to limit its movement depending on the type of control")
    mode : StringProperty(default='ANIMATE')

    def execute(self, context):
        run_ops_without_view_layer_update(self.run,context)
        context.view_layer.update()
        return {'FINISHED'}

    def run(self,context):
        original_active_obj = context.view_layer.objects.active
        original_mode = original_active_obj.mode             #Grab the current mode so we can switch back after
        original_frame = context.scene.frame_current
        if self.props_set:  #Properties have already been set. Just need to set the pointers
            self.morph_armature_obj = bpy.data.objects.get(self.morph_armature_obj_name)
            self.control_armature_x = bpy.data.objects.get(self.control_armature_name_x)
            self.control_armature_y = bpy.data.objects.get(self.control_armature_name_y)
        else:               #Properties haven't been set. Use the panel settings.
            self.morph_armature_obj = context.view_layer.objects.active
            self.set_props(original_active_obj.gp2dmorphs_panel_settings)
        if self.morph_armature_obj is None or (not self.generate_location and not self.generate_rotation and not self.generate_scale): return
        dw, dh = self.def_frames_w, self.def_frames_h
        orientation = 'H' if dh == 1 else 'V' if dw == 1 else '2'   #Morph is Horizontal, Vertical, or 2 dimensional
        def_length = max(dw,dh)
        multi_interp = def_length > 2
        ctrl_objs = list((None, None))
        if self.generate_control:
            trans_limits = {'L':None,'R':None,'S':None}    #Components of Loc,Rot,Scale that are needed.
            if self.gen_frames_w > 1:
                trans_type = self.control_bone_transform_type_x[0]
                trans_limits[trans_type] = {'X':None,'Y':None,'Z':None}
                trans_limits[trans_type][self.control_bone_transform_type_x[-1]] = (-0.5,0.5) if trans_type != 'R' else (self.control_range_start_x,self.control_range_end_x)
            if self.gen_frames_h > 1:
                trans_type = self.control_bone_transform_type_y[0]
                if trans_limits[trans_type] is None:
                    trans_limits[trans_type] = {'X':None,'Y':None,'Z':None}
                trans_limits[trans_type][self.control_bone_transform_type_y[-1]] = (-0.5,0.5) if trans_type != 'R' else (self.control_range_start_y,self.control_range_end_y)
            ctrl_objs[0] = get_or_create_control(self.control_type,
                                           self.morph_armature_obj.name + "Control" if (self.control_type=='OBJECT' or self.control_bone_name_x=='' ) else self.control_bone_name_x,
                                           self.control_armature_name_x,self.use_custom_shapes,self.use_control_constraints, trans_limits)
            ctrl_objs[1] = (get_or_create_control(self.control_type,
                                           self.morph_armature_obj.name + "Control" if (self.control_type=='OBJECT' or self.control_bone_name_y=='' ) else self.control_bone_name_y,
                                        self.control_armature_name_y,self.use_custom_shapes,self.use_control_constraints, trans_limits) 
                                        if self.control_armature_name_y != self.control_armature_name_x or self.control_bone_name_y != self.control_bone_name_x else ctrl_objs[0])
        else:
            ctrl_objs[0] = get_control(self.control_type,
                                           self.morph_armature_obj.name + "Control" if (self.control_type=='OBJECT' or self.control_bone_name_x=='' ) else self.control_bone_name_x,
                                           self.control_armature_name_x)
            ctrl_objs[1] = get_control(self.control_type,
                                           self.morph_armature_obj.name + "Control" if (self.control_type=='OBJECT' or self.control_bone_name_y=='' ) else self.control_bone_name_y,
                                           self.control_armature_name_y)
        
        #Create driver expression prefix and suffix
        driver_expr_head = ("biinterp" if orientation == '2' else "interp") + ("_multi(" if multi_interp else "(")
        driver_expr_tail = ((("," + create_driver_variable_expression('varX',self.control_bone_transform_type_x[:3],
                                                                    math.radians(self.control_range_start_x),math.radians(self.control_range_end_x),self.control_range_flip_x)) if dw > 1 else "")
                        +   (("," + create_driver_variable_expression('varY',self.control_bone_transform_type_y[:3],
                                                                    math.radians(self.control_range_start_y),math.radians(self.control_range_end_y),self.control_range_flip_y)) if dh > 1 else "")
                        +   ")")
        
        if original_active_obj is not self.morph_armature_obj:
            self.morph_armature_obj.select_set(True)
            context.view_layer.objects.active = self.morph_armature_obj
        if original_mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE', toggle=False)
        bpy.ops.gp2dmorphs.remove_morph_drivers()
        bones = context.selected_pose_bones
        bones_len = len(bones)
        #Transform arrays are in the format [Bone Index][morph x][morph y] or [Bone Index][morph alpha]
        if self.generate_location:
            bone_locs = [[[[0.0 for y in range(dh)] for x in range(dw)] for component in range(3)] if orientation == '2' else [[0.0 for i in range(def_length)] for component in range(3)] for bone_index in range(bones_len)]
            bone_locs_needed = [[False for component in range(3)] for bone_index in range(bones_len)]
        if self.generate_rotation:
            bone_rots = [[[[0.0 for y in range(dh)] for x in range(dw)] for component in range(4 if bone.rotation_mode=='QUATERNION' or bone.rotation_mode=='AXIS_ANGLE' else 3)] if orientation == '2' else 
                         [[0.0 for i in range(def_length)] for component in range(4 if bone.rotation_mode=='QUATERNION' or bone.rotation_mode=='AXIS_ANGLE' else 3)] 
                         for bone in bones]
            bone_rots_needed = [[False for component in range(len(bone_rots[bone_index]))] for bone_index in range(bones_len)]
        if self.generate_scale:
            bone_scales = [[[[0.0 for y in range(dh)] for x in range(dw)] for component in range(3)] if orientation == '2' else [[0.0 for i in range(def_length)] for component in range(3)] for bone_index in range(bones_len)]
            bone_scales_needed = [[False for component in range(3)] for bone_index in range(bones_len)]

        match orientation:  #Get the bone's transform values for the morph from the defined frames
            case '2':   #2 Dimensional
                for dx in range(dw):
                    for dy in range(dh):
                        context.scene.frame_set(def_array_pos_to_def_frame_pos(dx,dy,self.def_frame_start,dw))
                        for i,bone in enumerate(bones):
                            if self.generate_location:
                                self.set_comps_and_needed_2D(bone_locs[i],dx,dy,bone.location,bone_locs_needed[i])
                            if self.generate_rotation:
                                self.set_comps_and_needed_2D(bone_rots[i],dx,dy,bone.rotation_quaternion if bone.rotation_mode=='QUATERNION' else
                                                                            bone.rotation_axis_angle if bone.rotation_mode=='AXIS_ANGLE' else
                                                                            bone.rotation_euler,bone_rots_needed[i])
                            if self.generate_scale:
                                self.set_comps_and_needed_2D(bone_scales[i],dx,dy,bone.scale,bone_scales_needed[i])
            case 'H':   #Horizontal
                for dx in range(dw):
                    context.scene.frame_set(self.def_frame_start + dx)
                    for i,bone in enumerate(bones):
                        if self.generate_location:
                            self.set_comps_and_needed_1D(bone_locs[i],dx,bone.location,bone_locs_needed[i])
                        if self.generate_rotation:
                            self.set_comps_and_needed_1D(bone_rots[i],dx,bone.rotation_quaternion if bone.rotation_mode=='QUATERNION' else
                                                                        bone.rotation_axis_angle if bone.rotation_mode=='AXIS_ANGLE' else
                                                                        bone.rotation_euler,bone_rots_needed[i])
                        if self.generate_scale:
                            self.set_comps_and_needed_1D(bone_scales[i],dx,bone.scale,bone_scales_needed[i])
            case 'V':   #Vertical
                for dy in range(dh):
                    context.scene.frame_set(self.def_frame_start + dy*2)
                    for i,bone in enumerate(bones):
                        if self.generate_location:
                            self.set_comps_and_needed_1D(bone_locs[i],dy,bone.location,bone_locs_needed[i])
                        if self.generate_rotation:
                            self.set_comps_and_needed_1D(bone_rots[i],dy,bone.rotation_quaternion if bone.rotation_mode=='QUATERNION' else
                                                                        bone.rotation_axis_angle if bone.rotation_mode=='AXIS_ANGLE' else
                                                                        bone.rotation_euler,bone_rots_needed[i])
                        if self.generate_scale:
                            self.set_comps_and_needed_1D(bone_scales[i],dy,bone.scale,bone_scales_needed[i])
        for i,bone in enumerate(bones):
            bone_path = "pose.bones[\"" + bone.name + "\"]"
            #Location
            if self.generate_location:
                for comp in range(3):
                    if bone_locs_needed[i][comp] is True:
                        prop_name = "GP2DMorphsBoneMorphLocs" + str(comp)
                        driver = create_ctrl_driver(context,ctrl_objs[0],ctrl_objs[1],bone,"location",comp,
                                    control_transform_type_x=self.control_bone_transform_type_x,control_transform_type_y=self.control_bone_transform_type_y,
                                    control_type=self.control_type,mode=self.mode)
                        if multi_interp or orientation == '2':
                            expr = driver_expr_head + str(bone_locs[i][comp]) + driver_expr_tail
                            if len(expr) > 256: #Blender is dumb and only allows driver expressions with 256 characters or less, so we're going to have to use custom properties to hold large arrays instead of baking into the expression
                                expr = driver_expr_head + "eval(varArray)" + driver_expr_tail
                                # bone[prop_name] = bone_locs[i][comp]
                                bone[prop_name] = str(bone_locs[i][comp])
                                add_driver_custom_props_var(driver, self.morph_armature_obj, var_name='varArray', prop_name=prop_name, prop_path=bone_path)
                        else:
                            expr = f"{driver_expr_head}{bone_locs[i][comp][0]},{bone_locs[i][comp][1]}{driver_expr_tail}"
                        driver.expression = expr
            #Rotation
            if self.generate_rotation:
                rot_var_name = ("rotation_quaternion" if bone.rotation_mode=='QUATERNION' else
                                "rotation_axis_angle" if bone.rotation_mode=='AXIS_ANGLE' else
                                "rotation_euler")
                for comp in range(len(bone_rots_needed[i])):
                    if bone_rots_needed[i][comp] is True:
                        prop_name = "GP2DMorphsBoneMorphRots" + str(comp)
                        driver = create_ctrl_driver(context,ctrl_objs[0],ctrl_objs[1],bone,rot_var_name,comp,
                                    control_transform_type_x=self.control_bone_transform_type_x,control_transform_type_y=self.control_bone_transform_type_y,
                                    control_type=self.control_type,mode=self.mode)
                        if multi_interp or orientation == '2':
                            expr = driver_expr_head + str(bone_rots[i][comp]) + driver_expr_tail
                            if len(expr) > 256: #Blender is dumb and only allows driver expressions with 256 characters or less, so we're going to have to use custom properties to hold large arrays instead of baking into the expression
                                expr = driver_expr_head + "varArray" + driver_expr_tail
                                bone[prop_name] = bone_rots[i][comp]
                                add_driver_custom_props_var(driver, self.morph_armature_obj, var_name='varArray', prop_name=prop_name, prop_path=bone_path)
                        else:
                            expr = driver_expr_head + str(bone_rots[i][comp][0])+","+str(bone_rots[i][comp][1]) + driver_expr_tail
                        driver.expression = expr
            #Scale
            if self.generate_scale:
                for comp in range(3):
                    if bone_scales_needed[i][comp] is True:
                        prop_name = "GP2DMorphsBoneMorphScales" + str(comp)
                        driver = create_ctrl_driver(context,ctrl_objs[0],ctrl_objs[1],bone,"scale",comp,
                                    control_transform_type_x=self.control_bone_transform_type_x,control_transform_type_y=self.control_bone_transform_type_y,
                                    control_type=self.control_type,mode=self.mode)
                        if multi_interp or orientation == '2':
                            expr = driver_expr_head + str(bone_scales[i][comp]) + driver_expr_tail
                            if len(expr) > 256: #Blender is dumb and only allows driver expressions with 256 characters or less, so we're going to have to use custom properties to hold large arrays instead of baking into the expression
                                expr = driver_expr_head + "varArray" + driver_expr_tail
                                bone[prop_name] = bone_scales[i][comp]
                                add_driver_custom_props_var(driver, self.morph_armature_obj, var_name='varArray', prop_name=prop_name, prop_path=bone_path)
                        else:
                            expr = f"{driver_expr_head}{bone_scales[i][comp][0]},{bone_scales[i][comp][1]}{driver_expr_tail}"
                        driver.expression = expr
        
        context.scene.frame_set(original_frame) #TODO: check frame_current set instead
        context.view_layer.objects.active = original_active_obj
        bpy.ops.object.mode_set(mode=original_mode, toggle=False)
    
    def set_comps_and_needed_1D(self, comps, i, values, comps_needed):
        for comp,val in enumerate(values):   #For each component of the location vector X, Y, Z 
            comps[comp][i] = val
            needed_val = comps_needed[comp]
            if needed_val is False:     #Checks if the component ever changes. If it doesn't, we don't need to make a driver for it later.
                comps_needed[comp] = val
            elif needed_val is not True and not math.isclose(needed_val, val, abs_tol=0.001):
                comps_needed[comp] = True

    def set_comps_and_needed_2D(self, comps, dx, dy, values, comps_needed):
        for comp,val in enumerate(values):   #For each component of the location vector X, Y, Z 
            comps[comp][dx][dy] = val
            needed_val = comps_needed[comp]
            if needed_val is False:     #Checks if the component ever changes. If it doesn't, we don't need to make a driver for it later.
                comps_needed[comp] = val
            elif needed_val is not True and not math.isclose(needed_val, val, abs_tol=0.001):
                comps_needed[comp] = True
    
    def set_props(self, pg):
        self.def_frame_start=pg.def_frame_start
        self.def_frames_w=pg.def_frames_w
        self.def_frames_h=pg.def_frames_h
        self.generate_location=pg.generate_frames_or_location
        self.generate_rotation=pg.generate_control_or_rotation
        self.generate_scale=pg.generate_driver_or_scale
        self.control_type=pg.control_type
        self.control_armature_name_x='' if pg.control_armature_x is None else pg.control_armature_x.name
        self.control_bone_name_x=pg.control_bone_name_x
        self.control_bone_transform_type_x=pg.control_bone_transform_type_x
        self.control_range_start_x=pg.control_range_start_x
        self.control_range_end_x=pg.control_range_end_x
        self.control_range_flip_x=pg.control_range_flip_x
        self.control_armature_name_y='' if pg.control_armature_y is None else pg.control_armature_y.name
        self.control_bone_name_y=pg.control_bone_name_y
        self.control_bone_transform_type_y=pg.control_bone_transform_type_y
        self.control_range_start_y=pg.control_range_start_y
        self.control_range_end_y=pg.control_range_end_y
        self.control_range_flip_y=pg.control_range_flip_y
        
class GP2DMORPHS_OT_remove_morph_drivers(bpy.types.Operator):
    bl_idname = "gp2dmorphs.remove_morph_drivers"    
    bl_label = "Remove Morph Drivers"
    bl_description = "Removes drivers specified in the GP 2D Morphs panel"

    props_set: BoolProperty(name="props_set", default = False)

    remove_location: BoolProperty(default = True)
    remove_rotation: BoolProperty(default = True)
    remove_scale: BoolProperty(default = True)
    
    def execute(self, context):
        obj = context.view_layer.objects.active
        if not self.props_set:
            GP2DMORPHSVars = obj.gp2dmorphs_panel_settings
            self.remove_location = GP2DMORPHSVars.generate_frames_or_location
            self.remove_rotation = GP2DMORPHSVars.generate_control_or_rotation
            self.remove_scale = GP2DMORPHSVars.generate_driver_or_scale

        if obj.type == 'GPENCIL':
            layer = obj.data.layers.active
            #GP Time Offset Modifier
            mod_name = obj.name + layer.info + "TO"
            mod = obj.grease_pencil_modifiers.get(mod_name)
            if mod is not None:
                mod.driver_remove("offset")
        elif obj.type == 'ARMATURE':
            for bone in context.selected_pose_bones:
                #Location
                if self.remove_location:
                    bone.driver_remove("location")
                #Rotation
                if self.remove_rotation:
                    rot_var_name = ("rotation_quaternion" if bone.rotation_mode=='QUATERNION' else
                                    "rotation_axis_angle" if bone.rotation_mode=='AXIS_ANGLE' else
                                    "rotation_euler")
                    bone.driver_remove(rot_var_name)
                #Scale
                if self.remove_scale:
                    bone.driver_remove("scale")

        return {'FINISHED'}
    
class GP2DMORPHS_OT_remove_morph_properties(bpy.types.Operator):
    bl_idname = "gp2dmorphs.remove_morph_properties"    
    bl_label = "Remove Morph Properties"
    bl_description = "Removes GP2DMorphs custom properties from selected bones"
    
    def execute(self, context):
        for bone in context.selected_pose_bones:
            for i in range(len(bone.keys())-1,-1,-1):
                k = list(bone.keys())[i]
                if k.startswith("GP2DMorph"):
                    print(k)
                    del bone[k]

        return {'FINISHED'}

class GP2DMORPHS_OT_interpolate_sequence_disorderly(bpy.types.Operator):
    bl_idname = "gpencil.interpolate_sequence_disorderly"    
    bl_label = "Interpolate Sequence Disorderly"
    bl_description = "Interpolates between two Grease Pencil Frames like Interpolate Sequence, but can handle different stroke orders"
    bl_options = {'REGISTER', 'UNDO'}
    step : IntProperty(name="Step",description="Number of frames between generated interpolated frames",default=1,min=1,max=1048573)
    layers : EnumProperty(name="Layer", 
                                  items = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['layers'].enum_items], 
                                  description="Layers included in the interpolation",default='ACTIVE')
    interpolate_selected_only : BoolProperty(name="Only Selected", description="Interpolate only selected strokes",default=False)
    exclude_breakdowns : BoolProperty(name="Exclude Breakdowns", description="Exclude existing Breakdowns keyframes as interpolation extremes",default=False)
    flip : EnumProperty(name="Flip Mode", 
                                  items = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['flip'].enum_items], 
                                  description="Invert destination stroke to match start and end with source stroke", default='AUTO')
    smooth_steps : IntProperty(name="Iterations",description="Number of times to smooth newly created strokes",default=1,min=1,max=3)
    smooth_factor : FloatProperty(name="Smooth",description="Amount of smoothing to apply to interpolated strokes, to reduce jitter/noise",default=0.0,min=0.0,max=2.0)
    type : EnumProperty(name="Interpolation Type", 
                                  items = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['type'].enum_items if ot.identifier != 'CUSTOM'], 
                                  description="Interpolation Type in the left direction")
    easing : EnumProperty(name="Interpolation Easing", default='EASE_OUT', 
                                    items = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['easing'].enum_items], 
                                    description="Interpolation Easing in the left direction")
    back : FloatProperty(name="Back",description="Amount of overshoot for ‘back’ easing",default=1.702,min=0.0)
    amplitude : FloatProperty(name="Amplitude",description="Amount to boost elastic bounces for ‘elastic’ easing",default=0.15,min=0.0)
    period : FloatProperty(name="Period",description="Time between bounces for elastic easing",default=0.15)
    stroke_order_change_offset_factor : FloatProperty(name="Stroke Order Change Offset Factor", default=0.5, 
                                                                        description="Factor for the distance between two frames that new interpolated stroke orders should change",
                                                                        min=0.0,max=1.0)
    
    
    def execute(self, context):
        if context is None:
            context = bpy.context
        gp = context.view_layer.objects.active.data
        original_frame = context.scene.frame_current
        for layer in ([gp.layers.active] if self.layers == 'ACTIVE' else gp.layers):
            if layer.lock:
                continue
            frame_from, frame_to = None, None
            for frame in layer.frames:
                if frame.frame_number < context.scene.frame_current:
                    if frame_from is None or frame.frame_number > frame_from.frame_number:
                        frame_from = frame
                else:
                    if frame_to is None or frame.frame_number < frame_to.frame_number:
                        frame_to = frame
            if frame_from is None or frame_to is None:  #Failure. We'll get 'em next time.
                self.report({'ERROR'}, "Cannot find valid keyframes to interpolate (Breakdowns keyframes are not allowed)")
                return {'CANCELLED'}
            elif len(frame_from.strokes) == 0 or len(frame_to.strokes) == 0 or frame_to.frame_number-frame_from.frame_number < 2:
                continue
            orders_different = False
            order_change = list()
            for i in range(len(frame_from.strokes.values())):   #Find the differences between the two frames' stroke orders, if any
                stroke_from = frame_from.strokes.values()[i]
                to_index = self.get_stroke_index(frame_to.strokes, stroke_from,i)
                order_change.append(to_index)
                if to_index != i:       #A difference in stroke order was found. *Sigh* Now we'll have to actually do some work...
                    orders_different = True

            if orders_different:       
                #Reoder the To frame to have the same stroke order as the From frame so that interp doesn't fuck up
                context.scene.frame_set(frame_to.frame_number)
                self.strokes_order(frame_to.strokes,order_change)
                context.scene.frame_current = frame_to.frame_number-1
                #Interpolate
                interpolate_sequence_view_independent(context,step=self.step,layers=self.layers,interpolate_selected_only=self.interpolate_selected_only,
                                             exclude_breakdowns=self.exclude_breakdowns,flip=self.flip,smooth_steps=self.smooth_steps,smooth_factor=self.smooth_factor,
                                             type=self.type,easing=self.easing,back=self.back,amplitude=self.amplitude,period=self.period)
                #Now go back and change the To frame and some frames between to have the original To frame stroke order
                reorder_num = round((frame_to.frame_number-frame_from.frame_number-1)*self.stroke_order_change_offset_factor)
                for fi in range(len(layer.frames)-1,-1,-1): #For each new frame we just made by duplicating defined frames and interpolating
                    frame = layer.frames[fi]
                    if frame.frame_number < frame_from.frame_number: #We're done looking for frames to reorder
                        break
                    if frame.frame_number > frame_from.frame_number+reorder_num and frame.frame_number <= frame_to.frame_number:    #This is one of the frames we want to reorder
                        context.scene.frame_set(frame.frame_number)
                        self.strokes_order(frame.strokes,order_change,undo=True)
            else:
                #No stroke order changes, so just interpolate like normal
                interpolate_sequence_view_independent(context,step=self.step,layers=self.layers,interpolate_selected_only=self.interpolate_selected_only,
                                                exclude_breakdowns=self.exclude_breakdowns,flip=self.flip,smooth_steps=self.smooth_steps,smooth_factor=self.smooth_factor,
                                                type=self.type,easing=self.easing,back=self.back,amplitude=self.amplitude,period=self.period)
            context.scene.frame_current = original_frame
        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        split = layout.split(factor=0.4)
        col1 = split.column(align=True)
        col1.alignment='RIGHT' 
        col2 = split.column(align=True)
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        col1.label(text="Step")
        col2.prop(self, "step",text="")
        col1.label(text="Layer")
        col2.prop(self, "layers",text="")
        col1.separator_spacer()
        col2.prop(self, "interpolate_selected_only")
        col1.separator_spacer()
        col2.prop(self, "exclude_breakdowns")
        col1.label(text="Flip Mode")
        col2.prop(self, "flip",text="")
        col1.label(text="Smooth")
        col2.prop(self, "smooth_factor",text="")
        col1.label(text="Iterations")
        col2.prop(self, "smooth_steps",text="")
        col1.label(text="Type")
        col2.prop(self, "type",text="")
        if self.type != 'LINEAR':
            col1.label(text="Easing")
            col2.prop(self, "easing",text="")
        if self.type == 'BACK':
            col1.label(text="Back")
            col2.prop(self, "back",text="")
        elif self.type == 'ELASTIC':
            col1.label(text="Amplitude")
            col2.prop(self, "amplitude",text="")
            col1.label(text="Period")
            col2.prop(self, "period",text="")
        col1.label(text="Change Offset")
        col2.prop(self, "stroke_order_change_offset_factor",text="")
    
    def get_stroke_index(self, strokes, target, expected_index=0):
        if self.strokes_equal(strokes.values()[expected_index], target):
            return expected_index
        for i in range(expected_index+1,len(strokes.values())):
            if self.strokes_equal(strokes.values()[i], target):
                return i
        for i in range(expected_index-1,-1,-1):
            if self.strokes_equal(strokes.values()[i], target):
                return i
        return expected_index

    def strokes_equal(self, s1, s2):
        if s1.time_start == s2.time_start:
            if s1.time_start == 0:      #If both time_starts are 0, try other methods to compare them because time_start is invalid.
                if len(s1.points) != len(s2.points):
                    return False
                if s1.material_index != s2.material_index:
                    return False
                return (s1.vertex_color_fill[0] == s2.vertex_color_fill[0] and
                        s1.vertex_color_fill[1] == s2.vertex_color_fill[1] and
                        s1.vertex_color_fill[2] == s2.vertex_color_fill[2] and
                        s1.vertex_color_fill[3] == s2.vertex_color_fill[3]) #Final check. If the v-color is the same, then either it's the same stroke or there's no way for us to know for sure.
            else:
                return True
        return False
    
    def strokes_order(self, strokes, order_change, undo=False):
        bpy.ops.gpencil.select_all(action='DESELECT')
        stroke_order_old = list()
        for i in range(len(order_change)-1,-1,-1):
            stroke_order_old.append(strokes[order_change.index(i) if undo else order_change[i]])

        for s in stroke_order_old:
            s.select = True
            bpy.ops.gpencil.stroke_arrange(direction='BOTTOM')
            s.select = False
    
    @classmethod
    def poll(cls, context):
        ob = context.object
        return ob and ob.type == 'GPENCIL' and (ob.mode == 'EDIT_GPENCIL' or ob.mode == 'PAINT_GPENCIL') 

class GP2DMORPHS_OT_set_frame_by_defined_pos(bpy.types.Operator):
    bl_idname = "gp2dmorphs.set_frame_by_defined_pos"    
    bl_label = "Set Frame by Defined Position"
    bl_description = "Sets the current frame in the timeline to the frame of the associated frame in the Defined Frames array"
    pos_x: IntProperty()
    pos_y: IntProperty()
    def_frame_start: IntProperty()
    def_frames_w: IntProperty()

    def execute(self, context):
        context.scene.frame_current = def_array_pos_to_def_frame_pos(self.pos_x,self.pos_y,self.def_frame_start,self.def_frames_w)
        return {'FINISHED'}

class GP2DMORPHS_OT_fill_defined_frames(bpy.types.Operator):
    bl_idname = "gp2dmorphs.fill_defined_frames"    
    bl_label = "Fill Defined Frames"
    bl_description = "Fill Defined Frames array with duplicates of the current frame"
    bl_options = {'UNDO'}
    props_set: BoolProperty(name="props_set", default = False)

    def_frame_start: IntProperty(name="def_frame_start", default = 0, description="The starting frame for the user-defined frames")
    def_frames_w: IntProperty(name="def_frames_w", default = 3, description="The width of the '2D array' of user-defined frames",min=1)
    def_frames_h: IntProperty(name="def_frames_h", default = 3, description="The height of the '2D array' of user-defined frames",min=1)
    gp_obj = None
    gp_obj_name : StringProperty()
    layer_name : StringProperty()
    def execute(self, context):
        original_active_obj = context.view_layer.objects.active
        original_mode = original_active_obj.mode             #Grab the current mode so we can switch back after
        original_frame = bpy.context.scene.frame_current
        if self.props_set:  #Properties have already been set. Just need to set the two pointers because we 
            self.gp_obj = bpy.data.objects.get(self.gp_obj_name)
            if self.gp_obj is None:
                return {'CANCELLED'}
            original_layer = self.gp_obj.data.layers.active
            layer = self.gp_obj.data.layers.get(self.layer_name)
            if layer is None:
                return {'CANCELLED'}
            self.gp_obj.data.layers.active = layer
            dw, dh = self.def_frames_w, self.def_frames_h
        else:               #Properties haven't been set. Use the panel settings.
            self.gp_obj = context.view_layer.objects.active
            GP2DMORPHSVars = self.gp_obj.gp2dmorphs_panel_settings
            layer = self.gp_obj.data.layers.active
            original_layer = layer
            dw, dh = GP2DMORPHSVars.def_frames_w, GP2DMORPHSVars.def_frames_h
            self.def_frame_start = GP2DMORPHSVars.def_frame_start
        original_lock = layer.lock
        if original_lock:
            layer.lock = False
        src_frame = None
        def_frames = [[None for y in range(dh)] for x in range(dw)]
                
        for frame in layer.frames:
            n = frame.frame_number
            if n == context.scene.frame_current: #This is the frame we'll be copying
                src_frame = frame
            n -= self.def_frame_start
            f_y = math.floor(n/(dw+1))
            f_x = n-(f_y*(dw+1))
            if f_x < dw and f_y < dh:
                def_frames[f_x][f_y] = frame    #This frame is already defined, so don't overwrite it later when we do our frame duplication
        if src_frame == None:   #No frame to duplicate
            self.report({'ERROR'}, "No frame found at the selected frame and layer. Make sure the timeline's current frame is set to the frame you wish to duplicate")
            return {'FINISHED'}
        for dx in range(dw):
            for dy in range(dh):
                if def_frames[dx][dy] is None:
                    new_frame = layer.frames.copy(src_frame)
                    new_frame.frame_number = def_array_pos_to_def_frame_pos(dx,dy,self.def_frame_start,dw)
        refresh_GP_dopesheet(context)
        layer.lock = original_lock
        self.gp_obj.data.layers.active = original_layer
        context.view_layer.objects.active = original_active_obj
        bpy.ops.object.mode_set(mode=original_mode, toggle=False)
        bpy.context.scene.frame_current = original_frame
        return {'FINISHED'}

class GP2DMORPHS_OT_set_all_interp_types(bpy.types.Operator):
    bl_idname = "gp2dmorphs.set_all_interp_types"    
    bl_label = "Set All Interpolation Types"
    bl_description = "Sets the interpolation type for all directions at once"
    
    node_name: StringProperty(default='')
    type: EnumProperty(
        name="Type",
        description="The type of interpolation to use in this direction",
        items = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['type'].enum_items if ot.identifier != 'CUSTOM'],
        default='LINEAR',
    )

    def execute(self, context):
        if self.node_name == '':
            GP2DMORPHSVars = context.view_layer.objects.active.gp2dmorphs_panel_settings
        else:
            node_tree = get_tree(context)
            if node_tree is None:   return {'CANCELLED'}
            GP2DMORPHSVars = node_tree.nodes.get(self.node_name).props
        GP2DMORPHSVars.interp_type_left = self.type
        GP2DMORPHSVars.interp_type_right = self.type
        GP2DMORPHSVars.interp_type_up = self.type
        GP2DMORPHSVars.interp_type_down = self.type
        return {'FINISHED'}
    
class GP2DMORPHS_OT_set_all_interp_easings(bpy.types.Operator):
    bl_idname = "gp2dmorphs.set_all_interp_easings"    
    bl_label = "Set All Interpolation Easings"
    bl_description = "Sets the interpolation easing for all directions at once"
    
    node_name: StringProperty(default='')
    easing: EnumProperty(
        name="easing",
        description="The easing for interpolation to use in this direction",
        items = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['easing'].enum_items if ot.identifier != 'AUTO'],
        default='EASE_OUT',
        
    )

    def execute(self, context):
        if self.node_name == '':
            GP2DMORPHSVars = context.view_layer.objects.active.gp2dmorphs_panel_settings
        else:
            node_tree = get_tree(context)
            if node_tree is None:   return {'CANCELLED'}
            GP2DMORPHSVars = node_tree.nodes.get(self.node_name).props
        GP2DMORPHSVars.interp_easing_left = self.easing
        GP2DMORPHSVars.interp_easing_right = self.easing
        GP2DMORPHSVars.interp_easing_up = self.easing
        GP2DMORPHSVars.interp_easing_down = self.easing
        return {'FINISHED'}

def def_array_pos_to_def_frame_pos(x,y,def_frame_start,def_frames_w):
    return def_frame_start + y*(def_frames_w+1) + x

def gen_array_pos_to_gen_frame_pos(x,y,gen_frame_start,gen_frames_w):
    return gen_frame_start + y*(gen_frames_w+1) + x
#Parameters for def_size and gen_size ahould be the widths or heights depending on if the offset is horizontal or vertical
def def_pos_offset_to_gen_pos_offset(pos,def_size,gen_size):
    return math.floor(pos/max(1,def_size-1)*max(1,gen_size-1))
    
def gen_per_def(generated,defined):
    if generated <= 1:
        return 1
    if defined <= 1:
        return generated-2
    return math.floor(generated/(defined-1))

def get_control(control_type='BONE',control_name="",arm_name=""):
    context = bpy.context
    ctrl_obj = None
    armature_obj = None
    if control_type == 'OBJECT':
        return context.scene.objects.get(control_name)
    else:                            #'BONE'
        armature_obj = context.scene.objects.get(arm_name)
        if armature_obj is not None:
            ctrl_obj = armature_obj.pose.bones.get(control_name)
        return ctrl_obj
#orientation is in ('H','V','','R') for Horizontal, Vertical, both dimensions, or Rotation
def get_or_create_control(control_type='BONE',control_name="",arm_name="",use_custom_shapes=True,use_control_constraints=True,trans_comps_used={'L':{'X':(-0.5,0.5),'Y':(-0.5,0.5),'Z':None},'R':None,'S':None}):
    context = bpy.context
    ctrl_obj = get_control(control_type,control_name,arm_name)
    if ctrl_obj is not None:
        return ctrl_obj
    armature_obj = None
    if control_type == 'BONE':
        armature_obj = context.scene.objects.get(arm_name)
    
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    active_collection = context.collection
    cursor_location = context.scene.cursor.location
    #Base Mesh
    base_object = get_or_create_base_obj((control_name + 'Base' if control_type == 'OBJECT' else ''),trans_comps_used)
    #Knob Mesh
    knob_object = get_or_create_knob_obj((control_name + 'Knob' if control_type == 'OBJECT' else ''),trans_comps_used)
    if control_type == 'OBJECT':
        #Set up object constraints and relations
        knob_object.parent = base_object
        if use_control_constraints:
            update_or_create_limit_constraints(knob_object,control_name,trans_comps_used)
        base_object.location = cursor_location
    else:   #Create control bones
        base_object.hide_set(True)
        knob_object.hide_set(True)
        if armature_obj is None:
            armature = bpy.data.armatures.new("ControlArmature")
            armature_obj = bpy.data.objects.new("ControlArmature", armature)
            active_collection.objects.link(armature_obj)
        else:
            armature = armature_obj.data
            if armature_obj.pose.bones.get(control_name+"Knob") is not None:
                c = 2  #Counter
                while(armature_obj.pose.bones.get(control_name+str(c)+"Knob") is not None):
                    c += 1
                control_name += str(c)
        arm_hidden = armature_obj.hide_get()
        if arm_hidden:
            armature_obj.hide_set(False)
        context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode = 'EDIT')
        base_bone_name = control_name+"Base"    #Base
        base_bone = armature.edit_bones.new(base_bone_name)
        base_bone.use_deform = False
        base_bone.head = cursor_location
        base_bone.tail = [cursor_location.x,cursor_location.y,cursor_location.z+0.5]
        bpy.ops.object.mode_set(mode = 'POSE')
        base_bone_pose = armature_obj.pose.bones[base_bone_name]
        if use_custom_shapes:
            base_bone_pose.custom_shape = base_object
            base_bone_pose.custom_shape_rotation_euler = get_bone_custom_shape_rotation(trans_comps_used,True)
            base_bone_pose.use_custom_shape_bone_size = False
        bpy.ops.object.mode_set(mode = 'EDIT')
        knob_bone_name = control_name+"Knob"    #Knob
        knob_bone = armature.edit_bones.new(control_name+"Knob")
        knob_bone.use_deform = False
        base_bone = armature.edit_bones.get(base_bone_name)     #For some reason, the base bone reference can get mixed up with other bones during the above pose settings. Re-get.
        knob_bone.parent = base_bone
        knob_bone.head = cursor_location
        knob_bone.tail = [cursor_location.x,cursor_location.y,cursor_location.z+0.25]
        bpy.ops.object.mode_set(mode = 'POSE')
        knob_bone_pose = armature_obj.pose.bones[knob_bone_name]
        if use_custom_shapes:
            knob_bone_pose.custom_shape = knob_object
            knob_bone_pose.custom_shape_rotation_euler = get_bone_custom_shape_rotation(trans_comps_used,False)
            knob_bone_pose.use_custom_shape_bone_size = False
        #Constraint
        if use_control_constraints:
            update_or_create_limit_constraints(knob_bone_pose,knob_bone_name,trans_comps_used)

        bpy.ops.object.mode_set(mode = 'OBJECT')
        if arm_hidden:
            armature_obj.hide_set(True)
        return knob_bone_pose
    return knob_object
    
def create_ctrl_driver(context, ctrl_obj_x, ctrl_obj_y, driver_dest, dest_prop_name="offset", dest_prop_comp=None,
                         control_transform_type_x='LOC_X',control_transform_type_y='LOC_Y',control_type='BONE',mode='ANIMATE'):
    need_x, need_y = ctrl_obj_x is not None, ctrl_obj_y is not None
    #Driver
    if dest_prop_comp is not None:
        driver_dest.driver_remove(dest_prop_name, dest_prop_comp)
        fc = driver_dest.driver_add(dest_prop_name, dest_prop_comp)
    else:
        driver_dest.driver_remove(dest_prop_name)
        fc = driver_dest.driver_add(dest_prop_name)
    driver = fc.driver
    fc.mute = mode == 'EDIT'
    #Driver Vars
    if need_x:
        var_x = driver.variables.new()
        var_x.type='TRANSFORMS'
        var_x.name="varX"
        var_x.targets[0].transform_type = control_transform_type_x
        var_x.targets[0].transform_space = 'LOCAL_SPACE'
    if need_y:
        var_y = driver.variables.new()
        var_y.type='TRANSFORMS'
        var_y.name="varY"
        var_y.targets[0].transform_type = control_transform_type_y
        var_y.targets[0].transform_space = 'LOCAL_SPACE'
    
    if control_type == 'OBJECT':
        if need_x:
            var_x.targets[0].id = ctrl_obj_x
        if need_y:
            var_y.targets[0].id = ctrl_obj_y
        return driver
    if need_x:      # 'BONE'
        var_x.targets[0].id = ctrl_obj_x.id_data
        var_x.targets[0].bone_target = ctrl_obj_x.name
    if need_y:      # 'BONE'
        var_y.targets[0].id = ctrl_obj_y.id_data
        var_y.targets[0].bone_target = ctrl_obj_y.name
    return driver

def add_driver_custom_props_var(driver, target_id, target_id_type='OBJECT',var_name='varArray', prop_name='GP2DMorphsLocX', prop_path=""):
    var_prop = driver.variables.get(var_name,None)
    if var_prop is None:
        var_prop = driver.variables.new()
        var_prop.type='SINGLE_PROP'
        var_prop.name=var_name
        var_target = var_prop.targets[0]
        var_target.id_type = target_id_type
        var_target.id = target_id
        var_target.data_path = prop_path + f'''["{prop_name}"]'''
#The same as update_gp_time_offset_modifier, except doesn't check for conflicting modifiers to remove so it's a wee bit faster in some scenarios
def get_gp_time_offset_modifier(gp_obj,layer_name,mod_name='',pass_index=-2,mode='ANIMATE'):
    if gp_obj is None:  return None
    #GP Time Offset Modifier
    mod = None
    if pass_index > -1:    #Use the pass index to find the modifier
        for m in gp_obj.grease_pencil_modifiers:
            if m.type == 'GP_TIME':
                if m.layer_pass == pass_index:
                    mod = m
                    break
    else:                       #Use the layer to find the modifier
        for m in gp_obj.grease_pencil_modifiers:
            if m.type == 'GP_TIME':
                if m.layer == layer_name:
                    mod = m
                    break
    if mod is None:         #If we don't have a modifier yet, make one
        if mod_name == '':
            mod_name = gp_obj.name + layer_name + "TO"
        mod = gp_obj.grease_pencil_modifiers.new(name=mod_name, type='GP_TIME')
        if pass_index > -1:
            mod.layer_pass = pass_index
        else:
            mod.layer = layer_name
        mod.mode = 'FIX'
        if mode == 'EDIT':
            mod.show_viewport = False
        mod.show_expanded = False
        bpy.ops.object.gpencil_modifier_move_to_index(modifier=mod.name,index=0)
    return mod

def update_gp_time_offset_modifier(gp_obj,layer_names,mod_name='',pass_index=-2,mode='ANIMATE'):
    if gp_obj is None:  return None
    mods_to_remove = list()
    main_layer = None if len(layer_names) == 0 else gp_obj.data.layers.get(layer_names[0])
    mod = None
    if pass_index > -1:    #Use the pass index to find the modifier
        for m in gp_obj.grease_pencil_modifiers:
            if m.type == 'GP_TIME':
                if m.layer_pass == pass_index:
                    if mod is None:
                        mod = m
                    else:
                        mods_to_remove.append(m)    #Duplicate modifier. Remove.
                elif m.layer in layer_names:      #This modifier will conflict with ours. Probably a remnant of using different settings. Mark it for removal.
                    mods_to_remove.append(m)
    else:                       #Use the layer to find the modifier
        for m in gp_obj.grease_pencil_modifiers:
            if m.type == 'GP_TIME':
                if m.layer == main_layer.info:
                    if mod is None:
                        mod = m
                    else:
                        mods_to_remove.append(m)    #Duplicate modifier. Remove.
                elif m.layer_pass != 0 and m.layer_pass == main_layer.pass_index:      #This modifier will conflict with ours. Probably a remnant of using different settings. Mark it for removal.
                    mods_to_remove.append(m)
    for i in range(len(mods_to_remove)-1,-1,-1):    #Remove conflicting modifiers
        m = mods_to_remove[i]
        m.driver_remove("offset")
        gp_obj.grease_pencil_modifiers.remove(m)
    if mod is None:         #If we don't have a modifier yet, make one
        if mod_name == '':
            mod_name = gp_obj.name + main_layer.info + "TO"
        mod = gp_obj.grease_pencil_modifiers.new(name=mod_name, type='GP_TIME')
        if pass_index > -1:
            mod.layer_pass = pass_index
        else:
            mod.layer = main_layer.info
        mod.mode = 'FIX'
        if mode == 'EDIT':
            mod.show_viewport = False
        mod.show_expanded = False
        bpy.ops.object.gpencil_modifier_move_to_index(modifier=mod.name,index=0)
    return mod

def update_gp_time_offset_and_driver(pg,gp_obj,ctrl_obj_x,ctrl_obj_y,layer_names,pass_index=-2,mode='ANIMATE',update_mod=True,mod_name=''):
    if update_mod:
        mod = update_gp_time_offset_modifier(gp_obj,layer_names,mod_name,pass_index,mode)
    else:
        mod = get_gp_time_offset_modifier(gp_obj,layer_names[0],mod_name,pass_index,mode)
    driver = create_ctrl_driver(bpy.context,ctrl_obj_x,ctrl_obj_y,mod,"offset",
                                    control_transform_type_x=pg.control_bone_transform_type_x,control_transform_type_y=pg.control_bone_transform_type_y,mode=mode)
    x_comp, y_comp = '',''
    if ctrl_obj_x:
        range_start, range_end = math.radians(pg.control_range_start_x), math.radians(pg.control_range_end_x)
        var_x = create_driver_variable_expression("varX",pg.control_bone_transform_type_x[:3],range_start,range_end,pg.control_range_flip_x)
        x_comp = ("+round(" + var_x + "*" + str(pg.gen_frames_w-1) + ")")
    if ctrl_obj_y:
        range_start, range_end = math.radians(pg.control_range_start_y), math.radians(pg.control_range_end_y)
        var_y = create_driver_variable_expression("varY",pg.control_bone_transform_type_y[:3],range_start,range_end,pg.control_range_flip_y)
        y_comp = ("+round(" + var_y + "*" + str(pg.gen_frames_h-1) + ")*" + str(pg.gen_frames_w+1))
    driver.expression = (str(pg.gen_frame_start) + x_comp + y_comp)

def create_driver_variable_expression(var_name="varX",type='LOC',range_start=-math.pi,range_end=math.pi,flip=False):
    expr = "clamp("
    if type == 'LOC':       #Location 
        expr += var_name + "+.5"
    elif type == 'ROT':     #Rotation
        if ((range_start < range_end) ^ flip): #The simplest scenario
            rot_range = range_end-range_start
            expr += "(" + var_name + (f"-{range_start:.4f}" if range_start != 0 else "") + f")/{rot_range:.4f}"
        else:   #We're going to have to transition across 180 and -180... Fuck.                #Commentception: rotation numbers in comments are in degrees even though real numbers are radians
            full_circle = 2*math.pi
            if (flip):
                rot_range = full_circle-(range_end-range_start)
                range_mid =  range_start + (range_end-range_start)/2
                range_plus_end = rot_range+range_end
                expr += "(((" + var_name + f"-{range_start:.4f})*-1)if " + var_name + f"<{range_mid:.4f} else({range_plus_end:.4f}-" + var_name + f"))/{rot_range:.4f}"
            else:
                #If rot is greater than the mid-point
                #   take rot - start
                #Else
                #   take rot + (360 - start)
                #Then
                #   divide by range
                rot_range = full_circle-(range_start-range_end)
                range_mid =  range_end + (range_start-range_end)/2
                full_circle_minus_range_start = full_circle-range_start
                expr += "((" + var_name + f"-{range_start:.4f})if " + var_name + f">{range_mid:.4f} else(" + var_name + f"+{full_circle_minus_range_start:.4f}))/{rot_range:.4f}"
    else:                   #Scale
        expr += var_name + "/2"
            
    return expr + ")"
# Returns a tuple (Expression, Values were baked)
def bonemorph_driver_expression(values, driver_var_array="",driver_var_x="clamp(varX+.5)", driver_var_y="clamp(varY+.5)"):
    len_x = len(values)
    len_y = len(values[0])
    if len_x == 0 or len_y == 0:
        return "1"
    
    if len_x == 1:        #1 Dimensional Vertical
        if len_y > 2:
            expr_opening = "interp_multi("
            val_array = values[0]
            expr_tail = ","+driver_var_y+")"
        else:   #I'm not super worried about lerps between two values going over the 256 char limit, so just return it
            return "lerp("+str(values[0][0])+","+str(values[0][1])+","+driver_var_y+")"             #We only have linear interpolation implemented, so just use lerp.
    elif len_y == 1:   #1 Dimensional Horizontal
        if len_x > 2:
            expr_opening = "interp_multi("
            val_array = [val[0] for val in values]   #Convert a list of lists of single values into a list of those values
            expr_tail = ","+driver_var_x+")"
        else:
            return "lerp("+str(values[0][0])+","+str(values[1][0])+","+driver_var_x+")"             #We only have linear interpolation implemented, so just use lerp.
    else:
        expr_opening = "biinterp_multi(" if (len_x > 2 or len_y > 2) else "biinterp("
        val_array = values
        expr_tail = ","+driver_var_x+","+driver_var_y+")"
    
    expr = expr_opening + str(val_array) + expr_tail
    if len(expr) > 256: #Blender is dumb and only allows driver expressions with 256 characters or less, so we're going to have to use custom properties to hold large arrays instead of baking into the expression
        return (expr_opening + driver_var_array + expr_tail, False)
    return (expr, True)
        
def update_or_create_limit_constraints(obj,n,trans_comps_used={'L':{'X':(-0.5,0.5),'Y':(-0.5,0.5),'Z':None},'R':None,'S':None}):
    #Location
    trans_loc = trans_comps_used['L']
    con_loc = obj.constraints.get(n + "LocLimit")
    if trans_loc:                   #Location Control
        if con_loc is None:     #Make a new one
            con_loc = obj.constraints.new(type='LIMIT_LOCATION')
            con_loc.name = n + "LocLimit"
            con_loc.use_transform_limit = True
            con_loc.owner_space = 'LOCAL'
            con_loc.use_max_x, con_loc.use_max_y, con_loc.use_max_z, con_loc.use_min_x, con_loc.use_min_y, con_loc.use_min_z = True, True, True, True, True, True
        
        con_loc.min_x, con_loc.max_x = trans_loc['X'] if trans_loc['X'] else (0,0)
        con_loc.min_y, con_loc.max_y = trans_loc['Y'] if trans_loc['Y'] else (0,0)
        con_loc.min_z, con_loc.max_z = trans_loc['Z'] if trans_loc['Z'] else (0,0)
    elif con_loc:   #If we made a constraint before, but don't need it now, remove it.
        obj.constraints.remove(con_loc)
    #Scale
    trans_scale = trans_comps_used['S']
    con_scale = obj.constraints.get(n + "ScaleLimit")
    if trans_scale:                   #Location Control
        if con_scale is None:     #Make a new one
            con_scale = obj.constraints.new(type='LIMIT_SCALE')
            con_scale.name = n + "ScaleLimit"
            con_scale.use_transform_limit = True
            con_scale.owner_space = 'LOCAL'
            con_scale.use_max_x, con_scale.use_max_y, con_scale.use_max_z, con_scale.use_min_x, con_scale.use_min_y, con_scale.use_min_z = True, True, True, True, True, True
        
        con_scale.min_x, con_scale.max_x = trans_scale['X'] if trans_scale['X'] else (1,1)
        con_scale.min_y, con_scale.max_y = trans_scale['Y'] if trans_scale['Y'] else (1,1)
        con_scale.min_z, con_scale.max_z = trans_scale['Z'] if trans_scale['Z'] else (1,1)
    elif con_scale:   #If we made a constraint before, but don't need it now, remove it.
        obj.constraints.remove(con_scale)
#Returns the rotation of a custom shape given the control's transform components. There might be a better way to do this, but I'm just using this for now because it was easy...
def get_bone_custom_shape_rotation(trans_comps_used={'L':{'X':(-0.5,0.5),'Y':(-0.5,0.5),'Z':None},'R':None,'S':None}, is_base=False):
    loc_comps, rot_comps, scale_comps = trans_comps_used['L'], trans_comps_used['R'], trans_comps_used['S']
    if rot_comps and ((loc_comps is None and rot_comps is None) or not is_base):
        if rot_comps['Y']:	        return (0,0,0)
        elif rot_comps['Z']:	    return (-math.pi/2,0,0)
        else:                       return (0,math.pi/2,math.pi/2)     #X hopefully
    else:
        comps_to_use = loc_comps if loc_comps else scale_comps
        if comps_to_use is None:    return (math.pi/2,0,0)
        dimensions = 0
        for c in comps_to_use.values():
            if c: dimensions += 1
        if dimensions == 2:
            if comps_to_use['Z'] is None:	    return (math.pi/2,0,0)
            elif comps_to_use['Y'] is None:	return (0,0,0)
            else:	                        return (0,0,math.pi/2) #X is None hopefully
        elif dimensions == 1:
            if comps_to_use['X']:	    return (math.pi/2,0,0)
            elif comps_to_use['Y']:	    return (math.pi/2,0,math.pi/2) if is_base else (math.pi/2,0,0)
            else:                       return (0,math.pi/2,0) if is_base else (0,0,0)     #Z hopefully
        else:   #3 dimensions
            return (math.pi/2,0,0)

def get_or_create_base_obj(base_name='', trans_comps_used={'L':{'X':(-0.5,0.5),'Y':(-0.5,0.5),'Z':None},'R':None,'S':None}):
    trans_type = 'Scale' if trans_comps_used['S'] else 'Location' if trans_comps_used['L'] else 'Rotation' #Priority List: Scale, Location, Rotation
    dimensions = 0
    for v in trans_comps_used[trans_type[0]].values():
        if v:
            dimensions += 1
    if base_name == '':
        base_name = "GP2DMorphsShape" + trans_type + ('' if trans_type == 'Rotation' else (str(dimensions) + 'D')) + 'Base'
    
    base_object = bpy.context.scene.objects.get(base_name)
    if base_object is None:     #If the object doesn't exist, create it
        base_mesh = bpy.data.meshes.new(base_name)
        
        if trans_type == 'Location':
            if dimensions == 1:  #Horizontal 1 dimensional. Rotate later if it's vertical
                base_mesh.from_pydata([[-0.65,0,0],[-0.5,0,0.15],[0.5,0,0.15],[0.65,0,0],[0.5,0,-0.15],[-0.5,0,-0.15],[0,0,0.15],[0,0,-0.15]], 
                                        [[0,1],[1,2],[2,3],[3,4],[4,5],[5,0],[6,7]], [])
            elif dimensions == 2: #2 dimensional
                base_mesh.from_pydata([[-0.5,0,0.5],[0.5,0,0.5],[0.5,0,-0.5],[-0.5,0,-0.5],[0,0,-0.5],[0,0,0.5],[-0.5,0,0],[0.5,0,0]], 
                                        [[0,1],[1,2],[2,3],[3,0],[4,5],[6,7]], [])
            else: #dimensions == 3: #3 dimensional
                base_mesh.from_pydata([[-0.5,-0.5,0.5],[0.5,-0.5,0.5],[0.5,-0.5,-0.5],[-0.5,-0.5,-0.5],[-0.5,0.5,0.5],[0.5,0.5,0.5],[0.5,0.5,-0.5],[-0.5,0.5,-0.5],
                                       [0,-0.5,0.5],[0,-0.5,-0.5],[-0.5,-0.5,0],[0.5,-0.5,0],[0,0.5,0.5],[0,0.5,-0.5],[-0.5,0.5,0],[0.5,0.5,0],
                                       [-0.5,0,0.5],[0.5,0,0.5],[0.5,0,-0.5],[-0.5,0,-0.5]],  #Cross-section square
                                        [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7],
                                         [8,9],[10,11],[12,13],[14,15],[8,12],[9,13],[10,14],[11,15],[16,17],[17,18],[18,19],[19,16]
                                         ], [])
        elif trans_type == 'Rotation':
            segments = 32
            r = 0.5
            verts,edges,faces = create_circle_data(r)
            new_verts,new_edges,faces =  create_circle_data(r-0.05,vert_index_offset=segments)
            verts += new_verts
            edges += new_edges
            for i in range(0,segments,round(segments/16)):
                edges.append([i,i+segments])
                
            base_mesh.from_pydata(verts, edges, [])
        else:           #'Scale'
            if dimensions == 1:  #Horizontal 1 dimensional. Rotate later if it's vertical
                base_mesh.from_pydata([[-0.5,0,0.25],[0.5,0,0.25],[0.5,0,-0.25],[-0.5,0,-0.25],[-0.25,0,0.25],[-0.25,0,-0.25],[0.25,0,0.25],[0.25,0,-0.25],[0,0,0.25],[0,0,-0.25]], 
                                        [[0,1],[1,2],[2,3],[3,0],[4,5],[6,7],[8,9]], [])
            elif dimensions == 2: #2 dimensional
                base_mesh.from_pydata([[-0.5,0,0.5],[0.5,0,0.5],[0.5,0,-0.5],[-0.5,0,-0.5],[-0.25,0,0.25],[0.25,0,0.25],[0.25,0,-0.25],[-0.25,0,-0.25],[0,0,-0.5],[0,0,0.5],[-0.5,0,0],[0.5,0,0]], 
                                        [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[8,9],[10,11]], [])
            else: #dimensions == 3: #3 dimensional
                base_mesh.from_pydata([[-0.5,-0.5,0.5],[0.5,-0.5,0.5],[0.5,-0.5,-0.5],[-0.5,-0.5,-0.5],[-0.5,0.5,0.5],[0.5,0.5,0.5],[0.5,0.5,-0.5],[-0.5,0.5,-0.5],
                                       [0,-0.5,0.5],[0,-0.5,-0.5],[-0.5,-0.5,0],[0.5,-0.5,0],[0,0.5,0.5],[0,0.5,-0.5],[-0.5,0.5,0],[0.5,0.5,0],
                                       [-0.5,0,0.5],[0.5,0,0.5],[0.5,0,-0.5],[-0.5,0,-0.5],   #Cross-section square
                                       [-0.25,-0.25,0.25],[0.25,-0.25,0.25],[0.25,-0.25,-0.25],[-0.25,-0.25,-0.25],[-0.25,0.25,0.25],[0.25,0.25,0.25],[0.25,0.25,-0.25],[-0.25,0.25,-0.25]],  #Inner Cube
                                        [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7],
                                         [8,9],[10,11],[12,13],[14,15],[8,12],[9,13],[10,14],[11,15],
                                         [16,17],[17,18],[18,19],[19,16],
                                         [20,21],[21,22],[22,23],[23,20],[24,25],[25,26],[26,27],[27,24],[20,24],[21,25],[22,26],[23,27]], [])
            
        base_mesh.update()
        base_object = bpy.data.objects.new(base_name, base_mesh)
        collection_name = get_pref().custom_shapes_collection
        if collection_name == 'None':
            collection = bpy.context.collection
        else:
            collection = bpy.data.collections.get(collection_name)
            if collection is None:
                collection = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(collection)
                collection.hide_viewport = True
        collection.objects.link(base_object)
    return base_object

def get_or_create_knob_obj(knob_name='', trans_comps_used={'L':{'X':(-0.5,0.5),'Y':(-0.5,0.5),'Z':None},'R':None,'S':None}):
    trans_type = 'Rotation' if trans_comps_used['R'] else 'Scale' if trans_comps_used['S'] else 'Location' #Priority List: Rotation, Scale, Location
    dimensions = 0
    for v in trans_comps_used[trans_type[0]].values():
        if v:
            dimensions += 1
    if knob_name == '':
        knob_name = "GP2DMorphsShape" + trans_type + ('' if (trans_type == 'Rotation' or dimensions < 3) else (str(dimensions) + 'D')) + 'Knob'

    knob_object = bpy.context.scene.objects.get(knob_name)
    if knob_object is None:     #If the object doesn't exist, create it
        knob_mesh = bpy.data.meshes.new(knob_name)
        
        if trans_type == 'Location':
            if dimensions < 3:
                knob_mesh.from_pydata([[0,0,0.15],[0.15,0,0],[0,0,-0.15],[-0.15,0,0],[0,0,0.1],[0.1,0,0],[0,0,-0.1],[-0.1,0,0]], 
                                        [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4]], [])
            else:
                knob_mesh.from_pydata([[0,0,0.15],[0.15,0,0],[0,0,-0.15],[-0.15,0,0],[0,0,0.1],[0.1,0,0],[0,0,-0.1],[-0.1,0,0],
                                       [0,0.15,0],[0,-0.15,0],[0,0.1,0],[0,-0.1,0]], #3rd dimension
                                        [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],
                                         [8,0],[8,1],[8,2],[8,3],[9,0],[9,1],[9,2],[9,3],[10,4],[10,5],[10,6],[10,7],[11,4],[11,5],[11,6],[11,7]], [])
        elif trans_type == 'Rotation':
            vert_index_offset = 0
            segments = 32
            r = 0.25
            ####LARGER PART CIRCLE####
            verts, edges, faces = create_circle_data(r,segments,3,vert_index_offset)
            vert_index_offset += segments-3
            ####DIAL####
            first_dial_index = vert_index_offset
            r /= 2 #Radius of the circle
            new_verts, new_edges, faces = create_circle_data(r,segments,11,vert_index_offset)
            verts += new_verts
            edges += new_edges
            vert_index_offset += segments-11
            verts.append((0,0,0.5))
            edges.append((vert_index_offset-1,vert_index_offset))
            edges.append((vert_index_offset,first_dial_index))
            vert_index_offset += 1
            ####INNER DIAL CIRCLE####
            r /= 2
            new_verts, new_edges, faces = create_circle_data(r,segments,0,vert_index_offset)
            verts += new_verts
            edges += new_edges
            vert_index_offset += segments
            ####SUPER TINY INNER CIRCLE####
            r /= 8
            new_verts, new_edges, faces = create_circle_data(r,math.ceil(segments/8),0,vert_index_offset)
            verts += new_verts
            edges += new_edges
            knob_mesh.from_pydata(verts, edges, [])
        else:           #'Scale'
            if dimensions < 3:
                knob_mesh.from_pydata([[-0.25,0,0.25],[0.25,0,0.25],[0.25,0,-0.25],[-0.25,0,-0.25],[-0.2,0,0.2],[0.2,0,0.2],[0.2,0,-0.2],[-0.2,0,-0.2]], 
                                        [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4]], [])
            else:
                knob_mesh.from_pydata([[-0.25,-0.25,0.25],[0.25,-0.25,0.25],[0.25,-0.25,-0.25],[-0.25,-0.25,-0.25],[-0.25,0.25,0.25],[0.25,0.25,0.25],[0.25,0.25,-0.25],[-0.25,0.25,-0.25],
                                       [-0.2,-0.2,0.2],[0.2,-0.2,0.2],[0.2,-0.2,-0.2],[-0.2,-0.2,-0.2],[-0.2,0.2,0.2],[0.2,0.2,0.2],[0.2,0.2,-0.2],[-0.2,0.2,-0.2]], 
                                    [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7],
                                     [8,9],[9,10],[10,11],[11,8],[12,13],[13,14],[14,15],[15,12],[8,12],[9,13],[10,14],[11,15]], [])
            
        knob_mesh.update()
        knob_object = bpy.data.objects.new(knob_name, knob_mesh)
        collection_name = get_pref().custom_shapes_collection
        if collection_name == 'None':
            collection = bpy.context.collection
        else:
            collection = bpy.data.collections.get(collection_name)
            if collection is None:
                collection = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(collection)
                collection.hide_viewport = True
        collection.objects.link(knob_object)
    return knob_object
#Radius, Number of Segments in the circle, Number of points to not add (starting and centered at the top), the number of verts already added to the mesh so that our edges are right
def create_circle_data(r=1,segments=32,exclude_points=0,vert_index_offset=0):
    twopi = math.pi*2
    verts = []
    half_exclude = math.ceil(exclude_points/2)
    for i in range(half_exclude,segments-(exclude_points-half_exclude)): #Start at 2 and not doing the past point because we don't want the top 3 points in the circle for aesthetics
        angle = (twopi) * i / segments
        verts.append((math.sin(angle)*r, 0, math.cos(angle)*r))
    edges = [(i, i+1) for i in range(vert_index_offset,vert_index_offset+segments-exclude_points-1)]
    if exclude_points == 0:
        edges.append((vert_index_offset + segments - 1, vert_index_offset))
    return(verts,edges,[])

def update_ctrl_bone(bone, trans_comps_used={'L':{'X':(-0.5,0.5),'Y':(-0.5,0.5),'Z':None},'R':None,'S':None},use_custom_shapes=True,use_control_constraints=True):
    if bone is None:    return
    if use_control_constraints:
        update_or_create_limit_constraints(bone,bone.name,trans_comps_used)
    if use_custom_shapes:
        bone.custom_shape = get_or_create_knob_obj(trans_comps_used=trans_comps_used)
        bone.custom_shape_rotation_euler = get_bone_custom_shape_rotation(trans_comps_used,False)
        bone.use_custom_shape_bone_size = False
        base_bone = bone.parent
        if base_bone is not None:
            base_bone.custom_shape = get_or_create_base_obj(trans_comps_used=trans_comps_used)
            base_bone.custom_shape_rotation_euler = get_bone_custom_shape_rotation(trans_comps_used,True)
            base_bone.use_custom_shape_bone_size = False
#Operators can't have PointerProperties, and by extension PropertyGroups, so we're doing this now. Look at what you've made me do, blender developers. LOOK AT IT
def generate_2d_morphs_with_pg(pg,node_name='',pass_index=-1,use_custom_shapes=True,use_control_constraints=True,mode='ANIMATE'):
    bpy.ops.gp2dmorphs.generate_2d_morphs(
        props_set=True,
        def_frame_start=pg.def_frame_start,
        def_frames_w=pg.def_frames_w,
        def_frames_h=pg.def_frames_h,
        gen_frame_start=pg.gen_frame_start,
        gen_frames_w=pg.gen_frames_w,
        gen_frames_h=pg.gen_frames_h,
        generate_frames=pg.generate_frames_or_location,
        generate_control=pg.generate_control_or_rotation,
        generate_driver=pg.generate_driver_or_scale,
        mirror=pg.mirror,
        mirror_point_mode=pg.mirror_point_mode,
        mirror_use_axis_x=pg.mirror_use_axis_x,
        mirror_use_axis_y=pg.mirror_use_axis_y,
        mirror_use_axis_z=pg.mirror_use_axis_z,
        mirror_direction=pg.mirror_direction,
        mirror_custom_point=pg.mirror_custom_point,
        mirror_paired_layers=pg.mirror_paired_layers,
        interpolate=pg.interpolate,
        interp_type_left=pg.interp_type_left,
        interp_type_right=pg.interp_type_right,
        interp_type_up=pg.interp_type_up,
        interp_type_down=pg.interp_type_down,
        interp_easing_left=pg.interp_easing_left,
        interp_easing_right=pg.interp_easing_right,
        interp_easing_up=pg.interp_easing_up,
        interp_easing_down=pg.interp_easing_down,
        stroke_order_changes=pg.stroke_order_changes,
        stroke_order_change_offset_factor_horizontal=pg.stroke_order_change_offset_factor_horizontal,
        stroke_order_change_offset_factor_vertical=pg.stroke_order_change_offset_factor_vertical,
        control_type=pg.control_type,
        control_armature_name_x='' if pg.control_armature_x is None else pg.control_armature_x.name,
        control_bone_name_x=pg.control_bone_name_x,
        control_bone_transform_type_x=pg.control_bone_transform_type_x,
        control_range_start_x=pg.control_range_start_x,
        control_range_end_x=pg.control_range_end_x,
        control_range_flip_x=pg.control_range_flip_x,
        control_armature_name_y='' if pg.control_armature_y is None else pg.control_armature_y.name,
        control_bone_name_y=pg.control_bone_name_y,
        control_bone_transform_type_y=pg.control_bone_transform_type_y,
        control_range_start_y=pg.control_range_start_y,
        control_range_end_y=pg.control_range_end_y,
        control_range_flip_y=pg.control_range_flip_y,
        node_name=node_name,
        pass_index=pass_index,
        use_custom_shapes=use_custom_shapes,
        use_control_constraints=use_control_constraints,
        mode=mode
    )

def generate_2d_bone_morphs_with_pg(pg,morph_armature_obj_name,generate_control,use_custom_shapes=True,use_control_constraints=True,mode='ANIMATE'):
    bpy.ops.gp2dmorphs.generate_2d_bone_morphs(
        props_set=True,
        def_frame_start=pg.def_frame_start,
        def_frames_w=pg.def_frames_w,
        def_frames_h=pg.def_frames_h,
        generate_location=pg.generate_frames_or_location,
        generate_rotation=pg.generate_control_or_rotation,
        generate_scale=pg.generate_driver_or_scale,
        generate_control=generate_control,
        control_type=pg.control_type,
        control_armature_name_x='' if pg.control_armature_x is None else pg.control_armature_x.name,
        control_bone_name_x=pg.control_bone_name_x,
        control_bone_transform_type_x=pg.control_bone_transform_type_x,
        control_range_start_x=pg.control_range_start_x,
        control_range_end_x=pg.control_range_end_x,
        control_range_flip_x=pg.control_range_flip_x,
        control_armature_name_y='' if pg.control_armature_y is None else pg.control_armature_y.name,
        control_bone_name_y=pg.control_bone_name_y,
        control_bone_transform_type_y=pg.control_bone_transform_type_y,
        control_range_start_y=pg.control_range_start_y,
        control_range_end_y=pg.control_range_end_y,
        control_range_flip_y=pg.control_range_flip_y,
        morph_armature_obj_name=morph_armature_obj_name,
        use_custom_shapes=use_custom_shapes,
        use_control_constraints=use_control_constraints,
        mode=mode
    )

def generate_morph_frames(self, context):
    if self.layers is None or len(self.layers) == 0 or self.gp_obj is None: return False
    original_gp_select = self.gp_obj.select_get()
    if not original_gp_select:
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        self.gp_obj.select_set(True)
    context.view_layer.objects.active = self.gp_obj
    bpy.ops.object.mode_set(mode='EDIT_GPENCIL', toggle=False)
    gp = self.gp_obj.data
    original_autolock = gp.use_autolock_layers
    original_active_layer = gp.layers.active
    multiple_layers = len(self.layers) > 1
    op_layers = 'ALL' if multiple_layers else 'ACTIVE'
    if multiple_layers:
        original_layers_status = []
        if original_autolock:  #Turning off autolock so we can use the layers will unlock all layers so it has to be done after we record the layers' statuses, but before locking unused layers
            for l in gp.layers:
                original_layers_status.append((l, l.lock, l.hide))
            gp.use_autolock_layers = False
            for l in gp.layers:    
                if l in self.layers:
                    l.lock = False
                    l.hide = False
                else:
                    l.lock = True
        else:                   #No autolock, so we're free to do it all in one loop.
            for l in gp.layers:
                original_layers_status.append((l, l.lock, l.hide))
                if l in self.layers:
                    l.lock = False
                    l.hide = False
                else:
                    l.lock = True
    else:
        original_layer_locked = self.layers[0].lock
        self.layers[0].lock = False
    gp.layers.active = self.layers[0]
    dw, dh = self.def_frames_w, self.def_frames_h
    gw, gh = self.gen_frames_w, self.gen_frames_h
    gpdx, gpdy = (gw/dw), (gh/dh)       #Generated Per Defined for X and Y axis
    def_frames = {} #dict of key Layer, value 2D array of defined frames
    def_frame_end = def_array_pos_to_def_frame_pos(self.def_frames_w-1,self.def_frames_h-1,self.def_frame_start,dw)
    gen_frame_end = gen_array_pos_to_gen_frame_pos(self.gen_frames_w-1,self.gen_frames_h-1,self.gen_frame_start,gw)
    #Setup our array of defined frames for easy access later
    for layer in self.layers:
        if layer:
            def_frames_array = [[None for y in range(dh)] for x in range(dw)]
            for frame in layer.frames:
                n = frame.frame_number
                if n > def_frame_end: #We're out of range.
                    layer.frames.remove(frame)
                elif n >= self.def_frame_start:
                    n -= self.def_frame_start
                    dy = math.floor(n/(dw+1))
                    dx = n-(dy*(dw+1))
                    if dx < dw and dy < dh:
                        def_frames_array[dx][dy] = frame
            
            def_frames[layer] = def_frames_array
    tmp_offset = math.ceil(gen_frame_end/1000+1)*1000     #The area where we'll temporarily put frames for manipulating before moving them to their final location
    def_used_x = 0
    #Generate 'vertical' frame slices
    for dx in range(dw):
        if (dx*gpdx >= def_used_x):
            frames_found = False
            last_frame_num = -1000
            def_used_y = 0
            for dy in range(dh):    #For each defined frame in this vertical slice, move to the offset location plus the generated y offset and interpolate the rest of the generated vertical
                if (dy*gpdy >= def_used_y):
                    new_frame_num = tmp_offset + def_pos_offset_to_gen_pos_offset(dy,dh,gh)
                    for layer,frames in def_frames.items():
                        src_frame = frames[dx][dy]
                        if src_frame is None:   #The defined frame is undefined D:
                            if (dx == 0 or dx == dw-1) and (dy == 0 or dy == dh-1):     #If the undefined frame is a corner, we got big problems. Otherwise, we good. Move along.
                                if multiple_layers: reset_gp_layers_status(gp,multiple_layers,original_layers_status=original_layers_status,original_active_layer=original_active_layer,original_autolock=original_autolock)
                                else:               reset_gp_layers_status(gp,multiple_layers,original_layer_locked=original_layer_locked,original_active_layer=original_active_layer,original_autolock=original_autolock)
                                self.report({'ERROR'}, f"Corner Frame ({dx}, {dy}) of layer '{layer.info}' at frame {def_array_pos_to_def_frame_pos(dx,dy,self.def_frame_start,dw)} not defined.")
                                return
                            continue
                        else:   #Valid defined frame. Duplicate  and interpolate for this section of the vertical if needed.
                            if len(src_frame.strokes) == 0 and frames_found and new_frame_num > last_frame_num+1 and self.interpolate: #Blank frame. 
                                for i in range(new_frame_num-1,last_frame_num,-1):  #We're going to have to duplicate the frame manually because interpolation won't work.
                                    layer.frames.new(i)
                            layer.frames.copy(src_frame).frame_number = new_frame_num
                        
                    if frames_found and new_frame_num > last_frame_num+1 and self.interpolate:  #If there are frames before this one, and there is space, get to interpolating
                        context.scene.frame_current = new_frame_num-1
                        if dy == dh-1:  #Up direction
                            interpolate_frames(self, context, self.interp_type_up,self.interp_easing_up,direction=(0,1),layers=op_layers)
                        elif dy == 1:   #Down direction
                            interpolate_frames(self, context, self.interp_type_down,
                                                                'EASE_IN' if self.interp_easing_down == 'EASE_OUT'   #Flip since the down direction is technically going up
                                                                else 'EASE_OUT' if self.interp_easing_down == 'EASE_IN'
                                                                else self.interp_easing_down,
                                                                direction=(0,-1),layers=op_layers)
                        else:
                            interpolate_frames(self, context,direction=(0,1) if dy > (dh-1)/2 else (0,-1),layers=op_layers)
                    last_frame_num = new_frame_num
                    frames_found = True
                    def_used_y += 1
            
            gx = def_pos_offset_to_gen_pos_offset(dx,dw,gw)
            for layer in def_frames.keys():
                for fi in range(len(layer.frames)-1,-1,-1): #For each new frame we just made by duplicating defined frames and interpolating, move to its final generated resting place
                    frame = layer.frames[fi]
                    if frame.frame_number < tmp_offset: #We're done looking for frames to move
                        break
                    gy = frame.frame_number-tmp_offset #Generated Y position
                    frame.keyframe_type = 'KEYFRAME'
                    frame.frame_number = gen_array_pos_to_gen_frame_pos(gx,gy,self.gen_frame_start,gw)
            def_used_x += 1
    
    refresh_GP_dopesheet(context)
    #Generate 'horizontal' frame slices from 'vertical' slices made earlier
    if self.interpolate and gw > dw and gw > 1:
        gfpdx = gen_per_def(gw,dw)        #Generated Frames per Defined frames on the 'horizontal' (X) axis
        last_frame_num = -1000
        for gy in range(gh):
            vertical_frame_offset = self.gen_frame_start + gy*(gw+1)
            last_frame_num = vertical_frame_offset
            for dx in range(1,dw):
                if (new_frame_num := vertical_frame_offset + def_pos_offset_to_gen_pos_offset(dx,dw,gw) - 1) > last_frame_num:
                    context.scene.frame_current = new_frame_num
                    if dx == dw-2:  #Right direction
                        interpolate_frames(self, context, type=self.interp_type_right,easing=self.interp_easing_right,direction=(1,0),layers=op_layers)
                    elif dx == 0:   #Left direction
                        interpolate_frames(self, context, type=self.interp_type_left,easing= 'EASE_IN' if self.interp_easing_left == 'EASE_OUT'   #Flip since the left direction is technically going right
                                                                                                    else ('EASE_OUT' if self.interp_easing_left == 'EASE_IN'
                                                                                                    else self.interp_easing_left),
                                                                                                    direction=(-1,0),layers=op_layers)
                    else:           #Center
                        interpolate_frames(self, context,direction=(1,0) if dx > (dw-1)/2 else (-1,0),layers=op_layers)
                last_frame_num = new_frame_num + 1
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    if multiple_layers: reset_gp_layers_status(gp,multiple_layers,original_layers_status=original_layers_status,original_active_layer=original_active_layer,original_autolock=original_autolock)
    else:               reset_gp_layers_status(gp,multiple_layers,original_layer_locked=original_layer_locked,original_active_layer=original_active_layer,original_autolock=original_autolock)
    self.gp_obj.select_set(original_gp_select)
    return True

def interpolate_frames(self, context, type='LINEAR', easing='EASE_OUT', direction=(1,0),layers='ACTIVE'):
        if self.stroke_order_changes:
            vertical = direction[1] != 0
            #Now go back and change the To frame and some frames between to have the original To frame stroke order
            f = self.stroke_order_change_offset_factor_vertical if vertical else self.stroke_order_change_offset_factor_horizontal
            if direction[0] == -1 or direction[1] == -1:    #If the direction is left or down, flip the factor so that the factor is relative to the center of the grid
                f = 1-f
            print(direction)
            interpolate_sequence_view_independent(context,layers=layers,type=type,easing=easing,stroke_order_changes=True,stroke_order_change_offset_factor=f)
            return
        #No stroke order changes, so just interpolate like normal
        interpolate_sequence_view_independent(context,layers=layers,type=type,easing=easing)
        return
    
def reset_gp_layers_status(gp,multiple_layers=True,original_layers_status=None,original_layer_locked=False,original_active_layer=None,original_autolock=False):
    gp.use_autolock_layers = original_autolock
    if multiple_layers:
        for status in original_layers_status:
            l = status[0]
            l.lock = status[1]
            l.hide = status[2]
    else:
        gp.layers.active.lock = original_layer_locked
    gp.layers.active = original_active_layer

def interpolate_sequence_view_independent(context=None, step=1, layers='ACTIVE', interpolate_selected_only=False, exclude_breakdowns=False, flip='AUTO', 
                                          smooth_steps=1, smooth_factor=0.0, type='LINEAR', easing='AUTO', back=1.702, amplitude=0.15, period=0.15, stroke_order_changes=False,stroke_order_change_offset_factor=0.5):
    #We need to override the context area sometimes because interpolate_sequence can only be run in the 3D viewport.
    if context is None:
        context = bpy.context
    area_type = 'VIEW_3D' # change this to use the correct Area Type context you want to process in
    areas  = [area for area in context.window.screen.areas if area.type == area_type]
    if len(areas) <= 0:
        raise Exception(f"Make sure an Area of type {area_type} is open or visible in your screen!")
    with context.temp_override(
        window=context.window,
        area=areas[0],
        region=[region for region in areas[0].regions if region.type == 'WINDOW'][0],
        screen=context.window.screen
    ):
        if stroke_order_changes:
            bpy.ops.gpencil.interpolate_sequence_disorderly(step=step,layers=layers,interpolate_selected_only=interpolate_selected_only,
                                                exclude_breakdowns=exclude_breakdowns,flip=flip,smooth_steps=smooth_steps,smooth_factor=smooth_factor,
                                                type=type,easing=easing,back=back,amplitude=amplitude,period=period,stroke_order_change_offset_factor=stroke_order_change_offset_factor)
        else:
            bpy.ops.gpencil.interpolate_sequence(step=step,layers=layers,interpolate_selected_only=interpolate_selected_only,
                                                exclude_breakdowns=exclude_breakdowns,flip=flip,smooth_steps=smooth_steps,smooth_factor=smooth_factor,
                                                type=type,easing=easing,back=back,amplitude=amplitude,period=period)
#Regular lerp. In the future, might have more types, but for now it's just lerp.
# def interp(a,b,alpha, type='LINEAR'):
#     return bl_math.lerp(a,b,alpha)
#Returns value in list of values larger than 2 interpolated between the two values around it. Used by drivers to control armature bone transforms with controls in one dimension
def interp_multi(val_array, alpha, type='LINEAR'):
    alpha = bl_math.clamp(alpha)
    if alpha == 1:
        return val_array[len(val_array)-1]
    max_pos = len(val_array)-1
    factor = alpha*max_pos
    array_pos = math.floor(factor)
    factor -= array_pos
    return bl_math.lerp(val_array[array_pos],val_array[array_pos+1],factor)
#Returns value in 2x2 grid interpolated between the four values around it. Used by drivers to control armature bone transforms with controls
def biinterp(val_array, x, y, type='LINEAR'):
    x = bl_math.clamp(x)
    y = bl_math.clamp(y)
    val_x_a = bl_math.lerp(val_array[0][0],val_array[1][0],x)
    val_x_b = bl_math.lerp(val_array[0][1],val_array[1][1],x)
    return bl_math.lerp(val_x_a,val_x_b,y)
#Returns value in grid larger than 2x2 interpolated between the four values around it. Used by drivers to control armature bone transforms with controls
def biinterp_multi(val_array, x, y, type='LINEAR'):
    x = bl_math.clamp(x)
    y = bl_math.clamp(y)
    max_x = len(val_array)-1
    max_y = len(val_array[0])-1
    factor_x = x*max_x
    factor_y = y*max_y
    array_x = math.floor(factor_x)
    array_y = math.floor(factor_y)
    factor_x -= array_x
    factor_y -= array_y
    if array_x != max_x:        #If the x pos isn't on the right edge
        val_x_a = bl_math.lerp(val_array[array_x][array_y],val_array[array_x+1][array_y],factor_x)
        if array_y != max_y:    #If the y pos isn't on the upper edge
            val_x_b = bl_math.lerp(val_array[array_x][array_y+1],val_array[array_x+1][array_y+1],factor_x)
            return bl_math.lerp(val_x_a,val_x_b,factor_y)
        else:                   #No need to do vertical interpolation
            return val_x_a
    else:                       #No need to do horizontal interpolation
        val_x_a = val_array[array_x][array_y]
        if array_y != max_y:    #If the y pos isn't on the upper edge
            val_x_b = val_array[array_x][array_y+1]
            return bl_math.lerp(val_x_a,val_x_b,factor_y)
        else:                   #No nead to do vertical interpolation
            return val_x_a

def gpencil_menu_additions(self, context):
    self.layout.operator(GP2DMORPHS_OT_interpolate_sequence_disorderly.bl_idname)

_classes = [
    GP2DMORPHS_OT_generate_2d_morphs,
    GP2DMORPHS_OT_generate_2d_bone_morphs,
    GP2DMORPHS_OT_convert_defined_range,
    GP2DMORPHS_OT_interpolate_sequence_disorderly,
    GP2DMORPHS_OT_remove_morph_drivers,
    GP2DMORPHS_OT_remove_morph_properties,
    GP2DMORPHS_OT_set_frame_by_defined_pos,
    GP2DMORPHS_OT_fill_defined_frames,
    GP2DMORPHS_OT_set_all_interp_types,
    GP2DMORPHS_OT_set_all_interp_easings,
]

def register_driver_funcs():
    #bpy.app.driver_namespace['interp'] = interp      Not used yet. Uncomment if we ever implement non-linear interpolation
    bpy.app.driver_namespace['interp_multi'] = interp_multi
    bpy.app.driver_namespace['biinterp'] = biinterp
    bpy.app.driver_namespace['biinterp_multi'] = biinterp_multi

@persistent
def load_handler(dummy):
    register_driver_funcs()
    for obj in bpy.data.objects:    #For some reason, drivers that use my custom interp functions won't work after reloading the file, and need the dependencies to be refreshed.
        if obj.type == 'ARMATURE' and obj.animation_data:
            for fcurve in obj.animation_data.drivers:
                fcurve.driver.expression = fcurve.driver.expression #Would be nice if we didn't have to do this
    
def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_edit_gpencil.append(gpencil_menu_additions)
    bpy.types.VIEW3D_MT_draw_gpencil.append(gpencil_menu_additions)
    bpy.app.handlers.load_post.append(load_handler)
    register_driver_funcs()

def unregister():
    bpy.types.VIEW3D_MT_edit_gpencil.remove(gpencil_menu_additions)
    bpy.types.VIEW3D_MT_draw_gpencil.remove(gpencil_menu_additions)
    bpy.app.handlers.load_post.remove(load_handler)
    for cls in _classes:
        bpy.utils.unregister_class(cls)