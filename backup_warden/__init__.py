#!/usr/bin/python3

# Backup Warden

# Author: Charles Thompson
# Created on: July 1, 2023
# GitHub: https://github.com/charles-001/backup-warden

# Inspiration from https://github.com/xolox/python-rotate-backups

import os
import re
import shutil
from configparser import ConfigParser
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path
from pprint import pformat
from typing import List

import boto3
from botocore.exceptions import ClientError
from dateutil.relativedelta import relativedelta
from fabric import Connection
from humanfriendly.text import split
from invoke import UnexpectedExit
from loguru import logger
from paramiko import AuthenticationException
from simpleeval import simple_eval
from slack_sdk.webhook import WebhookClient
from tabulate import tabulate

# Sources that we can use to pull backups
SOURCE_S3 = "s3"
SOURCE_LOCAL = "local"
SOURCE_SSH = "ssh"
SOURCE_TYPES = [SOURCE_S3, SOURCE_LOCAL, SOURCE_SSH]

"""
A dictionary with rotation frequency names (strings) as keys and
:class:`~dateutil.relativedelta.relativedelta` objects as values.
"""
SUPPORTED_FREQUENCIES = {
    "minutely": relativedelta(minutes=1),
    "hourly": relativedelta(hours=1),
    "daily": relativedelta(days=1),
    "weekly": relativedelta(weeks=1),
    "monthly": relativedelta(months=1),
    "yearly": relativedelta(years=1),
}

"""
An iterable of tuples with two values each:

- The name of a date component (a string).
- :data:`True` for required components, :data:`False` for optional components.
"""
SUPPORTED_DATE_COMPONENTS = (
    ("year", True),
    ("month", True),
    ("day", True),
    ("hour", False),
    ("minute", False),
    ("second", False),
)

"""
A regular expression object used to match timestamps encoded in filenames.
"""
DEFAULT_TIMESTAMP_PATTERN = r"""
    # Required components.
    (?P<year>\d{4} ) \D?
    (?P<month>\d{2}) \D?
    (?P<day>\d{2}  ) \D?
    (?:
        # Optional components.
        (?P<hour>\d{2}  ) \D?
        (?P<minute>\d{2}) \D?
        (?P<second>\d{2})?
    )?
"""


@dataclass
class Warden_Config:
    config_name: str
    rotation_scheme: dict
    timestamp_pattern: re.Pattern
    include_list: List[str] = field(default_factory=list)
    exclude_list: List[str] = field(default_factory=list)
    relaxed: bool = False
    filestat: bool = False
    prefer_recent: bool = False
    utc: bool = False

    def __post_init__(self):
        self.timestamp_pattern = compile_timestamp_pattern(self.timestamp_pattern, self.filestat)

        if isinstance(self.include_list, str):
            self.include_list = split(self.include_list)
        if isinstance(self.exclude_list, str):
            self.exclude_list = split(self.exclude_list)


@dataclass(frozen=True)
class Backup:
    path_name: str  # full path to backup
    path_type: str  # directory or file
    timestamp: datetime
    size: int  # in bytes

    @property
    def week(self):
        """
        Returns the week number of the given timestamp.
        Note: For some days close to January 1, isocalendar()[1] may return the week number as 52 or 53
        For example, date(2022, 1, 1).isocalendar() returns (2021, 52, 6)
        """
        if self.year == self.timestamp.isocalendar()[0] + 1:
            return 0
        else:
            return self.timestamp.isocalendar()[1]

    def __getattr__(self, name):
        """Defer attribute access to :attr:`timestamp`."""
        return getattr(self.timestamp, name)


@dataclass(frozen=True)
class Warden_Backups:
    config: Warden_Config
    backups: List[Backup] = field(default_factory=list)

    paths = {}

    @classmethod
    def initialize(cls, backup_directory, config):
        return cls.paths.setdefault(backup_directory, cls(config))

    def add_backup(self, backup):
        self.backups.append(backup)


