"""Create a clean source ZIP without local databases or development caches."""

from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT.parent.parent / "outputs" / "Shelfwise_Project.zip"
SKIP_DIRS = {".git", "__pycache__", ".venv", "tmp", "logs"}
SKIP_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3"}


def main() -> None:
    output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OUTPUT.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    included = 0
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=8) as archive:
        for path in ROOT.rglob("*"):
            relative = path.relative_to(ROOT)
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in relative.parts):
                continue
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            archive.write(path, Path(ROOT.name) / relative)
            included += 1
    print(f"Created {output} with {included} project files.")


if __name__ == "__main__":
    main()
