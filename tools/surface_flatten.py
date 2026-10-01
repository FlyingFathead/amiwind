# SPDX-License-Identifier: GPL-3.0-only
"""Bake explicitly selected decorative meshes into flat, textured panels.

The caller keeps source geometry for collision. No source asset is modified.
Profiles specify an axis, facing sign and mounting plane in source coordinates;
we never infer that every thin object is safe to flatten.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.ndimage import distance_transform_edt


def load_profiles(path=None, *, scene_kind='exterior'):
    """Load only profiles approved for this scene's mounting geometry.

    Exterior window meshes also occur inside rooms. Their exterior mounting
    plane and outward wall test are not valid for those interior placements.
    """
    if scene_kind not in ('exterior', 'interior'):
        raise ValueError('Unknown flattening scene kind: ' + str(scene_kind))
    path = Path(path) if path else Path(__file__).resolve().parents[1]/'config/surface-flattening.json'
    data = json.loads(path.read_text())
    result = {}
    for kind, settings in data['types'].items():
        if not isinstance(settings['flatten'], bool):
            raise ValueError('flatten must be true or false')
        scenes = settings.get('scenes', ['exterior'])
        if not isinstance(scenes, list) or any(s not in ('exterior', 'interior') for s in scenes):
            raise ValueError('flatten scenes must contain exterior and/or interior')
        if settings['flatten'] and scene_kind in scenes:
            for name, profile in settings['models'].items():
                result[name] = {**profile, 'type': kind}
    return result


def bake_panel(vertices, faces, materials, image_for_material, profile):
    """Return new visual geometry and one RGB bake; inputs remain untouched.

    UVs wrap exactly like the source BSP textures. A depth buffer keeps the
    foremost source triangle at each texel. The convex source outline clips
    the final panel; nearest covered texels provide edge dilation, not black
    seams. Only closed decorative windows are approved by the initial profiles.
    """
    axis = int(profile['axis'])
    sign = int(profile['facing'])
    size = int(profile.get('texture_size', 64))
    plane = float(profile['plane'])
    if axis not in (0, 1, 2) or sign not in (-1, 1) or size not in (16, 32, 64):
        raise ValueError('Invalid panel projection')
    dims = [a for a in range(3) if a != axis]
    points = vertices[np.unique(faces[:, :3]), :3]
    low, high = points[:, dims].min(0), points[:, dims].max(0)
    extent = high-low
    if np.any(extent <= 1e-6) or not np.isfinite(plane):
        raise ValueError('Degenerate panel projection')
    xy = (vertices[:, dims]-low)/extent
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    depth = np.full((size, size), -np.inf)
    yy, xx = np.mgrid[:size, :size]
    samples = np.stack(((xx+.5)/size, (yy+.5)/size), axis=-1)
    images = {}
    for face in faces:
        ids, material = face[:3], int(face[3])
        tri = xy[ids]
        basis = np.column_stack((tri[1]-tri[0], tri[2]-tri[0]))
        if abs(np.linalg.det(basis)) < 1e-10:
            continue
        uv = (samples-tri[0]) @ np.linalg.inv(basis).T
        weights = np.stack((1-uv[..., 0]-uv[..., 1], uv[..., 0], uv[..., 1]), axis=-1)
        z = weights @ vertices[ids, axis]*sign
        mask = (weights.min(axis=-1) >= -1e-8) & (z > depth)
        if not mask.any():
            continue
        if material not in images:
            image = np.asarray(image_for_material(material), dtype=float)[..., :3]
            images[material] = np.clip(image*np.array(materials[material]['diffuse']), 0, 255).astype(np.uint8)
        image = images[material]
        st = weights[mask] @ vertices[ids, 3:5]
        h, w = image.shape[:2]
        rgb[mask] = image[np.floor(st[:, 1]*h).astype(int) % h,
                          np.floor(st[:, 0]*w).astype(int) % w]
        depth[mask] = z[mask]
    covered = np.isfinite(depth)
    if not covered.any():
        raise ValueError('Panel bake has no covered texels')
    nearest = distance_transform_edt(~covered, return_distances=False, return_indices=True)
    rgb[~covered] = rgb[tuple(nearest[:, ~covered])]
    outline = np.unique(points[:, dims], axis=0)
    outline = outline[ConvexHull(outline).vertices]
    out = np.zeros((len(outline), vertices.shape[1]))
    out[:, dims] = outline
    out[:, axis] = plane
    out[:, 3:5] = (outline-low)/extent
    out[:, 5:] = 255
    normal = np.cross(out[1, :3]-out[0, :3], out[2, :3]-out[0, :3])
    if normal[axis]*sign < 0:
        out = out[::-1].copy()
    triangles = np.array([[0, i, i+1, len(materials)] for i in range(1, len(out)-1)], dtype=int)
    report = {'type': profile['type'], 'source_triangles': len(faces),
              'visual_triangles': len(triangles), 'axis': axis, 'facing': sign,
              'mounting_plane': plane, 'texture_size': size,
              'covered_texels': int(covered.sum()), 'collision': 'unchanged source geometry'}
    return out, triangles, rgb, report


def mounting_shift(origin, normal, triangles, reach=16.0, clearance=0.5):
    """Ray-test a supporting façade; return movement along the outward normal.

    Inputs are placed runtime coordinates. Only parallel, outward-facing wall
    triangles qualify. Half a runtime unit separates quantized renderer depth from the wall. Missing
    support is an error: silently guessing can hide a window behind its wall.
    """
    origin=np.asarray(origin,float);normal=np.asarray(normal,float)
    triangles=np.asarray(triangles,float)
    if triangles.size==0:raise ValueError('No supporting façade geometry')
    e1=triangles[:,1]-triangles[:,0];e2=triangles[:,2]-triangles[:,0]
    normals=np.cross(e1,e2);length=np.linalg.norm(normals,axis=1)
    facing=(normals@normal)/np.maximum(length,1e-12)>.95
    direction=-normal;start=origin+normal*reach
    h=np.cross(np.broadcast_to(direction,e2.shape),e2)
    determinant=np.einsum('ij,ij->i',e1,h)
    valid=facing & (abs(determinant)>1e-9)
    inverse=np.zeros_like(determinant);inverse[valid]=1/determinant[valid]
    s=start-triangles[:,0];u=inverse*np.einsum('ij,ij->i',s,h)
    q=np.cross(s,e1);v=inverse*(q@direction)
    distance=inverse*np.einsum('ij,ij->i',e2,q)
    valid &= (u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)&(distance>=0)&(distance<=2*reach)
    if not valid.any():raise ValueError('Window has no parallel supporting façade within mounting range')
    return float(reach-distance[valid].min()+clearance)


def mount_references(index, references, models, centre, scale):
    """Use full source house walls to mount selected visual window instances."""
    from prepare_scenery import reference_rotation
    walls=[]
    for ref in references:
        mi=ref['model_index']
        if mi not in models or 'house' not in index['models'][mi]['source'].casefold():continue
        vertices,faces,*_=models[mi]
        origin=(np.asarray(ref['position'])-np.array([*centre,0]))*scale
        points=vertices[:,:3]@reference_rotation(ref).T*(scale*ref['scale'])+origin
        walls.extend(points[faces[:,:3]])
    for ref in references:
        mi=ref['model_index']
        if mi not in models or 'flatten' not in models[mi][4]:continue
        details=models[mi][4]['flatten'];normal=np.zeros(3)
        normal[details['axis']]=details['facing']
        normal=reference_rotation(ref)@normal
        origin=(np.asarray(ref['position'])-np.array([*centre,0]))*scale
        # Profiles initially project through the authored attachment origin.
        shift=mounting_shift(origin,normal,walls)
        ref['_flatten_shift']=shift-details['mounting_plane']*scale*ref['scale']*details['facing']
