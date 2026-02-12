#!/usr/bin/env python3
"""
Join multiple MP4 files into a single video using ffmpeg (concat demuxer, no re-encode).
Requires ffmpeg on PATH.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def find_ffmpeg() -> str:
    """Return path to ffmpeg executable or raise if not found."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return "ffmpeg"
    except FileNotFoundError:
        pass
    raise SystemExit("ffmpeg not found. Install ffmpeg and add it to your PATH.")


def join_mp4(
    input_paths: list[Path],
    output_path: Path,
    ffmpeg_path: str = "ffmpeg",
) -> bool:
    """
    Concatenate MP4 files in order using ffmpeg concat demuxer (stream copy, no re-encode).
    Returns True on success, False on failure.
    """
    if not input_paths:
        print("No input files given.", file=sys.stderr)
        return False

    for p in input_paths:
        if not p.exists():
            print(f"Input file not found: {p}", file=sys.stderr)
            return False

    # Concat demuxer expects paths in a list file; paths must be absolute for -safe 0
    abs_paths = [str(p.resolve()) for p in input_paths]
    lines = [f"file '{p}'" for p in abs_paths]
    list_content = "\n".join(lines)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(list_content)
        list_path = f.name

    try:
        cmd = [
            ffmpeg_path,
            "-y",  # overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return False
        return True
    finally:
        Path(list_path).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Join multiple MP4 files into one video (no re-encode)."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Input MP4 files in desired order (e.g. part1.mp4 part2.mp4 part3.mp4)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("joined_output.mp4"),
        help="Output file path (default: joined_output.mp4)",
    )
    args = parser.parse_args()

    find_ffmpeg()

    if join_mp4(args.inputs, args.output):
        print(f"Done. Output: {args.output.resolve()}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
