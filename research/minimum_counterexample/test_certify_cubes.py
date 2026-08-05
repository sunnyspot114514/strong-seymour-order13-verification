#!/usr/bin/env python3
"""Regression tests for strict certificate-checker exit handling."""

from __future__ import annotations

import unittest

from certify_cubes import require_successful_check


class CertificateCheckerExitTests(unittest.TestCase):
    def test_zero_exit_with_verified_marker_is_accepted(self) -> None:
        require_successful_check(7, "core extraction", 0, "s VERIFIED\n")

    def test_timeout_with_verified_marker_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            r"cube 143: core extraction status 124",
        ):
            require_successful_check(
                143,
                "core extraction",
                124,
                "s VERIFIED\ncertificate command timed out after 600s\n",
            )

    def test_zero_exit_without_verified_marker_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            r"cube 5: core verification status 0",
        ):
            require_successful_check(5, "core verification", 0, "")


if __name__ == "__main__":
    unittest.main()