@dataclass
class BackupWarden:
    config: Warden_Config  # Will be either parameters or set to a path's config in the main loop
    config_file: str = None
    warden_configs: dict = None  # Holds all config section paths and their data from confile file
    path: str = None
    source: str = None
    environment: str = None
    bucket: str = None
    delete: bool = False
    debug: bool = False
    log_file: str = None
    s3_endpoint_url: str = None
    s3_access_key_id: str = None
    s3_secret_access_key: str = None
    slack_webhook: str = None
    ssh_host: str = None
    ssh_sudo: bool = False

    max_backup_name_length: int = 0
    tabulate_rows: list = field(default_factory=list)

    def __post_init__(self):
        # Load config path sections from file if it exists
        if self.config_file and Path(self.config_file).is_file():
            self.warden_configs = load_config_file(configuration_file=self.config_file, app_config=False)
            logger.info(f"Config file '{self.config_file}' found")
        else:
            logger.debug(pformat(self.config))
            logger.info(f"Config file '{self.config_file}' not found. Command line parameters will be used")

    def print_tabulate(self):
        table_columns = [
            "Backup" + " " * (self.max_backup_name_length - 7),
            "Timestamp",
            "Size" + " " * 4,
            "Status",
        ]

        table = tabulate(self.tabulate_rows, table_columns, tablefmt="rounded_outline") + "\n"

        print(table)

        # Write to log file. Couldn't use loguru for logging to a file due to message being too long
        if self.log_file:
            with open(self.log_file, "a") as file:
                file.write(table + "\n")

    def apply_config_to_path(self, backup_path: Path):
        """
        Apply a config to a path.

        :param backup_path: The backup path.
        :return: A Warden_Config or None if the config section doesn't have a match in the path.
        """

        if self.warden_configs:
            for config_section_path, warden_config in self.warden_configs.items():
                warden_config: Warden_Config
                if fnmatch(backup_path, f"{config_section_path}*"):
                    return warden_config

            # Path not found in config file
            return None
        else:
            # Command-line parameters since there's no config used
            return self.config

    def filter_exclude_include(self, backup_path: Path, include_list, exclude_list):
        """
        Filter the backup path based on the include and exclude lists.

        :param backup_path: The backup path.
        :param include_list: The list of patterns to include.
        :param exclude_list: The list of patterns to exclude.
        :return: True if the backup path should be excluded, False otherwise.
        """

        if exclude_list and any(fnmatch(backup_path, p) for p in exclude_list):
            logger.debug(f"Excluded {backup_path} because it didn't match the exclude list")
            return True

        if include_list and not any(fnmatch(backup_path, p) for p in include_list):
            logger.debug(f"Excluded {backup_path} because it didn't match the include list")
            return True

        return False

    def extract_timestamp(self, backup_path: Path, config: Warden_Config, last_modified=None):
        """
        Extract the timestamp from the backup path based on the timestamp pattern or if filestat is used.

        :param backup_path: The backup path.
        :param config: The configuration for the path.
        :return: The extracted timestamp as a datetime object, or None if no timestamp is found.
        """

        backup_name = backup_path.name

        if config.utc:
            specified_timezone = timezone.utc
        else:
            specified_timezone = datetime.now().astimezone().tzinfo

        timestamp_extract = config.timestamp_pattern.search(backup_name)
        if timestamp_extract:
            unixtime = timestamp_extract.groupdict().get("unixtime")
            if unixtime:
                unixtime = int(unixtime)
                # Support seconds and milliseconds-precision timestamps
                for time in (unixtime, unixtime / 1000):
                    try:
                        return datetime.fromtimestamp(time, tz=specified_timezone)
                    except ValueError:
                        pass

                logger.debug(f"Unable to parse unix timestamp from {backup_path}")
            elif config.filestat:
                if self.source in (SOURCE_LOCAL, SOURCE_SSH):
                    return datetime.fromtimestamp(int(last_modified), tz=specified_timezone)
                elif self.source == SOURCE_S3:
                    return last_modified.replace(tzinfo=None)
            else:
                try:
                    return datetime(*map(int, timestamp_extract.groups("0")), tzinfo=specified_timezone)
                except ValueError:
                    pass

        # No timestamp or file match for filestat found, indicating no relevant timestamp
        return None

    def collect_backups(self):
        """
        Collect the backups based on the specified source and configurations.

        :return: A dictionary containing the collected backup paths in Path format as keys and backups along with
        the path configs as values
        """

        # Connect to our sources
        if self.source == SOURCE_SSH:
            if not self.ssh_host:
                raise Exception("An SSH host must be specified")

            try:
                self.ssh_client = Connection(host=self.ssh_host)

                # Execute a command to determine the remote system
                try:
                    result = self.ssh_client.run("uname -s", hide=True, shell=True)
                    self.ssh_system = result.stdout.strip()
                except UnexpectedExit as message:
                    raise Exception(f"Error running uname command: {message.result}")
            except AuthenticationException:
                raise Exception("SSH Authentication failed! Check your SSH key or credentials")
            except Exception as exception:
                raise Exception(f"Error occurred with SSH: {exception}")
        elif self.source == SOURCE_S3:
            if not self.bucket:
                raise Exception("S3 bucket must be specified")

            if not self.s3_access_key_id or not self.s3_secret_access_key:
                raise Exception("S3 credentials must be specified")

            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.s3_endpoint_url,
                aws_access_key_id=self.s3_access_key_id,
                aws_secret_access_key=self.s3_secret_access_key,
            )

        # We either use the path and traverse or loop through the config sections
        paths = (
            [self.path] if self.path else [config_section_path for config_section_path in self.warden_configs.keys()]
        )
        for path in paths:
            if self.source == SOURCE_S3:
                self.scan_for_backups_s3(path)
            elif self.source == SOURCE_LOCAL:
                self.scan_for_backups_local(path)
            elif self.source == SOURCE_SSH:
                self.scan_for_backups_ssh(path)

        print("")

        # Find the maximum backup name length to size the backup name column
        # for tabulate so all tables are the same size
        if Warden_Backups.paths:
            self.max_backup_name_length = max(
                len(os.path.basename(backup.path_name))
                for warden_backups in Warden_Backups.paths.values()
                for backup in warden_backups.backups
            )

        # Sort paths dictionary by key
        return sorted(Warden_Backups.paths.items(), key=lambda x: x[0])

    def scan_for_backups_s3(self, path):
        """
        Scan for backups from Amazon S3

        :param path: The path to scan for backups

        Updates Warden_Backups object with the backups it finds
        """

        kwargs = {"Bucket": self.bucket, "Prefix": str(path)}
        paginator = self.s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(**kwargs, PaginationConfig={"PageSize": 500})

        for page in page_iterator:
            if "Contents" in page:
                for obj in page.get("Contents"):
                    backup_path = Path(obj["Key"])
                    backup_size = obj["Size"]
                    backup_dir = str(backup_path.parent)

                    config = self.apply_config_to_path(backup_path)
                    if config:
                        if self.filter_exclude_include(backup_path, config.include_list, config.exclude_list):
                            continue

                        last_modified = obj["LastModified"] if config.filestat else None

                        try:
                            timestamp = self.extract_timestamp(backup_path, config, last_modified)
                        except AttributeError as e:
                            raise Exception(f"Failed extracting timestamp from backup name: {e}")

                        if timestamp:
                            # Create or retrieve existing object for Warden_Backups
                            warden_backups = Warden_Backups.initialize(backup_directory=backup_dir, config=config)

                            # Add the backup to it
                            warden_backups.add_backup(
                                Backup(
                                    path_name=str(backup_path),
                                    path_type="file",
                                    timestamp=timestamp,
                                    size=backup_size,
                                )
                            )

    def scan_for_backups_local(self, recursed_path):
        """
        Scan for backups from the local file system.

        :param recursed_path: The path to scan for backups

        Updates Warden_Backups object with the backups it finds
        """

        if not os.path.exists(recursed_path):
            raise ValueError(f"Path '{recursed_path}' does not exist")

        logger.info(f"Scanning path: {recursed_path}")
        for path in sorted(os.scandir(recursed_path), key=lambda p: p.name):
            backup_path = Path(path)
            backup_dir = str(backup_path.parent)

            config = self.apply_config_to_path(backup_path)
            if not config:
                if self.path and backup_path.is_dir():
                    self.scan_for_backups_local(backup_path)
                continue

            last_modified = os.stat(backup_path).st_mtime if config.filestat else None

            try:
                timestamp = self.extract_timestamp(backup_path, config, last_modified)
            except AttributeError as e:
                raise Exception(f"Failed extracting timestamp from backup name: {e}")

            if timestamp:
                if self.filter_exclude_include(backup_path, config.include_list, config.exclude_list):
                    continue

                if backup_path.is_dir():
                    path_type = "directory"
                    backup_size = 0

                    for file in os.scandir(backup_path):
                        backup_size += os.path.getsize(file.path)
                else:
                    path_type = "file"
                    backup_size = os.path.getsize(backup_path)

                # Create or retrieve existing object for Warden_Backups
                warden_backups = Warden_Backups.initialize(backup_directory=backup_dir, config=config)

                # Add the backup to it
                warden_backups.add_backup(
                    Backup(
                        path_name=str(backup_path),
                        path_type=path_type,
                        timestamp=timestamp,
                        size=backup_size,
                    )
                )
            else:
                if self.path and backup_path.is_dir():
                    self.scan_for_backups_local(backup_path)

    def scan_for_backups_ssh(self, recursed_path):
        """
        Scan for backups from SSH

        :param recursed_path: The path to scan for backups.

        Updates Warden_Backups object with the backups it finds
        """

        # Darwin/Linux don't use the same commands, so we specify them specifically
        if self.ssh_system == "Darwin":
            command = f"""find {recursed_path} -mindepth 1 -maxdepth 1 \
                -exec sh -c 'file="$1"; printf "%s\t" "$(date -r "$file" +"%s")"; [ -f "$file" ] && \
                printf "%s\t" "file" || printf "%s\t" "directory"; printf "%s\n" "$(du -sk "$file")"' sh {{}} \\; \
                | sort -k4
            """
        else:
            command = f"""find {recursed_path} -mindepth 1 -maxdepth 1 \
                -exec sh -c 'file="$1"; printf "%s\t" "$(stat -c "%Y" "$file")"; [ -f "$file" ] && \
                printf "%s\t" "file" || printf "%s\t" "directory"; printf "%s\n" "$(du -sb -B1 "$file")"' sh {{}} \\; \
                | sort -k4
            """

        logger.info(f"Scanning path: {recursed_path}")

        try:
            command_runner = self.ssh_client.sudo if self.ssh_sudo else self.ssh_client.run
            result = command_runner(command, hide=True)

            if result.stderr:
                raise Exception(f"Failed to scan path {recursed_path}: {result.stderr}")
        except UnexpectedExit as e:
            raise Exception(f"Error running find command: {e.result}")

        # Process the command output to collect backup information
        for line in result.stdout.splitlines():
            last_modified, path_type, backup_size, recursed_path = line.strip().split("\t")
            backup_path = Path(recursed_path)
            backup_dir = str(backup_path.parent)

            # For Darwin, we need to convert the kilobytes it returns to byte for a proper conversion to human readable
            if self.ssh_system == "Darwin":
                backup_size = int(backup_size) * 1024
            else:
                backup_size = int(backup_size)

            config = self.apply_config_to_path(backup_path)
            if not config:
                if self.path and backup_path.is_dir():
                    self.scan_for_backups_local(backup_path)
                continue

            last_modified = last_modified if config.filestat else None

            try:
                timestamp = self.extract_timestamp(backup_path, config, last_modified)
            except AttributeError as e:
                raise Exception(f"Failed extracting timestamp from backup name: {e}")

            if timestamp:
                if self.filter_exclude_include(backup_path, config.include_list, config.exclude_list):
                    continue

                # Create or retrieve existing object for Warden_Backups
                warden_backups = Warden_Backups.initialize(backup_directory=backup_dir, config=config)

                # Add the backup to it
                warden_backups.add_backup(
                    Backup(
                        path_name=str(backup_path),
                        path_type=path_type,
                        timestamp=timestamp,
                        size=int(backup_size),
                    )
                )
            else:
                if self.path and path_type == "directory":
                    self.scan_for_backups_ssh(recursed_path)

    def group_backups(self, backups):
        """
        Group backups collected by :func:`collect_backups()` by rotation frequencies.

        :param backups: A :class:`set` of :class:`Backup` objects.
        :returns: A :class:`dict` whose keys are the names of rotation
                frequencies ('hourly', 'daily', etc.) and whose values are
                dictionaries. Each nested dictionary contains lists of
                :class:`Backup` objects that are grouped together because
                they belong into the same time unit for the corresponding
                rotation frequency.
        """
        frequency_key_mapping = {
            "minutely": lambda b: (b.year, b.month, b.day, b.hour, b.minute),
            "hourly": lambda b: (b.year, b.month, b.day, b.hour),
            "daily": lambda b: (b.year, b.month, b.day),
            "weekly": lambda b: (b.year, b.week),
            "monthly": lambda b: (b.year, b.month),
            "yearly": lambda b: b.year,
        }

        backups_by_frequency = {frequency: {} for frequency in SUPPORTED_FREQUENCIES}

        for b in backups:
            for frequency, key_mapping in frequency_key_mapping.items():
                # If frequency is set to 0, don't add it
                if self.config.rotation_scheme.get(frequency) != 0:
                    key = key_mapping(b)
                    backups_by_frequency[frequency].setdefault(key, []).append(b)

        return backups_by_frequency

    def apply_rotation_scheme(self, backups_by_frequency, most_recent_backup):
        """
        Apply the user defined rotation scheme to the result of :func:`group_backups()`.

        :param backups_by_frequency: A :class:`dict` in the format generated by
                                     :func:`group_backups()`.
        :param most_recent_backup: The :class:`~datetime.datetime` of the most
                                   recent backup.

        .. note:: This method mutates the given data structure by removing all
                  backups that should be removed to apply the user defined
                  rotation scheme.
        """
        rotation_scheme = self.config.rotation_scheme

        if not rotation_scheme:
            raise Exception("Refusing to use empty rotation scheme! (all backups would be deleted)")

        for frequency, backups in backups_by_frequency.items():
            # Ignore frequencies not specified by the user.
            if frequency not in rotation_scheme:
                backups.clear()
            else:
                # Reduce the number of backups in each time slot of this
                # rotation frequency to a single backup (the oldest one or the
                # newest one).
                for period, backups_in_period in backups.items():
                    index = -1 if self.config.prefer_recent else 0
                    selected_backup = list(backups_in_period)[index]
                    backups[period] = [selected_backup]

                # Check if we need to rotate away backups in old periods.
                retention_period = rotation_scheme[frequency]

                if retention_period != "always":
                    # Remove backups created before the minimum date of this
                    # rotation frequency? (relative to the most recent backup)
                    if not self.config.relaxed:
                        minimum_date = most_recent_backup - SUPPORTED_FREQUENCIES[frequency] * retention_period
                        for backup, backups_in_period in list(backups.items()):
                            backups_in_period[:] = [
                                backup for backup in backups_in_period if backup.timestamp >= minimum_date
                            ]
                            if not backups_in_period:
                                backups.pop(backup)

                    # If there are more periods remaining than the user
                    # requested to be preserved we delete the oldest one(s).
                    items_to_preserve = list(backups.items())[-retention_period:]
                    backups_by_frequency[frequency] = dict(items_to_preserve)

    def find_preservation_criteria(self, backups_by_frequency):
        """
        Collect the criteria used to decide which backups to preserve.

        :param backups_by_frequency: A :class:`dict` in the format generated by
                                     :func:`group_backups()` which has been
                                     processed by :func:`apply_rotation_scheme()`.
        :returns: A :class:`dict` with :class:`Backup` objects as keys and
                  :class:`list` objects containing strings (rotation
                  frequencies) as values.
        """
        backups_to_preserve = {}
        for frequency, backups in backups_by_frequency.items():
            for period_backups in backups.values():
                for backup in period_backups:
                    backups_to_preserve.setdefault(backup, []).append(frequency)

        return backups_to_preserve

    def rotate_backups(self):
        """
        Rotate the backups in a directory according to a flexible rotation scheme
        """
        tool_start_time = datetime.utcnow()

        total_backup_size = 0
        total_backup_files_count = 0
        total_backup_deleted_size = 0
        total_backup_deleted_file_count = 0
        no_backups_24hrs = []

        for path_name, warden_backups in self.collect_backups():
            warden_backups: Warden_Backups

            path_backup_size = 0
            path_backup_files_count = 0
            path_backup_deleted_size = 0
            path_backup_deleted_files_count = 0
            s3_delete_list = []
            self.tabulate_rows = []

            # Apply the path's config to self
            logger.debug(pformat(warden_backups.config, sort_dicts=False))
            self.config = warden_backups.config

            logger.opt(colors=True).info(f"Processing path: <cyan>{path_name}</cyan>")
            logger.opt(colors=True).info(
                f"Using <fg #d0d5d6>{self.config.config_name}</fg #d0d5d6> retention policy:"
                f" {self.config.rotation_scheme}"
            )

            backups = sorted(warden_backups.backups, key=lambda b: b.timestamp)
            if backups:
                most_recent_backup: Backup = backups[-1]
                backups_by_frequency = self.group_backups(backups)
                self.apply_rotation_scheme(backups_by_frequency, most_recent_backup.timestamp)
                backups_to_preserve = self.find_preservation_criteria(backups_by_frequency)

                if most_recent_backup.timestamp < (datetime.now(timezone.utc) - timedelta(1)):
                    no_backups_24hrs.append(path_name)
                    warning_message = (
                        f"No backup taken for path {path_name} in the past 24 hours! Most recent backup:"
                        f" {most_recent_backup.timestamp}"
                    )
                    logger.error(warning_message)
                    slack_notify(
                        webhook_url=self.slack_webhook,
                        environment=self.environment,
                        source=self.source,
                        backup_status="warning",
                        status_message="No backup taken in the past 24 hours!",
                        backup_path=path_name,
                        most_recent_backup=most_recent_backup.timestamp,
                    )

                # Loop through the backups
                for backup_object in backups:
                    backup_path = backup_object.path_name
                    backup_path_type = backup_object.path_type
                    backup_timestamp = backup_object.timestamp
                    backup_size = backup_object.size
                    backup_size_human = convert_bytes(backup_size)

                    backup_name = (
                        f"{os.path.basename(backup_path)}/"
                        if backup_path_type == "directory"
                        else os.path.basename(backup_path)
                    )

                    if backup_object in backups_to_preserve:
                        matching_types = "', '".join(backups_to_preserve[backup_object])
                        period = "period" if len(backups_to_preserve[backup_object]) == 1 else "periods"
                        backup_status = f"Preserving (matches '{matching_types}' retention {period})"
                    else:
                        # Delete!
                        if self.delete:
                            backup_status = "Deleted"

                            if self.source == SOURCE_LOCAL:
                                backup_type = "file" if Path(backup_path).is_file() else "path"

                                try:
                                    if backup_type == "file":
                                        os.remove(backup_path)
                                    else:
                                        shutil.rmtree(backup_path)
                                except OSError as e:
                                    raise Exception(
                                        f"Error occurred while deleting the {backup_type} {backup_path}: {e}"
                                    )

                            elif self.source == SOURCE_S3:
                                # We add to an array until all paths are done scanning
                                s3_delete_list.append({"Key": backup_path})

                            elif self.source == SOURCE_SSH:
                                command = f"rm -rf {backup_path}"
                                command_runner = self.ssh_client.sudo if self.ssh_sudo else self.ssh_client.run

                                try:
                                    result = command_runner(command, hide=True)
                                    if result.stderr:
                                        raise Exception(f"Failed to delete {backup_path}: {result.stderr}")
                                except UnexpectedExit as e:
                                    raise Exception(f"Error running SSH delete command: {e.result}")

                        else:
                            backup_status = "Deleted (skipped)"

                        path_backup_deleted_size += backup_size
                        path_backup_deleted_files_count += 1

                    path_backup_size += backup_size
                    path_backup_files_count += 1

                    self.tabulate_rows.append([backup_name, backup_timestamp, backup_size_human, backup_status])

                # We bulk delete for S3 since it has better performance
                if self.delete and s3_delete_list:
                    try:
                        response = self.s3_client.delete_objects(Bucket=self.bucket, Delete={"Objects": s3_delete_list})
                        if "Errors" in response:
                            # Update the status for tabulate
                            for rows in self.tabulate_rows:
                                if rows[3] == "Deleted":
                                    rows[3] = "Deleted (failed)"

                            for error in response["Errors"]:
                                logger.error(
                                    f"Failed to delete backup {error['Key']}: {error['Code']} - {error['Message']}"
                                )

                            raise Exception("Failed to delete backups!")
                    except ClientError as e:
                        raise Exception(f"Error deleting file '{backup_path}': {e.response['Error']['Message']}")

            if path_backup_files_count:
                self.tabulate_rows.append(["", "", "", ""])
                self.tabulate_rows.append(
                    [
                        f"Total: {path_backup_files_count}",
                        "",
                        convert_bytes(path_backup_size),
                        (
                            "All backups preserved"
                            if not path_backup_deleted_files_count
                            else (
                                f"Deleted {path_backup_deleted_files_count} backups totaling"
                                f" {convert_bytes(path_backup_deleted_size)}"
                                if self.delete
                                else (
                                    f"Deleted {path_backup_deleted_files_count} backups totaling"
                                    f" {convert_bytes(path_backup_deleted_size)} (skipped)"
                                )
                            )
                        ),
                    ]
                )
                self.print_tabulate()
            else:
                print()

            total_backup_size += path_backup_size
            total_backup_files_count += path_backup_files_count
            total_backup_deleted_size += path_backup_deleted_size
            total_backup_deleted_file_count += path_backup_deleted_files_count

        remaining_total_files = total_backup_files_count - total_backup_deleted_file_count
        remaining_total_size = total_backup_size - total_backup_deleted_size
        runtime = str(datetime.utcnow() - tool_start_time).split(".")[0]

        if len(Warden_Backups.paths):
            logger.info(f"{'Paths:':<12} {len(Warden_Backups.paths)}")
            logger.info(f"{'Backups:':<12} {total_backup_files_count:<7} ({convert_bytes(total_backup_size)})")
            logger.info(
                f"{'Deleted:':<12} {total_backup_deleted_file_count:<7} ({convert_bytes(total_backup_deleted_size)})"
            )
            logger.info(f"{'Remaining:':<12} {remaining_total_files:<7} ({convert_bytes(remaining_total_size)})")
            logger.info(f"{'Runtime:':<12} {runtime}")

            if no_backups_24hrs:
                print("")

                path_spelling = "paths haven't" if len(no_backups_24hrs) > 1 else "path hasn't"
                logger.info(f"{len(no_backups_24hrs)} {path_spelling} had a backup in the past 24 hours:")

                for path in no_backups_24hrs:
                    logger.info(path)
        else:
            logger.info("No backups were found")

        slack_notify(
            webhook_url=self.slack_webhook,
            environment=self.environment,
            source=self.source,
            backup_status="success",
            backups_deleted=total_backup_deleted_file_count,
            size_deleted=convert_bytes(total_backup_deleted_size),
            total_size=convert_bytes(remaining_total_size),
            runtime=runtime,
        )


