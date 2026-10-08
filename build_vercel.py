"""Copy first-party assets to Vercel's public directory at build time."""
from pathlib import Path
import shutil

def build(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    source = root / "static"
    destination = root / "public" / "static"
    destination.mkdir(parents=True, exist_ok=True)
    for asset in source.iterdir():
        if asset.is_file() and asset.suffix in (".css", ".js"):
            shutil.copyfile(asset, destination / asset.name)

if __name__ == "__main__":
    build()
