#!/usr/bin/python3

# Backup Warden

# Author: Charles Thompson
# Created on: July 1, 2023
# GitHub: https://github.com/charles-001/backup-warden

import argparse
import os
import sys
from importlib import metadata
from logging.handlers import SysLogHandler

import requests
from backup_warden import (
    SOURCE_LOCAL,
    SOURCE_TYPES,
    BackupWarden,
    Warden_Config,
    load_config_file,
    parse_timestamp_frequency,
    slack_notify,
)
from loguru import logger
from packaging.version import parse as parse_version

try:
    __package_name__ = metadata.metadata(__package__ or __name__)["Name"]
    __version__ = metadata.version(__package__ or __name__)
except Exception:
    __package_name__ = "N/A"
    __version__ = "N/A"


def setup_logging(args):
    # Setup logging with pretty colors
    logger.remove()
    logger.level("DEBUG", color="<magenta>")
    logger.level("INFO", color="<blue>")
    logger.level("WARNING", color="<yellow>")
    logger.level("ERROR", color="<red>")
    log_format = "<dim>{time:MM-DD-YYYY HH:mm:ss}</dim> <b><level>[{level}]</level></b> {message}"

    log_level = "INFO"
    if args.debug:
        log_level = "DEBUG"

    # Add terminal logging
    logger.add(
        sys.stdout,
        format=log_format,
        backtrace=True,
        colorize=True,
        level=log_level,
    )

    if args.syslog:
        # Add syslog logging
        linux_address = "/dev/log"
        darwin_address = "/var/run/syslog"
        if os.path.exists(linux_address):
            syslog_address = linux_address
        elif os.path.exists(darwin_address):
            syslog_address = darwin_address
        else:
            syslog_address = None
            logger.error("Cannot find a valid syslog address to use")

        if syslog_address:
            handler = SysLogHandler(address=syslog_address)
            handler.ident = "backup_warden:"

            logger.add(handler, level="INFO", format="{message}")

    # Add file logging
    if args.log_file:
        logger.add(args.log_file, format=log_format, backtrace=True, level=log_level, colorize=False)


def check_for_update():
    # Query PyPI API to get the latest version
    url = f"https://pypi.org/pypi/{__package_name__}/json"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        # Extract the latest version from the response
        latest_version = data["info"]["version"]

        # Compare the current version with the latest version
        if parse_version(latest_version) > parse_version(__version__):
            logger.opt(colors=True).info(
                f"<green>New version available!</green>\n\nCurrent version: <cyan>{__version__}</cyan>\nLatest version:"
                f" <cyan>{latest_version}</cyan>\n\nPlease update to the latest version at your convenience"
            )
    else:
        logger.error(
            f"Failed to retrieve package information from PyPI! URL: {url} - Code: {response.status_code} - Response:"
            f" {response.json()}"
        )


def main():
    options = vars(setup_options())
    backup_warden = None

    try:
        check_for_update()

        # Create rotation scheme and remove from options so they don't get sent to BackupWarden
        rotation_scheme = {
            frequency: parse_timestamp_frequency(options.pop(frequency, None))
            for frequency in ("minutely", "hourly", "daily", "weekly", "monthly", "yearly")
        }

        # Create our parameter config as a default
        config = Warden_Config(
            config_name="parameters",
            rotation_scheme=rotation_scheme,
            timestamp_pattern=options.pop("timestamp_pattern"),
            filestat=options.pop("filestat"),
            include_list=options.pop("include_list"),
            exclude_list=options.pop("exclude_list"),
            relaxed=options.pop("relaxed"),
            utc=options.pop("utc"),
            prefer_recent=options.pop("prefer_recent"),
        )

        # Remove syslog from options so it isn't sent to BackupWarden since it's only used here
        options.pop("syslog")

        backup_warden = BackupWarden(config=config, **options)
        backup_warden.rotate_backups()
    except Exception as e:
        e = str(e)

        if backup_warden:
            if backup_warden.tabulate_rows:
                backup_warden.print_tabulate()

            # If slack notify called this, don't call it again to avoid circular dependency
            if "Slack alert" not in e:
                slack_notify(
                    webhook_url=backup_warden.slack_webhook,
                    environment=backup_warden.environment,
                    source=backup_warden.source,
                    backup_status="failure",
                    status_message=e,
                )

        if options["debug"]:
            logger.exception(e)
        else:
            logger.critical(e)


