import os
import math
import json
import struct
import base64
import numpy as np

MODEL_DIR = "/tmp/work_merge/sekarang/web-peta-interaktif/models"
WEB_DATA_DIR = "/tmp/work_merge/sekarang/web-peta-interaktif/data"
os.makedirs(MODEL_DIR, exist_ok=True)

def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def hex_to_linear(hex_str: str):
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return [round(srgb_to_linear(r), 6), round(srgb_to_linear(g), 6), round(srgb_to_linear(b), 6), 1.0]

MATERIALS_DEF = {
    "M_Ink": {"color": "#071B2B", "roughness": 0.6},
    "M_Teal": {"color": "#167D8D", "roughness": 0.52},
    "M_Ice": {"color": "#B9E4E8", "roughness": 0.45},
    "M_Paper": {"color": "#EEEEEE", "roughness": 0.68},
    "M_White": {"color": "#FFFFFF", "roughness": 0.5},
    "LampGlow": {"color": "#FFC94D", "roughness": 0.25, "emissive": True},
    "M_LeafDark": {"color": "#15803D", "roughness": 0.55},
    "M_LeafBright": {"color": "#22C55E", "roughness": 0.48},
    "M_Wood": {"color": "#5C4033", "roughness": 0.75},
    "M_FireRed": {"color": "#DC2626", "roughness": 0.42},
    "M_WarnOrange": {"color": "#F97316", "roughness": 0.48},
    "M_WaterBlue": {"color": "#0284C7", "roughness": 0.35},
}

def rot_matrix(rx, ry, rz):
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx

def zup_to_yup(pts):
    # Blender Z-up (x, y, z) -> glTF Y-up (x, z, -y)
    out = np.empty_like(pts)
    out[:, 0] = pts[:, 0]
    out[:, 1] = pts[:, 2]
    out[:, 2] = -pts[:, 1]
    return out

