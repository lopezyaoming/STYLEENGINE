# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making Tencent Hunyuan 3D Omni available.
"""

import ctypes
libgcc_s = ctypes.CDLL('libgcc_s.so.1')

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import warnings
warnings.filterwarnings('ignore')

import io
import json
import random
import argparse
import torch
import trimesh
import glob
import shutil
import numpy as np
from PIL import Image
from hy3dshape.pipelines import Hunyuan3DOmniSiTFlowMatchingPipeline
from hy3dshape.preprocessors import ImageProcessorV2
from hy3dshape.postprocessors import FloaterRemover, DegenerateFaceRemover

def save_ply_points(filename: str, points: np.ndarray) -> None:
    with open(filename, 'w') as f:
        f.write('ply\n')
        f.write('format ascii 1.0\n')
        f.write('element vertex %d\n' % len(points))
        f.write('property float x\n')
        f.write('property float y\n')
        f.write('property float z\n')
        f.write('end_header\n')
        for point in points:
            f.write('%f %f %f\n' % (point[0], point[1], point[2]))

def normalize_mesh(mesh: trimesh.Trimesh, scale: float = 0.9999) -> trimesh.Trimesh:
    bbox = mesh.bounds
    center = (bbox[1] + bbox[0]) / 2
    scale_ = (bbox[1] - bbox[0]).max()
    mesh.apply_translation(-center)
    mesh.apply_scale(1 / scale_ * 2 * scale)
    return mesh

def postprocess(mesh, file_name, save_dir, sampled_point, image_file):
    mesh = FloaterRemover()(mesh)
    mesh = DegenerateFaceRemover()(mesh)
    mesh.export(os.path.join(save_dir, '%s.glb' % (file_name)))
    save_ply_points(os.path.join(save_dir, '%s.ply' % file_name), sampled_point.cpu().numpy())
    shutil.copy(image_file, os.path.join(save_dir, '%s.png' % file_name))

# --- UPDATED INFERENCE FUNCTIONS ---

def infer_bbox(pipeline, data_json: str, save_dir: str, guidance_scale: float = 4.5) -> None:
    data = json.load(open(data_json))
    image_files = data['image']
    bboxs = data['bbox']
    os.makedirs(save_dir, exist_ok=True)
    for i in range(len(image_files)):
        image_file = image_files[i]
        bbox = bboxs[i]
        if not os.path.exists(image_file): continue
        bbox = torch.FloatTensor(bbox).unsqueeze(0).unsqueeze(0).to(pipeline.device).to(pipeline.dtype)

        result = pipeline(
            image=image_file,
            bbox=bbox,
            num_inference_steps=50,
            octree_resolution=512,
            mc_level=0,
            guidance_scale=guidance_scale, # Now dynamic
            conditioning_scale=0.7,        # Natively relaxes influence
            generator=torch.Generator('cuda').manual_seed(1234),
        )
        mesh = result['shapes'][0][0]
        sampled_point = result['sampled_point'][0]
        base_name = image_file.split("/")[-1].split('.')[0]
        file_name = f"{base_name}_bbox"
        postprocess(mesh, file_name, save_dir, sampled_point, image_file)

def infer_pose(pipeline, images: list, pose_dict: dict, save_dir: str, guidance_scale: float = 4.5) -> None:
    os.makedirs(save_dir, exist_ok=True)
    for i in range(len(images)):
        image_file = images[i]
        if not os.path.exists(image_file): continue
        for pose_key in pose_dict.keys():
            bone_path = pose_dict[pose_key]
            bone_points = torch.from_numpy(np.loadtxt(bone_path)).to(pipeline.device).to(pipeline.dtype).unsqueeze(0)
            result = pipeline(
                image=image_file,
                pose=bone_points,
                num_inference_steps=50,
                octree_resolution=512,
                mc_level=0,
                guidance_scale=guidance_scale,
                generator=torch.Generator('cuda').manual_seed(1234),
            )
            mesh = result['shapes'][0][0]
            sampled_point = result['sampled_point'][0] 
            file_name = image_file.split("/")[-1].split('.')[0] + "_" + pose_key
            postprocess(mesh, file_name, save_dir, sampled_point, image_file)

def infer_point(pipeline, data_json: str, save_dir: str, guidance_scale: float = 4.5) -> None:
    data = json.load(open(data_json))
    image_files = data['image']
    mesh_files = data['point']
    os.makedirs(save_dir, exist_ok=True)
    for i in range(len(image_files)):
        mesh_file = mesh_files[i]
        image_file = image_files[i]
        if not os.path.exists(mesh_file) or not os.path.exists(image_file): continue
        mesh = trimesh.load(mesh_file)
        mesh = normalize_mesh(mesh, scale=0.98)
        surface = torch.FloatTensor(mesh.vertices).unsqueeze(0).to(pipeline.device).to(pipeline.dtype)
        result = pipeline(
            image=image_file,
            point=surface,
            num_inference_steps=50,
            octree_resolution=512,
            mc_level=0,
            guidance_scale=guidance_scale,
            conditioning_scale=0.6,        # Smooths "chewed" points
            generator=torch.Generator('cuda').manual_seed(1234),
        )
        mesh = result['shapes'][0][0]
        sampled_point = result['sampled_point'][0]
        file_name = image_file.split("/")[-1].split('.')[0]
        postprocess(mesh, file_name, save_dir, sampled_point, image_file)

def infer_voxel(pipeline, data_json: str, save_dir: str, guidance_scale: float = 4.5) -> None:
    data = json.load(open(data_json))
    image_files = data['image']
    mesh_files = data['voxel']
    os.makedirs(save_dir, exist_ok=True)
    for i in range(len(image_files)):
        mesh_file = mesh_files[i]
        image_file = image_files[i]
        if not os.path.exists(mesh_file) or not os.path.exists(image_file): continue
        mesh = trimesh.load(mesh_file)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0]))
        mesh = normalize_mesh(mesh)
        surface = torch.FloatTensor(mesh.sample(81920)).unsqueeze(0).to(pipeline.device).to(pipeline.dtype)
        result = pipeline(
            image=image_file,
            voxel=surface,
            num_inference_steps=50,
            octree_resolution=512,
            mc_level=0,
            guidance_scale=guidance_scale,
            conditioning_scale=0.75,
            generator=torch.Generator('cuda').manual_seed(1234),
        )
        mesh = result['shapes'][0][0]
        sampled_point = result['sampled_point'][0]
        file_name = image_file.split("/")[-1].split('.')[0]
        postprocess(mesh, file_name, save_dir, sampled_point, image_file)

def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--gpu_id', type=int, default=0)
    parser.add_argument('--num_gpu', type=int, default=1)
    parser.add_argument('--save_dir', type=str, default="./omni_inference_results")
    parser.add_argument('--control_type', type=str, required=True, choices=["voxel", "point", 'pose', 'bbox'])
    parser.add_argument('--repo_id', type=str, default="tencent/Hunyuan3D-Omni")
    parser.add_argument('--use_ema', action='store_true')
    parser.add_argument('--flashvdm', action='store_true')
    parser.add_argument('--guidance_scale', type=float, default=4.5) # The new flag
    return parser.parse_args()

if __name__ == "__main__":
    args = get_args()
    pipeline = Hunyuan3DOmniSiTFlowMatchingPipeline.from_pretrained(args.repo_id, fast_decode=args.flashvdm)

    if args.control_type == "bbox":
        infer_bbox(pipeline, "./demos/bbox/data.json", os.path.join(args.save_dir, "3domni_bbox"), args.guidance_scale)

    if args.control_type == "pose":
        pose_configs = {"a_pose": "./demos/pose/a_pose_bone.txt", "handup_pose": "./demos/pose/handup_pose_bone.txt", "sky_pose": "./demos/pose/sky_pose_bone.txt"}
        infer_pose(pipeline, glob.glob("./demos/pose/*.png"), pose_configs, os.path.join(args.save_dir, "3domni_pose"), args.guidance_scale)

    if args.control_type == "point":
        infer_point(pipeline, "./demos/point/data.json", os.path.join(args.save_dir, "3domni_point"), args.guidance_scale)

    if args.control_type == "voxel":
        infer_voxel(pipeline, "./demos/voxel/data.json", os.path.join(args.save_dir, "3domni_voxel"), args.guidance_scale)