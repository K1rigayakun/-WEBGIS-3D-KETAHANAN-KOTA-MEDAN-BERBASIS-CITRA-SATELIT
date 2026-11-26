import os
import zipfile
from pathlib import Path

BASE_DIR = Path(r"M:\Kuliah\Semester 5\SIG\Project Akhir")
ZIP_PATH = BASE_DIR / "Tugas_Akhir_SIG_Orang5.zip"


def add_file(zf: zipfile.ZipFile, src: Path, arc: str) -> None:
    zf.write(src, arc)


def main() -> None:
    required_root = [
        BASE_DIR / "Layout_Peta_Orang5.png",
        BASE_DIR / "Medan_DarkZone_Crime_Orang5.qgz",
        BASE_DIR / "Makalah_Tugas_Akhir_SIG_Orang5.pdf",
    ]
    for p in required_root:
        if not p.exists():
            raise FileNotFoundError(f"Missing required deliverable: {p}")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in required_root:
            add_file(zf, p, p.name)

        data_dir = BASE_DIR / "data"
        for root, dirs, files in os.walk(data_dir):
            dirs[:] = [d for d in sorted(dirs) if d != "raw_osm"]
            for fname in sorted(files):
                fpath = Path(root) / fname
                rel = fpath.relative_to(BASE_DIR).as_posix()
                add_file(zf, fpath, rel)

        web_dir = BASE_DIR / "web-peta-interaktif"
        for root, dirs, files in os.walk(web_dir):
            dirs[:] = [d for d in sorted(dirs) if d != "_backup_v1"]
            for fname in sorted(files):
                if ".blend" in fname:
                    continue
                fpath = Path(root) / fname
                rel = fpath.relative_to(BASE_DIR).as_posix()
                add_file(zf, fpath, rel)

    print(f"[04_ZIP] Created {ZIP_PATH.name} ({ZIP_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
