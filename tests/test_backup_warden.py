import os
import sys
from configparser import ConfigParser
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from backup_warden.app import main as app_main

SAMPLE_BACKUP_SET = [
    "2013-10-10@20:07",
    "2013-10-11@20:06",
    "2013-10-12@20:06",
    "2013-10-13@20:07",
    "2013-10-14@20:06",
    "2013-10-15@20:06",
    "2013-10-16@20:06",
    "2013-10-17@20:07",
    "2013-10-18@20:06",
    "2013-10-19@20:06",
    "2013-10-20@20:05",
    "2013-10-21@20:07",
    "2013-10-22@20:06",
    "2013-10-23@20:06",
    "2013-10-24@20:06",
    "2013-10-25@20:06",
    "2013-10-26@20:06",
    "2013-10-27@20:06",
    "2013-10-28@20:07",
    "2013-10-29@20:06",
    "2013-10-30@20:07",
    "2013-10-31@20:07",
    "2013-11-01@20:06",
    "2013-11-02@20:06",
    "2013-11-03@20:05",
    "2013-11-04@20:07",
    "2013-11-05@20:06",
    "2013-11-06@20:07",
    "2013-11-07@20:07",
    "2013-11-08@20:07",
    "2013-11-09@20:06",
    "2013-11-10@20:06",
    "2013-11-11@20:07",
    "2013-11-12@20:06",
    "2013-11-13@20:07",
    "2013-11-14@20:06",
    "2013-11-15@20:07",
    "2013-11-16@20:06",
    "2013-11-17@20:07",
    "2013-11-18@20:07",
    "2013-11-19@20:06",
    "2013-11-20@20:07",
    "2013-11-21@20:06",
    "2013-11-22@20:06",
    "2013-11-23@20:07",
    "2013-11-24@20:06",
    "2013-11-25@20:07",
    "2013-11-26@20:06",
    "2013-11-27@20:07",
    "2013-11-28@20:06",
    "2013-11-29@20:07",
    "2013-11-30@20:06",
    "2013-12-01@20:07",
    "2013-12-02@20:06",
    "2013-12-03@20:07",
    "2013-12-04@20:07",
    "2013-12-05@20:06",
    "2013-12-06@20:07",
    "2013-12-07@20:06",
    "2013-12-08@20:06",
    "2013-12-09@20:07",
    "2013-12-10@20:06",
    "2013-12-11@20:07",
    "2013-12-12@20:07",
    "2013-12-13@20:07",
    "2013-12-14@20:06",
    "2013-12-15@20:06",
    "2013-12-16@20:07",
    "2013-12-17@20:06",
    "2013-12-18@20:07",
    "2013-12-19@20:07",
    "2013-12-20@20:08",
    "2013-12-21@20:06",
    "2013-12-22@20:07",
    "2013-12-23@20:08",
    "2013-12-24@20:07",
    "2013-12-25@20:07",
    "2013-12-26@20:06",
    "2013-12-27@20:07",
    "2013-12-28@20:06",
    "2013-12-29@20:07",
    "2013-12-30@20:07",
    "2013-12-31@20:06",
    "2014-01-01@20:07",
    "2014-01-02@20:07",
    "2014-01-03@20:08",
    "2014-01-04@20:06",
    "2014-01-05@20:07",
    "2014-01-06@20:07",
    "2014-01-07@20:06",
    "2014-01-08@20:09",
    "2014-01-09@20:07",
    "2014-01-10@20:07",
    "2014-01-11@20:06",
    "2014-01-12@20:07",
    "2014-01-13@20:07",
    "2014-01-14@20:07",
    "2014-01-15@20:06",
    "2014-01-16@20:06",
    "2014-01-17@20:04",
    "2014-01-18@20:02",
    "2014-01-19@20:02",
    "2014-01-20@20:04",
    "2014-01-21@20:04",
    "2014-01-22@20:04",
    "2014-01-23@20:05",
    "2014-01-24@20:08",
    "2014-01-25@20:03",
    "2014-01-26@20:02",
    "2014-01-27@20:08",
    "2014-01-28@20:07",
    "2014-01-29@20:07",
    "2014-01-30@20:08",
    "2014-01-31@20:04",
    "2014-02-01@20:05",
    "2014-02-02@20:03",
    "2014-02-03@20:05",
    "2014-02-04@20:06",
    "2014-02-05@20:07",
    "2014-02-06@20:06",
    "2014-02-07@20:05",
    "2014-02-08@20:06",
    "2014-02-09@20:04",
    "2014-02-10@20:07",
    "2014-02-11@20:07",
    "2014-02-12@20:07",
    "2014-02-13@20:06",
    "2014-02-14@20:06",
    "2014-02-15@20:05",
    "2014-02-16@20:04",
    "2014-02-17@20:06",
    "2014-02-18@20:04",
    "2014-02-19@20:08",
    "2014-02-20@20:06",
    "2014-02-21@20:07",
    "2014-02-22@20:05",
    "2014-02-23@20:06",
    "2014-02-24@20:05",
    "2014-02-25@20:06",
    "2014-02-26@20:04",
    "2014-02-27@20:05",
    "2014-02-28@20:03",
    "2014-03-01@20:04",
    "2014-03-02@20:01",
    "2014-03-03@20:05",
    "2014-03-04@20:06",
    "2014-03-05@20:05",
    "2014-03-06@20:24",
    "2014-03-07@20:03",
    "2014-03-08@20:04",
    "2014-03-09@20:01",
    "2014-03-10@20:05",
    "2014-03-11@20:05",
    "2014-03-12@20:05",
    "2014-03-13@20:05",
    "2014-03-14@20:04",
    "2014-03-15@20:04",
    "2014-03-16@20:02",
    "2014-03-17@20:04",
    "2014-03-18@20:06",
    "2014-03-19@20:06",
    "2014-03-20@20:06",
    "2014-03-21@20:04",
    "2014-03-22@20:03",
    "2014-03-23@20:01",
    "2014-03-24@20:03",
    "2014-03-25@20:05",
    "2014-03-26@20:03",
    "2014-03-27@20:04",
    "2014-03-28@20:03",
    "2014-03-29@20:03",
    "2014-03-30@20:01",
    "2014-03-31@20:04",
    "2014-04-01@20:03",
    "2014-04-02@20:05",
    "2014-04-03@20:03",
    "2014-04-04@20:04",
    "2014-04-05@20:02",
    "2014-04-06@20:02",
    "2014-04-07@20:02",
    "2014-04-08@20:04",
    "2014-04-09@20:04",
    "2014-04-10@20:04",
    "2014-04-11@20:04",
    "2014-04-12@20:03",
    "2014-04-13@20:01",
    "2014-04-14@20:05",
    "2014-04-15@20:05",
    "2014-04-16@20:06",
    "2014-04-17@20:05",
    "2014-04-18@20:06",
    "2014-04-19@20:02",
    "2014-04-20@20:01",
    "2014-04-21@20:01",
    "2014-04-22@20:06",
    "2014-04-23@20:06",
    "2014-04-24@20:05",
    "2014-04-25@20:04",
    "2014-04-26@20:02",
    "2014-04-27@20:02",
    "2014-04-28@20:05",
    "2014-04-29@20:05",
    "2014-04-30@20:05",
    "2014-05-01@20:06",
    "2014-05-02@20:05",
    "2014-05-03@20:03",
    "2014-05-04@20:01",
    "2014-05-05@20:06",
    "2014-05-06@20:06",
    "2014-05-07@20:05",
    "2014-05-08@20:03",
    "2014-05-09@20:01",
    "2014-05-10@20:01",
    "2014-05-11@20:01",
    "2014-05-12@20:05",
    "2014-05-13@20:06",
    "2014-05-14@20:04",
    "2014-05-15@20:06",
    "2014-05-16@20:05",
    "2014-05-17@20:02",
    "2014-05-18@20:01",
    "2014-05-19@20:02",
    "2014-05-20@20:04",
    "2014-05-21@20:03",
    "2014-05-22@20:02",
    "2014-05-23@20:02",
    "2014-05-24@20:01",
    "2014-05-25@20:01",
    "2014-05-26@20:05",
    "2014-05-27@20:03",
    "2014-05-28@20:03",
    "2014-05-29@20:01",
    "2014-05-30@20:02",
    "2014-05-31@20:02",
    "2014-06-01@20:01",
    "2014-06-02@20:05",
    "2014-06-03@20:02",
    "2014-06-04@20:03",
    "2014-06-05@20:03",
    "2014-06-06@20:02",
    "2014-06-07@20:01",
    "2014-06-08@20:01",
    "2014-06-09@20:01",
    "2014-06-10@20:02",
    "2014-06-11@20:02",
    "2014-06-12@20:03",
    "2014-06-13@20:05",
    "2014-06-14@20:01",
    "2014-06-15@20:01",
    "2014-06-16@20:02",
    "2014-06-17@20:01",
    "2014-06-18@20:01",
    "2014-06-19@20:04",
    "2014-06-20@20:02",
    "2014-06-21@20:02",
    "2014-06-22@20:01",
    "2014-06-23@20:04",
    "2014-06-24@20:06",
    "2014-06-25@20:03",
    "2014-06-26@20:04",
    "2014-06-27@20:02",
    "2014-06-28@20:02",
    "2014-06-29@20:01",
    "2014-06-30@20:03",
    "2014-07-01@20:02",
    "2014-07-02@20:03",
    "some-random-directory",
]


