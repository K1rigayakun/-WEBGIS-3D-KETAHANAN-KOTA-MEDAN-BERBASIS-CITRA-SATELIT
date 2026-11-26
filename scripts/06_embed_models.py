import base64
import json
from pathlib import Path

BASE_DIR = Path(r"M:\Kuliah\Semester 5\SIG\Project Akhir")
MODEL_DIR = BASE_DIR / "web-peta-interaktif" / "models"
OUT_JS = BASE_DIR / "web-peta-interaktif" / "data" / "models_bundle.js"

NAMES = ["pju_smart", "cctv_pole", "pos_pantau", "police_post"]


def main() -> None:
    bundle = {}
    for name in NAMES:
        p = MODEL_DIR / f"{name}.glb"
        if not p.exists():
            raise FileNotFoundError(f"Missing GLB: {p}")
        raw = p.read_bytes()
        bundle[name] = base64.b64encode(raw).decode("ascii")
        print(f"[06_EMBED] {name}.glb: {len(raw)} bytes -> b64 len {len(bundle[name])}")

    OUT_JS.write_text("window.MEDAN_MODELS = " + json.dumps(bundle, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"[06_EMBED] Saved {OUT_JS} ({OUT_JS.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