def parse_timestamp_frequency(value):
    """
    Parse a retention period to a Python value.

    :param value: A string containing the text 'always', a number or
                  an expression that can be evaluated to a number.
    :returns: A number or the string 'always'.
    :raises: :exc:`~exceptions.ValueError` when the string can't be parsed
    """
    # Return if we have an integer (normal number)
    if isinstance(value, int):
        return value

    # If what is inputted isn't a string, error
    if not isinstance(value, str):
        raise ValueError(f"Expected string for a math expression, got {type(value)} instead!")

    # Support the 'always' value
    value = value.strip().lower()
    if value == "always":
        return "always"

    # Evaluate math expressions as a value (i.e. 4*2)
    try:
        value = simple_eval(value)
    except (ValueError, SyntaxError):
        raise ValueError(f"Expected string or numeric value, got {type(value)} instead!")

    return value


def load_config_file(configuration_file, app_config=False):
    """
    Load the configuration file.

    :param configuration_file: The path to the configuration file.
    :param app_config: True if loading application-level configuration, False for path-level configuration.

    :return: A dictionary of the loaded configuration data.
    """

    config_data = {}

    config = ConfigParser()
    config.read(configuration_file)

    for section in sorted(config.sections(), reverse=True):
        if app_config and section == "main":
            # We create a main config based off of the keys in BackupWarden object
            for option, data_type in BackupWarden.__annotations__.items():
                # These options won't be in the config file
                if option not in ["config", "config_file", "warden_configs"]:
                    if data_type is bool:
                        try:
                            config_value = config.getboolean(section, option, fallback=False)
                        except ValueError as e:
                            raise Exception(
                                f"Failed to retrieve boolean value for config option {option} under section"
                                f" {section}: {e}"
                            )
                    else:
                        config_value = config.get(section, option, fallback=None)

                    config_data[option] = config_value
        elif not app_config and section != "main":
            rotation_scheme = {
                name: parse_timestamp_frequency(config.get(section, name, fallback=""))
                for name in SUPPORTED_FREQUENCIES
                if config.get(section, name, fallback=None)
            }

            config_options = {"config_name": section, "rotation_scheme": rotation_scheme}

            # We create a config section based off of the keys in Warden_Config object
            for option, data_type in Warden_Config.__annotations__.items():
                # These options won't be in the config file
                if option not in ["config_name", "rotation_scheme"]:
                    if data_type is bool:
                        try:
                            config_value = config.getboolean(section, option, fallback=False)
                        except ValueError as e:
                            raise Exception(
                                f"Failed to retrieve boolean value for config option {option} under section"
                                f" {section}: {e}"
                            )
                    else:
                        config_value = config.get(section, option, fallback=None)

                    config_options[option] = config_value

            config_data[section] = Warden_Config(**config_options)

    logger.debug(pformat(config_data, sort_dicts=False))
    return config_data