@pytest.fixture
def config_file(tmp_path):
    """Create a config file path using pytest's native fixture."""
    return tmp_path / "backup_warden.ini"


@pytest.fixture
def run_cli(capsys):
    """
    Fixture that runs the application in-process instead of subprocess.
    This saves seconds of overhead per test by avoiding interpreter startup.
    """

    def _run(args):
        # Simulate command line arguments
        argv = ["backup-warden"] + args
        with patch.object(sys, "argv", argv):
            try:
                app_main()
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code if isinstance(e.code, int) else 1
            except Exception:
                exit_code = 1

        # Capture stdout/stderr
        captured = capsys.readouterr()

        # Echo output for visibility (optional - uncomment to see output)
        if captured.out:
            print(f"\n{'=' * 80}\nSTDOUT:\n{captured.out}{'=' * 80}")
        if captured.err:
            print(f"\n{'=' * 80}\nSTDERR:\n{captured.err}{'=' * 80}")

        # Mimic subprocess.CompletedProcess interface for compatibility
        class Result:
            def __init__(self, rc, out, err):
                self.returncode = rc
                self.stdout = out
                self.stderr = err

        return Result(exit_code, captured.out, captured.err)

    return _run


def create_backup_dirs(root_dir, backup_names):
    """Helper to create directories quickly."""
    for name in backup_names:
        (root_dir / name).mkdir(parents=True, exist_ok=True)


