import bpy, math, time
from bpy.props import IntProperty, BoolProperty, EnumProperty

class GP2DMORPHS_OT_generate_2d_morphs(bpy.types.Operator):
    bl_idname = "gp2dmorphs.generate_2d_morphs"    
    bl_label = "Generate 2D Morphs"
    bl_description = "Using predefined frames made by the user, creates a 'grid' of interpolated frames and a Time Offset Modifier, Control and Driver to manipulate the frames"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        run_ops_without_view_layer_update(self.run)
        return {'FINISHED'}


    def run(self):
        context = bpy.context
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        gp_obj = context.view_layer.objects.active
        
        original_mode = gp_obj.mode             #Grab the current mode so we can switch back after
        original_frame = bpy.context.scene.frame_current

        if GP2DMORPHSVars.generate_frames:
            self.generate_frames(context, gp_obj)
        ctrl_obj = None
        if GP2DMORPHSVars.generate_control:
            ctrl_obj = self.generate_control(context, gp_obj)
        if GP2DMORPHSVars.generate_driver:
            self.generate_driver(context, gp_obj, ctrl_obj)

        context.view_layer.objects.active = gp_obj
        bpy.ops.object.mode_set(mode=original_mode, toggle=False)
        bpy.context.scene.frame_current = original_frame

    def generate_frames(self, context, gp_obj):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        dw, dh = GP2DMORPHSVars.def_frames_w, GP2DMORPHSVars.def_frames_h
        gw, gh = GP2DMORPHSVars.gen_frames_w, GP2DMORPHSVars.gen_frames_h
        gp = gp_obj.data
        bpy.ops.object.mode_set(mode='EDIT_GPENCIL', toggle=False)
        layer = gp.layers.active
        def_frames = [[None for y in range(dh)] for x in range(dw)]
        def_frames_end = def_array_pos_to_def_frame_pos(GP2DMORPHSVars.def_frames_w-1,GP2DMORPHSVars.def_frames_h-1)
        gen_frames_end = gen_array_pos_to_gen_frame_pos(GP2DMORPHSVars.gen_frames_w-1,GP2DMORPHSVars.gen_frames_h-1)
        #Setup our array of defined frames for easy access later
        for frame in layer.frames:
            n = frame.frame_number
            if n > def_frames_end: #We're out of range.
                layer.frames.remove(frame)
            if n >= GP2DMORPHSVars.def_frame_start:
                n -= GP2DMORPHSVars.def_frame_start
                f_y = math.floor(n/(dw+1))
                f_x = n-(f_y*(dw+1))
                if f_x < dw and f_y < dh:
                    def_frames[f_x][f_y] = frame
        tmp_offset = math.ceil(gen_frames_end/1000+1)*1000     #The area where we'll temporarily put frames for manipulating before moving them to their final location
        #Generate 'vertical' frame slices
        for dx in range(dw):
            frames_found = False
            last_frame = None
            for dy in range(max(min(gh,2),dh)):    #For each defined frame in this vertical slice, move to the offset location plus the generated y offset and interpolate the rest of the generated vertical
                src_frame = def_frames[dx][min(dh-1, dy)]
                if src_frame is None:   #The defined frame is undefined D:
                    if (dx == 0 or dx == dw-1) and (dy == 0 or dy == dh-1):     #If the undefined frame is a corner, we got big problems. Otherwise, we good. Move along.
                        for fi in range(len(layer.frames)-1,-1,-1): #We failed, so delete the generated frames we made
                            frame = layer.frames[fi]
                            if frame.frame_number < GP2DMORPHSVars.gen_frame_start: #We're done looking for frames to kill
                                break
                            layer.frames.remove(frame)
                        self.report({'ERROR'}, 'Corner Frame (' + str(dx) + ", " + str(dy) + ") not defined.")
                        return
                    continue
                else:   #Valid defined frame. Duplicate  and interpolate for this section of the vertical if needed.
                    new_frame = layer.frames.copy(src_frame)
                    new_frame.frame_number = tmp_offset + def_frame_pos_offset_to_gen_frame_pos_offset(dy,False)
                    if frames_found and GP2DMORPHSVars.interpolate and new_frame.frame_number > last_frame.frame_number+1:  #If there are frames before this one, and there is space, get to interpolating
                        context.scene.frame_current = new_frame.frame_number-1
                        #self.interpolate_sequence_disorderly(context, (0,1 if dy == dh-1 else (-1 if dy == 1 else 0)),last_frame,new_frame)
                        if dy == dh-1:  #Up direction
                            self.interpolate_sequence_disorderly(context, GP2DMORPHSVars.interp_type_up,GP2DMORPHSVars.interp_easing_up,last_frame,new_frame,direction=(0,1))
                        elif dy == 1:   #Down direction
                            self.interpolate_sequence_disorderly(context, GP2DMORPHSVars.interp_type_down,
                                                                'EASE_IN' if GP2DMORPHSVars.interp_easing_down == 'EASE_OUT'   #Flip since the down direction is technically going up
                                                                else ('EASE_OUT' if GP2DMORPHSVars.interp_easing_down == 'EASE_IN'
                                                                else GP2DMORPHSVars.interp_easing_down),last_frame,new_frame,
                                                                direction=(0,-1))
                        else:
                            self.interpolate_sequence_disorderly(context,frame_from=last_frame,frame_to=new_frame,direction=(1,0) if dy > (dh-1)/2 else (-1,0))
                    last_frame = new_frame
                    frames_found = True
            
            gx = def_frame_pos_offset_to_gen_frame_pos_offset(dx)
            for fi in range(len(layer.frames)-1,-1,-1): #For each new frame we just made by duplicating defined frames and interpolating, move to its final generated resting place
                frame = layer.frames[fi]
                if frame.frame_number < tmp_offset: #We're done looking for frames to move
                    break
                gy = frame.frame_number-tmp_offset #Generated Y position
                frame.keyframe_type = 'KEYFRAME'
                frame.frame_number = gen_array_pos_to_gen_frame_pos(gx,gy)
        
        refresh_GP_dopesheet()
        #Generate 'horizontal' frame slices from 'vertical' slices made earlier
        if GP2DMORPHSVars.interpolate:
            gfpdx = gen_per_def(gw,dw)        #Generated Frames per Defined frames on the 'horizontal' (X) axis
            for gy in range(gh):
                vertical_frame_offset = GP2DMORPHSVars.gen_frame_start + gy*(gw+1)
                for dx in range(dw-1):
                    context.scene.frame_current = vertical_frame_offset + dx*gfpdx + 1
                    #self.interpolate_sequence_disorderly(context, (1 if dx == dw-1 else (-1 if dx == 1 else 0),0))  #A relic from the past when I wanted clean code
                    if dx == dw-2:  #Right direction
                        self.interpolate_sequence_disorderly(context, type=GP2DMORPHSVars.interp_type_right,easing=GP2DMORPHSVars.interp_easing_right,direction=(1,0))
                    elif dx == 0:   #Left direction
                        self.interpolate_sequence_disorderly(context, type=GP2DMORPHSVars.interp_type_left,easing= 'EASE_IN' if GP2DMORPHSVars.interp_easing_left == 'EASE_OUT'   #Flip since the left direction is technically going right
                                                                                                    else ('EASE_OUT' if GP2DMORPHSVars.interp_easing_left == 'EASE_IN'
                                                                                                    else GP2DMORPHSVars.interp_easing_left),
                                                                                                    direction=(-1,0))
                    else:
                        self.interpolate_sequence_disorderly(context,direction=(1,0) if dx > (dw-1)/2 else (-1,0))
        return
    
    def interpolate_sequence_disorderly(self, context, type='LINEAR', easing='EASE_OUT', frame_from=None, frame_to=None, direction=(0,0)):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        if GP2DMORPHSVars.stroke_order_changes:
            vertical = direction[1] != 0
            gp = context.view_layer.objects.active.data
            layer = gp.layers.active
            if frame_from is None or frame_to is None:      #At least one of the frames is undefined. Find them.
                for frame in layer.frames:
                    if frame.frame_number < context.scene.frame_current:
                        if frame_from is None or frame.frame_number > frame_from.frame_number:
                            frame_from = frame
                    else:
                        if frame_to is None or frame.frame_number < frame_to.frame_number:
                            frame_to = frame
                if frame_from is None or frame_to is None:  #Failure. We'll get 'em next time.
                    print("One of two frames to test order wasn't found :(")
                    bpy.ops.gpencil.interpolate_sequence(type=type,easing=easing)
                    return

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
                bpy.ops.gpencil.interpolate_sequence(type=type,easing=easing)
                #Now go back and change the To frame and some frames between to have the original To frame stroke order
                f = GP2DMORPHSVars.stroke_order_change_offset_factor_vertical if vertical else GP2DMORPHSVars.stroke_order_change_offset_factor_horizontal
                if direction[0] == -1 or direction[1] == -1:    #If the direction is left or down, flip the factor so that the factor is relative to the center of the grid
                    f = 1-f
                reorder_num = round((gen_per_def(GP2DMORPHSVars.gen_frames_h,GP2DMORPHSVars.def_frames_h)-1 if vertical else gen_per_def(GP2DMORPHSVars.gen_frames_w,GP2DMORPHSVars.def_frames_w)-1)*f)
                for fi in range(len(layer.frames)-1,-1,-1): #For each new frame we just made by duplicating defined frames and interpolating
                    frame = layer.frames[fi]
                    if frame.frame_number < frame_from.frame_number: #We're done looking for frames to reorder
                        break
                    if frame.frame_number > frame_from.frame_number+reorder_num and frame.frame_number <= frame_to.frame_number:    #This is one of the frames we want to reorder
                        context.scene.frame_set(frame.frame_number)
                        self.strokes_order(frame.strokes,order_change,undo=True)
                return
        #No stroke order changes, so just interpolate like normal
        bpy.ops.gpencil.interpolate_sequence(type=type,easing=easing)
        return
    
    def get_stroke_index(self, strokes, target, expected_index=0):
        if self.strokes_equal(strokes.values()[expected_index], target):
            return expected_index
        for i in range(expected_index+1,len(strokes.values())):
            if self.strokes_equal(strokes.values()[i], target):
                return i
        for i in range(expected_index-1,-1,-1):
            if self.strokes_equal(strokes.values()[i], target):
                return i
        return -1

    def strokes_equal(self, s1, s2):
        return s1.time_start == s2.time_start
    
    def strokes_order(self, strokes, order_change, undo=False):
        bpy.ops.gpencil.select_all(action='DESELECT')
        stroke_order_old = list()
        for i in range(len(order_change)-1,-1,-1):
            s = strokes[order_change.index(i) if undo else order_change[i]]
            stroke_order_old.append(s)

        for s in stroke_order_old:
            s.select = True
            bpy.ops.gpencil.stroke_arrange(direction='BOTTOM')
            s.select = False

    def generate_control(self, context, gp_obj):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        gp = gp_obj.data
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        layer = gp.layers.active
        control_name = (gp_obj.name + layer.info + "Control")
        active_collection = bpy.context.collection
        cursor_location = bpy.context.scene.cursor.location
        #Base Mesh
        base_name = (control_name if GP2DMORPHSVars.control_type == 'OBJECT' else ("GP2DMorphsShape" + ("H" if GP2DMORPHSVars.gen_frames_h == 1 else ("V" if GP2DMORPHSVars.gen_frames_w == 1 else "")))) + 'Base'
        base_object = context.scene.objects.get(base_name)
        if not base_object:     #If the object doesn't exist, create it
            base_mesh = bpy.data.meshes.new(base_name)
            if GP2DMORPHSVars.gen_frames_h == 1:    #Horizontal 1 dimensional morph 
                base_mesh.from_pydata([[-0.65,0,0],[-0.5,0,0.15],[0.5,0,0.15],[0.65,0,0],[0.5,0,-0.15],[-0.5,0,-0.15],[0,0,0.15],[0,0,-0.15]], 
                                      [[0,1],[1,2],[2,3],[3,4],[4,5],[5,0],[6,7]], [])
            elif GP2DMORPHSVars.gen_frames_w == 1:  #Vertical 1 dimensional morph
                base_mesh.from_pydata([[0,0,-0.65],[0.15,0,-0.5],[0.15,0,0.5],[0,0,0.65],[-0.15,0,0.5],[-0.15,0,-0.5],[0.15,0,0],[-0.15,0,0]], 
                                      [[0,1],[1,2],[2,3],[3,4],[4,5],[5,0],[6,7]], [])
            else:
                base_mesh.from_pydata([[-0.5,0,0.5],[0.5,0,0.5],[0.5,0,-0.5],[-0.5,0,-0.5],[0,0,-0.5],[0,0,0.5],[-0.5,0,0],[0.5,0,0]], 
                                      [[0,1],[1,2],[2,3],[3,0],[4,5],[6,7]], [])
            base_mesh.update()
            base_object = bpy.data.objects.new(base_name + 'Base', base_mesh)
            active_collection.objects.link(base_object)
        #Knob Mesh
        knob_name = (control_name if GP2DMORPHSVars.control_type == 'OBJECT' else "GP2DMorphsShape") + 'Knob'
        knob_object = context.scene.objects.get(knob_name)
        if knob_object is None:     #If the object doesn't exist, create it
            vertices = [[0,0,0.15],[0.15,0,0],[0,0,-0.15],[-0.15,0,0],[0,0,0.1],[0.1,0,0],[0,0,-0.1],[-0.1,0,0]]
            edges = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4]]
            knob_mesh = bpy.data.meshes.new(knob_name)
            knob_mesh.from_pydata(vertices, edges, [])
            knob_mesh.update()
            knob_object = bpy.data.objects.new(knob_name, knob_mesh)
            active_collection.objects.link(knob_object)
        if GP2DMORPHSVars.control_type == 'OBJECT':
            #Set up object constraints and relations
            knob_object.parent = base_object
            con = knob_object.constraints.new(type='LIMIT_LOCATION')
            con.name = control_name + "Limit"
            con.use_max_x, con.use_max_y, con.use_max_z, con.use_min_x, con.use_min_y, con.use_min_z = True, True, True, True, True, True
            if GP2DMORPHSVars.gen_frames_h == 1: #Horizontal 1 dimensional morph
                con.max_x, con.max_y, con.max_z = 0.5, 0, 0
                con.min_x, con.min_y, con.min_z = -0.5, 0, 0
            elif GP2DMORPHSVars.gen_frames_w == 1:  #Vertical 1 dimensional morph
                con.max_x, con.max_y, con.max_z = 0, 0, 0.5
                con.min_x, con.min_y, con.min_z = 0, 0, -0.5
            else:
                con.max_x, con.max_y, con.max_z = 0.5, 0, 0.5
                con.min_x, con.min_y, con.min_z = -0.5, 0, -0.5
            con.use_transform_limit = True
            con.owner_space = 'LOCAL'
            base_object.location = cursor_location
        else:   #Create control bones
            base_object.hide_set(True)
            knob_object.hide_set(True)
            armatureObj = GP2DMORPHSVars.control_armature
            if armatureObj is None:
                armature = bpy.data.armatures.new("ControlArmature")
                armatureObj = bpy.data.objects.new("ControlArmature", armature)
                active_collection.objects.link(armatureObj)
            else:
                armature = armatureObj.data
            context.view_layer.objects.active = armatureObj

            bpy.ops.object.mode_set(mode = 'EDIT')
            base_bone_name = control_name+"Base"    #Base
            base_bone = armature.edit_bones.get(base_bone_name)
            if base_bone is None:
                base_bone = armature.edit_bones.new(base_bone_name)
                base_bone.use_deform = False
                base_bone.head = cursor_location
                base_bone.tail = [cursor_location.x,cursor_location.y+1,cursor_location.z]
                bpy.ops.object.mode_set(mode = 'POSE')
                base_bone_pose = armatureObj.pose.bones[base_bone_name]
                base_bone_pose.custom_shape = base_object
                base_bone_pose.use_custom_shape_bone_size = False
                bpy.ops.object.mode_set(mode = 'EDIT')
            knob_bone_name = control_name+"Knob"    #Knob
            knob_bone = armature.edit_bones.get(knob_bone_name)
            if knob_bone is None:
                knob_bone = armature.edit_bones.new(control_name+"Knob")
                knob_bone.use_deform = False
                knob_bone.parent = base_bone
                knob_bone.head = cursor_location
                knob_bone.tail = [cursor_location.x,cursor_location.y+0.5,cursor_location.z]
                bpy.ops.object.mode_set(mode = 'POSE')
                knob_bone_pose = armatureObj.pose.bones[knob_bone_name]
                knob_bone_pose.custom_shape = knob_object
                knob_bone_pose.use_custom_shape_bone_size = False
                #Constraint
                con = knob_bone_pose.constraints.new(type='LIMIT_LOCATION')
                con.name = control_name + "Limit"
                con.use_max_x, con.use_max_y, con.use_max_z, con.use_min_x, con.use_min_y, con.use_min_z = True, True, True, True, True, True
                if GP2DMORPHSVars.gen_frames_h == 1: #Horizontal 1 dimensional morph
                    con.max_x, con.max_y, con.max_z = 0.5, 0, 0
                    con.min_x, con.min_y, con.min_z = -0.5, 0, 0
                elif GP2DMORPHSVars.gen_frames_w == 1:  #Vertical 1 dimensional morph
                    con.max_x, con.max_y, con.max_z = 0, 0, 0.5
                    con.min_x, con.min_y, con.min_z = 0, 0, -0.5
                else:
                    con.max_x, con.max_y, con.max_z = 0.5, 0, 0.5
                    con.min_x, con.min_y, con.min_z = -0.5, 0, -0.5
                con.use_transform_limit = True
                con.owner_space = 'LOCAL'
            else:
                knob_bone_pose = armatureObj.pose.bones.get(knob_bone_name)

            return knob_bone_pose
        return knob_object

    def generate_driver(self, context, gp_obj, ctrl_obj):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        gp = gp_obj.data
        layer = gp.layers.active
        #GP Time Offset Modifier
        mod_name = gp_obj.name + layer.info + "TO"
        mod = gp_obj.grease_pencil_modifiers.get(mod_name)
        if not mod:         #If we don't have a modifier yet, make one
            mod = gp_obj.grease_pencil_modifiers.new(name=mod_name, type='GP_TIME')
            mod.layer = layer.info
            mod.mode = 'FIX'
        #Driver
        mod.driver_remove("offset")
        driver = mod.driver_add("offset").driver
        #Driver Vars
        var_x = driver.variables.new()
        var_x.type='TRANSFORMS'
        var_x.name="posX"
        var_x.targets[0].transform_type = 'LOC_X'
        var_x.targets[0].transform_space = 'LOCAL_SPACE'

        var_y = driver.variables.new()
        var_y.type='TRANSFORMS'
        var_y.name="posY"
        var_y.targets[0].transform_type = 'LOC_Z'   #The variable is for the Y location in the array of frames, which is mapped to the Z location because you usually GPencil sideways instead of top-down
        var_y.targets[0].transform_space = 'LOCAL_SPACE'
        
        if GP2DMORPHSVars.control_type == 'OBJECT':
            var_x.targets[0].id = ctrl_obj
            var_y.targets[0].id = ctrl_obj
        elif ctrl_obj is not None:      # 'BONE'
            var_x.targets[0].id = ctrl_obj.id_data
            var_x.targets[0].bone_target = ctrl_obj.name
            var_y.targets[0].id = ctrl_obj.id_data
            var_y.targets[0].bone_target = ctrl_obj.name
        
        driver.expression =  str(GP2DMORPHSVars.gen_frame_start) + "+round((posX+.5)*" + str(GP2DMORPHSVars.gen_frames_w-1) + ")+round((posY+.5)*" + str(GP2DMORPHSVars.gen_frames_h-1) + ")*" + str(GP2DMORPHSVars.gen_frames_w+1)

