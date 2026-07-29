#!/usr/bin/env python3
"""Exhaustively check the projection of the exact sequential encoder."""

from __future__ import annotations

import itertools

from generate_tournament_cnf import CNF


def satisfiable_extension(
    cnf: CNF,
    fixed: dict[int, bool],
    primary: list[int],
) -> bool:
    auxiliary = [
        variable
        for variable in range(1, cnf.variable_count + 1)
        if variable not in primary
    ]
    for values in itertools.product((False, True), repeat=len(auxiliary)):
        assignment = fixed | dict(zip(auxiliary, values))
        if all(
            any(
                assignment[abs(literal)] == (literal > 0)
                for literal in clause
            )
            for clause in cnf.clauses
        ):
            return True
    return False


def main() -> None:
    cases = 0
    for count in range(1, 6):
        for bound in range(-1, count + 1):
            for gate_sign in (None, 1, -1):
                cnf = CNF(exact_sequential=True)
                inputs = [
                    cnf.variable(("input", index))
                    for index in range(count)
                ]
                gate_variable = (
                    cnf.variable(("gate",))
                    if gate_sign is not None
                    else None
                )
                gate = (
                    gate_sign * gate_variable
                    if gate_variable is not None
                    else None
                )
                cnf.at_most(inputs, bound, ("counter",), gate)
                primary = inputs + (
                    [gate_variable]
                    if gate_variable is not None
                    else []
                )
                for values in itertools.product(
                    (False, True), repeat=len(primary)
                ):
                    fixed = dict(zip(primary, values))
                    disabled = (
                        False
                        if gate is None
                        else fixed[abs(gate)] == (gate > 0)
                    )
                    expected = (
                        disabled
                        or sum(fixed[variable] for variable in inputs)
                        <= bound
                    )
                    actual = satisfiable_extension(cnf, fixed, primary)
                    if actual != expected:
                        raise AssertionError(
                            (
                                count,
                                bound,
                                gate_sign,
                                values,
                                actual,
                                expected,
                            )
                        )
                    cases += 1
    print(f"exact sequential projection: PASS ({cases} cases)")


if __name__ == "__main__":
    main()
