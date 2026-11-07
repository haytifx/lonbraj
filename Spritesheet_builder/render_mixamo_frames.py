#!/usr/bin/env python3
"""
render_mixamo_frames.py
------------------------
Rann yon animasyon Mixamo (.fbx) an frame PNG transparan, vi sou kote, pou fe
yon POZ-REFERANS (mannequin gri). Apre sa Gemini redesine chak pwa a an James.

POUKISA : Mixamo bay mouvman pwofesyonel ki fliyid (mache, mache akoupi,
pistolè, tire, touche, mouri, sote...). Men se yon pèsonaj 3D. Nou pran
POZ yo ak TAN yo, epi James pran plas kò a.

Sa script la garanti (sa Gemini pa ka garanti) :
  * MENM gwosè nan tout frame yo (yon sèl kamera fiks pou tout animasyon an)
  * PYE yo sou menm liy tè nan tout frame yo
  * pèsonaj la santre, san anyen ki koupe
  * pa gen tèks, pa gen lonbraj sou tè a, fon transparan

ENSTALASYON : Blender gratis (https://www.blender.org/download/). Pa bezwen pyès
lòt bagay.

KIJAN POU ITILIZE (Windows PowerShell ; chanje chemen Blender a si l pa menm) :

    & "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe" -b -P render_mixamo_frames.py -- --input Walking.fbx --name walk --frames 8

    -> kreye  pose_frames/walk_1.png ... walk_8.png  (+ walk_strip.png)

Pou chak lòt animasyon, ranpli --name ak non jwèt la espere a :
    walk, sneak, crouch, idle, jump, hurt, dead, takedown,
    pistol_walk, pistol_sneak, pistol_idle, pistol_aim, pistol_shoot

OPSYON ENPÒTAN
    --frames N         kantite frame (defo 8)
    --oneshot          pou animasyon ki jwe YON SÈL FWA (jump, hurt, dead, takedown,
                       pistol_shoot...) : pran dènye pwa a tou. San li : se yon BOUKL
                       (walk, sneak...) epi dènye frame a pa repete premye a.
    --ortho-scale X    GWOSÈ KAMERA A. PRAN VALÈ A KE SCRIPT LA ENPRIME LÈ W RANN "walk"
                       EPI METE L MENM JAN POU TOUT LÒT ANIMASYON : konsa James gen menm
                       gwosè nan tout animasyon yo.
    --camera -x|+x     defo -x : pèsonaj la fè fas a DWAT. Si l fè fas a GOCH nan imaj yo, chanje an +x
    --size 256         gwosè chak frame (kare) an pixel
    --engine workbench pi rapid (si òdinatè w gen GPU/OpenGL) ; defo "cycles" mache toupatou

PREPARE FBX LA SOU MIXAMO :
    - Format FBX (.fbx), Skin "With Skin", 30 fps
    - KOCHE "In Place" (enpòtan : pèsonaj la pa avanse, se jwèt la ki deplase l)
"""

import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

GROUND_MARGIN = 0.06      # fraksyon wotè imaj la ant pye yo ak anba imaj la (ak anwo tèt la)

AXES = {
    "-x": Vector((-1, 0, 0)),   # kamera nan -X : pèsonaj Mixamo (ki fè fas a -Y) parèt fè fas a DWAT (defo)
    "+x": Vector((1, 0, 0)),    # kamera nan +X : pèsonaj la parèt fè fas a GOCH
    "-y": Vector((0, -1, 0)),
    "+y": Vector((0, 1, 0)),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description="Rann yon animasyon Mixamo an frame PNG")
    p.add_argument("--input", required=True, help="Fichye .fbx (oswa .glb) telechaje sou Mixamo")
    p.add_argument("--name", default=None, help="Non animasyon an (walk, sneak...). Defo : non fichye a")
    p.add_argument("--output-dir", default="pose_frames")
    p.add_argument("--frames", type=int, default=8)
    p.add_argument("--oneshot", action="store_true", help="Animasyon ki jwe yon sèl fwa (pa boukl)")
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--camera", choices=list(AXES), default="-x")
    p.add_argument("--ortho-scale", type=float, default=None)
    p.add_argument("--engine", choices=["cycles", "workbench"], default="cycles")
    p.add_argument("--samples", type=int, default=16, help="Echantiyon Cycles (plis = pi lis, pi dousman)")
    p.add_argument("--no-strip", action="store_true", help="Pa kreye bann lan (name_strip.png)")
    return p.parse_args(argv)


