# ================================================================
#    Style Engine - Main Pie Menu
#    Alt+W hotkey for quick access to all Style Engine features
# ================================================================

import bpy
from bpy.types import Menu, Operator


def get_quality_params(quality_preset):
    """
    Get workflow parameters for quality preset.
    
    Args:
        quality_preset: 'SKETCH', 'FAST', 'BALANCED', or 'DETAILED'
    
    Returns:
        dict: Parameters for workflow nodes
    """
    presets = {
        'SKETCH': {
            'mesh_steps': 10,
            'octree_resolution': 96,
            'num_chunks': 32000,
            'max_faces': 20000,
            'view_size': 512,
            'texture_steps': 4,
            'texture_size': 512,
        },
        'FAST': {
            'mesh_steps': 15,
            'octree_resolution': 128,
            'num_chunks': 32000,
            'max_faces': 50000,
            'view_size': 512,
            'texture_steps': 6,
            'texture_size': 512,
        },
        'BALANCED': {
            'mesh_steps': 25,
            'octree_resolution': 256,
            'num_chunks': 64000,
            'max_faces': 200000,
            'view_size': 768,
            'texture_steps': 10,
            'texture_size': 1024,
        },
        'DETAILED': {
            'mesh_steps': 50,
            'octree_resolution': 512,
            'num_chunks': 64000,
            'max_faces': 500000,
            'view_size': 1024,
            'texture_steps': 30,
            'texture_size': 2048,
        },
    }
    
    return presets.get(quality_preset, presets['BALANCED'])


# ----------------------------------------------------------------
# PLACEHOLDER OPERATORS (To be implemented later)
# ----------------------------------------------------------------

class WM_OT_ProjectTextureScene(Operator):
    """Project AI texture onto selected objects from camera view"""
    bl_idname = "style_engine.project_texture_scene"
    bl_label = "Project Texture"
    bl_description = "Project current_ai.png from camera perspective onto selected objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Use the existing project_texture operator which does camera projection
        bpy.ops.style_engine.project_texture()
        return {'FINISHED'}