class TestBasicRotation:
    """Test basic backup rotation functionality."""

    def test_backup_warden_full_rotation(self, tmp_path, run_cli):
        """Test backup rotation using command-line parameters with full dataset."""
        expected_preserved = {
            "2013-10-10@20:07",  # monthly, yearly
            "2013-11-01@20:06",  # monthly
            "2013-12-01@20:07",  # monthly
            "2014-01-01@20:07",  # monthly, yearly
            "2014-02-01@20:05",  # monthly
            "2014-03-01@20:04",  # monthly
            "2014-04-01@20:03",  # monthly
            "2014-05-01@20:06",  # monthly
            "2014-06-01@20:01",  # monthly
            "2014-06-09@20:01",  # weekly
            "2014-06-16@20:02",  # weekly
            "2014-06-23@20:04",  # weekly
            "2014-06-26@20:04",  # daily
            "2014-06-27@20:02",  # daily
            "2014-06-28@20:02",  # daily
            "2014-06-29@20:01",  # daily
            "2014-06-30@20:03",  # daily, weekly
            "2014-07-01@20:02",  # daily, monthly
            "2014-07-02@20:03",  # hourly, daily
            "some-random-directory",
        }

        create_backup_dirs(tmp_path, SAMPLE_BACKUP_SET)

        result = run_cli(
            [
                "--source=local",
                f"--path={tmp_path}",
                "--hourly=24",
                "--daily=7",
                "--weekly=4",
                "--monthly=12",
                "--yearly=always",
                "--delete",
            ]
        )

        assert result.returncode == 0
        preserved_backups = set(os.listdir(tmp_path))
        assert preserved_backups == expected_preserved

    def test_prefer_recent(self, tmp_path, run_cli):
        """Test the preference for newest backup in each time slot."""
        backups = ["backup-2016-01-10_21-15-00", "backup-2016-01-10_21-30-00", "backup-2016-01-10_21-45-00"]
        create_backup_dirs(tmp_path, backups)

        result = run_cli(
            [
                f"--path={tmp_path}",
                "--hourly=1",
                "--prefer-recent",
                "--delete",
            ]
        )

        assert result.returncode == 0
        # Should keep only the most recent
        assert not (tmp_path / backups[0]).exists()
        assert not (tmp_path / backups[1]).exists()
        assert (tmp_path / backups[2]).exists()

    @pytest.mark.parametrize(
        "mode,extra_args,expected_indices",
        [
            ("strict", [], [0, 2]),  # Strict: drops middle backup
            ("relaxed", ["--relaxed"], [0, 1, 2]),  # Relaxed: keeps all
        ],
    )
    def test_rotation_modes(self, tmp_path, run_cli, mode, extra_args, expected_indices):
        """Test strict vs relaxed rotation modes."""
        backup_names = [
            "galera_backup_db4.sl.example.lab_2016-03-17_10-00",
            "galera_backup_db4.sl.example.lab_2016-03-17_12-00",
            "galera_backup_db4.sl.example.lab_2016-03-17_16-00",
        ]
        create_backup_dirs(tmp_path, backup_names)

        args = [f"--path={tmp_path}", "--hourly=3", "--daily=1", "--delete"] + extra_args
        result = run_cli(args)

        assert result.returncode == 0
        for i, name in enumerate(backup_names):
            exists = (tmp_path / name).exists()
            assert exists == (i in expected_indices), f"{mode} mode: {name} existence mismatch"