class GP2DMORPHS_OT_set_frame_by_defined_pos(bpy.types.Operator):
    bl_idname = "gp2dmorphs.set_frame_by_defined_pos"    
    bl_label = "Set Frame by Defined Position"
    bl_description = "Sets the current frame in the timeline to the frame of the associated frame in the Defined Frames array"
    pos_x: IntProperty(
        name="Position X",
        description="X Position of the frame in the Defined Frames array",
        default=0
    )
    pos_y: IntProperty(
        name="Position X",
        description="X Position of the frame in the Defined Frames array",
        default=0
    )

    def execute(self, context):
        context.scene.frame_current = def_array_pos_to_def_frame_pos(self.pos_x,self.pos_y)
        return {'FINISHED'}
    
class GP2DMORPHS_OT_fill_defined_frames(bpy.types.Operator):
    bl_idname = "gp2dmorphs.fill_defined_frames"    
    bl_label = "Fill Defined Frames"
    bl_description = "Fill Defined Frames array with duplicates of the current frame"
    bl_options = {'UNDO'}
    fill_edges: BoolProperty(
        name="Fill Edges",
        description="X Position of the frame in the Defined Frames array",
        default=0
    )
    def execute(self, context):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        dw, dh = GP2DMORPHSVars.def_frames_w, GP2DMORPHSVars.def_frames_h
        gw, gh = GP2DMORPHSVars.gen_frames_w, GP2DMORPHSVars.gen_frames_h
        src_frame = None
        gp = context.view_layer.objects.active.data
        layer = gp.layers.active
        def_frames = [[None for x in range(dw)] for y in range(dh)]
        #bpy.ops.object.mode_set(mode='EDIT_GPENCIL', toggle=False)
                
        for frame in layer.frames:
            n = frame.frame_number
            if n == context.scene.frame_current: #This is the frame we'll be copying
                src_frame = frame
            n -= GP2DMORPHSVars.def_frame_start
            f_y = math.floor(n/(dw+1))
            f_x = n-(f_y*(dw+1))
            if f_x < dw and f_y < dh:
                def_frames[f_x][f_y] = frame    #This frame is already defined, so don't overwrite it later when we do our frame duplication
        if src_frame == None:   #No frame to duplicate
            self.report({'ERROR'}, "No frame found at the selected frame and layer. Make sure the timeline's current frame is set to the frame you wish to copy")
            return {'FINISHED'}
        for dx in range(dw):
            for dy in range(dh):
                if def_frames[dx][dy] is None:
                    new_frame = layer.frames.copy(src_frame)
                    new_frame.frame_number = def_array_pos_to_def_frame_pos(dx,dy)
        refresh_GP_dopesheet()
        return {'FINISHED'}