class MeshBuilder:
    def __init__(self, name):
        self.name = name
        self.by_mat = {} # mat_name -> {"pos": [], "norm": [], "idx": []}

    def _add_raw(self, mat_name, verts_zup, norms_zup, faces):
        verts = zup_to_yup(verts_zup)
        norms = zup_to_yup(norms_zup)
        norm_lens = np.linalg.norm(norms, axis=1, keepdims=True)
        norms = norms / np.maximum(norm_lens, 1e-8)

        bucket = self.by_mat.setdefault(mat_name, {"pos": [], "norm": [], "idx": []})
        base_idx = len(bucket["pos"])
        bucket["pos"].extend(verts.tolist())
        bucket["norm"].extend(norms.tolist())
        for f in faces:
            bucket["idx"].extend([base_idx + f[0], base_idx + f[1], base_idx + f[2]])

    def add_box(self, size, loc, mat_name, rot=(0, 0, 0)):
        sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
        R = rot_matrix(*rot)
        T = np.array(loc, dtype=np.float64)
        # 6 faces, 4 vertices each
        face_defs = [
            ([(-sx,-sy, sz), ( sx,-sy, sz), ( sx, sy, sz), (-sx, sy, sz)], (0, 0, 1)),
            ([(-sx, sy,-sz), ( sx, sy,-sz), ( sx,-sy,-sz), (-sx,-sy,-sz)], (0, 0,-1)),
            ([( sx,-sy,-sz), ( sx, sy,-sz), ( sx, sy, sz), ( sx,-sy, sz)], (1, 0, 0)),
            ([(-sx, sy,-sz), (-sx,-sy,-sz), (-sx,-sy, sz), (-sx, sy, sz)], (-1, 0, 0)),
            ([(-sx, sy,-sz), ( sx, sy,-sz), ( sx, sy, sz), (-sx, sy, sz)], (0, 1, 0)),
            ([( sx,-sy,-sz), (-sx,-sy,-sz), (-sx,-sy, sz), ( sx,-sy, sz)], (0,-1, 0)),
        ]
        verts = []
        norms = []
        faces = []
        for quad, n in face_defs:
            b = len(verts)
            rn = (R @ np.array(n, dtype=np.float64)).tolist()
            for v in quad:
                rv = (R @ np.array(v, dtype=np.float64) + T).tolist()
                verts.append(rv)
                norms.append(rn)
            faces.append((b, b+1, b+2))
            faces.append((b, b+2, b+3))
        self._add_raw(mat_name, np.array(verts), np.array(norms), faces)

    def add_cyl(self, r_bot, r_top, depth, loc, mat_name, segs=16, rot=(0, 0, 0)):
        R = rot_matrix(*rot)
        T = np.array(loc, dtype=np.float64)
        hz = depth / 2.0
        verts = []
        norms = []
        faces = []
        # Side wall
        for i in range(segs):
            a0 = 2 * math.pi * i / segs
            a1 = 2 * math.pi * ((i + 1) % segs) / segs
            c0, s0 = math.cos(a0), math.sin(a0)
            c1, s1 = math.cos(a1), math.sin(a1)
            b = len(verts)
            v00 = R @ np.array([r_bot * c0, r_bot * s0, -hz]) + T
            v10 = R @ np.array([r_bot * c1, r_bot * s1, -hz]) + T
            v11 = R @ np.array([r_top * c1, r_top * s1,  hz]) + T
            v01 = R @ np.array([r_top * c0, r_top * s0,  hz]) + T
            n0 = R @ np.array([c0, s0, (r_bot - r_top) / max(depth, 0.01)])
            n1 = R @ np.array([c1, s1, (r_bot - r_top) / max(depth, 0.01)])
            verts.extend([v00, v10, v11, v01])
            norms.extend([n0, n1, n1, n0])
            faces.append((b, b+1, b+2))
            faces.append((b, b+2, b+3))
        # Top cap
        if r_top > 1e-4:
            bt = len(verts)
            nt = R @ np.array([0.0, 0.0, 1.0])
            verts.append(R @ np.array([0.0, 0.0, hz]) + T)
            norms.append(nt)
            for i in range(segs):
                a = 2 * math.pi * i / segs
                verts.append(R @ np.array([r_top * math.cos(a), r_top * math.sin(a), hz]) + T)
                norms.append(nt)
            for i in range(segs):
                faces.append((bt, bt + 1 + i, bt + 1 + ((i + 1) % segs)))
        # Bottom cap
        if r_bot > 1e-4:
            bb = len(verts)
            nb = R @ np.array([0.0, 0.0, -1.0])
            verts.append(R @ np.array([0.0, 0.0, -hz]) + T)
            norms.append(nb)
            for i in range(segs):
                a = 2 * math.pi * i / segs
                verts.append(R @ np.array([r_bot * math.cos(a), r_bot * math.sin(a), -hz]) + T)
                norms.append(nb)
            for i in range(segs):
                faces.append((bb, bb + 1 + ((i + 1) % segs), bb + 1 + i))
        self._add_raw(mat_name, np.array(verts), np.array(norms), faces)

    def add_sphere(self, radius, loc, mat_name, segs=14, rings=10, scale=(1.0, 1.0, 1.0)):
        T = np.array(loc, dtype=np.float64)
        sx, sy, sz = scale
        verts = []
        norms = []
        faces = []
        for r in range(rings + 1):
            phi = math.pi * r / rings
            sp, cp = math.sin(phi), math.cos(phi)
            for s in range(segs):
                theta = 2 * math.pi * s / segs
                ct, st = math.cos(theta), math.sin(theta)
                nx, ny, nz = sp * ct, sp * st, cp
                vx = radius * sx * nx
                vy = radius * sy * ny
                vz = radius * sz * nz
                verts.append(np.array([vx, vy, vz]) + T)
                norms.append(np.array([nx / max(sx, 0.01), ny / max(sy, 0.01), nz / max(sz, 0.01)]))
        for r in range(rings):
            for s in range(segs):
                i0 = r * segs + s
                i1 = r * segs + ((s + 1) % segs)
                i2 = (r + 1) * segs + ((s + 1) % segs)
                i3 = (r + 1) * segs + s
                faces.append((i0, i2, i1))
                faces.append((i0, i3, i2))
        self._add_raw(mat_name, np.array(verts), np.array(norms), faces)

    def export_glb(self, out_path):
        materials = []
        primitives = []
        buffer_views = []
        accessors = []
        bin_chunks = bytearray()

        def pad4(buf):
            rem = len(buf) % 4
            if rem:
                buf.extend(b"\x00" * (4 - rem))

        for mat_name, bucket in self.by_mat.items():
            mdef = MATERIALS_DEF[mat_name]
            col = hex_to_linear(mdef["color"])
            mat_obj = {
                "name": mat_name,
                "doubleSided": True,
                "pbrMetallicRoughness": {
                    "baseColorFactor": col,
                    "metallicFactor": 0.0,
                    "roughnessFactor": mdef["roughness"],
                },
            }
            if mdef.get("emissive"):
                mat_obj["emissiveFactor"] = col[:3]
                mat_obj["extensions"] = {"KHR_materials_emissive_strength": {"emissiveStrength": 4.0}}
            mat_idx = len(materials)
            materials.append(mat_obj)

            pos_arr = np.array(bucket["pos"], dtype=np.float32)
            norm_arr = np.array(bucket["norm"], dtype=np.float32)
            idx_arr = np.array(bucket["idx"], dtype=np.uint16)

            # Position bufferView + accessor
            pos_offset = len(bin_chunks)
            pos_bytes = pos_arr.tobytes()
            bin_chunks.extend(pos_bytes)
            pad4(bin_chunks)
            bv_pos = len(buffer_views)
            buffer_views.append({"buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes), "target": 34962})
            acc_pos = len(accessors)
            accessors.append({
                "bufferView": bv_pos,
                "componentType": 5126,
                "count": len(pos_arr),
                "type": "VEC3",
                "min": pos_arr.min(axis=0).tolist(),
                "max": pos_arr.max(axis=0).tolist(),
            })

            # Normal bufferView + accessor
            norm_offset = len(bin_chunks)
            norm_bytes = norm_arr.tobytes()
            bin_chunks.extend(norm_bytes)
            pad4(bin_chunks)
            bv_norm = len(buffer_views)
            buffer_views.append({"buffer": 0, "byteOffset": norm_offset, "byteLength": len(norm_bytes), "target": 34962})
            acc_norm = len(accessors)
            accessors.append({
                "bufferView": bv_norm,
                "componentType": 5126,
                "count": len(norm_arr),
                "type": "VEC3",
            })

            # Index bufferView + accessor
            idx_offset = len(bin_chunks)
            idx_bytes = idx_arr.tobytes()
            bin_chunks.extend(idx_bytes)
            pad4(bin_chunks)
            bv_idx = len(buffer_views)
            buffer_views.append({"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_bytes), "target": 34963})
            acc_idx = len(accessors)
            accessors.append({
                "bufferView": bv_idx,
                "componentType": 5123,
                "count": len(idx_arr),
                "type": "SCALAR",
            })

            primitives.append({
                "attributes": {"POSITION": acc_pos, "NORMAL": acc_norm},
                "indices": acc_idx,
                "material": mat_idx,
            })

        gltf = {
            "asset": {"generator": "MedanResilience3D GLB Builder", "version": "2.0"},
            "scene": 0,
            "scenes": [{"name": "Scene", "nodes": [0]}],
            "nodes": [{"mesh": 0, "name": self.name}],
            "meshes": [{"name": self.name, "primitives": primitives}],
            "materials": materials,
            "accessors": accessors,
            "bufferViews": buffer_views,
            "buffers": [{"byteLength": len(bin_chunks)}],
        }
        json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        json_pad = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b" " * json_pad

        total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_chunks)
        with open(out_path, "wb") as fp:
            fp.write(struct.pack("<4sII", b"glTF", 2, total_len))
            fp.write(struct.pack("<I4s", len(json_bytes), b"JSON"))
            fp.write(json_bytes)
            fp.write(struct.pack("<I4s", len(bin_chunks), b"BIN\x00"))
            fp.write(bin_chunks)
        print(f"[GLB] Built {os.path.basename(out_path)} ({total_len} bytes)")

def build_all():
    # 1. Halte Teduh (Cool Transit Shelter - Orang 1 William)
    m = MeshBuilder("halte_teduh")
    m.add_box((5.2, 2.6, 0.24), (0, 0, 0.12), "M_Paper")
    m.add_cyl(0.12, 0.12, 3.1, (-2.1, -0.8, 1.66), "M_Ink", segs=12)
    m.add_cyl(0.12, 0.12, 3.1, ( 2.1, -0.8, 1.66), "M_Ink", segs=12)
    m.add_box((4.5, 0.24, 2.7), (0, 0.9, 1.55), "M_Teal")
    m.add_box((4.2, 0.32, 2.3), (0, 0.86, 1.55), "M_LeafBright")
    m.add_box((0.32, 1.8, 2.4), (-2.15, 0.0, 1.55), "M_LeafDark")
    m.add_box((3.2, 0.58, 0.16), (0, 0.35, 0.72), "M_Wood")
    m.add_box((5.6, 3.0, 0.28), (0, 0, 3.25), "M_White", rot=(math.radians(6), 0, 0))
    m.add_box((2.2, 1.2, 0.12), (0, 0, 3.46), "M_Teal", rot=(math.radians(6), 0, 0))
    m.add_box((4.6, 0.28, 0.12), (0, -0.7, 3.06), "LampGlow")
    m.export_glb(os.path.join(MODEL_DIR, "halte_teduh.glb"))

    # 2. Pohon Peneduh (Trembesi / Mahoni / RTH Park Tree - Orang 1 William & Orang 2 Jordan)
    m = MeshBuilder("pohon_peneduh")
    m.add_box((1.6, 1.6, 0.3), (0, 0, 0.15), "M_Paper")
    m.add_cyl(0.32, 0.20, 3.4, (0, 0, 1.8), "M_Wood", segs=12)
    m.add_sphere(2.3, (0, 0, 4.3), "M_LeafDark", segs=14, rings=10, scale=(1.35, 1.35, 0.72))
    m.add_sphere(1.7, (0.3, -0.2, 5.2), "M_LeafBright", segs=12, rings=8, scale=(1.2, 1.2, 0.68))
    m.add_sphere(1.5, (-0.8, 0.5, 4.1), "M_LeafBright", segs=12, rings=8, scale=(1.1, 1.1, 0.65))
    m.export_glb(os.path.join(MODEL_DIR, "pohon_peneduh.glb"))

    # 3. Posko Evakuasi Banjir (Elevated Shelter - Orang 3)
    m = MeshBuilder("posko_evakuasi")
    m.add_box((6.4, 5.2, 0.45), (0, 0, 0.22), "M_Ink")
    m.add_box((6.0, 4.8, 0.35), (0, 0, 1.15), "M_Paper")
    for sx in (-2.5, 2.5):
        for sy in (-1.9, 1.9):
            m.add_cyl(0.22, 0.22, 1.1, (sx, sy, 0.55), "M_Ink", segs=10)
    m.add_box((5.2, 4.0, 2.8), (0, 0, 2.7), "M_White")
    m.add_box((5.35, 4.15, 0.58), (0, 0, 2.1), "M_WarnOrange")
    m.add_box((5.8, 4.6, 0.48), (0, 0, 4.25), "M_Teal")
    m.add_cyl(0.32, 0.22, 0.5, (0, 0, 4.72), "LampGlow", segs=12)
    m.export_glb(os.path.join(MODEL_DIR, "posko_evakuasi.glb"))

    # 4. Hidran Darurat (Fire Hydrant Pillar - Orang 4 Peter)
    m = MeshBuilder("hidran_darurat")
    m.add_box((1.5, 1.5, 0.3), (0, 0, 0.15), "M_Paper")
    m.add_cyl(0.40, 0.38, 1.95, (0, 0, 1.2), "M_FireRed", segs=14)
    m.add_sphere(0.42, (0, 0, 2.22), "M_FireRed", segs=14, rings=10, scale=(1, 1, 0.8))
    m.add_cyl(0.14, 0.12, 0.25, (0, 0, 2.58), "M_White", segs=8)
    m.add_cyl(0.18, 0.18, 0.45, (-0.45, 0, 1.65), "M_White", segs=10, rot=(0, math.radians(90), 0))
    m.add_cyl(0.18, 0.18, 0.45, ( 0.45, 0, 1.65), "M_White", segs=10, rot=(0, math.radians(90), 0))
    m.add_cyl(0.22, 0.22, 0.48, (0, -0.46, 1.55), "LampGlow", segs=12, rot=(math.radians(90), 0, 0))
    m.export_glb(os.path.join(MODEL_DIR, "hidran_darurat.glb"))

    # 5. Pos Damkar (Fire Station 2-Bay + Siren Tower - Orang 4 Peter)
    m = MeshBuilder("pos_damkar")
    m.add_box((9.2, 6.8, 0.4), (0, 0, 0.2), "M_Paper")
    m.add_box((8.4, 6.0, 5.2), (0, 0, 2.9), "M_White")
    m.add_box((8.65, 6.25, 1.1), (0, 0, 4.4), "M_FireRed")
    m.add_box((2.4, 0.3, 3.1), (-1.9, -3.0, 1.9), "M_FireRed")
    m.add_box((2.4, 0.3, 3.1), ( 1.9, -3.0, 1.9), "M_FireRed")
    m.add_box((9.0, 6.6, 0.5), (0, 0, 5.7), "M_Ink")
    m.add_box((2.2, 2.2, 3.2), (2.6, 1.4, 7.3), "M_FireRed")
    m.add_cyl(0.38, 0.28, 0.6, (2.6, 1.4, 9.15), "LampGlow", segs=14)
    m.export_glb(os.path.join(MODEL_DIR, "pos_damkar.glb"))

    all_names = [
        "pju_smart", "cctv_pole", "pos_pantau", "police_post",
        "halte_teduh", "pohon_peneduh", "posko_evakuasi", "hidran_darurat", "pos_damkar"
    ]
    bundle = {}
    for name in all_names:
        p = os.path.join(MODEL_DIR, f"{name}.glb")
        with open(p, "rb") as f:
            bundle[name] = base64.b64encode(f.read()).decode("ascii")
    out_js = os.path.join(WEB_DATA_DIR, "models_bundle.js")
    with open(out_js, "w", encoding="utf-8") as fp:
        fp.write("window.MEDAN_MODELS = ")
        json.dump(bundle, fp, separators=(",", ":"))
        fp.write(";\n")
    print(f"[GLB] Bundled all {len(bundle)} models into models_bundle.js ({os.path.getsize(out_js)//1024} KB)")

if __name__ == "__main__":
    build_all()