def setup_options():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        type=str,
        default="/etc/backup_warden.ini",
        help="Location of the config file",
    )
    parser.add_argument(
        "-s",
        "--source",
        choices=SOURCE_TYPES,
        default=SOURCE_LOCAL,
        help="Source of where the backups are stored",
    )
    parser.add_argument(
        "-b",
        "--bucket",
        type=str,
        default="",
        help="Name of the AWS S3 bucket",
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default="",
        help="Specify a path to traverse all directories it contains for granular retention policies",
    )
    parser.add_argument(
        "-e",
        "--environment",
        type=str,
        default="",
        help="Environment the backups are rotated in (used for Slack alert only)",
    )
    parser.add_argument(
        "-t",
        "--timestamp-pattern",
        type=str,
        default="",
        help="The timestamp pattern using a regex expression to parse out of filenames",
    )
    parser.add_argument(
        "-l",
        "--log-file",
        type=str,
        default="",
        help="Enable logging to this file path",
    )
    parser.add_argument(
        "-I",
        "--include",
        dest="include_list",
        type=str,
        default="",
        help="Include backups based on their directory path and/or filename (separated by comma)",
    )
    parser.add_argument(
        "-E",
        "--exclude",
        dest="exclude_list",
        type=str,
        default="",
        help="Exclude backups based on their directory path and/or filename (separated by comma)",
    )
    parser.add_argument(
        "-H",
        "--ssh-host",
        type=str,
        default="",
        help="SSH host/alias to use",
    )

    parser.add_argument(
        "--ssh-sudo",
        dest="ssh_sudo",
        action="store_true",
        help="Wrap SSH commands with sudo for escalated privileges",
    )
    parser.add_argument(
        "--filestat",
        action="store_true",
        help="Use the file's last modified date instead of parsing timestamp from filename",
    )
    parser.add_argument(
        "--prefer-recent",
        action="store_true",
        help="Keep the most recent backup in each time slot instead of oldest",
    )
    parser.add_argument(
        "--relaxed",
        action="store_true",
        help="Time windows are not enforced (see documentation for more information)",
    )
    parser.add_argument(
        "--utc", action="store_true", help="Use UTC timezone instead of local machine's timezone for timestamps"
    )
    parser.add_argument(
        "--syslog",
        dest="syslog",
        action="store_true",
        help="Use syslog",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Log debug messages that can help troubleshoot",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Commit to deleting backups (DANGER ZONE)",
    )
    parser.add_argument("-V", "--version", action="version", version=__version__, help="Display version and exit")

    retention_group = parser.add_argument_group("Retention options")
    retention_options = [
        ("minutely", "Number of minutely backups to preserve", 0),
        ("hourly", "Number of hourly backups to preserve", 72),
        ("daily", "Number of daily backups to preserve", 7),
        ("weekly", "Number of weekly backups to preserve", 6),
        ("monthly", "Number of monthly backups to preserve", 12),
        ("yearly", "Number of yearly backups to preserve", "always"),
    ]
    for option_name, option_help, option_default in retention_options:
        retention_group.add_argument(
            f"--{option_name}",
            type=str,
            default=option_default,
            help=option_help,
        )

    args = parser.parse_args()

    setup_logging(args)

    if os.path.isfile(args.config_file):
        main_config = load_config_file(configuration_file=args.config_file, app_config=True)
        if main_config:
            allowed_options = {"config_file", "delete", "debug"}
            # We find exactly what parameters are actually passed and fail if they're used when --config is passed
            for action in parser._get_optional_actions():
                if isinstance(action, (argparse._StoreAction, argparse._StoreTrueAction)):
                    arg_name = ", ".join(action.option_strings)
                    default_value = action.default
                    arg_value = getattr(args, action.dest)
                    if action.dest not in allowed_options and arg_value != default_value:
                        sys.exit(
                            logger.critical(
                                f"Parameter '{arg_name}' is not allowed when a config file is used. "
                                "You will need to set it there."
                            )
                        )

            # Overwrite parameter values/defaults with config file values
            config_options = argparse.Namespace(
                bucket=main_config.get("bucket"),
                path=main_config.get("path"),
                environment=main_config.get("environment"),
                source=main_config.get("source"),
                ssh_host=main_config.get("ssh_host"),
                ssh_sudo=main_config.get("ssh_sudo"),
                log_file=main_config.get("log_file"),
                syslog=main_config.get("syslog"),
                slack_webhook=main_config.get("slack_webhook"),
                s3_endpoint_url=main_config.get("s3_endpoint_url"),
                s3_access_key_id=main_config.get("s3_access_key_id"),
                s3_secret_access_key=main_config.get("s3_secret_access_key"),
            )
            args.__dict__.update(config_options.__dict__)
    else:
        if not args.path:
            sys.exit(logger.critical("A path must be specified"))

    if args.source not in SOURCE_TYPES:
        sys.exit(logger.critical(f"Source {args.source} is not valid! Choose from {SOURCE_TYPES}"))

    # Create dict that pairs an environment variable with args value
    env_variables = {
        "S3_ENDPOINT_URL": "s3_endpoint_url",
        "AWS_ACCESS_KEY_ID": "s3_access_key_id",
        "AWS_SECRET_ACCESS_KEY": "s3_secret_access_key",
        "SLACK_WEBHOOK": "slack_webhook",
    }

    # Overwrite args variable with environment variable if specified
    for var, arg_name in env_variables.items():
        value = os.environ.get(var)
        if value:
            setattr(args, arg_name, value)
            logger.info(f"Using environment variable: {var}")

    # Enable syslog if config specified it
    setup_logging(args)

    return args


if __name__ == "__main__":
    main()