class WM_OT_UVTexture(Operator):
    """Generate UV textures for selected mesh using AI (Hunyuan 3D 2.1)"""
    bl_idname = "style_engine.uv_texture"
    bl_label = "UV Texture"
    bl_description = "Generate UV-mapped textures for selected mesh using AI and current_ai.png as reference"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        from . import runcomfy_deployment
        from pathlib import Path
        import tempfile
        import time
        
        # Check if in GCS mode
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "UV Texture requires GCS mode (Self-Hosted ComfyUI)")
            print("[UV Texture] ❌ Feature requires GCS backend mode")
            return {'CANCELLED'}
        
        # Check if object is selected
        if not context.active_object:
            self.report({'ERROR'}, "No object selected. Please select a mesh object.")
            print("[UV Texture] ❌ No active object")
            return {'CANCELLED'}
        
        obj = context.active_object
        
        # Check if it's a mesh
        if obj.type != 'MESH':
            self.report({'ERROR'}, f"Selected object '{obj.name}' is not a mesh (type: {obj.type})")
            print(f"[UV Texture] ❌ Object is {obj.type}, not MESH")
            return {'CANCELLED'}
        
        print(f"[UV Texture] ============================================")
        print(f"[UV Texture] STARTING UV TEXTURE GENERATION")
        print(f"[UV Texture] Object: {obj.name}")
        print(f"[UV Texture] ============================================")
        
        try:
            # Step 1: Export mesh as GLB
            temp_dir = Path(tempfile.gettempdir()) / "styleengine_uv"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            glb_filename = f"{obj.name}_{int(time.time())}.glb"
            glb_path = temp_dir / glb_filename
            
            print(f"[UV Texture] Step 1: Exporting mesh to GLB...")
            print(f"[UV Texture]   Export path: {glb_path}")
            
            # Export using Blender's GLTF exporter
            bpy.ops.export_scene.gltf(
                filepath=str(glb_path),
                use_selection=True,
                export_format='GLB',
                export_texcoords=True,
                export_normals=True,
                export_materials='EXPORT',
                export_cameras=False,
                export_lights=False
            )
            
            file_size = glb_path.stat().st_size / 1024
            print(f"[UV Texture] ✓ Exported: {file_size:.1f} KB")
            
            # Step 2: Upload mesh to ComfyUI server
            print(f"[UV Texture] Step 2: Uploading mesh to server...")
            server_client = runcomfy_deployment.get_server_client()
            upload_result = server_client.upload_mesh(str(glb_path), overwrite=True)
            
            uploaded_mesh_name = upload_result['name']
            print(f"[UV Texture] ✓ Uploaded as: {uploaded_mesh_name}")
            
            # Step 3: Get current_ai.png and upload it
            print(f"[UV Texture] Step 3: Uploading reference image...")
            temp_img_dir = workspace_setup.get_temp_directory(context)
            current_ai_path = temp_img_dir / "current_ai.png"
            
            if not current_ai_path.exists():
                self.report({'ERROR'}, "current_ai.png not found. Generate an image first.")
                print(f"[UV Texture] ❌ current_ai.png not found at {current_ai_path}")
                return {'CANCELLED'}
            
            img_upload = server_client.upload_image(str(current_ai_path), overwrite=True)
            uploaded_img_name = img_upload['name']
            print(f"[UV Texture] ✓ Image uploaded as: {uploaded_img_name}")
            
            # Step 4: Load and configure workflow
            print(f"[UV Texture] Step 4: Loading workflow...")
            addon_dir = Path(__file__).parent
            workflow_path = addon_dir / "workflows" / "Object" / "objectUVTexture.json"
            
            if not workflow_path.exists():
                self.report({'ERROR'}, f"Workflow not found: {workflow_path.name}")
                print(f"[UV Texture] ❌ Workflow missing: {workflow_path}")
                return {'CANCELLED'}
            
            import json
            with open(workflow_path, 'r') as f:
                workflow_json = json.load(f)
            
            print(f"[UV Texture] ✓ Loaded workflow: {workflow_path.name}")
            
            # Step 5: Override nodes with quality parameters
            print(f"[UV Texture] Step 5: Configuring workflow nodes...")
            
            # Get quality parameters
            style_props = context.scene.style_engine_props
            quality = style_props.object_quality if hasattr(style_props, 'object_quality') else 'BALANCED'
            params = get_quality_params(quality)
            
            # Apply quality parameters (texture only, mesh is from user)
            workflow_json["20"]["inputs"]["view_size"] = params['view_size']
            workflow_json["20"]["inputs"]["steps"] = params['texture_steps']
            workflow_json["20"]["inputs"]["texture_size"] = params['texture_size']
            
            print(f"[UV Texture] ✓ Quality: {quality}")
            print(f"[UV Texture] ✓ Texture: view={params['view_size']}, steps={params['texture_steps']}, size={params['texture_size']}")
            
            # Get ComfyUI path from preferences
            prefs = context.preferences.addons['styleengine'].preferences
            comfy_base_path = prefs.comfy_path if prefs.comfy_path else ""
            
            # If not set, try to detect from server or use common defaults
            if not comfy_base_path:
                # Try common paths based on OS
                import platform
                if platform.system() == 'Windows':
                    comfy_base_path = "C:/ComfyUI"
                else:
                    comfy_base_path = "/home/Juan/ComfyUI"  # Linux/GCS default
                print(f"[UV Texture] ⚠️ ComfyUI path not set in preferences, using default: {comfy_base_path}")
                print(f"[UV Texture] Set in: Edit → Preferences → Style Engine → Advanced → ComfyUI Path")
            
            # Construct full server path for mesh (uploads go to input/ directory)
            mesh_server_path = f"{comfy_base_path}/input/{uploaded_mesh_name}"
            
            workflow_json["55"]["inputs"]["load_path"] = mesh_server_path  # Full path!
            workflow_json["14"]["inputs"]["image"] = uploaded_img_name  # Image name only (LoadImage handles this)
            workflow_json["32"]["inputs"]["string"] = f"UV_{obj.name}_{int(time.time())}"  # Output name
            
            print(f"[UV Texture] ✓ Node 55 (mesh): {mesh_server_path}")
            print(f"[UV Texture] ✓ Node 14 (image): {uploaded_img_name}")
            
            # Step 6: Submit workflow (NON-BLOCKING)
            print(f"[UV Texture] Step 6: Submitting workflow to server...")
            self.report({'INFO'}, f"Generating UV textures for {obj.name}... (check console)")
            
            result = server_client.queue_prompt(workflow_json)
            prompt_id = result['prompt_id']
            print(f"[UV Texture] ✓ Queued: {prompt_id}")
            
            # Store workflow for progress bar node name lookup
            from . import progress_bar
            progress_bar.set_current_workflow(workflow_json)
            
            print(f"[UV Texture] ⏳ Processing in background (1-2 minutes)...")
            print(f"[UV Texture] Watch console for completion message")
            
            # Capture variables for callback (avoid stale references)
            output_name = workflow_json["32"]["inputs"]["string"]
            obj_name = obj.name
            obj_location = obj.location.copy()
            download_path = temp_dir / f"textured_{glb_filename}"
            
            # Step 7: Start background polling (NON-BLOCKING)
            from . import runcomfy_polling
            
            # Create completion callback
            def on_uv_texture_complete(success, result=None, error=None, workflow_type=None):
                """Called when UV texture generation completes (runs in background)"""
                print(f"[UV Texture] ============================================")
                print(f"[UV Texture] GENERATION COMPLETE")
                print(f"[UV Texture] ============================================")
                
                if not success:
                    print(f"[UV Texture] ❌ Generation failed: {error}")
                    return
                
                try:
                    # Step 8: Download textured mesh
                    print(f"[UV Texture] Step 8: Downloading textured mesh...")
                    
                    # Find output GLB in history
                    outputs = result.get('outputs', {})
                    output_filename = None
                    
                    # Look for GLB output
                    for node_id, node_output in outputs.items():
                        # Check if this node has file outputs
                        if isinstance(node_output, dict):
                            if 'gltf' in node_output or 'filename' in node_output:
                                files = node_output.get('gltf', node_output.get('filename', []))
                                if files and isinstance(files, list) and len(files) > 0:
                                    output_filename = files[0].get('filename') if isinstance(files[0], dict) else files[0]
                                    if output_filename:
                                        print(f"[UV Texture] Found output in node {node_id}: {output_filename}")
                                        break
                    
                    if not output_filename:
                        # Fallback: construct expected filename (use captured variable)
                        output_filename = f"{output_name}_00001_.glb"
                        print(f"[UV Texture] Using constructed filename: {output_filename}")
                    
                    # Download (use captured download_path)
                    download_success = server_client.download_mesh(
                        output_filename, 
                        str(download_path),
                        file_type="output"
                    )
                    
                    if not download_success:
                        print(f"[UV Texture] ❌ Download failed")
                        return
                    
                    print(f"[UV Texture] ✓ Downloaded: {download_path.name}")
                    
                    # Step 9: Import textured mesh back into Blender
                    print(f"[UV Texture] Step 9: Importing textured mesh into scene...")
                    
                    # Store original selection
                    original_selected = list(bpy.context.selected_objects)
                    
                    # Import GLB
                    bpy.ops.import_scene.gltf(filepath=str(download_path))
                    
                    # Get newly imported objects
                    newly_imported = [o for o in bpy.context.selected_objects if o not in original_selected]
                    
                    if newly_imported:
                        new_obj = newly_imported[0]
                        new_obj.name = f"{obj_name}_Textured"  # Use captured name
                        
                        # Position next to original (use captured location)
                        new_obj.location = obj_location
                        new_obj.location.x += 2.0  # Offset to the right
                        
                        print(f"[UV Texture] ✓ Imported: {new_obj.name}")
                        
                        # Save mesh to Models library
                        workspace_setup.save_mesh_to_library(bpy.context, download_path, mesh_type='uv_textured')
                        
                        print(f"[UV Texture] ✅ UV textured mesh created: {new_obj.name}")
                    else:
                        print(f"[UV Texture] ⚠️ Mesh imported but not found in scene")
                    
                    print(f"[UV Texture] ============================================")
                    print(f"[UV Texture] UV TEXTURE GENERATION COMPLETE")
                    print(f"[UV Texture] ============================================")
                    
                except Exception as e:
                    print(f"[UV Texture] ❌ Error during download/import: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register for background polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',  # Server mode
                request_id=prompt_id,
                callback=on_uv_texture_complete,
                workflow_type='uv_texture'
            )
            
            print(f"[UV Texture] ✅ Submitted! Processing in background...")
            print(f"[UV Texture] Blender will remain responsive")
            print(f"[UV Texture] ============================================")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"UV Texture failed: {e}")
            print(f"[UV Texture] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class WM_OT_CreateObject(Operator):
    """Create 3D mesh object from current_ai.png using Hunyuan 3D 2.1"""
    bl_idname = "style_engine.create_object"
    bl_label = "Create Object"
    bl_description = "Generate a new 3D mesh (no texture) from current_ai.png using AI"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        from . import runcomfy_deployment
        from pathlib import Path
        import tempfile
        import time
        
        # Check if in GCS mode
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Create Object requires GCS mode (Self-Hosted ComfyUI)")
            print("[Create Object] ❌ Feature requires GCS backend mode")
            return {'CANCELLED'}
        
        print(f"[Create Object] ============================================")
        print(f"[Create Object] STARTING 3D MESH GENERATION")
        print(f"[Create Object] ============================================")
        
        try:
            # Step 1: Get current_ai.png
            print(f"[Create Object] Step 1: Getting reference image...")
            temp_img_dir = workspace_setup.get_temp_directory(context)
            current_ai_path = temp_img_dir / "current_ai.png"
            
            if not current_ai_path.exists():
                self.report({'ERROR'}, "current_ai.png not found. Generate an image first.")
                print(f"[Create Object] ❌ current_ai.png not found at {current_ai_path}")
                return {'CANCELLED'}
            
            print(f"[Create Object] ✓ Found: {current_ai_path.name}")
            
            # Step 2: Upload image to server
            print(f"[Create Object] Step 2: Uploading image to server...")
            server_client = runcomfy_deployment.get_server_client()
            img_upload = server_client.upload_image(str(current_ai_path), overwrite=True)
            uploaded_img_name = img_upload['name']
            print(f"[Create Object] ✓ Uploaded as: {uploaded_img_name}")
            
            # Step 3: Load workflow
            print(f"[Create Object] Step 3: Loading workflow...")
            addon_dir = Path(__file__).parent
            workflow_path = addon_dir / "workflows" / "Object" / "objectCreateObject.json"
            
            if not workflow_path.exists():
                self.report({'ERROR'}, f"Workflow not found: {workflow_path.name}")
                print(f"[Create Object] ❌ Workflow missing: {workflow_path}")
                return {'CANCELLED'}
            
            import json
            with open(workflow_path, 'r') as f:
                workflow_json = json.load(f)
            
            print(f"[Create Object] ✓ Loaded workflow: {workflow_path.name}")
            
            # Step 4: Override nodes with quality parameters
            print(f"[Create Object] Step 4: Configuring workflow nodes...")
            
            # Get quality parameters
            style_props = context.scene.style_engine_props
            quality = style_props.object_quality if hasattr(style_props, 'object_quality') else 'BALANCED'
            params = get_quality_params(quality)
            
            workflow_json["14"]["inputs"]["image"] = uploaded_img_name
            workflow_json["32"]["inputs"]["string"] = f"StyleEngine_Mesh_{int(time.time())}"
            workflow_json["37"]["inputs"]["seed"] = int(time.time() * 1000) % 999999999999
            
            # Apply quality parameters
            workflow_json["37"]["inputs"]["steps"] = params['mesh_steps']
            workflow_json["9"]["inputs"]["octree_resolution"] = params['octree_resolution']
            workflow_json["9"]["inputs"]["num_chunks"] = params['num_chunks']
            workflow_json["30"]["inputs"]["value"] = params['max_faces']
            
            output_name = workflow_json["32"]["inputs"]["string"]
            print(f"[Create Object] ✓ Quality: {quality}")
            print(f"[Create Object] ✓ Mesh steps: {params['mesh_steps']}, Octree: {params['octree_resolution']}, Max faces: {params['max_faces']}")
            print(f"[Create Object] ✓ Node 14 (image): {uploaded_img_name}")
            print(f"[Create Object] ✓ Node 32 (output): {output_name}")
            
            # Step 5: Submit workflow (NON-BLOCKING)
            print(f"[Create Object] Step 5: Submitting workflow to server...")
            self.report({'INFO'}, f"Generating 3D mesh from current_ai.png... (check console)")
            
            result = server_client.queue_prompt(workflow_json)
            prompt_id = result['prompt_id']
            print(f"[Create Object] ✓ Queued: {prompt_id}")
            
            # Store workflow for progress bar node name lookup
            from . import progress_bar
            progress_bar.set_current_workflow(workflow_json)
            
            print(f"[Create Object] ⏳ Processing in background (1-2 minutes)...")
            
            # Capture variables for callback
            temp_dir = Path(tempfile.gettempdir()) / "styleengine_create"
            temp_dir.mkdir(parents=True, exist_ok=True)
            download_path = temp_dir / f"{output_name}.glb"
            
            # Step 6: Start background polling
            from . import runcomfy_polling
            
            def on_create_object_complete(success, result=None, error=None, workflow_type=None):
                """Called when mesh generation completes"""
                print(f"[Create Object] ============================================")
                print(f"[Create Object] GENERATION COMPLETE")
                print(f"[Create Object] ============================================")
                
                if not success:
                    print(f"[Create Object] ❌ Generation failed: {error}")
                    return
                
                try:
                    # Find output GLB from Node 44 (saves untextured mesh)
                    print(f"[Create Object] Step 6: Downloading mesh...")
                    outputs = result.get('outputs', {})
                    print(f"[Create Object] DEBUG: Available nodes: {list(outputs.keys())}")
                    
                    output_filename = None
                    subfolder = ""
                    
                    # Node 44 (Hy3D21ExportMesh) saves the mesh
                    # Check if it appears in outputs with 'gltf' key
                    if '44' in outputs:
                        node_44_output = outputs['44']
                        print(f"[Create Object] DEBUG: Node 44 output: {json.dumps(node_44_output, indent=2)}")
                        
                        if isinstance(node_44_output, dict) and 'gltf' in node_44_output:
                            files = node_44_output['gltf']
                            if files and isinstance(files, list) and len(files) > 0:
                                file_info = files[0]
                                output_filename = file_info.get('filename') if isinstance(file_info, dict) else file_info
                                subfolder = file_info.get('subfolder', '') if isinstance(file_info, dict) else ''
                                print(f"[Create Object] ✓ Found GLB: {output_filename}")
                    
                    if not output_filename:
                        # Fallback: construct from Node 32
                        output_filename = f"{output_name}_00001_.glb"
                        print(f"[Create Object] ⚠️ Using constructed filename: {output_filename}")
                    
                    # Download
                    download_success = server_client.download_mesh(
                        output_filename,
                        str(download_path),
                        subfolder=subfolder,
                        file_type="output"
                    )
                    
                    if not download_success:
                        print(f"[Create Object] ❌ Download failed")
                        return
                    
                    print(f"[Create Object] ✓ Downloaded: {download_path.name}")
                    
                    # Step 7: Import into Blender
                    print(f"[Create Object] Step 7: Importing mesh into scene...")
                    
                    original_selected = list(bpy.context.selected_objects)
                    
                    # Import GLB
                    bpy.ops.import_scene.gltf(filepath=str(download_path))
                    
                    # Get newly imported
                    newly_imported = [o for o in bpy.context.selected_objects if o not in original_selected]
                    
                    if newly_imported:
                        new_obj = newly_imported[0]
                        new_obj.name = f"AI_Mesh_{int(time.time())}"
                        
                        # Position at world origin
                        new_obj.location = (0, 0, 0)
                        
                        print(f"[Create Object] ✓ Imported: {new_obj.name}")
                        
                        # Save mesh to Models library
                        workspace_setup.save_mesh_to_library(bpy.context, download_path, mesh_type='mesh')
                        
                        print(f"[Create Object] ✅ 3D mesh created from AI!")
                    else:
                        print(f"[Create Object] ⚠️ Mesh imported but not found")
                    
                    print(f"[Create Object] ============================================")
                    print(f"[Create Object] MESH GENERATION COMPLETE")
                    print(f"[Create Object] ============================================")
                    
                except Exception as e:
                    print(f"[Create Object] ❌ Error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register for polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_create_object_complete,
                workflow_type='create_object'
            )
            
            print(f"[Create Object] ✅ Submitted! Processing in background...")
            print(f"[Create Object] ============================================")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Create Object failed: {e}")
            print(f"[Create Object] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class WM_OT_CreateTexturedObject(Operator):
    """Create textured 3D mesh from current_ai.png using Hunyuan 3D 2.1"""
    bl_idname = "style_engine.create_textured_object"
    bl_label = "Create Textured Object"
    bl_description = "Generate a new 3D mesh WITH UV-mapped textures from current_ai.png"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        from . import runcomfy_deployment
        from pathlib import Path
        import tempfile
        import time
        
        # Check if in GCS mode
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Create Textured Object requires GCS mode")
            print("[Create Textured] ❌ Feature requires GCS backend mode")
            return {'CANCELLED'}
        
        print(f"[Create Textured] ============================================")
        print(f"[Create Textured] STARTING TEXTURED MESH GENERATION")
        print(f"[Create Textured] ============================================")
        
        try:
            # Step 1: Get current_ai.png
            print(f"[Create Textured] Step 1: Getting reference image...")
            temp_img_dir = workspace_setup.get_temp_directory(context)
            current_ai_path = temp_img_dir / "current_ai.png"
            
            if not current_ai_path.exists():
                self.report({'ERROR'}, "current_ai.png not found. Generate an image first.")
                print(f"[Create Textured] ❌ current_ai.png not found")
                return {'CANCELLED'}
            
            print(f"[Create Textured] ✓ Found: {current_ai_path.name}")
            
            # Step 2: Upload image
            print(f"[Create Textured] Step 2: Uploading image to server...")
            server_client = runcomfy_deployment.get_server_client()
            img_upload = server_client.upload_image(str(current_ai_path), overwrite=True)
            uploaded_img_name = img_upload['name']
            print(f"[Create Textured] ✓ Uploaded as: {uploaded_img_name}")
            
            # Step 3: Load workflow
            print(f"[Create Textured] Step 3: Loading workflow...")
            addon_dir = Path(__file__).parent
            workflow_path = addon_dir / "workflows" / "Object" / "objectCreateTexturedObject.json"
            
            if not workflow_path.exists():
                self.report({'ERROR'}, f"Workflow not found: {workflow_path.name}")
                print(f"[Create Textured] ❌ Workflow missing")
                return {'CANCELLED'}
            
            import json
            with open(workflow_path, 'r') as f:
                workflow_json = json.load(f)
            
            print(f"[Create Textured] ✓ Loaded workflow: {workflow_path.name}")
            
            # Step 4: Override nodes with quality parameters
            print(f"[Create Textured] Step 4: Configuring workflow...")
            
            # Get quality parameters
            style_props = context.scene.style_engine_props
            quality = style_props.object_quality if hasattr(style_props, 'object_quality') else 'BALANCED'
            params = get_quality_params(quality)
            
            workflow_json["14"]["inputs"]["image"] = uploaded_img_name
            workflow_json["32"]["inputs"]["string"] = f"StyleEngine_Textured_{int(time.time())}"
            workflow_json["37"]["inputs"]["seed"] = int(time.time() * 1000) % 999999999999
            
            # Apply quality parameters (mesh + texture)
            workflow_json["37"]["inputs"]["steps"] = params['mesh_steps']
            workflow_json["9"]["inputs"]["octree_resolution"] = params['octree_resolution']
            workflow_json["9"]["inputs"]["num_chunks"] = params['num_chunks']
            workflow_json["30"]["inputs"]["value"] = params['max_faces']
            workflow_json["20"]["inputs"]["view_size"] = params['view_size']
            workflow_json["20"]["inputs"]["steps"] = params['texture_steps']
            workflow_json["20"]["inputs"]["texture_size"] = params['texture_size']
            
            output_name = workflow_json["32"]["inputs"]["string"]
            print(f"[Create Textured] ✓ Quality: {quality}")
            print(f"[Create Textured] ✓ Mesh: steps={params['mesh_steps']}, octree={params['octree_resolution']}, faces={params['max_faces']}")
            print(f"[Create Textured] ✓ Texture: view={params['view_size']}, steps={params['texture_steps']}, size={params['texture_size']}")
            print(f"[Create Textured] ✓ Node 14 (image): {uploaded_img_name}")
            print(f"[Create Textured] ✓ Node 32 (output): {output_name}")
            
            # Step 5: Submit
            print(f"[Create Textured] Step 5: Submitting workflow...")
            self.report({'INFO'}, f"Generating textured 3D mesh... (2-3 minutes)")
            
            result = server_client.queue_prompt(workflow_json)
            prompt_id = result['prompt_id']
            print(f"[Create Textured] ✓ Queued: {prompt_id}")
            
            # Store workflow for progress bar node name lookup
            from . import progress_bar
            progress_bar.set_current_workflow(workflow_json)
            
            print(f"[Create Textured] ⏳ Processing (includes mesh + texture generation)...")
            
            # Capture variables
            temp_dir = Path(tempfile.gettempdir()) / "styleengine_create"
            temp_dir.mkdir(parents=True, exist_ok=True)
            download_path = temp_dir / f"{output_name}.glb"
            
            # Step 6: Start polling
            from . import runcomfy_polling
            
            def on_create_textured_complete(success, result=None, error=None, workflow_type=None):
                """Called when textured mesh generation completes - schedules heavy import work"""
                if not success:
                    print(f"[Create Textured] ❌ Generation failed: {error}")
                    return
                
                print(f"[Create Textured] ✓ Generation complete! Scheduling download/import...")
                
                # Schedule heavy operations separately (keeps callback fast!)
                def do_download_and_import():
                    """Heavy operations - download and import GLB"""
                    try:
                        print(f"[Create Textured] ============================================")
                        print(f"[Create Textured] Starting download & import...")
                        print(f"[Create Textured] ============================================")
                        
                        outputs = result.get('outputs', {})
                        output_filename = None
                        subfolder = ""
                        
                        # Get filename from Node 62
                        if '62' in outputs:
                            node_62_output = outputs['62']
                            if isinstance(node_62_output, dict) and 'result' in node_62_output:
                                result_data = node_62_output['result']
                                if isinstance(result_data, list) and len(result_data) > 0:
                                    full_path = result_data[0]
                                    if full_path and full_path.endswith('.glb'):
                                        if '/' in full_path:
                                            subfolder, output_filename = full_path.rsplit('/', 1)
                                        else:
                                            output_filename = full_path
                                        print(f"[Create Textured] ✓ Found: {subfolder}/{output_filename}" if subfolder else f"✓ Found: {output_filename}")
                        
                        if not output_filename:
                            print(f"[Create Textured] ❌ No GLB found!")
                            return None
                        
                        # Download
                        print(f"[Create Textured] Downloading...")
                        download_success = server_client.download_mesh(output_filename, str(download_path), subfolder=subfolder, file_type="output")
                        
                        if not download_success:
                            print(f"[Create Textured] ❌ Download failed")
                            return None
                        
                        print(f"[Create Textured] ✓ Downloaded ({download_path.stat().st_size / 1024:.1f} KB)")
                        
                        # Import (heavy operation)
                        print(f"[Create Textured] Importing...")
                        original_selected = list(bpy.context.selected_objects)
                        bpy.ops.import_scene.gltf(filepath=str(download_path))
                        newly_imported = [o for o in bpy.context.selected_objects if o not in original_selected]
                        
                        if newly_imported:
                            new_obj = newly_imported[0]
                            new_obj.name = f"AI_Textured_{int(time.time())}"
                            new_obj.location = (0, 0, 0)
                            
                            # Save mesh to Models library
                            workspace_setup.save_mesh_to_library(bpy.context, download_path, mesh_type='textured')
                            
                            print(f"[Create Textured] ✅ Textured 3D mesh created: {new_obj.name}")
                        
                        print(f"[Create Textured] ============================================")
                        print(f"[Create Textured] COMPLETE!")
                        print(f"[Create Textured] ============================================")
                        
                    except Exception as e:
                        print(f"[Create Textured] ❌ Error: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    return None  # Don't repeat timer
                
                # Schedule heavy work separately (keeps polling callback fast!)
                bpy.app.timers.register(do_download_and_import, first_interval=0.1)
            
            # Register polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_create_textured_complete,
                workflow_type='create_textured'
            )
            
            print(f"[Create Textured] ✅ Submitted! Processing in background...")
            print(f"[Create Textured] ============================================")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Create Textured Object failed: {e}")
            print(f"[Create Textured] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class WM_OT_SetVisualization(Operator):
    """Switch camera background visualization type"""
    bl_idname = "style_engine.set_visualization"
    bl_label = "Set Visualization"
    bl_description = "Switch between Combined, Silhouette (Canny), and Depth visualizations"
    bl_options = {'REGISTER', 'UNDO'}
    
    viz_type: bpy.props.EnumProperty(
        name="Visualization Type",
        items=[
            ('COMBINED', "Combined", "Final generated image"),
            ('CANNY', "Silhouette", "Canny edge detection"),
            ('DEPTH', "Depth", "Depth map"),
        ],
        default='COMBINED'
    )
    
    def execute(self, context):
        style_props = context.scene.style_engine_props
        style_props.visualization_type = self.viz_type
        return {'FINISHED'}


class WM_OT_SetRenderQuality(Operator):
    """Set render quality for AI generation"""
    bl_idname = "style_engine.set_render_quality"
    bl_label = "Set Render Quality"
    bl_description = "Choose between Fast (Workbench) or Detailed (EEVEE) render quality"
    bl_options = {'REGISTER', 'UNDO'}
    
    quality: bpy.props.EnumProperty(
        name="Quality",
        items=[
            ('FAST', "Fast", "Workbench render - fast preview quality"),
            ('DETAILED', "Detailed", "EEVEE render - high quality for img2img"),
        ],
        default='FAST'
    )
    
    def execute(self, context):
        style_props = context.scene.style_engine_props
        style_props.render_quality = self.quality
        
        if self.quality == 'FAST':
            self.report({'INFO'}, "Render Quality: Fast (Workbench)")
        else:
            self.report({'INFO'}, "Render Quality: Detailed (EEVEE)")
        
        return {'FINISHED'}


class WM_OT_PrevGeneration(Operator):
    """Navigate to previous generation"""
    bl_idname = "style_engine.prev_generation"
    bl_label = "Previous Generation"
    bl_description = "Load previous generation to current_ai.png"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        
        style_props = context.scene.style_engine_props
        
        # Get list of generations
        generations = workspace_setup.get_generation_list(context)
        
        if not generations:
            self.report({'WARNING'}, "No generations found")
            return {'CANCELLED'}
        
        # Handle index (-1 means latest/newest)
        if style_props.current_generation_index == -1:
            # Currently at latest, go to second-to-last
            new_index = len(generations) - 2
        else:
            # Go one step back (older)
            new_index = style_props.current_generation_index - 1
        
        # Clamp to valid range
        new_index = max(0, min(new_index, len(generations) - 1))
        
        # Load the generation
        if workspace_setup.load_generation_to_current(context, generations[new_index]):
            style_props.current_generation_index = new_index
            self.report({'INFO'}, f"Generation {new_index + 1}/{len(generations)}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to load generation")
            return {'CANCELLED'}


class WM_OT_NextGeneration(Operator):
    """Navigate to next generation"""
    bl_idname = "style_engine.next_generation"
    bl_label = "Next Generation"
    bl_description = "Load next generation to current_ai.png"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        
        style_props = context.scene.style_engine_props
        
        # Get list of generations
        generations = workspace_setup.get_generation_list(context)
        
        if not generations:
            self.report({'WARNING'}, "No generations found")
            return {'CANCELLED'}
        
        # Handle index (-1 means latest/newest)
        if style_props.current_generation_index == -1:
            # Already at latest
            self.report({'INFO'}, f"Already at latest generation")
            return {'CANCELLED'}
        
        # Go one step forward (newer)
        new_index = style_props.current_generation_index + 1
        
        # Check if we've reached the latest
        if new_index >= len(generations) - 1:
            new_index = -1  # Back to "latest" mode
        
        # Load the generation
        if new_index == -1:
            # Load the latest generation
            if workspace_setup.load_generation_to_current(context, generations[-1]):
                style_props.current_generation_index = -1
                self.report({'INFO'}, f"Latest generation")
                return {'FINISHED'}
        else:
            if workspace_setup.load_generation_to_current(context, generations[new_index]):
                style_props.current_generation_index = new_index
                self.report({'INFO'}, f"Generation {new_index + 1}/{len(generations)}")
                return {'FINISHED'}
        
        self.report({'ERROR'}, "Failed to load generation")
        return {'CANCELLED'}


class WM_OT_PrevPrompt(Operator):
    """Navigate to previous prompt snapshot"""
    bl_idname = "style_engine.prev_prompt"
    bl_label = "Previous Prompt"
    bl_description = "Load previous prompt snapshot to text editor"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        
        style_props = context.scene.style_engine_props
        
        # Get list of prompts
        prompts = workspace_setup.get_prompt_list(context)
        
        if not prompts:
            self.report({'WARNING'}, "No prompt snapshots found")
            return {'CANCELLED'}
        
        # Handle index (-1 means latest/newest)
        if style_props.current_prompt_index == -1:
            # Currently at latest, go to second-to-last
            new_index = len(prompts) - 2
        else:
            # Go one step back (older)
            new_index = style_props.current_prompt_index - 1
        
        # Clamp to valid range
        new_index = max(0, min(new_index, len(prompts) - 1))
        
        # Load the prompt
        if workspace_setup.load_prompt_to_editor(context, prompts[new_index]):
            style_props.current_prompt_index = new_index
            self.report({'INFO'}, f"Prompt {new_index + 1}/{len(prompts)}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to load prompt")
            return {'CANCELLED'}


class WM_OT_NextPrompt(Operator):
    """Navigate to next prompt snapshot"""
    bl_idname = "style_engine.next_prompt"
    bl_label = "Next Prompt"
    bl_description = "Load next prompt snapshot to text editor"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        
        style_props = context.scene.style_engine_props
        
        # Get list of prompts
        prompts = workspace_setup.get_prompt_list(context)
        
        if not prompts:
            self.report({'WARNING'}, "No prompt snapshots found")
            return {'CANCELLED'}
        
        # Handle index (-1 means latest/newest)
        if style_props.current_prompt_index == -1:
            # Already at latest
            self.report({'INFO'}, f"Already at latest prompt")
            return {'CANCELLED'}
        
        # Go one step forward (newer)
        new_index = style_props.current_prompt_index + 1
        
        # Check if we've reached the latest
        if new_index >= len(prompts) - 1:
            new_index = -1  # Back to "latest" mode
        
        # Load the prompt
        if new_index == -1:
            # Load the latest prompt
            if workspace_setup.load_prompt_to_editor(context, prompts[-1]):
                style_props.current_prompt_index = -1
                self.report({'INFO'}, f"Latest prompt")
                return {'FINISHED'}
        else:
            if workspace_setup.load_prompt_to_editor(context, prompts[new_index]):
                style_props.current_prompt_index = new_index
                self.report({'INFO'}, f"Prompt {new_index + 1}/{len(prompts)}")
                return {'FINISHED'}
        
        self.report({'ERROR'}, "Failed to load prompt")
        return {'CANCELLED'}


class WM_OT_PrevModel(Operator):
    """Navigate to previous model in library"""
    bl_idname = "style_engine.prev_model"
    bl_label = "Previous Model"
    bl_description = "Select previous model in library"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        from . import workspace_setup
        
        style_props = context.scene.style_engine_props
        
        # Get list of models
        models = workspace_setup.get_model_list(context)
        
        if not models:
            self.report({'WARNING'}, "No models found in library")
            return {'CANCELLED'}
        
        # Handle index (-1 means latest/newest)
        if style_props.current_model_index == -1:
            # Currently at latest, go to second-to-last
            new_index = len(models) - 2
        else:
            # Go one step back (older)
            new_index = style_props.current_model_index - 1
        
        # Clamp to valid range
        new_index = max(0, min(new_index, len(models) - 1))
        
        style_props.current_model_index = new_index
        self.report({'INFO'}, f"Model {new_index + 1}/{len(models)}")
        return {'FINISHED'}


class WM_OT_NextModel(Operator):
    """Navigate to next model in library"""
    bl_idname = "style_engine.next_model"
    bl_label = "Next Model"
    bl_description = "Select next model in library"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        from . import workspace_setup
        
        style_props = context.scene.style_engine_props
        
        # Get list of models
        models = workspace_setup.get_model_list(context)
        
        if not models:
            self.report({'WARNING'}, "No models found in library")
            return {'CANCELLED'}
        
        # Handle index (-1 means latest/newest)
        if style_props.current_model_index == -1:
            # Already at latest
            self.report({'INFO'}, f"Already at latest model")
            return {'CANCELLED'}
        
        # Go one step forward (newer)
        new_index = style_props.current_model_index + 1
        
        # Check if we've reached the latest
        if new_index >= len(models) - 1:
            new_index = -1  # Back to "latest" mode
        
        style_props.current_model_index = new_index
        if new_index == -1:
            self.report({'INFO'}, f"Latest model")
        else:
            self.report({'INFO'}, f"Model {new_index + 1}/{len(models)}")
        return {'FINISHED'}


class WM_OT_SpawnModel(Operator):
    """Spawn the currently selected model into the scene"""
    bl_idname = "style_engine.spawn_model"
    bl_label = "Spawn Model"
    bl_description = "Import the selected model from library at 3D cursor location"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        
        style_props = context.scene.style_engine_props
        
        # Get list of models
        models = workspace_setup.get_model_list(context)
        
        if not models:
            self.report({'ERROR'}, "No models found in library")
            return {'CANCELLED'}
        
        # Determine which model to spawn
        if style_props.current_model_index == -1:
            model_path = models[-1]  # Latest
        else:
            idx = min(style_props.current_model_index, len(models) - 1)
            model_path = models[idx]
        
        # Spawn the model
        new_obj = workspace_setup.spawn_model_from_library(context, model_path)
        
        if new_obj:
            self.report({'INFO'}, f"Spawned: {new_obj.name}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to spawn model")
            return {'CANCELLED'}


# ----------------------------------------------------------------
# MAIN PIE MENU
# ----------------------------------------------------------------

class STYLEENGINE_MT_pie_main(Menu):
    """Style Engine Main Pie Menu - Alt+W"""
    bl_label = "Style Engine"
    bl_idname = "STYLEENGINE_MT_pie_main"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        style_props = context.scene.style_engine_props
        
        # ═══════════════════════════════════════════════════
        # Position 0: TOP (NORTH) - Object (3D Generation)
        # ═══════════════════════════════════════════════════
        box = pie.box()
        col = box.column(align=True)
        col.scale_y = 1.1
        
        # Header
        row = col.row()
        row.label(text="Object", icon='OBJECT_DATA')
        col.separator()
        
        # Big Project Texture button (same format as Generate Image)
        row = col.row()
        row.scale_y = 2.5
        row.operator("style_engine.project_texture_scene", 
                     text="Project Texture", 
                     icon='TEXTURE')
        
        col.separator()
        
        # 3D Generation buttons
        # # HIDDEN: UV Texture - available in N panel
        # col.operator("style_engine.uv_texture", 
        #              text="UV Texture", 
        #              icon='UV')
        col.operator("style_engine.create_object", 
                     text="Create Object", 
                     icon='MESH_CUBE')
        col.operator("style_engine.create_textured_object", 
                     text="Create Textured Object", 
                     icon='SHADING_TEXTURE')
        
        col.separator()
        
        # 3D Quality selector
        quality_box = col.box()
        quality_col = quality_box.column(align=True)
        quality_col.label(text="3D Quality", icon='MODIFIER')
        quality_col.prop(style_props, "object_quality", text="")
        
        # ═══════════════════════════════════════════════════
        # Position 1: LEFT (WEST) - Workspace
        # ═══════════════════════════════════════════════════
        box = pie.box()
        col = box.column(align=True)
        col.scale_y = 1.1
        
        # Header
        row = col.row()
        row.label(text="Workspace", icon='WORKSPACE')
        col.separator()
        
        # Setup Workspace button (full setup with AI workspace)
        row = col.row()
        row.scale_y = 2.5
        row.operator("style_engine.setup_workspace", 
                     text="Setup Workspace", 
                     icon='PLAY')
        
        # Populate Assets button (assets only, no workspace change)
        col.separator()
        row = col.row()
        row.scale_y = 1.2
        row.operator("style_engine.populate_assets", 
                     text="Populate Assets", 
                     icon='FILE_REFRESH')
        
        # Set Camera button (copy from selected/active camera)
        row = col.row()
        row.scale_y = 1.2
        row.operator("style_engine.set_camera", 
                     text="Set Camera", 
                     icon='OUTLINER_OB_CAMERA')
        
        # # HIDDEN: Background opacity - moved to Visualization category
        # col.separator()
        # col.label(text="Background Opacity")
        # col.prop(style_props, "background_opacity", text="", slider=True)
        
        # # HIDDEN: Resolution - available in N panel (File category)
        # col.separator()
        # col.label(text="Resolution")
        # col.prop(style_props, "ai_resolution", text="")
        
        # ═══════════════════════════════════════════════════
        # Position 2: BOTTOM (SOUTH) - Generate Image
        # ═══════════════════════════════════════════════════
        box = pie.box()
        col = box.column(align=True)
        
        # Big generate button
        row = col.row()
        row.scale_y = 2.5
        row.operator("style_engine.generate_ai_quick", 
                     text="Generate Image", 
                     icon='IMAGE_DATA')
        
        col.separator()
        
        # Influence sliders section
        influence_box = col.box()
        influence_col = influence_box.column(align=True)
        influence_col.label(text="Influences", icon='SMOOTHCURVE')
        
        influence_col.prop(style_props, "silhouette_influence", 
                          text="Silhouette", slider=True)
        influence_col.prop(style_props, "depth_influence", 
                          text="Depth", slider=True)
        influence_col.prop(style_props, "texture_influence", 
                          text="Viewport", slider=True)
        
        # # HIDDEN: Steps - available in N panel (Image Generation > Influence)
        # col.separator()
        # col.label(text="Steps", icon='SORTTIME')
        # col.prop(style_props, "steps", text="", slider=True)
        
        # # HIDDEN: Autogenerate - available in N panel (Image Generation)
        # col.separator()
        # row = col.row()
        # row.scale_y = 1.5
        # row.prop(style_props, "auto_generate", 
        #          text="Autogenerate", 
        #          toggle=True, 
        #          icon='FILE_REFRESH')
        
        # # HIDDEN: Render Quality - available in N panel (File category)
        # col.separator()
        # quality_box = col.box()
        # quality_col = quality_box.column(align=True)
        # quality_col.label(text="Render Quality", icon='SHADING_RENDERED')
        # 
        # # Two buttons: Fast (Workbench) and Detailed (EEVEE)
        # row = quality_col.row(align=True)
        # row.scale_y = 1.3
        # 
        # # Fast button
        # op = row.operator("style_engine.set_render_quality", 
        #                  text="Fast", 
        #                  icon='SHADING_WIRE',
        #                  depress=(style_props.render_quality == 'FAST'))
        # op.quality = 'FAST'
        # 
        # # Detailed button
        # op = row.operator("style_engine.set_render_quality", 
        #                  text="Detailed", 
        #                  icon='SHADING_RENDERED',
        #                  depress=(style_props.render_quality == 'DETAILED'))
        # op.quality = 'DETAILED'
        # 
        # quality_col.separator(factor=0.5)
        # 
        # # Show description based on current selection
        # if style_props.render_quality == 'FAST':
        #     quality_col.label(text="Workbench - Quick iterations", icon='INFO')
        # else:
        #     quality_col.label(text="EEVEE - Better for img2img", icon='INFO')
        
        # # HIDDEN: LoRa Configuration - available in N panel (Image Generation > LoRas)
        # col.separator()
        # lora_box = col.box()
        # lora_col = lora_box.column(align=True)
        # lora_col.label(text="LoRa", icon='MODIFIER')
        # 
        # # Enable checkbox
        # lora_col.prop(style_props, "lora_enabled", 
        #               text="Use LoRa", 
        #               toggle=True)
        # 
        # # Only show controls if enabled
        # if style_props.lora_enabled:
        #     lora_col.separator(factor=0.5)
        #     
        #     # LoRa dropdown with refresh button
        #     lora_col.label(text="Model:", icon='FILE')
        #     refresh_row = lora_col.row(align=True)
        #     refresh_row.prop(style_props, "lora_name", text="")
        #     refresh_row.operator("style_engine.refresh_lora_list", text="", icon='FILE_REFRESH')
        #     
        #     lora_col.separator(factor=0.5)
        #     
        #     # Strength slider
        #     lora_col.label(text="Strength:", icon='FORCE_FORCE')
        #     lora_col.prop(style_props, "lora_strength_model", 
        #                   text="", 
        #                   slider=True)
        #     
        #     lora_col.separator(factor=0.3)
        #     
        #     # Show active LoRa
        #     if style_props.lora_name != 'NONE':
        #         info_row = lora_col.row()
        #         info_row.scale_y = 0.7
        #         # Truncate long names
        #         display_name = style_props.lora_name.replace('.safetensors', '')
        #         if len(display_name) > 20:
        #             display_name = display_name[:17] + "..."
        #         info_row.label(text=f"Active: {display_name}", icon='CHECKMARK')
        
        # ═══════════════════════════════════════════════════
        # Position 3: RIGHT (EAST) - Visualization Type
        # ═══════════════════════════════════════════════════
        # Check if preview images are enabled
        prefs = context.preferences.addons.get('styleengine')
        show_visualization = (prefs and 
                             prefs.preferences.api_backend == 'GCS' and 
                             prefs.preferences.gcs_download_preview_images)
        
        if show_visualization:
            # Show Visualization Type switcher (compact width to match Generate Image)
            box = pie.box()
            box.ui_units_x = 10  # Constrain width
            col = box.column(align=True)
            col.scale_y = 1.1
            
            # Header
            row = col.row()
            row.label(text="Visualization", icon='VIEW_CAMERA')
            col.separator()
            
            # Visualization type buttons (icon-only for compact width)
            row = col.row(align=True)
            row.scale_y = 1.5
            
            # Combined button
            op = row.operator("style_engine.set_visualization", 
                             text="Combined", 
                             icon='IMAGE_DATA',
                             depress=(style_props.visualization_type == 'COMBINED'))
            op.viz_type = 'COMBINED'
            
            # Silhouette button
            op = row.operator("style_engine.set_visualization", 
                             text="", 
                             icon='MESH_PLANE',
                             depress=(style_props.visualization_type == 'CANNY'))
            op.viz_type = 'CANNY'
            
            # Depth button
            op = row.operator("style_engine.set_visualization", 
                             text="", 
                             icon='EMPTY_SINGLE_ARROW',
                             depress=(style_props.visualization_type == 'DEPTH'))
            op.viz_type = 'DEPTH'
            
            col.separator()
            
            # Show current visualization
            col.label(text=f"Current: {style_props.visualization_type.title()}", icon='INFO')
            
            # Background opacity (moved from Setup Workspace)
            col.separator()
            col.label(text="Background Opacity")
            col.prop(style_props, "background_opacity", text="", slider=True)
            
            # ═══════════════════════════════════════════════════
            # Generation Browser - Navigate Through Saved Generations
            # ═══════════════════════════════════════════════════
            col.separator()
            col.label(text="Generation Browser", icon='RENDERLAYERS')
            
            # Get generation info
            from . import workspace_setup
            generations = workspace_setup.get_generation_list(context)
            
            if generations:
                # Navigation buttons
                row = col.row(align=True)
                row.scale_y = 1.3
                
                # Check if at boundaries
                at_oldest = (style_props.current_generation_index == 0)
                at_latest = (style_props.current_generation_index == -1)
                
                # Previous button (go to older)
                prev_row = row.row(align=True)
                prev_row.enabled = not at_oldest  # Disable if at oldest
                prev_row.operator("style_engine.prev_generation", 
                                 text="", 
                                 icon='TRIA_LEFT')
                
                # Current generation indicator
                if at_latest:
                    current_text = f"Latest ({len(generations)})"
                else:
                    current_text = f"{style_props.current_generation_index + 1}/{len(generations)}"
                
                row.label(text=current_text)
                
                # Next button (go to newer)
                next_row = row.row(align=True)
                next_row.enabled = not at_latest  # Disable if at latest
                next_row.operator("style_engine.next_generation", 
                                 text="", 
                                 icon='TRIA_RIGHT')
            else:
                col.label(text="No generations yet", icon='INFO')
        
        else:
            # Fallback: empty box or placeholder
            box = pie.box()
            col = box.column(align=True)
            col.scale_y = 1.1
            
            row = col.row()
            row.label(text="Visualization", icon='VIEW_CAMERA')
            col.separator()
            
            col.label(text="Enable 'Download Preview", icon='INFO')
            col.label(text="Images' in GCS settings")
            col.label(text="to use this feature")
        


# ----------------------------------------------------------------
# Registration
# ----------------------------------------------------------------

classes = (
    WM_OT_ProjectTextureScene,
    WM_OT_UVTexture,
    WM_OT_CreateObject,
    WM_OT_CreateTexturedObject,
    WM_OT_SetVisualization,
    WM_OT_SetRenderQuality,
    WM_OT_PrevGeneration,
    WM_OT_NextGeneration,
    WM_OT_PrevPrompt,
    WM_OT_NextPrompt,
    WM_OT_PrevModel,
    WM_OT_NextModel,
    WM_OT_SpawnModel,
    STYLEENGINE_MT_pie_main,
)

addon_keymaps = []


def register():
    """Register pie menu and Alt+W hotkey"""
    
    # Register classes
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass  # Already registered
    
    # Register keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        # Register for 3D View (works in Object Mode, Sculpt, etc.)
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new('wm.call_menu_pie', 'W', 'PRESS', alt=True)
        kmi.properties.name = "STYLEENGINE_MT_pie_main"
        addon_keymaps.append((km, kmi))
        
        # ALSO register for Mesh (Edit Mode) - conflict-free with Blender & HEAVYPOLY
        # Blender uses W alone (Select menu), HEAVYPOLY doesn't use Alt+W
        # Our Alt+W is completely free and ergonomic (W = Workflow!)
        km_mesh = kc.keymaps.new(name='Mesh', space_type='VIEW_3D')
        kmi_mesh = km_mesh.keymap_items.new('wm.call_menu_pie', 'W', 'PRESS', alt=True)
        kmi_mesh.properties.name = "STYLEENGINE_MT_pie_main"
        addon_keymaps.append((km_mesh, kmi_mesh))
        
        # Also register for other edit modes (Curve, Armature, etc.)
        for mode_name in ['Curve', 'Armature', 'Pose', 'Sculpt']:
            km_mode = kc.keymaps.new(name=mode_name, space_type='VIEW_3D')
            kmi_mode = km_mode.keymap_items.new('wm.call_menu_pie', 'W', 'PRESS', alt=True)
            kmi_mode.properties.name = "STYLEENGINE_MT_pie_main"
            addon_keymaps.append((km_mode, kmi_mode))
        
        print("[Style Engine] ✅ Pie menu registered (Alt+W) for all modes - macOS/Windows/Linux compatible")


def unregister():
    """Unregister pie menu and hotkey"""
    
    # Unregister keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    # Unregister classes
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
    
    print("[Style Engine] ✅ Pie menu unregistered")


if __name__ == "__main__":
    register()