class TestOutputFlags:
    """Test output control flags."""

    def test_silent_flag(self, tmp_path, run_cli):
        """Test that --silent suppresses INFO output and tables (Unix philosophy)."""
        backups = ["backup-2016-01-10_21-15-00", "backup-2016-01-10_21-30-00"]
        create_backup_dirs(tmp_path, backups)

        result = run_cli([f"--path={tmp_path}", "--hourly=1", "--silent"])

        assert result.returncode == 0
        # Should suppress INFO logs
        assert "[INFO]" not in result.stdout
        # Should suppress table output (Unix philosophy: silent unless error)
        assert "╭─" not in result.stdout  # Table border character
        assert "Backup" not in result.stdout  # Table header
        # Should still show ERROR messages
        assert "[ERROR]" in result.stdout

    def test_print_deleted_flag(self, tmp_path, run_cli):
        """Test that --print-deleted prints only files to be deleted."""
        backups = [
            "backup-2016-01-10_21-15-00",
            "backup-2016-01-10_21-30-00",
            "backup-2016-01-10_21-45-00",
        ]
        create_backup_dirs(tmp_path, backups)

        result = run_cli(
            [
                f"--path={tmp_path}",
                "--hourly=1",
                "--prefer-recent",
                "--print-deleted",
            ]
        )

        assert result.returncode == 0
        deleted_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]

        # Should print exactly 2 files
        assert len(deleted_files) == 2

        # Verify no INFO or table output
        assert "[INFO]" not in result.stdout
        assert "Backup" not in result.stdout

    def test_print_not_deleted_flag(self, tmp_path, run_cli):
        """Test that --print-not-deleted prints only files to be preserved."""
        backups = [
            "backup-2016-01-10_21-15-00",
            "backup-2016-01-10_21-30-00",
            "backup-2016-01-10_21-45-00",
        ]
        create_backup_dirs(tmp_path, backups)

        result = run_cli(
            [
                f"--path={tmp_path}",
                "--hourly=1",
                "--prefer-recent",
                "--print-not-deleted",
            ]
        )

        assert result.returncode == 0
        preserved_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]

        # Should print exactly 1 file (most recent)
        assert len(preserved_files) == 1
        preserved_basename = Path(preserved_files[0]).name
        assert preserved_basename == "backup-2016-01-10_21-45-00"

    def test_print_flags_mutual_exclusivity(self, tmp_path, run_cli):
        """Test that --print-deleted and --print-not-deleted are mutually exclusive."""
        create_backup_dirs(tmp_path, ["backup-2016-01-10_21-15-00"])

        result = run_cli(
            [
                f"--path={tmp_path}",
                "--hourly=1",
                "--print-deleted",
                "--print-not-deleted",
            ]
        )

        assert result.returncode != 0
        assert "not allowed with argument" in result.stderr

    def test_print_deleted_with_delete(self, tmp_path, run_cli):
        """Test that --print-deleted works with --delete and actually deletes files."""
        backups = [
            "backup-2016-01-10_21-15-00",
            "backup-2016-01-10_21-30-00",
            "backup-2016-01-10_21-45-00",
        ]
        create_backup_dirs(tmp_path, backups)

        result = run_cli(
            [
                f"--path={tmp_path}",
                "--hourly=1",
                "--prefer-recent",
                "--print-deleted",
                "--delete",
            ]
        )

        assert result.returncode == 0
        deleted_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        assert len(deleted_files) == 2

        # Verify files were actually deleted
        assert not (tmp_path / backups[0]).exists()
        assert not (tmp_path / backups[1]).exists()
        assert (tmp_path / backups[2]).exists()


