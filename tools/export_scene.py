"""Export the composed USD initial scene as a static, Y-up web viewing adapter.
Usage: python tools/export_scene.py SOURCE_ROOT OUTPUT.glb
Requires usd-core, trimesh, numpy, Pillow, fast-simplification and embreex. Never edits source layers or motions.
"""
from pathlib import Path
import sys,json,hashlib,struct
import numpy as np
import trimesh
from PIL import Image
from pxr import Usd,UsdGeom,UsdShade

source=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2])
stage=Usd.Stage.Open(str(source/'home_backgrounds/shared_desk_home_initial.usda'))
cache=UsdGeom.XformCache(Usd.TimeCode.Default())
scene=trimesh.Scene()
yup=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]],dtype=float)
materials={}
textures={}
counts={}

def material_for(prim):
    mat,_=UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
    key=str(mat.GetPath()) if mat else 'default'
    if key in materials:return materials[key]
    color=[.55,.60,.66,1.0];rough=.65;metal=0.;image=None
    if mat:
        shader=mat.ComputeSurfaceSource()[0]
        if not shader: shader=mat.ComputeSurfaceSource("mdl")[0]
        if shader:
            for name in ['diffuseColor','diffuse_color_constant']:
                inp=shader.GetInput(name)
                value=inp.Get() if inp else None
                if value is not None:color=[*value,1.]
                connection=inp.GetConnectedSource() if inp else None
                if connection:
                    tex=UsdShade.Shader(connection[0].GetPrim()).GetInput('file')
                    asset=tex.Get() if tex else None
                    path=Path(asset.resolvedPath) if asset and asset.resolvedPath else None
                    if path and path.is_file():
                        textures[str(path.relative_to(source)).replace('\\','/')] = hashlib.sha256(path.read_bytes()).hexdigest()
                        image=Image.open(path).convert('RGB');image.thumbnail((1024,1024))
                        color=[1.0,1.0,1.0,1.0]
            for name in ['roughness','reflection_roughness_constant']:
                val=shader.GetInput(name).Get() if shader.GetInput(name) else None
                if val is not None:rough=float(val)
            for name in ['metallic','metallic_constant']:
                val=shader.GetInput(name).Get() if shader.GetInput(name) else None
                if val is not None:metal=float(val)
    result=trimesh.visual.material.PBRMaterial(name=key,baseColorFactor=color,baseColorTexture=image,roughnessFactor=rough,metallicFactor=metal,doubleSided=True)
    materials[key]=result
    return result

for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
    if not prim.IsA(UsdGeom.Gprim):continue
    imageable=UsdGeom.Imageable(prim)
    if imageable.ComputeVisibility()=='invisible' or imageable.ComputePurpose() in ('guide','proxy'):continue
    if any(x in str(prim.GetPath()).lower() for x in ['collision','groundplane']):continue
    kind=prim.GetTypeName();uv=None
    if kind=='Mesh':
        usdmesh=UsdGeom.Mesh(prim)
        points=np.asarray(usdmesh.GetPointsAttr().Get(),dtype=float)
        sizes=list(usdmesh.GetFaceVertexCountsAttr().Get() or [])
        indices=np.asarray(usdmesh.GetFaceVertexIndicesAttr().Get(),dtype=int)
        if not len(points) or not len(indices):continue
        # Expand face corners so authored UV seams survive triangulation.
        vertices=points[indices];faces=[];offset=0
        for size in sizes:
            faces.extend([offset,offset+j,offset+j+1] for j in range(1,size-1));offset+=size
        faces=np.asarray(faces,dtype=int)
        if usdmesh.GetOrientationAttr().Get()=='leftHanded':faces=faces[:,::-1]
        mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
        st=UsdGeom.PrimvarsAPI(prim).GetPrimvar('st')
        if st and st.HasValue():
            values=np.asarray(st.ComputeFlattened(),dtype=float)
            if st.GetInterpolation()=='faceVarying' and len(values)==len(indices):uv=values
            elif st.GetInterpolation() in ('vertex','varying'):uv=values[indices]
    elif kind=='Cube':
        size=UsdGeom.Cube(prim).GetSizeAttr().Get();mesh=trimesh.creation.box(extents=[size]*3)
    elif kind=='Sphere':mesh=trimesh.creation.icosphere(subdivisions=2,radius=UsdGeom.Sphere(prim).GetRadiusAttr().Get())
    elif kind in ('Cylinder','Capsule','Cone'):
        obj=getattr(UsdGeom,kind)(prim);r=obj.GetRadiusAttr().Get();h=obj.GetHeightAttr().Get()
        if kind=='Cylinder':mesh=trimesh.creation.cylinder(radius=r,height=h,sections=32)
        elif kind=='Cone':mesh=trimesh.creation.cone(radius=r,height=h,sections=32)
        else:mesh=trimesh.creation.capsule(radius=r,height=h,count=[12,16])
        axis=obj.GetAxisAttr().Get()
        if axis=='X':mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]))
        if axis=='Y':mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
    else:
        raise ValueError(f'Unsupported visible geometry: {prim.GetPath()} {kind}')
    if str(prim.GetPath()).startswith("/World/Robot/") and len(mesh.faces)>3000:
        mesh.merge_vertices()
        mesh=mesh.simplify_quadric_decimation(percent=0.8)
        uv=None
    # Subdivide large room surfaces for a static vertex lightmap; geometry stays fixed.
    if kind=='Mesh' and str(prim.GetPath()).startswith('/World/HomeSet/'):
        for _ in range(5):
            attrs={'uv':uv} if uv is not None else None
            if attrs:
                v,f,a=trimesh.remesh.subdivide(mesh.vertices,mesh.faces,vertex_attributes=attrs)
                uv=a['uv']
            else:
                v,f=trimesh.remesh.subdivide(mesh.vertices,mesh.faces)
            mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
    mesh.visual=trimesh.visual.TextureVisuals(uv=uv,material=material_for(prim))
    transform=yup@np.asarray(cache.GetLocalToWorldTransform(prim),dtype=float).T
    scene.add_geometry(mesh,node_name=str(prim.GetPath()),geom_name=str(prim.GetPath()),transform=transform)
    counts[kind]=counts.get(kind,0)+1