def compile_timestamp_pattern(pattern, filestat):
    """
    Compile the timestamp pattern and validate its capture groups.

    :param pattern: The timestamp pattern string.
    :param filestat: A boolean indicating whether filestat is used or not.
    :return: The compiled pattern object.
    :raises: :exc:`~exceptions.ValueError` if there is an error compiling the pattern
             or if the pattern is missing required capture groups.
    """

    if pattern:
        try:
            compiled_pattern = re.compile(pattern, re.VERBOSE)
        except re.error as e:
            raise ValueError(f"Error compiling timestamp pattern '{pattern}': {str(e)}")

        if "unixtime" not in compiled_pattern.groupindex and not filestat:
            for component, required in SUPPORTED_DATE_COMPONENTS:
                if component not in compiled_pattern.groupindex and required:
                    raise ValueError(
                        f"Timestamp pattern is missing required capture group '{component}' for pattern: {pattern}"
                    )

        return compiled_pattern
    else:
        return re.compile(DEFAULT_TIMESTAMP_PATTERN, re.VERBOSE)


def slack_notify(
    webhook_url,
    environment,
    source,
    backup_status="",
    backups_deleted=0,
    size_deleted=0,
    total_size=0,
    runtime="",
    status_message="",
    backup_path="",
    most_recent_backup="",
):
    if not webhook_url:
        return

    title_app = "Backup Warden"

    if backup_status == "success":
        title = f"*{title_app} Success | {environment}*"
        notification_text = f"{title_app} successfully completed!"
        status_icon = ":large_green_circle:"
        theme_color = "#00b301"

        fields = [
            {"type": "mrkdwn", "text": f"*Backups Deleted*\n{backups_deleted}"},
            {"type": "mrkdwn", "text": f"*Size Deleted*\n{size_deleted}"},
            {"type": "mrkdwn", "text": f"*Current Total Size*\n{total_size}"},
            {"type": "mrkdwn", "text": f"*Runtime*\n{runtime}"},
        ]
    elif backup_status == "warning":
        title = f"*{title_app} Warning | {environment}*"
        notification_text = f"{title_app} warning!"
        status_icon = ":large_yellow_circle:"
        theme_color = "#ffd600"

        fields = [
            {"type": "mrkdwn", "text": f"*Alert*\n{status_message}"},
            {"type": "mrkdwn", "text": f"*Path*\n{backup_path}"},
            {"type": "mrkdwn", "text": f"*Most Recent Backup*\n{most_recent_backup}"},
        ]
    else:
        title = f"*{title_app} Failure | {environment}*"
        notification_text = f"{title_app} failed!"
        status_icon = ":red_circle:"
        theme_color = "#df2220"

        fields = [
            {"type": "mrkdwn", "text": f"*Alert*\n{status_message}"},
        ]

    if source == SOURCE_SSH:
        source = source.upper()
    else:
        source = source.capitalize()

    elements = [
        {
            "type": "mrkdwn",
            "text": f"Source: {source}",
        }
    ]

    payload = {
        "text": notification_text,
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{status_icon} {title}"},
            }
        ],
        "attachments": [
            {
                "fallback": title,
                "color": theme_color,
                "blocks": [{"type": "section", "fields": fields}, {"type": "context", "elements": elements}],
            }
        ],
    }

    client = WebhookClient(webhook_url)
    response = client.send_dict(payload)

    if response.body == "ok":
        logger.debug("Successfully sent Slack message!")
    else:
        raise Exception(f"Failed to send Slack alert! Reason: {response.body}")


def convert_bytes(bytes_value):
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0

    while bytes_value >= 1024 and unit_index < len(units) - 1:
        bytes_value /= 1024
        unit_index += 1

    return f"{bytes_value:.2f} {units[unit_index]}"