class TestConfigFile:
    """Test configuration file functionality."""

    def test_config_processing(self, tmp_path, config_file, run_cli):
        """Test backup rotation using config file."""
        expected_preserved = {
            "2013-10-10@20:07",  # monthly, yearly
            "2013-11-01@20:06",  # monthly
            "2013-12-01@20:07",  # monthly
            "2014-01-01@20:07",  # monthly, yearly
            "2014-02-01@20:05",  # monthly
            "2014-03-01@20:04",  # monthly
            "2014-04-01@20:03",  # monthly
            "2014-05-01@20:06",  # monthly
            "2014-06-01@20:01",  # monthly
            "2014-06-09@20:01",  # weekly
            "2014-06-16@20:02",  # weekly
            "2014-06-23@20:04",  # weekly
            "2014-06-26@20:04",  # daily
            "2014-06-27@20:02",  # daily
            "2014-06-28@20:02",  # daily
            "2014-06-29@20:01",  # daily
            "2014-06-30@20:03",  # daily, weekly
            "2014-07-01@20:02",  # daily, monthly
            "2014-07-02@20:03",  # hourly, daily
            "some-random-directory",
            "backup_warden.ini",  # Config file itself is preserved
        }

        # Create config
        parser = ConfigParser()
        parser["main"] = {"path": str(tmp_path), "source": "local"}
        parser[str(tmp_path)] = {"hourly": "24", "daily": "7", "weekly": "4", "monthly": "12", "yearly": "always"}
        with open(config_file, "w") as f:
            parser.write(f)

        create_backup_dirs(tmp_path, SAMPLE_BACKUP_SET)

        result = run_cli(["--delete", f"--config={config_file}"])

        assert result.returncode == 0
        preserved_backups = set(os.listdir(tmp_path))
        assert preserved_backups == expected_preserved


