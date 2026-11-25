#!/usr/bin/env python3
"""Unit tests for nightjob. Stdlib only, like the tool: no GPU, no systemd.

The suite covers what a failed night depends on and what needs no device: the
duration and size grammars, the state-directory contract, the CLI surface the
README documents, the report's exit-code wording, and the shell quoting that
builds the supervisor's command line.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import nightjob as nj


class DurationTest(unittest.TestCase):
    def test_single_units(self):
        self.assertEqual(nj.parse_duration("90s"), 90)
        self.assertEqual(nj.parse_duration("30m"), 1800)
        self.assertEqual(nj.parse_duration("8h"), 8 * 3600)
        self.assertEqual(nj.parse_duration("2d"), 2 * 86400)

    def test_compound_and_spacing(self):
        self.assertEqual(nj.parse_duration("8h30m"), 8 * 3600 + 30 * 60)
        self.assertEqual(nj.parse_duration("1h 30m"), 5400)
        self.assertEqual(nj.parse_duration("2D"), 2 * 86400)

    def test_rejects_garbage(self):
        for bad in ("", "abc", "8x", "h", "12", "8h junk"):
            with self.assertRaises(ValueError, msg=bad):
                nj.parse_duration(bad)


class HumanTest(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(nj.human_bytes(0), "0 MiB")
        self.assertEqual(nj.human_bytes(nj.MIB), "1 MiB")
        self.assertEqual(nj.human_bytes(nj.GIB), "1.0 GiB")
        self.assertEqual(nj.human_bytes(int(1.5 * nj.GIB)), "1.5 GiB")

    def test_duration(self):
        self.assertEqual(nj.human_duration(0), "0s")
        self.assertEqual(nj.human_duration(-5), "0s")
        self.assertEqual(nj.human_duration(42), "42s")
        self.assertEqual(nj.human_duration(90), "1m30s")
        self.assertEqual(nj.human_duration(3600), "1h00m")
        self.assertEqual(nj.human_duration(3661), "1h01m")


class SizeTest(unittest.TestCase):
    def test_units(self):
        self.assertEqual(nj.parse_size("0 B"), 0)
        self.assertEqual(nj.parse_size("512 MiB"), 512 * nj.MIB)
        self.assertEqual(nj.parse_size("12 GiB"), 12 * nj.GIB)

    def test_garbage_is_zero(self):
        self.assertEqual(nj.parse_size(""), 0)
        self.assertEqual(nj.parse_size("unknown"), 0)


class StateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_state = nj.STATE_DIR
        nj.STATE_DIR = Path(self.tmp.name)

    def tearDown(self):
        nj.STATE_DIR = self.old_state
        self.tmp.cleanup()

    def test_latest_run_is_empty_before_any_run(self):
        self.assertIsNone(nj.latest_run("main"))

    def test_a_run_lives_under_its_unit_and_is_the_latest(self):
        run = nj.new_run_dir("main")
        self.assertTrue(run.is_dir())
        self.assertEqual(run.parent, nj.STATE_DIR / "main")
        self.assertEqual(nj.latest_run("main"), run)
        self.assertIsNone(nj.latest_run("other"))

    def test_json_roundtrip_leaves_no_temporary_file(self):
        run = nj.new_run_dir("main")
        path = run / "final.json"
        nj.write_json(path, {"rc": 0, "unit": "main"})
        self.assertEqual(nj.read_json(path), {"rc": 0, "unit": "main"})
        self.assertEqual(sorted(p.name for p in run.iterdir()), ["final.json"])
        self.assertTrue(path.read_text().endswith("\n"))


class CliTest(unittest.TestCase):
    def setUp(self):
        self.parser = nj.build_parser()

    def test_run_keeps_the_command_after_the_separator(self):
        args = self.parser.parse_args(
            ["run", "--budget", "90m", "--", "python", "train.py"]
        )
        self.assertEqual(args.cmd, ["--", "python", "train.py"])
        self.assertEqual(nj.parse_duration(args.budget), 90 * 60)
        self.assertEqual(args.unit, "main")

    def test_preflight_defaults_match_the_documented_budget(self):
        args = self.parser.parse_args(["preflight"])
        self.assertEqual(nj.need_mib(args), 12 * 1024)
        self.assertEqual(nj.reserve_mib(args), 1024)
        self.assertFalse(args.json)

    def test_env_action_is_checked_by_the_parser(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["env", "frobnicate"])

    def test_a_subcommand_is_required(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args([])


class HelpersTest(unittest.TestCase):
    def test_unit_name(self):
        self.assertEqual(nj.unit_name("main"), "nightjob-main")

    def test_preflight_ready_reads_the_flag(self):
        self.assertTrue(nj.preflight_ready({"ready": True}))
        self.assertFalse(nj.preflight_ready({"ready": False}))

    def test_parse_env_accepts_values_with_equals(self):
        self.assertEqual(nj._parse_env(["A=1", "B=x=y"]), {"A": "1", "B": "x=y"})
        with self.assertRaises(SystemExit):
            nj._parse_env(["oops"])

    def test_shell_quote(self):
        self.assertEqual(nj._shell_quote("python3"), "python3")
        self.assertEqual(nj._shell_quote("a b"), "'a b'")
        self.assertEqual(nj._shell_quote("it's"), "'it'\\''s'")

    def test_describe_rc(self):
        self.assertEqual(nj._describe_rc(0), "0")
        self.assertEqual(nj._describe_rc(2), "2")
        self.assertEqual(nj._describe_rc(-15), "signal SIGTERM")
        self.assertEqual(nj._describe_rc(-999), "signal 999")
        self.assertEqual(nj._describe_rc(None), "unknown")


if __name__ == "__main__":
    unittest.main()