output.parent.mkdir(parents=True,exist_ok=True)
# Bake deterministic ambient occlusion into glTF COLOR_0. Camera remains free.
from trimesh.ray.ray_pyembree import RayMeshIntersector
world_meshes=[]
for node in scene.graph.nodes_geometry:
    transform,geometry=scene.graph[node]
    m=scene.geometry[geometry].copy();m.apply_transform(transform);world_meshes.append(m)
intersector=RayMeshIntersector(trimesh.util.concatenate(world_meshes))
rng=np.random.default_rng(1001)
lights={}
for node in scene.graph.nodes_geometry:
    transform,geometry=scene.graph[node]
    mesh=scene.geometry[geometry]
    vertices=trimesh.transform_points(mesh.vertices,transform)
    normals=mesh.vertex_normals@transform[:3,:3].T
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    origins=vertices+normals*.004
    blocked=np.zeros(len(vertices))
    # Cosine-weighted hemisphere samples; static contact shading only, no motion.
    tangent=np.cross(normals,np.tile([0.,1.,0.],(len(normals),1)))
    parallel=np.linalg.norm(tangent,axis=1)<.01
    tangent[parallel]=np.cross(normals[parallel],[1.,0.,0.])
    tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-12)
    bitangent=np.cross(normals,tangent)
    for sample in range(24):
        u=(sample+.5)/24;angle=sample*2.399963229728653
        direction=tangent*(np.sqrt(u)*np.cos(angle))+bitangent*(np.sqrt(u)*np.sin(angle))+normals*np.sqrt(1-u)
        loc,ray,_=intersector.intersects_location(origins,direction,multiple_hits=False)
        if len(ray):
            distance=np.linalg.norm(loc-origins[ray],axis=1)
            blocked[ray]+=np.clip(1-distance/1.1,0,1)
    factor=1-.72*blocked/24
    lights[geometry]=np.repeat(np.round(factor[:,None]*255).astype(np.uint8),3,axis=1)
    print('Baked',geometry,len(vertices),flush=True)
raw=scene.export(file_type='glb')
json_size=struct.unpack_from('<I',raw,12)[0]
gltf=json.loads(raw[20:20+json_size]);binary=bytearray(raw[28+json_size:])
for mesh in gltf['meshes']:
    colors=lights[mesh['name']]
    for primitive in mesh['primitives']:
        count=gltf['accessors'][primitive['attributes']['POSITION']]['count']
        assert len(colors)==count,(mesh['name'],len(colors),count)
        while len(binary)%4:binary.append(0)
        offset=len(binary);payload=colors.tobytes();binary.extend(payload)
        view=len(gltf['bufferViews']);gltf['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(payload),'target':34962})
        acc=len(gltf['accessors']);gltf['accessors'].append({'bufferView':view,'componentType':5121,'count':count,'type':'VEC3','normalized':True})
        primitive['attributes']['COLOR_0']=acc
while len(binary)%4:binary.append(0)
gltf['buffers'][0]['byteLength']=len(binary)
encoded=json.dumps(gltf,separators=(',',':')).encode()
encoded+=b' '*((-len(encoded))%4)
output.write_bytes(struct.pack('<III',0x46546c67,2,28+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary)
loaded=[{'path':str(Path(layer.realPath).relative_to(source)).replace('\\','/'),'sha256':hashlib.sha256(Path(layer.realPath).read_bytes()).hexdigest()} for layer in stage.GetUsedLayers() if layer.realPath and Path(layer.realPath).is_relative_to(source)]
report={'sourceRepository':'HHD000EXE/PersonaRobotBench','sourceRevision':'26cc1ccc3fd97bbcb834b550af11af0d2b1284ff','entryLayer':'home_backgrounds/shared_desk_home_initial.usda','role':'Static initial-scene viewing adapter; not a simulation, trajectory, policy rollout or evidence of success.','conversions':['Composed default USD pose, original object transforms retained','Z-up meters to glTF Y-up meters: (x,y,z) -> (x,z,-y)','Polygon fan triangulation; procedural primitives tessellated', 'Robot render meshes above 3000 triangles simplified by 80%; poses and transforms unchanged; not suitable for measurement','Diffuse textures resized to maximum 1024 pixels; MDL diffuse/metallic/roughness mapped to glTF PBR; no physics', '24-sample deterministic static ambient-occlusion baked into COLOR_0; room faces subdivided without changing surface shape','Invisible, proxy, guide and collision geometry excluded; rendering ground plane omitted in favor of authored room floor'],'geometryCounts':counts,'boundsYUpMeters':scene.bounds.tolist(),'sourceTextures':textures,'sourceLayers':sorted(loaded,key=lambda x:x['path']),'outputSha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size}
output.with_suffix('.provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['geometryCounts','boundsYUpMeters','bytes']}))

