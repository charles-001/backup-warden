import os
import subprocess
import unittest
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

SAMPLE_BACKUP_SET = set(
    [
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
)


class BackupWardenTestCase(unittest.TestCase):
    def setUp(self):
        self.root = TemporaryDirectory(prefix="rotate-backups-", suffix="-test-suite")
        self.config_file = Path(self.root.name) / "backup_warden.ini"

    def tearDown(self):
        self.root.cleanup()

    def create_sample_backup_set(self, backups):
        """Create a sample backup set to be rotated."""
        for name in backups:
            backup_dir = Path(self.root.name) / name
            backup_dir.mkdir()

    def test_backup_warden_parameters(self):
        expected_to_be_preserved = set(
            [
                "2013-10-10@20:07",  # monthly (1), yearly (1)
                "2013-11-01@20:06",  # monthly (2)
                "2013-12-01@20:07",  # monthly (3)
                "2014-01-01@20:07",  # monthly (4), yearly (2)
                "2014-02-01@20:05",  # monthly (5)
                "2014-03-01@20:04",  # monthly (6)
                "2014-04-01@20:03",  # monthly (7)
                "2014-05-01@20:06",  # monthly (8)
                "2014-06-01@20:01",  # monthly (9)
                "2014-06-09@20:01",  # weekly (1)
                "2014-06-16@20:02",  # weekly (2)
                "2014-06-23@20:04",  # weekly (3)
                "2014-06-26@20:04",  # daily (1)
                "2014-06-27@20:02",  # daily (2)
                "2014-06-28@20:02",  # daily (3)
                "2014-06-29@20:01",  # daily (4)
                "2014-06-30@20:03",  # daily (5), weekly (4)
                "2014-07-01@20:02",  # daily (6), monthly (10)
                "2014-07-02@20:03",  # hourly (1), daily (7)
                "some-random-directory",  # no recognizable time stamp, should definitely be preserved
            ]
        )

        # Create a sample backup set
        self.create_sample_backup_set(SAMPLE_BACKUP_SET)

        # Get the list of backups before run to compare after
        original_backups = set(os.listdir(self.root.name))

        command = [
            "poetry",
            "run",
            "backup-warden",
            "--source=local",
            f"--path={self.root.name}",
            "--hourly=24",
            "--daily=7",
            "--weekly=4",
            "--monthly=12",
            "--yearly=always",
            "--delete",
        ]
        subprocess.run(command, check=True, cwd=Path(__file__).parent)

        # Get the list of backups that were preserved
        backups_that_were_preserved = set(os.listdir(self.root.name))
        # Identify the backups that were preserved
        preserved_backups = original_backups.intersection(backups_that_were_preserved)

        # Assert that the preserved backups match the expected ones
        self.assertEqual(preserved_backups, expected_to_be_preserved)

    def test_backup_warden(self):
        expected_to_be_preserved = set(
            [
                "2013-10-10@20:07",  # monthly (1), yearly (1)
                "2013-11-01@20:06",  # monthly (2)
                "2013-12-01@20:07",  # monthly (3)
                "2014-01-01@20:07",  # monthly (4), yearly (2)
                "2014-02-01@20:05",  # monthly (5)
                "2014-03-01@20:04",  # monthly (6)
                "2014-04-01@20:03",  # monthly (7)
                "2014-05-01@20:06",  # monthly (8)
                "2014-06-01@20:01",  # monthly (9)
                "2014-06-09@20:01",  # weekly (1)
                "2014-06-16@20:02",  # weekly (2)
                "2014-06-23@20:04",  # weekly (3)
                "2014-06-26@20:04",  # daily (1)
                "2014-06-27@20:02",  # daily (2)
                "2014-06-28@20:02",  # daily (3)
                "2014-06-29@20:01",  # daily (4)
                "2014-06-30@20:03",  # daily (5), weekly (4)
                "2014-07-01@20:02",  # daily (6), monthly (10)
                "2014-07-02@20:03",  # hourly (1), daily (7)
                "some-random-directory",  # no recognizable time stamp, should definitely be preserved
                "backup_warden.ini",  # no recognizable time stamp, should definitely be preserved
            ]
        )

        # Create the configuration parser and set the main section
        parser = ConfigParser()
        parser["main"] = {"path": self.root.name, "source": "local"}
        parser[self.root.name] = {"hourly": "24", "daily": "7", "weekly": "4", "monthly": "12", "yearly": "always"}

        # Write the configuration to the file
        with open(self.config_file, "w") as handle:
            parser.write(handle)

        # Create a sample backup set
        self.create_sample_backup_set(SAMPLE_BACKUP_SET)

        # Get the list of backups before run to compare after
        original_backups = set(os.listdir(self.root.name))

        command = ["poetry", "run", "backup-warden", "--delete", f"--config={self.config_file}"]
        subprocess.run(command, check=True, cwd=Path(__file__).parent)

        # Get the list of backups that were preserved
        backups_that_were_preserved = set(os.listdir(self.root.name))
        # Identify the backups that were preserved
        preserved_backups = original_backups.intersection(backups_that_were_preserved)

        # Assert that the preserved backups match the expected ones
        self.assertEqual(preserved_backups, expected_to_be_preserved)

    def test_include_list(self):
        # These are the backups expected to be preserved within the year 2014
        # (other years are excluded and so should all be preserved, see below).
        # After each backup I've noted which rotation scheme it falls in.
        expected_to_be_preserved = set(
            [
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
                "some-random-directory",  # no recognizable time stamp, should definitely be preserved
                "backup_warden.ini",  # no recognizable time stamp, should definitely be preserved
            ]
        )

        for name in SAMPLE_BACKUP_SET:
            if not name.startswith("2014-"):
                expected_to_be_preserved.add(name)

        # Create the configuration parser and set the main section
        parser = ConfigParser()
        parser["main"] = {"path": self.root.name, "source": "local"}
        parser[self.root.name] = {
            "hourly": "24",
            "daily": "7",
            "weekly": "4",
            "monthly": "12",
            "yearly": "always",
            "include_list": "*2014*",
        }

        # Write the configuration to the file
        with open(self.config_file, "w") as handle:
            parser.write(handle)

        # Create a sample backup set
        self.create_sample_backup_set(SAMPLE_BACKUP_SET)

        # Get the list of backups before run to compare after
        original_backups = set(os.listdir(self.root.name))

        command = ["poetry", "run", "backup-warden", "--delete", f"--config={self.config_file}"]
        subprocess.run(command, check=True, cwd=Path(__file__).parent)

        # Get the list of backups that were preserved
        backups_that_were_preserved = set(os.listdir(self.root.name))
        # Identify the backups that were preserved
        preserved_backups = original_backups.intersection(backups_that_were_preserved)

        # Assert that the preserved backups match the expected ones
        self.assertEqual(preserved_backups, expected_to_be_preserved)

    def test_exclude_list(self):
        # These are the backups expected to be preserved. After each backup
        # I've noted which rotation scheme it falls in and the number of
        # preserved backups within that rotation scheme (counting up as we
        # progress through the backups sorted by date).
        expected_to_be_preserved = set(
            [
                "2013-10-10@20:07",  # monthly (1), yearly (1)
                "2013-11-01@20:06",  # monthly (2)
                "2013-12-01@20:07",  # monthly (3)
                "2014-01-01@20:07",  # monthly (4), yearly (2)
                "2014-02-01@20:05",  # monthly (5)
                "2014-03-01@20:04",  # monthly (6)
                "2014-04-01@20:03",  # monthly (7)
                "2014-05-01@20:06",  # monthly (8)
                "2014-05-19@20:02",  # weekly (1)
                "2014-05-26@20:05",  # weekly (2)
                "2014-06-01@20:01",  # monthly (9)
                "2014-06-09@20:01",  # weekly (3)
                "2014-06-16@20:02",  # weekly (4)
                "2014-06-23@20:04",  # weekly (5)
                "2014-06-26@20:04",  # daily (1)
                "2014-06-27@20:02",  # daily (2)
                "2014-06-28@20:02",  # daily (3)
                "2014-06-29@20:01",  # daily (4)
                "2014-06-30@20:03",  # daily (5), weekly (6)
                "2014-07-01@20:02",  # daily (6), monthly (10)
                "2014-07-02@20:03",  # hourly (1), daily (7)
                "some-random-directory",  # no recognizable time stamp, should definitely be preserved
                "backup_warden.ini",  # no recognizable time stamp, should definitely be preserved
            ]
        )

        for name in SAMPLE_BACKUP_SET:
            if name.startswith("2014-05-"):
                expected_to_be_preserved.add(name)

        # Create the configuration parser and set the main section
        parser = ConfigParser()
        parser["main"] = {"path": self.root.name, "source": "local"}
        parser[self.root.name] = {
            "hourly": "24",
            "daily": "7",
            "weekly": "4",
            "monthly": "12",
            "yearly": "always",
            "exclude_list": "*2014-05-*",
        }

        # Write the configuration to the file
        with open(self.config_file, "w") as handle:
            parser.write(handle)

        # Create a sample backup set
        self.create_sample_backup_set(SAMPLE_BACKUP_SET)

        # Get the list of backups before run to compare after
        original_backups = set(os.listdir(self.root.name))

        command = ["poetry", "run", "backup-warden", "--delete", f"--config={self.config_file}"]
        subprocess.run(command, check=True, cwd=Path(__file__).parent)

        # Get the list of backups that were preserved
        backups_that_were_preserved = set(os.listdir(self.root.name))
        # Identify the backups that were preserved
        preserved_backups = original_backups.intersection(backups_that_were_preserved)

        # Assert that the preserved backups match the expected ones
        self.assertEqual(preserved_backups, expected_to_be_preserved)

    def test_unix_timestamp(self):
        total_backups = set(
            [
                "test-1612396800061.tar.gz",
                "test-1641238061.tar.gz",
                "test-1686083461.tar.gz",
                "test-1807311501019237.tar.gz",
            ]
        )
        expected_to_be_preserved = set(
            [
                "test-1807311501019237.tar.gz",
                "backup_warden.ini",
            ]
        )

        # Create the configuration parser and set the main section
        parser = ConfigParser()
        parser["main"] = {"path": self.root.name, "source": "local"}
        parser[self.root.name] = {
            "hourly": "0",
            "daily": "0",
            "weekly": "0",
            "monthly": "0",
            "yearly": "0",
            "timestamp_pattern": r"(?P<unixtime>\d+)",
        }

        # Write the configuration to the file
        with open(self.config_file, "w") as handle:
            parser.write(handle)

        # Create a sample backup set
        self.create_sample_backup_set(total_backups)

        # Get the list of backups before run to compare after
        original_backups = set(os.listdir(self.root.name))

        command = ["poetry", "run", "backup-warden", "--delete", f"--config={self.config_file}"]
        subprocess.run(command, check=True, cwd=Path(__file__).parent)

        # Get the list of backups that were preserved
        backups_that_were_preserved = set(os.listdir(self.root.name))
        # Identify the backups that were preserved
        preserved_backups = original_backups.intersection(backups_that_were_preserved)

        # Assert that the preserved backups match the expected ones
        self.assertEqual(preserved_backups, expected_to_be_preserved)

    def apply_mtime_and_rename(self, root, subdir):
        """Extract mtime from filename, update file stat, rename and return a map of old to new name"""
        os.mkdir(subdir)
        file_map = {}
        for name in os.listdir(root):
            file = os.path.join(root, name)
            parts = name.split("@")
            if len(parts) != 2:
                continue  # Skip files that don't have the expected format
            date_str = parts[0]
            date = datetime.strptime(date_str, "%Y-%m-%d")
            timestamp = int(date.timestamp())
            new_name = f"{timestamp}s"
            new_file = os.path.join(subdir, new_name)
            os.utime(file, times=(timestamp, timestamp))
            os.rename(file, new_file)
            file_map[name] = new_name
        return file_map

    def test_filestat(self):
        expected_to_be_preserved = set(
            [
                "2013-10-10@20:07",  # monthly (1), yearly (1)
                "2013-11-01@20:06",  # monthly (2)
                "2013-12-01@20:07",  # monthly (3)
                "2014-01-01@20:07",  # monthly (4), yearly (2)
                "2014-02-01@20:05",  # monthly (5)
                "2014-03-01@20:04",  # monthly (6)
                "2014-04-01@20:03",  # monthly (7)
                "2014-05-01@20:06",  # monthly (8)
                "2014-06-01@20:01",  # monthly (9)
                "2014-06-09@20:01",  # weekly (1)
                "2014-06-16@20:02",  # weekly (2)
                "2014-06-23@20:04",  # weekly (3)
                "2014-06-26@20:04",  # daily (1)
                "2014-06-27@20:02",  # daily (2)
                "2014-06-28@20:02",  # daily (3)
                "2014-06-29@20:01",  # daily (4)
                "2014-06-30@20:03",  # daily (5), weekly (4)
                "2014-07-01@20:02",  # daily (6), monthly (10)
                "2014-07-02@20:03",  # hourly (1), daily (7),
            ]
        )

        subdir = os.path.join(self.root.name, "mtime")
        # Create the configuration parser and set the main section
        parser = ConfigParser()
        parser["main"] = {"path": self.root.name, "source": "local"}
        parser[subdir] = {
            "hourly": "24",
            "daily": "7",
            "weekly": "4",
            "monthly": "12",
            "yearly": "always",
            "filestat": True,
            "timestamp_pattern": "\\d+",
        }

        # Write the configuration to the file
        with open(self.config_file, "w") as handle:
            parser.write(handle)

        # Create a sample backup set
        self.create_sample_backup_set(SAMPLE_BACKUP_SET)
        map = self.apply_mtime_and_rename(self.root.name, subdir)

        command = ["poetry", "run", "backup-warden", "--delete", f"--config={self.config_file}"]
        subprocess.run(command, check=True, cwd=Path(__file__).parent)

        # Get the list of backups that were preserved
        backups_that_were_preserved = set(os.listdir(subdir))

        # Assert that the preserved backups match the expected ones
        self.assertEqual(backups_that_were_preserved, set([map[e] for e in expected_to_be_preserved]))

    def test_strict_rotation(self):
        """Test strict rotation."""
        backup_dir1 = Path(self.root.name) / "galera_backup_db4.sl.example.lab_2016-03-17_10-00"
        backup_dir2 = Path(self.root.name) / "galera_backup_db4.sl.example.lab_2016-03-17_12-00"
        backup_dir3 = Path(self.root.name) / "galera_backup_db4.sl.example.lab_2016-03-17_16-00"
        backup_dir1.mkdir()
        backup_dir2.mkdir()
        backup_dir3.mkdir()
        command = [
            "poetry",
            "run",
            "backup-warden",
            f"--path={self.root.name}",
            "--hourly=3",
            "--daily=1",
            "--delete",
        ]
        subprocess.run(command, check=True, cwd=Path(__file__).parent)
        self.assertTrue(backup_dir1.exists())
        self.assertFalse(backup_dir2.exists())
        self.assertTrue(backup_dir3.exists())

    def test_relaxed_rotation(self):
        """Test relaxed rotation."""
        backup_dir1 = Path(self.root.name) / "galera_backup_db4.sl.example.lab_2016-03-17_10-00"
        backup_dir2 = Path(self.root.name) / "galera_backup_db4.sl.example.lab_2016-03-17_12-00"
        backup_dir3 = Path(self.root.name) / "galera_backup_db4.sl.example.lab_2016-03-17_16-00"
        backup_dir1.mkdir()
        backup_dir2.mkdir()
        backup_dir3.mkdir()
        command = [
            "poetry",
            "run",
            "backup-warden",
            f"--path={self.root.name}",
            "--hourly=3",
            "--daily=1",
            "--relaxed",
            "--delete",
        ]
        subprocess.run(command, check=True, cwd=Path(__file__).parent)
        self.assertTrue(backup_dir1.exists())
        self.assertTrue(backup_dir2.exists())
        self.assertTrue(backup_dir3.exists())

    def test_prefer_recent(self):
        """Test the alternative preference for the newest backup in each time slot."""
        backup_dir1 = Path(self.root.name) / "backup-2016-01-10_21-15-00"
        backup_dir2 = Path(self.root.name) / "backup-2016-01-10_21-30-00"
        backup_dir3 = Path(self.root.name) / "backup-2016-01-10_21-45-00"
        backup_dir1.mkdir()
        backup_dir2.mkdir()
        backup_dir3.mkdir()
        command = [
            "poetry",
            "run",
            "backup-warden",
            f"--path={self.root.name}",
            "--hourly=1",
            "--prefer-recent",
            "--delete",
        ]
        subprocess.run(command, check=True, cwd=Path(__file__).parent)
        self.assertFalse(backup_dir1.exists())
        self.assertFalse(backup_dir2.exists())
        self.assertTrue(backup_dir3.exists())


if __name__ == "__main__":
    unittest.main()
