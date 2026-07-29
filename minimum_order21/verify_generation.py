#!/usr/bin/env python3
"""Regenerate every order-20 branch and compare the published inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


CUBE_BRANCHES = {(8, 0), (8, 1), (9, 0), (9, 1), (9, 2), (9, 3)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("generator", type=Path)
    parser.add_argument("cube_generator", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    for source in (args.generator, args.cube_generator):
        if not source.is_file():
            raise FileNotFoundError(source)

    records: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(
        prefix="strong-seymour-generation-"
    ) as temporary:
        temporary_root = Path(temporary)
        for degree in range(1, 10):
            for cover_left in range(degree):
                stem = f"n20_d{degree}p{cover_left}"
                kind = (
                    "cubes"
                    if (degree, cover_left) in CUBE_BRANCHES
                    else "direct"
                )
                published = (
                    args.bundle / "certificates" / kind / stem
                )
                generated_cnf = temporary_root / f"{stem}.cnf"
                command = [
                    "python3",
                    str(args.generator),
                    "20",
                    str(degree),
                    str(generated_cnf),
                    "--encoding",
                    "conditional-cover",
                    "--root-cover-left",
                    str(cover_left),
                    "--symmetry",
                    "hierarchical-profile-ties",
                ]
                if kind == "cubes":
                    command.append("--exact-sequential")
                subprocess.run(
                    command,
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
                compared = []
                for suffix in (".cnf", ".json"):
                    generated = generated_cnf.with_suffix(suffix)
                    expected = published / f"{stem}{suffix}"
                    if not expected.is_file():
                        raise FileNotFoundError(expected)
                    generated_hash = sha256(generated)
                    if generated_hash != sha256(expected):
                        raise ValueError(
                            f"{stem}{suffix}: regenerated hash mismatch"
                        )
                    compared.append(
                        {
                            "file": expected.name,
                            "sha256": generated_hash,
                        }
                    )
                if kind == "cubes":
                    generated_cubes = temporary_root / f"{stem}.row.cubes"
                    subprocess.run(
                        [
                            "python3",
                            str(args.cube_generator),
                            str(generated_cnf.with_suffix(".json")),
                            str(generated_cubes),
                        ],
                        check=True,
                        stdout=subprocess.DEVNULL,
                    )
                    expected_cubes = published / generated_cubes.name
                    cubes_hash = sha256(generated_cubes)
                    if cubes_hash != sha256(expected_cubes):
                        raise ValueError(
                            f"{stem}.row.cubes: regenerated hash mismatch"
                        )
                    compared.append(
                        {
                            "file": expected_cubes.name,
                            "sha256": cubes_hash,
                        }
                    )
                records.append(
                    {
                        "branch": stem,
                        "certificate_kind": kind,
                        "cardinality_encoder": (
                            "exact_triangular_sequential"
                            if kind == "cubes"
                            else "triangular_sinz_sequential"
                        ),
                        "files": compared,
                    }
                )
                print(f"[{len(records)}/45] {stem}: identical", flush=True)

    result = {
        "verified": True,
        "order": 20,
        "branches_regenerated": len(records),
        "encoding": "conditional-cover",
        "symmetry": "hierarchical-profile-ties",
        "cardinality_encoders": {
            "direct_branches": "triangular_sinz_sequential",
            "row_partition_branches": "exact_triangular_sequential",
        },
        "records": records,
    }
    output = args.output or args.bundle / "GENERATION_VERIFICATION.json"
    output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"verified": True, "branches": len(records)}))


if __name__ == "__main__":
    main()