# ----------------------------------------------------------------------
# Chajman
# ----------------------------------------------------------------------
def import_model(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".fbx":
        if hasattr(bpy.ops.import_scene, "fbx"):
            bpy.ops.import_scene.fbx(filepath=path)
        else:                                   # Blender ki pi nouvo
            bpy.ops.wm.fbx_import(filepath=path)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        raise SystemExit(f"ERÈ: fòma {ext} pa sipòte (itilize .fbx oswa .glb)")


def animation_range(armatures):
    for arm in armatures:
        ad = arm.animation_data
        if ad and ad.action:
            start, end = ad.action.frame_range
            return float(start), float(end)
    scene = bpy.context.scene
    return float(scene.frame_start), float(scene.frame_end)


def sample_times(start, end, count, oneshot):
    if count < 2:
        return [start]
    divisor = (count - 1) if oneshot else count     # boukl : dènye pwa a = premye a, pa repete l
    return [start + (end - start) * i / divisor for i in range(count)]


def set_time(scene, t):
    whole = math.floor(t)
    scene.frame_set(int(whole), subframe=t - whole)


def union_bbox(scene, meshes, times):
    """Bwat ki kouvri pèsonaj la sou TOUT frame yo (monn, mèt)."""
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for t in times:
        set_time(scene, t)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for obj in meshes:
            ev = obj.evaluated_get(depsgraph)
            mw = ev.matrix_world
            for corner in ev.bound_box:
                w = mw @ Vector(corner)
                for i in range(3):
                    mn[i] = min(mn[i], w[i])
                    mx[i] = max(mx[i], w[i])
    return mn, mx


# ----------------------------------------------------------------------
# Sèn
# ----------------------------------------------------------------------
def setup_render(scene, args):
    r = scene.render
    r.resolution_x = r.resolution_y = args.size
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    if args.engine == "workbench":
        r.engine = "BLENDER_WORKBENCH"
        sh = scene.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_object_outline = True
        sh.object_outline_color = (0.0, 0.0, 0.0)
    else:
        r.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = False
        scene.cycles.film_exposure = 1.0
    scene.view_settings.view_transform = "Standard"      # koulè pa chanje (pa "Filmic/AgX")

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.9, 0.9, 0.9, 1.0)
    bg.inputs[1].default_value = 0.3        # limyè anbyan fèb : kò a pa blan, janm yo rete li
    scene.world = world