class TestUnixTimestamp:
    """Test Unix timestamp pattern support."""

    def test_unix_timestamp(self, tmp_path, config_file, run_cli):
        """Test Unix timestamp pattern matching."""
        total_backups = [
            "test-1612396800061.tar.gz",  # 2021-02-03
            "test-1641238061.tar.gz",  # 2022-01-03
            "test-1686083461.tar.gz",  # 2023-06-06
            "test-1807311501019237.tar.gz",  # 2027-04-21 (microseconds) - newest
        ]

        # Create config
        parser = ConfigParser()
        parser["main"] = {"path": str(tmp_path), "source": "local"}
        parser[str(tmp_path)] = {
            "hourly": "0",
            "daily": "0",
            "weekly": "0",
            "monthly": "0",
            "yearly": "0",
            "timestamp_pattern": r"(?P<unixtime>\d+)",
        }
        with open(config_file, "w") as f:
            parser.write(f)

        create_backup_dirs(tmp_path, total_backups)

        result = run_cli(["--delete", f"--config={config_file}"])

        assert result.returncode == 0
        # With all retention set to 0, only newest backup should remain
        assert (tmp_path / "test-1807311501019237.tar.gz").exists()
        assert not (tmp_path / "test-1612396800061.tar.gz").exists()
        assert not (tmp_path / "test-1641238061.tar.gz").exists()
        assert not (tmp_path / "test-1686083461.tar.gz").exists()


class TestFilters:
    """Test include and exclude list functionality."""

    def test_include_list(self, tmp_path, config_file, run_cli):
        """Test include list filtering - only 2014 backups are rotated."""
        expected_preserved = {
            "2014-01-01@20:07",  # monthly, yearly
            "2014-02-01@20:05",  # monthly
            "2014-03-01@20:04",  # monthly
            "2014-04-01@20:03",  # monthly
            "2014-05-01@20:06",  # monthly
            "2014-06-01@20:01",  # monthly
            "2014-06-09@20:01",  # weekly
            "2014-06-16@20:02",  # weekly
            "2014-06-23@20:04",  # weekly
            "2014-06-26@20:04",  # daily
            "2014-06-27@20:02",  # daily
            "2014-06-28@20:02",  # daily
            "2014-06-29@20:01",  # daily
            "2014-06-30@20:03",  # daily, weekly
            "2014-07-01@20:02",  # daily, monthly
            "2014-07-02@20:03",  # hourly, daily
            "some-random-directory",
            "backup_warden.ini",
        }

        # Add all non-2014 backups (excluded from rotation, so preserved)
        for name in SAMPLE_BACKUP_SET:
            if not name.startswith("2014-"):
                expected_preserved.add(name)

        # Create config
        parser = ConfigParser()
        parser["main"] = {"path": str(tmp_path), "source": "local"}
        parser[str(tmp_path)] = {
            "hourly": "24",
            "daily": "7",
            "weekly": "4",
            "monthly": "12",
            "yearly": "always",
            "include_list": "*2014*",
        }
        with open(config_file, "w") as f:
            parser.write(f)

        create_backup_dirs(tmp_path, SAMPLE_BACKUP_SET)

        result = run_cli(["--delete", f"--config={config_file}"])

        assert result.returncode == 0
        preserved_backups = set(os.listdir(tmp_path))
        assert preserved_backups == expected_preserved

    def test_exclude_list(self, tmp_path, config_file, run_cli):
        """Test exclude list filtering - 2014-05-* backups are excluded from rotation."""
        expected_preserved = {
            "2013-10-10@20:07",  # monthly, yearly
            "2013-11-01@20:06",  # monthly
            "2013-12-01@20:07",  # monthly
            "2014-01-01@20:07",  # monthly, yearly
            "2014-02-01@20:05",  # monthly
            "2014-03-01@20:04",  # monthly
            "2014-04-01@20:03",  # monthly
            "2014-05-01@20:06",  # monthly
            "2014-06-01@20:01",  # monthly
            "2014-06-09@20:01",  # weekly
            "2014-06-16@20:02",  # weekly
            "2014-06-23@20:04",  # weekly
            "2014-06-26@20:04",  # daily
            "2014-06-27@20:02",  # daily
            "2014-06-28@20:02",  # daily
            "2014-06-29@20:01",  # daily
            "2014-06-30@20:03",  # daily, weekly
            "2014-07-01@20:02",  # daily, monthly
            "2014-07-02@20:03",  # hourly, daily
            "some-random-directory",
            "backup_warden.ini",
        }

        # Add all 2014-05-* backups (excluded from rotation, so preserved)
        for name in SAMPLE_BACKUP_SET:
            if name.startswith("2014-05-"):
                expected_preserved.add(name)

        # Create config
        parser = ConfigParser()
        parser["main"] = {"path": str(tmp_path), "source": "local"}
        parser[str(tmp_path)] = {
            "hourly": "24",
            "daily": "7",
            "weekly": "4",
            "monthly": "12",
            "yearly": "always",
            "exclude_list": "*2014-05-*",
        }
        with open(config_file, "w") as f:
            parser.write(f)

        create_backup_dirs(tmp_path, SAMPLE_BACKUP_SET)

        result = run_cli(["--delete", f"--config={config_file}"])

        assert result.returncode == 0
        preserved_backups = set(os.listdir(tmp_path))
        assert preserved_backups == expected_preserved


