# Backup Warden

In today's digital landscape, every business is taking backups of their data (hopefully). These backups can be challenging as they often require substantial disk space and/or cloud storage that can lead to significant financial expenses. If you're in search of a solution to handle your backups and retain only the necessary ones according to your retention policies, look no further! With Backup Warden, it will supervise and maintain your backups simplifying your overall data life cycle and enabling you to have smarter resource utilization.

Thanks to xolox for his work on [rotate-backups](https://github.com/xolox/python-rotate-backups) that gave me a lot of inspiration for this project!

## Usage

| Option                      | Description                                                                                    | Default Value            |
| --------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------ |
| `--minutely`                | Number of minutely backups to preserve                                                         | `0`                      |
| `--hourly`                  | Number of hourly backups to preserve                                                           | `72`                     |
| `--daily`                   | Number of daily backups to preserve                                                            | `7`                      |
| `--weekly`                  | Number of weekly backups to preserve                                                           | `6`                      |
| `--monthly`                 | Number of monthly backups to preserve                                                          | `12`                     |
| `--yearly`                  | Number of yearly backups to preserve                                                           | `always`                 |
| `-c`, `--config`            | Location of the config file                                                                    | `/etc/backup_warden.ini` |
| `-s`, `--source`            | Source of where the backups are stored. Select from: `local`, `ssh`, `s3`                      | `local`                  |
| `-b`, `--bucket`            | Name of the AWS S3 bucket                                                                      |                          |
| `-p`, `--path`              | Specify a path to traverse all directories it contains for granular retention policies         |                          |
| `-e`, `--environment`       | Environment the backups are rotated in (used for Slack alert only)                             |                          |
| `-t`, `--timestamp-pattern` | The timestamp pattern using a regex expression to parse out of filenames                       |                          |
| `-l`, `--log-file`          | Enable logging to this file path                                                               |                          |
| `-I`, `--include`           | Include backups based on their directory path and/or filename (separated by comma)             |                          |
| `-E`, `--exclude`           | Exclude backups based on their directory path and/or filename (separated by comma)             |                          |
| `-H`, `--ssh-host`          | SSH host/alias to use                                                                          |                          |
| `--ssh-sudo`                | Wrap SSH commands with sudo for escalated privileges                                           | `False`                  |
| `--filestat`                | Use the file's last modified date instead of parsing timestamp from filename                   | `False`                  |
| `--prefer-recent`           | Keep the most recent backup in each time slot instead of oldest                                | `False`                  |
| `--relaxed`                 | Time windows are not enforced                                                                  | `False`                  |
| `--utc`                     | Use UTC timezone instead of local machine's timezone for timestamps                            | `False`                  |
| `--syslog`                  | Use syslog                                                                                     | `False`                  |
| `--debug`                   | Log debug messages that can help troubleshoot                                                  | `False`                  |
| `--delete`                  | Commit to deleting backups (DANGER ZONE)                                                       | `False`                  |
| `-V`, `--version`           | Display version and exit                                                                       |                          |
| `-h`, `--help`              | Show this help message and exit                                                                |                          |

**Note**: Boolean options such as `--filestat` can be specified as `yes`/`no`, `true`/`false`, or `1`/`0` in the config

### Additional Information for Options

#### Option: `minutely`, `hourly`, `daily`, `weekly`, `monthly`, `yearly`

- These options determine the number of backups to retain for each respective frequency
- You have the flexibility to provide an expression that will be evaluated to calculate a value. For example, using `--hourly=5+2` would result in 7
- Alternatively, you can specify "always" as the value to preserve all backups for that particular frequency

#### Option: `source`
There are currently three available sources, each functioning differently when scanning directories to find backups.

- `local`

This option is straightforward and doesn't really require any additional explanation. It is a simple method for locating backups

- `ssh`

To use this source, you need to configure the SSH config file (`~/.ssh/config`) with the relevant host information. It also supports aliases defined in the SSH config, as well as jump hosts

- `s3`

One thing to note is the `s3_endpoint_url` option. This lets you specify an endpoint other than the default to be able to use an alternative like DigitalOcean Spaces (i.e. `https://nyc3.digitaloceanspaces.com`)

#### Option: `path`

**Using Config File**

When `path` is used under the `[main]` section in config, it significantly alters Backup Warden's functionality. In this case, Backup Warden will traverse through every directory and file under the given path until it locates a backup. Once a backup is found, it associates the backup with a config section using `fnmatch` for pattern matching that defines its retention policy. If there isn't a config section that matches all possibilities of a path found, it's ignored. If `path` is not specified, Backup Warden will only scan the path defined in each config section.

Using the `path` option provides granular control over retention policies and allows for flexible path name conventions. It enables you to define custom retention rules based on very specific paths. 

**Using Parameters**

`--path` is the same as using `path` under `[main]` section in config.

**Note**: Specifying a `path` may result in a performance impact if there are a lot of non-backup directories/files within the specified path. This shouldn't be an issue though unless your setup is very abnormal. You can use `exclude_list` to help out if this is a scenario.

#### Option: `timestamp-pattern`

The `timestamp-pattern` option provides the flexibility to customize the regular expression used for extracting timestamps from filenames. The value for this option should be a Python-compatible regular expression that includes the named capture groups 'year', 'month', and 'day'. Additionally, it can optionally include the groups 'hour', 'minute', and 'second'. 'unixtime' is also supported (see below for how to use it)

Here is an example of the default regular expression:

```r
# Required components
(?P<year>\d{4} ) \D?
(?P<month>\d{2}) \D?
(?P<day>\d{2}  ) \D?
(?:
    # Optional components
    (?P<hour>\d{2}  ) \D?
    (?P<minute>\d{2}) \D?
    (?P<second>\d{2})?
)?
```

Regular expressions are compiled using the [re.VERBOSE](https://docs.python.org/3/library/re.html#re.VERBOSE) flag which ignores whitespace, including newlines.

If your backups utilize Unix timestamps instead of standard timestamps, you can specify a pattern like:

```r
(?P<unixtime>\d+)
```

#### Option: `filestat`

In cases where your backup files do not contain a timestamp, you have the option to use the last modified time of the backup instead. However, it is important to note that when utilizing this parameter, you will also need to modify the `timestamp-pattern` to accurately identify which directories/files are considered backups. For example, if all of your backups have filenames starting with "backup-", you would change the `timestamp-pattern` to `backup-\S+`.

If your backup file names are not standardized and do not follow a specific pattern, this feature is currently not supported.

#### Option: `relaxed`

Backup Warden offers the `--relaxed` option to modify its default rotation behavior. By default, Backup Warden enforces strict time windows for each rotation scheme. However, with the `--relaxed` option, you can relax this enforcement. Here's a clear explanation/example of the difference between strict and relaxed rotation:

- **Strict Rotation**: When the number of hourly backups to preserve is set to three, only backups created within the relevant time window (the hour of the most recent backup and the two hours leading up to it) will match the hourly frequency. Choose this option if your backups are created at regular intervals without any missed intervals

- **Relaxed Rotation**: With the `--relaxed` option enabled, the three most recent backups will all match the hourly frequency and be preserved, regardless of the calculated time window. Choose this option if your backups are created at irregular intervals, as it allows for the preservation of more backups

#### Option: `include-list`/`exclude-list`

These options utilize `fnmatch`, allowing the use of asterisks as wildcards. This enables precise definition of which backups should be excluded from deletion. Include and exclude can be used together for fine-grained control.

For example, to exclude the `cluster1` from Backup Warden's operations, you can use the `--exclude-list="*cluster1*"` argument. This ensures that any directories/files containing `cluster1` in their names will be excluded.

To further expand the exclusion criteria, you can exclude backups from the year 2022 by using `--exclude-list="*cluster1*, *2022*"`.

The same concept applies to the `exclude-list` option under each section in the config file:

```ini
[/path/backups/*/logical]
hourly = 72
daily = 7
weekly = 6
monthly = 12
yearly = always
include_list =
exclude_list = *cluster1*, *2022*
```

Include functions in the opposite manner. If you want to only include specific backups, you can utilize this feature. It can be used as a command-line argument using `--include-list`, or as the `include_list` option in a config path section.


## Installation & Execution
Must be using Python 3.8+

Using PyPi:
```shell
pip install backup-warden

backup-warden --config config/example.ini
```

Using Poetry:
```shell
curl -sSL https://install.python-poetry.org | python3 -

poetry install

poetry run backup-warden --config config/example.ini
```

## Configuration

Backup Warden offers two methods for setting it up: parameters and a config file. The recommended approach is to use a config file, which allows customization of directory paths and their respective retention policies. You can find examples of the config file [here](https://github.com/charles-001/backup-warden/tree/main/example_configs)

With a config file, each section represents a specific path containing backups to be rotated. Within each section, you can define the rotation scheme and other options. Please refer to the above information for detailed instructions on how to utilize pattern matching effectively when using the `path` option.

**Note**: If you specify a config file along with config path(s), command-line parameters will have no effect. The methods are not interchangeable.

Under the `[main]` section in the config file, you can set the following options:

- `bucket`
- `path`
- `source`
- `environment`
- `ssh_host`
- `ssh_sudo`
- `syslog`
- `log_file`
- `s3_endpoint_url`
- `s3_access_key_id`
- `s3_secret_access_key`
- `slack_webhook`

For each config `[path]` section, you can set the following options:

- `minutely`, `hourly`, `daily`, `weekly`, `monthly`, `yearly`
- `timestamp_pattern`
- `include_list`/`exclude_list`
- `filestat`
- `relaxed`
- `prefer_recent`
- `utc`

You can also set the following options using environment variables, which will override the corresponding config values:

- `S3_ENDPOINT_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `SLACK_WEBHOOK`

### Not using `path`

When the `path` parameter is omitted under the `[main]` section, Backup Warden does not accept wildcarding for config sections. In this scenario, Backup Warden will solely scan the specified config sections without traversing through additional directories.

This means that instead of scanning the entire file system or applying wildcards to match multiple paths, Backup Warden will focus solely on the directories specified within the config sections. It will not explore subdirectories or perform any recursive scanning.

By adhering to this behavior, Backup Warden provides a targeted approach, limiting the scope of its backup scanning and rotation operations to the explicitly defined directories within the config sections.

**Directory structure**
```shell
/path/backups/logical/$backups
/path/backups/physical/$backups
```

**Config**
```ini
[/path/backups/logical]
hourly = 15
daily = 3
weekly = 5
monthly = 12
yearly = always

[/path/backups/physical]
hourly = 10
daily = 7
weekly = 4 
monthly = 12
yearly = always
```
This is a basic setup and works as you expect.

### Using `path`

When the `path` option is used under the `[main]` section, Backup Warden allows wildcarding to be applied flexibly within the config sections.

By specifying the `path` option, you gain the ability to use wildcards to define the directories or files that Backup Warden should scan for backups. This enables a more dynamic and versatile approach. Backup Warden will effectively traverse through the specified paths, including subdirectories if necessary, to locate the backups based on the wildcard patterns provided.

**Directory structure**
```shell
/path/backups/cluster1/logical/$backups
/path/backups/cluster2/logical/$backups
/path/backups/cluster1/physical/$backups
/path/backups/cluster2/physical/$backups
```

**Config**
```ini
[main]
path=/path/backups

[/path/backups/*/logical]
hourly = 15
daily = 3
weekly = 5
monthly = 12
yearly = always

[/path/backups/*/physical]
hourly = 10
daily = 7
weekly = 4 
monthly = 12
yearly = always
```
Backup Warden's design incorporates hierarchical directory structure awareness, allowing for precise configuration and retention policies.

By defining `/path/backups/*/logical` as a config section, Backup Warden acknowledges the wildcard (`*`) as a placeholder that matches any subdirectory under `/path/backups/` and assigns it to the `logical` config section.

When a retention policy is set for a broader path, such as `path/backups`, it will not override or take precedence over a more specific path like `/path/backups/cluster1/logical`. Backup Warden's scanning and rotation operations respect the defined hierarchy, ensuring that retention policies are accurately applied to the corresponding backup directories without unintentionally affecting others.


## Alerting

Backup Warden offers a convenient Slack integration feature that allows you to stay informed about your backups if you specify a Slack Webhook URL. Benefit from the following alerts:

1. **Non-Backup Alert**: Get notified if a path doesn't have a backup in the past 24 hours
2. **Success Alert**: Receive notification after a successful execution, along with detailed statistics about what it did
3. **Failure Alert**: In case of a failed execution, be promptly notified to address any potential issues


## Functionality Overview

Backup Warden employs the following steps to carry out the backup rotation process:
1. **Specify Paths**: You need to provide a `path` and/or use config sections for paths to inform Backup Warden about the locations where the backups are stored
2. **Scan for Backups**: Backup Warden scans each specified path to locate backups. These backups can be in the form of either directories or files. Backup Warden identifies backups by searching for timestamps in their names. If you're using `filestat`, it will not look for a timestamp, but what you specify in place of it
3. **Apply Rotation Scheme**: Backup Warden applies the defined rotation scheme to the identified backups. If the outcome doesn't align with your expectations, you can experiment with the `relaxed` and/or `prefer-recent` options to achieve the desired behavior
4. **Backup Deletion**: Backups that are determined to be rotated based on the rotation scheme will be deleted if the `delete` option is passed. If it isn't, Backup Warden will skip the deletion step and preserve the rotated backups 


## Output Example
<img width="1598" alt="Screenshot 2023-07-01 at 3 50 57 AM" src="https://github.com/charles-001/backup-warden/assets/13244625/eda58941-605f-482a-8800-77f3a1086838">