def add_camera_and_light(scene, args, center_h, center_depth, ground_z, ortho):
    axis = AXES[args.camera]
    depth_idx = 0 if abs(axis.x) > 0 else 1
    hor_idx = 1 if depth_idx == 0 else 0

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho
    cam_data.clip_start = 0.1
    cam_data.clip_end = 1000.0
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)

    loc = Vector((0, 0, 0))
    loc[hor_idx] = center_h
    loc[depth_idx] = center_depth + axis[depth_idx] * 100.0
    loc.z = ground_z + ortho * (0.5 - GROUND_MARGIN)       # tè a = GROUND_MARGIN anwo anba imaj la
    cam.location = loc
    look_target = Vector(loc)
    look_target[depth_idx] = center_depth
    cam.rotation_euler = (look_target - loc).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    sun_data = bpy.data.lights.new("sun", "SUN")
    sun_data.energy = 2.0
    sun = bpy.data.objects.new("sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = cam.rotation_euler
    sun.rotation_euler.rotate_axis("X", math.radians(-35))   # limyè ki soti anlè devan
    sun.rotation_euler.rotate_axis("Y", math.radians(20))


# ----------------------------------------------------------------------
# Bann (tout frame yo kolè kote youn kote lòt)
# ----------------------------------------------------------------------
def make_strip(paths, out_path):
    import numpy as np
    arrays = []
    for p in paths:
        img = bpy.data.images.load(p)
        img.alpha_mode = "STRAIGHT"
        w, h = img.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        arrays.append(buf.reshape(h, w, 4))
        bpy.data.images.remove(img)
    strip = np.concatenate(arrays, axis=1)
    h, w, _ = strip.shape
    out = bpy.data.images.new("strip", w, h, alpha=True)
    out.alpha_mode = "STRAIGHT"
    out.pixels.foreach_set(strip.ravel())
    out.filepath_raw = out_path
    out.file_format = "PNG"
    out.save()


# ----------------------------------------------------------------------
def main():
    args = parse_args()
    path = os.path.abspath(args.input)
    if not os.path.exists(path):
        raise SystemExit(f"ERÈ: fichye pa egziste : {path}")
    name = args.name or os.path.splitext(os.path.basename(path))[0].lower().replace(" ", "_")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_model(path)
    scene = bpy.context.scene

    meshes = [o for o in scene.objects if o.type == "MESH"]
    armatures = [o for o in scene.objects if o.type == "ARMATURE"]
    if not meshes:
        raise SystemExit("ERÈ: pa gen okenn mesh nan fichye a. Telechaje l ak 'Skin: With Skin' sou Mixamo.")

    start, end = animation_range(armatures)
    if end <= start:
        print("ATANSYON: pa jwenn animasyon nan fichye a (se yon pòz fiks).")
    times = sample_times(start, end, args.frames, args.oneshot)

    mn, mx = union_bbox(scene, meshes, times)
    axis = AXES[args.camera]
    depth_idx = 0 if abs(axis.x) > 0 else 1
    hor_idx = 1 if depth_idx == 0 else 0
    height = mx.z - mn.z
    width = mx[hor_idx] - mn[hor_idx]
    needed = max(height, width) / (1.0 - 2.0 * GROUND_MARGIN)
    ortho = args.ortho_scale or needed
    if args.ortho_scale and needed > args.ortho_scale * 1.0001:
        print(f"ATANSYON: animasyon sa a bezwen --ortho-scale {needed:.3f} (ou bay {args.ortho_scale}). "
              f"Pèsonaj la ap koupe. Rann premye animasyon an ankò ak yon valè ki pi gwo.")

    setup_render(scene, args)
    center_h = (mn[hor_idx] + mx[hor_idx]) / 2.0
    center_depth = (mn[depth_idx] + mx[depth_idx]) / 2.0
    add_camera_and_light(scene, args, center_h, center_depth, mn.z, ortho)

    out_dir = os.path.abspath(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, t in enumerate(times):
        set_time(scene, t)
        fp = os.path.join(out_dir, f"{name}_{i + 1}.png")
        scene.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        paths.append(fp)
        print(f"  frame {i + 1}/{len(times)}  (tan {t:.1f})  -> {fp}")

    if not args.no_strip:
        strip_path = os.path.join(out_dir, f"{name}_strip.png")
        make_strip(paths, strip_path)
        print(f"  bann: {strip_path}")

    print(f"\nOK: {len(paths)} frame '{name}' nan {out_dir}")
    print(f"    wotè pèsonaj la = {height:.3f}  |  --ortho-scale itilize = {ortho:.4f}")
    if not args.ortho_scale:
        print(f"    >>> Pou TOUT lòt animasyon, ajoute:  --ortho-scale {ortho:.4f}")


if __name__ == "__main__":
    main()