class GP2DMORPHS_OT_set_all_interp_types(bpy.types.Operator):
    bl_idname = "gp2dmorphs.set_all_interp_types"    
    bl_label = "Set All Interpolation Types"
    bl_description = "Sets the interpolation type for all directions at once"
    
    interp_type_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['type'].enum_items if ot.identifier != 'CUSTOM']
    type: EnumProperty(
        name="Type",
        description="The type of interpolation to use in this direction",
        items = interp_type_enum,
        default='LINEAR',
        
    )

    def execute(self, context):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        GP2DMORPHSVars.interp_type_left = self.type
        GP2DMORPHSVars.interp_type_right = self.type
        GP2DMORPHSVars.interp_type_up = self.type
        GP2DMORPHSVars.interp_type_down = self.type
        return {'FINISHED'}
    
class GP2DMORPHS_OT_set_all_interp_easings(bpy.types.Operator):
    bl_idname = "gp2dmorphs.set_all_interp_easings"    
    bl_label = "Set All Interpolation Easings"
    bl_description = "Sets the interpolation easing for all directions at once"
    
    interp_easing_enum = [(ot.identifier, ot.name, ot.description, ot.icon, ot.value) for ot in bpy.ops.gpencil.interpolate_sequence.get_rna_type().properties['easing'].enum_items if ot.identifier != 'AUTO']
    easing: EnumProperty(
        name="easing",
        description="The easing for interpolation to use in this direction",
        items = interp_easing_enum,
        default='EASE_OUT',
        
    )

    def execute(self, context):
        GP2DMORPHSVars = context.scene.gp2dmorphs_panel_settings
        GP2DMORPHSVars.interp_easing_left = self.easing
        GP2DMORPHSVars.interp_easing_right = self.easing
        GP2DMORPHSVars.interp_easing_up = self.easing
        GP2DMORPHSVars.interp_easing_down = self.easing
        return {'FINISHED'}

