from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src-tauri" / "binaries"
OUT.mkdir(parents=True, exist_ok=True)

triple = subprocess.check_output(
    ["rustc", "--print", "host-tuple"],
    text=True,
).strip()

extension = ".exe" if platform.system() == "Windows" else ""
target = OUT / f"vibesorter-sidecar-{triple}{extension}"

subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        "vibesorter-sidecar",
        str(ROOT / "scripts" / "vibesorter_sidecar.py"),
    ],
    cwd=ROOT,
    check=True,
)

built = ROOT / "dist" / f"vibesorter-sidecar{extension}"
shutil.copy2(built, target)
print(f"Created {target}")
