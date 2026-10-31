"""Upload the prepared 24-case batch and start its GPU-gated remote run."""

from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

from scripts.download_remote_60 import ssh_command


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/round2_image_batch24"
DEST = "/mnt/data1/azureuser/video_teacher_round2_image_batch24"


def remote(command: str, *, input_file=None) -> subprocess.CompletedProcess:
    return subprocess.run(ssh_command("'" + command + "'"),
                          stdin=input_file, capture_output=True, text=False,
                          timeout=120, check=True)


def main() -> None:
    archive = SOURCE / "transfer.tar"
    with tarfile.open(archive, "w") as tf:
        for path in sorted(SOURCE.rglob("*")):
            if path.is_file() and path != archive:
                tf.add(path, arcname=path.relative_to(SOURCE).as_posix())
    try:
        with archive.open("rb") as stream:
            remote(f"mkdir -p {DEST} && tar -C {DEST} -xf -", input_file=stream)
    finally:
        archive.unlink(missing_ok=True)
    check = remote(f"wc -l {DEST}/prompts.jsonl {DEST}/image_manifest.jsonl")
    print(check.stdout.decode(errors="replace").strip())
    launch = remote(f"nohup bash {DEST}/run_remote.sh > {DEST}/run.log 2>&1 < /dev/null & echo $!")
    print("remote_pid=" + launch.stdout.decode(errors="replace").strip())


if __name__ == "__main__":
    main()