class TestFilestat:
    """Test filestat (modification time) based rotation."""

    def test_filestat_mtime(self, tmp_path, config_file, run_cli):
        """Test using file modification time instead of filename timestamp."""
        # Expected backups based on rotation policy
        expected_to_be_preserved = {
            "2013-10-10@20:07",  # monthly, yearly
            "2013-11-01@20:06",  # monthly
            "2013-12-01@20:07",  # monthly
            "2014-01-01@20:07",  # monthly, yearly
            "2014-02-01@20:05",  # monthly
            "2014-03-01@20:04",  # monthly
            "2014-04-01@20:03",  # monthly
            "2014-05-01@20:06",  # monthly
            "2014-06-01@20:01",  # monthly
            "2014-06-09@20:01",  # weekly
            "2014-06-16@20:02",  # weekly
            "2014-06-23@20:04",  # weekly
            "2014-06-26@20:04",  # daily
            "2014-06-27@20:02",  # daily
            "2014-06-28@20:02",  # daily
            "2014-06-29@20:01",  # daily
            "2014-06-30@20:03",  # daily, weekly
            "2014-07-01@20:02",  # daily, monthly
            "2014-07-02@20:03",  # hourly, daily
        }

        subdir = tmp_path / "mtime"
        subdir.mkdir()

        # Create config
        parser = ConfigParser()
        parser["main"] = {"path": str(tmp_path), "source": "local"}
        parser[str(subdir)] = {
            "hourly": "24",
            "daily": "7",
            "weekly": "4",
            "monthly": "12",
            "yearly": "always",
            "filestat": "True",
            "utc": "True",
            "timestamp_pattern": r"\d+",
        }
        with open(config_file, "w") as f:
            parser.write(f)

        # Create mapping from backup name to timestamp filename
        file_map = {}
        for name in SAMPLE_BACKUP_SET:
            if name == "some-random-directory":
                continue

            # Extract date from name to use as mtime
            date_str = name.split("@")[0]
            ts = int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
            new_name = f"{ts}s"

            # Create file with timestamp in name
            p = subdir / new_name
            p.touch()
            # Set the modification time
            os.utime(p, (ts, ts))
            file_map[name] = new_name

        result = run_cli(["--delete", f"--config={config_file}"])

        assert result.returncode == 0

        # Verify preserved backups match expectations
        backups_that_were_preserved = set(os.listdir(subdir))
        expected_preserved_files = {file_map[e] for e in expected_to_be_preserved}
        assert backups_that_were_preserved == expected_preserved_files