def def_array_pos_to_def_frame_pos(x,y):
    GP2DMORPHSVars = bpy.context.scene.gp2dmorphs_panel_settings
    return GP2DMORPHSVars.def_frame_start + y*(GP2DMORPHSVars.def_frames_w+1) + x

def gen_array_pos_to_gen_frame_pos(x,y):
    GP2DMORPHSVars = bpy.context.scene.gp2dmorphs_panel_settings
    return GP2DMORPHSVars.gen_frame_start + y*(GP2DMORPHSVars.gen_frames_w+1) + x

def def_frame_pos_offset_to_gen_frame_pos_offset(pos,horizontal=True):
    GP2DMORPHSVars = bpy.context.scene.gp2dmorphs_panel_settings
    if horizontal:
        return math.floor(pos/max(1,GP2DMORPHSVars.def_frames_w-1)*max(1,GP2DMORPHSVars.gen_frames_w-1))
    else:
        return math.floor(pos/max(1,GP2DMORPHSVars.def_frames_h-1)*max(1,GP2DMORPHSVars.gen_frames_h-1))
    
def gen_per_def(generated,defined):
    if generated <= 1:
        return 1
    if defined <= 1:
        return generated-2
    return math.floor(generated/(defined-1))

#This function is thanks to Tomreggae from https://blender.stackexchange.com/questions/204636/moving-gpencil-frames-in-time-with-python-causes-viewport-issues
def refresh_GP_dopesheet() :  
    #dirty way to force blender to refresh frames indices in grease pencil dopesheet
    if bpy.context.object.type == 'GPENCIL' :
        cur_areatype = str(bpy.context.area.type)
        bpy.context.area.type = 'DOPESHEET_EDITOR'
        cur_space_mode = str(bpy.context.area.spaces[0].mode)
        bpy.context.area.spaces[0].mode = 'GPENCIL'
        bpy.ops.action.mirror(type = 'XAXIS')
        bpy.ops.action.mirror(type = 'XAXIS')
        bpy.context.area.spaces[0].mode = cur_space_mode
        bpy.context.area.type = cur_areatype

#This function is thanks to scurest from https://blender.stackexchange.com/questions/7358/python-performance-with-blender-operators
def run_ops_without_view_layer_update(func):
    from bpy.ops import _BPyOpsSubModOp

    view_layer_update = _BPyOpsSubModOp._view_layer_update

    def dummy_view_layer_update(context):
        pass

    try:
        _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update

        func()

    finally:
        _BPyOpsSubModOp._view_layer_update = view_layer_update
        
_classes = [
    GP2DMORPHS_OT_generate_2d_morphs,
    GP2DMORPHS_OT_set_frame_by_defined_pos,
    GP2DMORPHS_OT_fill_defined_frames,
    GP2DMORPHS_OT_set_all_interp_types,
    GP2DMORPHS_OT_set_all_interp_easings
]
    
def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in _classes:
        bpy.utils.unregister_class(cls)