#!/usr/bin/env python3
"""Build a complete adaptive checked certificate tree for one parent CNF."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, allow_failure: bool = False) -> int:
    completed = subprocess.run(command, check=False)
    if completed.returncode and not allow_failure:
        raise RuntimeError(
            f"command failed with status {completed.returncode}: "
            + " ".join(command)
        )
    return completed.returncode


def read_cubes(path: Path) -> list[list[int]]:
    cubes = [
        [int(token) for token in line.split()[1:-1]]
        for line in path.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]
    if not cubes:
        raise ValueError(f"{path} contains no cubes")
    return cubes


def clean_failed_outputs(
    certificate_dir: Path,
    failed_indices: list[int],
) -> None:
    for index in failed_indices:
        stem = certificate_dir / f"cube_{index:05d}"
        for suffix in (
            ".cnf",
            ".drat",
            ".core.rup",
            ".core.rup.xz",
            ".core.drat",
            ".core.drat.xz",
            ".solver.log",
            ".core-extraction.log",
            ".core-verification.log",
        ):
            path = Path(f"{stem}{suffix}")
            if path.exists():
                path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parent_cnf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("cube_generator", type=Path)
    parser.add_argument("solver", type=Path)
    parser.add_argument("drat_trim", type=Path)
    parser.add_argument(
        "--solver-kind",
        choices=("gimsatul", "cadical", "kissat"),
        default="gimsatul",
        help="select the command-line interface used by the leaf solver",
    )
    parser.add_argument(
        "--proof-mode",
        choices=("rup", "drat"),
        default="rup",
        help="restrict leaf proofs to RUP or allow full DRAT",
    )
    parser.add_argument("--initial-depth", type=int, default=8)
    parser.add_argument("--additional-depth", type=int, default=6)
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--maximum-seconds", type=int, default=600)
    parser.add_argument(
        "--checker-seconds",
        type=int,
        default=0,
        help=(
            "timeout for each drat-trim pass; zero follows the current "
            "solver timeout"
        ),
    )
    parser.add_argument(
        "--constant-rounds",
        type=int,
        default=1,
        help=(
            "keep the initial timeout unchanged for this many rounds "
            "before exponential growth begins"
        ),
    )
    parser.add_argument(
        "--retries-before-split",
        type=int,
        default=0,
        help=(
            "after each split, retry unresolved cubes this many times with "
            "doubling timeouts before splitting them again"
        ),
    )
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--xz-level", type=int, default=1)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="continue a verified round-limit partial tree in output",
    )
    parser.add_argument(
        "--fixed-variable-upper-bound",
        type=int,
        default=0,
        help=(
            "on split rounds, exhaustively assign unused variables up to "
            "this bound instead of using CaDiCaL lookahead"
        ),
    )
    args = parser.parse_args()

    if args.output.exists() and not args.resume:
        raise ValueError(f"refusing existing output: {args.output}")
    if (
        args.initial_depth < 1
        or args.additional_depth < 1
        or args.seconds < 1
        or args.maximum_seconds < args.seconds
        or args.checker_seconds < 0
        or args.constant_rounds < 1
        or args.retries_before_split < 0
        or args.fixed_variable_upper_bound < 0
        or args.jobs < 1
        or args.rounds < 1
        or not 0 <= args.xz_level <= 9
    ):
        raise ValueError("invalid adaptive-certificate parameters")
    for path in (
        args.parent_cnf,
        args.cube_generator,
        args.solver,
        args.drat_trim,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    script_dir = Path(__file__).resolve().parent
    refine_script = script_dir / "refine_cubes.py"
    primary_refine_script = script_dir / "refine_cubes_primary.py"
    coverage_script = script_dir / "verify_cube_cover.py"
    certify_script = script_dir / "certify_cubes.py"
    select_script = script_dir / "select_failed_certificate_cubes.py"

    if args.resume:
        partial_path = args.output / "adaptive_manifest.json"
        if not partial_path.is_file():
            raise FileNotFoundError(
                f"missing partial adaptive manifest: {partial_path}"
            )
        partial = json.loads(partial_path.read_text(encoding="utf-8"))
        rounds = partial.get("rounds")
        if (
            partial.get("verified") is not False
            or partial.get("reason") != "round limit reached"
            or partial.get("parent_cnf_sha256") != sha256(args.parent_cnf)
            or not isinstance(rounds, list)
            or not rounds
        ):
            raise ValueError(f"cannot resume {partial_path}")
        for expected_round, record in enumerate(rounds, start=1):
            if (
                int(record["round"]) != expected_round
                or record.get("mode") not in {"split", "retry"}
            ):
                raise ValueError(
                    f"invalid prior round metadata in {partial_path}"
                )
        last_record = rounds[-1]
        if int(last_record["failed_count"]) < 1:
            raise ValueError(
                f"partial tree has no unresolved cubes: {partial_path}"
            )
        last_round = args.output / f"round_{len(rounds):02d}"
        parents = last_round / "failed.cubes"
        if (
            not parents.is_file()
            or len(read_cubes(parents))
            != int(last_record["failed_count"])
        ):
            raise ValueError(
                f"invalid unresolved frontier for {partial_path}"
            )
        total_refutations = sum(
            int(record["verified_count"]) for record in rounds
        )
        retries_since_split = 0
        for record in reversed(rounds):
            if record["mode"] != "retry":
                break
            retries_since_split += 1
        if retries_since_split > args.retries_before_split:
            raise ValueError(
                "prior retry state exceeds --retries-before-split"
            )
        start_round = len(rounds) + 1
        print(
            json.dumps(
                {
                    "resuming": True,
                    "next_round": start_round,
                    "unresolved_cubes": len(read_cubes(parents)),
                    "retained_refutations": total_refutations,
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
    else:
        args.output.mkdir(parents=True)
        root_parents = args.output / "root.cubes"
        root_parents.write_text("a 0\n", encoding="ascii", newline="\n")
        parents = root_parents
        rounds: list[dict[str, object]] = []
        total_refutations = 0
        retries_since_split = 0
        start_round = 1

    for round_number in range(start_round, args.rounds + 1):
        round_dir = args.output / f"round_{round_number:02d}"
        round_dir.mkdir()
        round_parents = round_dir / "parents.cubes"
        round_parents.write_bytes(parents.read_bytes())
        children = round_dir / "children.cubes"
        retry_mode = (
            round_number > 1
            and args.retries_before_split > 0
            and retries_since_split < args.retries_before_split
        )
        if retry_mode:
            mode = "retry"
            depth = 0
            retries_since_split += 1
            round_seconds = min(
                args.maximum_seconds,
                args.seconds * (2**retries_since_split),
            )
            children.write_bytes(round_parents.read_bytes())
        else:
            mode = "split"
            depth = (
                args.initial_depth
                if round_number == 1
                else args.additional_depth
            )
            retries_since_split = 0
            round_seconds = (
                args.seconds
                if args.retries_before_split > 0
                else min(
                    args.maximum_seconds,
                    args.seconds
                    * (
                        2
                        ** max(
                            0,
                            round_number - args.constant_rounds,
                        )
                    ),
                )
            )
            if args.fixed_variable_upper_bound:
                split_strategy = "fixed-primary"
                run(
                    [
                        sys.executable,
                        str(primary_refine_script),
                        str(args.parent_cnf),
                        str(round_parents),
                        str(children),
                        "--variable-upper-bound",
                        str(args.fixed_variable_upper_bound),
                        "--additional-depth",
                        str(depth),
                    ]
                )
            else:
                split_strategy = "cadical-lookahead"
                run(
                    [
                        sys.executable,
                        str(refine_script),
                        str(args.parent_cnf),
                        str(round_parents),
                        str(children),
                        str(args.cube_generator),
                        "--additional-depth",
                        str(depth),
                        "--jobs",
                        str(args.jobs),
                    ]
                )

        coverage = round_dir / "coverage.json"
        run(
            [
                sys.executable,
                str(coverage_script),
                str(round_parents),
                str(children),
                "--output",
                str(coverage),
            ]
        )

        certificate_dir = round_dir / "certificate"
        certificate_status = run(
            [
                sys.executable,
                str(certify_script),
                str(args.parent_cnf),
                str(children),
                str(certificate_dir),
                str(args.solver),
                str(args.drat_trim),
                "--solver-kind",
                args.solver_kind,
                "--proof-mode",
                args.proof_mode,
                "--jobs",
                str(args.jobs),
                "--solver-threads",
                "1",
                "--seconds",
                str(round_seconds),
                "--checker-seconds",
                str(args.checker_seconds),
                "--xz-level",
                str(args.xz_level),
                "--discard-logs",
                "--coverage",
                str(coverage),
            ],
            allow_failure=True,
        )

        manifest_path = certificate_dir / "certificate_manifest.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        child_count = len(read_cubes(children))
        records = manifest["records"]
        failures = manifest["failed_cubes"]
        verified_indices = {
            int(record["cube_index"]) for record in records
        }
        failed_indices = {
            int(failure["cube_index"]) for failure in failures
        }
        if (
            verified_indices & failed_indices
            or verified_indices | failed_indices
            != set(range(child_count))
            or any(
                record.get("proof_mode") != args.proof_mode
                or (
                    args.proof_mode == "rup"
                    and record.get("rup_only") is not True
                )
                for record in records
            )
        ):
            raise ValueError(
                f"round {round_number} has an incomplete manifest"
            )
        if bool(failures) == (certificate_status == 0):
            raise ValueError(
                f"round {round_number} status disagrees with failures"
            )

        ordered_failed = sorted(failed_indices)
        clean_failed_outputs(certificate_dir, ordered_failed)
        total_refutations += len(records)
        round_record = {
            "round": round_number,
            "mode": mode,
            "split_depth": depth,
            "split_strategy": (
                "none" if mode == "retry" else split_strategy
            ),
            "parents": round_parents.name,
            "parents_sha256": sha256(round_parents),
            "children": children.name,
            "children_sha256": sha256(children),
            "coverage": coverage.name,
            "coverage_sha256": sha256(coverage),
            "certificate_manifest": (
                f"certificate/{manifest_path.name}"
            ),
            "certificate_manifest_sha256": sha256(manifest_path),
            "parent_count": len(read_cubes(round_parents)),
            "child_count": child_count,
            "verified_count": len(records),
            "failed_count": len(ordered_failed),
            "failed_indices": ordered_failed,
            "seconds_per_command": round_seconds,
            "solver_kind": args.solver_kind,
            "proof_mode": args.proof_mode,
            "checker_seconds_per_command": (
                args.checker_seconds or round_seconds
            ),
        }
        rounds.append(round_record)

        if not ordered_failed:
            result = {
                "verified": True,
                "parent_cnf": args.parent_cnf.name,
                "parent_cnf_sha256": sha256(args.parent_cnf),
                "initial_depth": args.initial_depth,
                "additional_depth": args.additional_depth,
                "initial_seconds_per_command": args.seconds,
                "maximum_seconds_per_command": args.maximum_seconds,
                "constant_timeout_rounds": args.constant_rounds,
                "retries_before_split": args.retries_before_split,
                "fixed_variable_upper_bound": (
                    args.fixed_variable_upper_bound
                ),
                "jobs": args.jobs,
                "xz_level": args.xz_level,
                "solver_kind": args.solver_kind,
                "proof_mode": args.proof_mode,
                "proof_modes": sorted(
                    {
                        str(record.get("proof_mode", "rup"))
                        for record in rounds
                    }
                ),
                "checker_seconds_per_command": args.checker_seconds,
                "round_count": round_number,
                "terminal_refutations": total_refutations,
                "rounds": rounds,
            }
            output = args.output / "adaptive_manifest.json"
            output.write_text(
                json.dumps(result, indent=2) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(result, separators=(",", ":")))
            return

        next_parents = round_dir / "failed.cubes"
        run(
            [
                sys.executable,
                str(select_script),
                str(children),
                str(manifest_path),
                str(next_parents),
            ]
        )
        parents = next_parents

    partial = {
        "verified": False,
        "reason": "round limit reached",
        "parent_cnf": args.parent_cnf.name,
        "parent_cnf_sha256": sha256(args.parent_cnf),
        "initial_depth": args.initial_depth,
        "additional_depth": args.additional_depth,
        "initial_seconds_per_command": args.seconds,
        "maximum_seconds_per_command": args.maximum_seconds,
        "constant_timeout_rounds": args.constant_rounds,
        "retries_before_split": args.retries_before_split,
        "fixed_variable_upper_bound": args.fixed_variable_upper_bound,
        "jobs": args.jobs,
        "xz_level": args.xz_level,
        "solver_kind": args.solver_kind,
        "proof_mode": args.proof_mode,
        "proof_modes": sorted(
            {
                str(record.get("proof_mode", "rup"))
                for record in rounds
            }
        ),
        "checker_seconds_per_command": args.checker_seconds,
        "round_count": len(rounds),
        "terminal_refutations": total_refutations,
        "rounds": rounds,
    }
    (args.output / "adaptive_manifest.json").write_text(
        json.dumps(partial, indent=2) + "\n",
        encoding="utf-8",
    )
    raise SystemExit("adaptive certificate did not finish")


if __name__ == "__main__":
    main()
