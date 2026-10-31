"""Upload the prepared 24-case batch and start its GPU-gated remote run."""

from __future__ import annotations

import subprocess
import tarfile
import argparse
from pathlib import Path

from scripts.download_remote_60 import ssh_command


ROOT = Path(__file__).resolve().parents[1]


def remote(command: str, *, input_file=None) -> subprocess.CompletedProcess:
    return subprocess.run(ssh_command("'" + command + "'"),
                          stdin=input_file, capture_output=True, text=False,
                          timeout=120, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", choices=("round2_image_batch24", "round2_grade_probe11"),
                    default="round2_image_batch24")
    args = ap.parse_args()
    source = ROOT / "data" / args.batch
    dest = "/mnt/data1/azureuser/video_teacher_" + args.batch
    archive = source / "transfer.tar"
    with tarfile.open(archive, "w") as tf:
        for path in sorted(source.rglob("*")):
            if path.is_file() and path != archive:
                tf.add(path, arcname=path.relative_to(source).as_posix())
    try:
        with archive.open("rb") as stream:
            remote(f"mkdir -p {dest} && tar -C {dest} -xf -", input_file=stream)
    finally:
        archive.unlink(missing_ok=True)
    check = remote(f"wc -l {dest}/prompts.jsonl")
    print(check.stdout.decode(errors="replace").strip())
    launch = remote(f"nohup bash {dest}/run_remote.sh > {dest}/run.log 2>&1 < /dev/null & echo $!")
    print("remote_pid=" + launch.stdout.decode(errors="replace").strip())


if __name__ == "__main__":
    main()
