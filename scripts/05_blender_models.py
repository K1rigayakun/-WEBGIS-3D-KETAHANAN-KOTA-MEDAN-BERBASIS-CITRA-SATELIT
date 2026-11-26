import math
import os
import bpy
from mathutils import Euler, Vector

BASE_DIR = r"M:\Kuliah\Semester 5\SIG\Project Akhir"
MODEL_DIR = os.path.join(BASE_DIR, "web-peta-interaktif", "models")
PREVIEW_PNG = os.path.join(BASE_DIR, "testing", "screenshoot", "blender_models_preview.png")
BLEND_OUT = os.path.join(BASE_DIR, "scripts", "blender_models_source.blend")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(os.path.dirname(PREVIEW_PNG), exist_ok=True)


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(hex_str: str):
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)


def make_material(name: str, hex_str: str, roughness: float = 0.58, emission_strength: float = 0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    col = hex_to_linear(hex_str)
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = roughness
    if emission_strength > 0:
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    return {
        "ink": make_material("M_Ink", "#071B2B", roughness=0.6),
        "teal": make_material("M_Teal", "#167D8D", roughness=0.52),
        "ice": make_material("M_Ice", "#B9E4E8", roughness=0.45),
        "paper": make_material("M_Paper", "#EEEEEE", roughness=0.68),
        "white": make_material("M_White", "#FFFFFF", roughness=0.5),
        "lamp": make_material("LampGlow", "#FFC94D", roughness=0.25, emission_strength=4.0),
    }


def add_bevel(obj, width: float = 0.04, segments: int = 2):
    mod = obj.modifiers.new(name="ClayBevel", type="BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def add_box(name, size, loc, mat, rot=(0, 0, 0), bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.data.materials.append(mat)
    if bevel > 0:
        add_bevel(obj, width=bevel, segments=2)
    return obj


def add_cyl(name, r_bot, r_top, depth, loc, mat, segs=16, rot=(0, 0, 0), bevel=0.02):
    bpy.ops.mesh.primitive_cone_add(
        vertices=segs,
        radius1=r_bot,
        radius2=r_top,
        depth=depth,
        location=loc,
        rotation=rot,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    if bevel > 0:
        add_bevel(obj, width=bevel, segments=2)
    return obj


def add_sphere(name, radius, loc, mat, segs=14):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=10, radius=radius, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return obj


def join_and_anchor(name, parts):
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = name
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    return obj


def build_pju_smart(mats):
    parts = [
        # Concrete plinth
        add_box("pju_plinth", (0.6, 0.6, 0.4), (0, 0, 0.2), mats["paper"], bevel=0.04),
        # Tapered main pole (height 9m from plinth top z=0.4 -> center 4.7)
        add_cyl("pju_pole", 0.09, 0.06, 8.6, (0, 0, 4.7), mats["ink"], segs=16, bevel=0.015),
        # Angled arm reaching +X ~1.6m
        add_cyl("pju_arm", 0.055, 0.045, 1.7, (0.78, 0, 8.75), mats["ink"], segs=12, rot=(0, math.radians(72), 0), bevel=0.015),
        # Lamp head housing
        add_box("pju_head", (0.72, 0.34, 0.16), (1.65, 0, 8.95), mats["teal"], bevel=0.03),
        # Glowing bottom lens (LampGlow)
        add_box("pju_lens", (0.58, 0.24, 0.06), (1.65, 0, 8.86), mats["lamp"], bevel=0.015),
        # Solar panel frame & active surface tilted 25 deg at pole peak
        add_box("pju_solar_frame", (1.24, 0.74, 0.07), (0.0, 0, 9.18), mats["ice"], rot=(0, math.radians(-25), 0), bevel=0.025),
        add_box("pju_solar_cell", (1.14, 0.64, 0.08), (0.0, 0, 9.19), mats["teal"], rot=(0, math.radians(-25), 0), bevel=0.02),
        # Sensor dome
        add_sphere("pju_sensor", 0.12, (1.65, 0, 9.05), mats["ice"]),
    ]
    return join_and_anchor("pju_smart", parts)


def build_cctv_pole(mats):
    parts = [
        add_box("cctv_plinth", (0.55, 0.55, 0.38), (0, 0, 0.19), mats["paper"], bevel=0.04),
        add_cyl("cctv_pole", 0.085, 0.06, 6.8, (0, 0, 3.78), mats["ink"], segs=16, bevel=0.015),
        # Upper lamp arm + small warm LED head
        add_cyl("cctv_lamp_arm", 0.045, 0.038, 1.15, (0.52, 0, 7.05), mats["ink"], segs=12, rot=(0, math.radians(75), 0), bevel=0.01),
        add_box("cctv_lamp_head", (0.44, 0.24, 0.12), (1.08, 0, 7.16), mats["teal"], bevel=0.025),
        add_box("cctv_lamp_lens", (0.34, 0.16, 0.05), (1.08, 0, 7.09), mats["lamp"], bevel=0.01),
        # CCTV bracket + body pointing opposite/angled
        add_box("cctv_bracket", (0.55, 0.1, 0.1), (-0.28, 0, 6.2), mats["ink"], bevel=0.02),
        add_box("cctv_body", (0.46, 0.22, 0.22), (-0.58, 0, 6.18), mats["white"], rot=(0, math.radians(15), 0), bevel=0.035),
        add_cyl("cctv_lens", 0.08, 0.08, 0.16, (-0.82, 0, 6.11), mats["ink"], segs=14, rot=(0, math.radians(105), 0), bevel=0.01),
        # Status LED strip on CCTV
        add_box("cctv_led", (0.14, 0.24, 0.05), (-0.58, 0, 6.3), mats["lamp"], rot=(0, math.radians(15), 0), bevel=0.01),
    ]
    return join_and_anchor("cctv_pole", parts)


def build_pos_pantau(mats):
    parts = [
        # Kiosk base pad
        add_box("pos_pad", (2.7, 2.7, 0.18), (0, 0, 0.09), mats["paper"], bevel=0.04),
        # Main kiosk body 2.4x2.4x2.5
        add_box("pos_body", (2.3, 2.3, 2.45), (0, 0, 1.4), mats["white"], bevel=0.06),
        # Teal accent band
        add_box("pos_band", (2.36, 2.36, 0.42), (0, 0, 1.05), mats["teal"], bevel=0.04),
        # Overhanging flat roof
        add_box("pos_roof", (2.85, 2.85, 0.28), (0, 0, 2.72), mats["ink"], bevel=0.06),
        # Windows (front/back & left/right)
        add_box("pos_win_x", (2.38, 1.45, 0.72), (0, 0, 1.92), mats["ice"], bevel=0.03),
        add_box("pos_win_y", (1.45, 2.38, 0.72), (0, 0, 1.92), mats["ice"], bevel=0.03),
        # Roof beacon light
        add_cyl("pos_beacon", 0.18, 0.14, 0.24, (0, 0, 2.98), mats["lamp"], segs=14, bevel=0.02),
        # Front Panic Button Pedestal (1.2m tall)
        add_cyl("pos_panic_post", 0.07, 0.07, 1.2, (1.55, 0, 0.6), mats["ink"], segs=12, bevel=0.015),
        add_box("pos_panic_box", (0.28, 0.28, 0.34), (1.55, 0, 1.28), mats["teal"], bevel=0.03),
        add_sphere("pos_panic_btn", 0.11, (1.68, 0, 1.28), mats["lamp"]),
    ]
    return join_and_anchor("pos_pantau", parts)


def build_police_post(mats):
    parts = [
        # Base platform
        add_box("pol_base", (10.6, 7.6, 0.4), (0, 0, 0.2), mats["paper"], bevel=0.08),
        # 2-story main block 10x7x6.6
        add_box("pol_body", (9.8, 6.8, 6.6), (0, 0, 3.7), mats["white"], bevel=0.12),
        # Teal mid horizontal band & lower trim
        add_box("pol_band", (10.05, 7.05, 0.9), (0, 0, 3.75), mats["teal"], bevel=0.06),
        add_box("pol_porch", (3.6, 1.8, 0.35), (0, -3.9, 3.1), mats["teal"], bevel=0.05),
        # Roof parapet
        add_box("pol_roof", (10.4, 7.4, 0.65), (0, 0, 7.25), mats["ink"], bevel=0.08),
        # Windows grid (front/back and sides)
        add_box("pol_win_f1", (1.6, 7.02, 1.4), (-2.9, 0, 5.4), mats["ice"], bevel=0.04),
        add_box("pol_win_f2", (1.6, 7.02, 1.4), (0.0, 0, 5.4), mats["ice"], bevel=0.04),
        add_box("pol_win_f3", (1.6, 7.02, 1.4), (2.9, 0, 5.4), mats["ice"], bevel=0.04),
        add_box("pol_win_l1", (1.6, 7.02, 1.3), (-2.9, 0, 1.9), mats["ice"], bevel=0.04),
        add_box("pol_win_l2", (1.6, 7.02, 1.3), (2.9, 0, 1.9), mats["ice"], bevel=0.04),
        add_box("pol_door", (1.8, 0.3, 2.3), (0.0, -3.35, 1.55), mats["ink"], bevel=0.04),
        # Roof rotator beacon
        add_cyl("pol_rotator", 0.35, 0.28, 0.45, (-2.8, -1.8, 7.8), mats["lamp"], segs=16, bevel=0.04),
        # Flagpole 8m tall beside entrance
        add_cyl("pol_flagpole", 0.09, 0.05, 8.0, (5.5, -2.5, 4.0), mats["ink"], segs=12, bevel=0.015),
        add_box("pol_flag", (1.6, 0.06, 0.95), (6.3, -2.5, 7.35), mats["teal"], bevel=0.01),
    ]
    return join_and_anchor("police_post", parts)


def export_model(obj, filename):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    out_path = os.path.join(MODEL_DIR, filename)
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
    )
    vcount = len(obj.data.vertices)
    fsize = os.path.getsize(out_path)
    print(f"[BLENDER] Exported {filename}: {fsize} bytes, {vcount} vertices", flush=True)


def render_preview(objs):
    # Arrange all 4 models side by side cleanly framed with flagpole
    positions = [-11.5, -5.8, -0.2, 8.2]
    for obj, px in zip(objs, positions):
        obj.location = (px, 0.0, 0.0)

    # World background #EEEEEE
    world = bpy.data.worlds.new("PreviewWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = hex_to_linear("#EEEEEE")
        bg.inputs["Strength"].default_value = 1.0

    # Ground plane subtle paper
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.02))
    ground = bpy.context.active_object
    ground.data.materials.append(make_material("M_Paper", "#EEEEEE", roughness=0.85))

    # Sun light
    light_data = bpy.data.lights.new(name="SunLight", type="SUN")
    light_data.energy = 3.2
    light_obj = bpy.data.objects.new(name="SunLight", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.rotation_euler = Euler((math.radians(48), math.radians(-20), math.radians(32)), "XYZ")

    # Camera isometric view framing all 4 models including police flagpole
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 36
    cam_obj = bpy.data.objects.new("PreviewCam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.5, -34.0, 13.5)
    direction = Vector((0.2, 0.0, 4.0)) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam_obj

    scene = bpy.context.scene
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = PREVIEW_PNG

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        bpy.ops.render.render(write_still=True)
        print(f"[BLENDER] Rendered EEVEE_NEXT preview -> {PREVIEW_PNG}", flush=True)
    except Exception as exc:
        print(f"[BLENDER] EEVEE_NEXT failed ({exc}), falling back to BLENDER_WORKBENCH", flush=True)
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        bpy.ops.render.render(write_still=True)
        print(f"[BLENDER] Rendered WORKBENCH preview -> {PREVIEW_PNG}", flush=True)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    print(f"[BLENDER] Saved source .blend -> {BLEND_OUT}", flush=True)


def main():
    mats = reset_scene()
    m1 = build_pju_smart(mats)
    m2 = build_cctv_pole(mats)
    m3 = build_pos_pantau(mats)
    m4 = build_police_post(mats)

    export_model(m1, "pju_smart.glb")
    export_model(m2, "cctv_pole.glb")
    export_model(m3, "pos_pantau.glb")
    export_model(m4, "police_post.glb")

    render_preview([m1, m2, m3, m4])


if __name__ == "__main__":
    main()
