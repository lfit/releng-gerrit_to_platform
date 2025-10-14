# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Configuration subsystem."""

import configparser
import os.path
import re
from configparser import ConfigParser, NoOptionError
from enum import Enum
from typing import Dict, Optional, TypedDict, Union

from xdg import XDG_CONFIG_HOME

# CONSTANTS
CONFIG = "config"
REPLICATION = "replication"
DEFAULT_CONFIG = CONFIG


# Type Definitions
class Remote(TypedDict):
    """Remote Dictionary definition."""

    owner: str
    remotenamestyle: str
    repo: str


PlatformType = Dict[str, Remote]


class ReplicationRemotes(TypedDict, total=False):
    """Platform Dictionary definition."""

    github: PlatformType
    gitlab: PlatformType


class Platform(Enum):
    """Enumeration of all platforms recognized by the app."""

    GITHUB = "github"
    GITLAB = "gitlab"


G2P_CONFIG_FILE = os.path.join(
    XDG_CONFIG_HOME, "gerrit_to_platform", "gerrit_to_platform.ini"
)

GERRIT_REPLICATION_CONFIG = os.path.join(
    XDG_CONFIG_HOME, "gerrit_to_platform", "replication.config"
)

CONFIG_FILES = {
    CONFIG: G2P_CONFIG_FILE,
    REPLICATION: GERRIT_REPLICATION_CONFIG,
}


def get_config(config_type: str = DEFAULT_CONFIG) -> ConfigParser:
    """
    Get the config object.

    Args:
        config_type (str): Type of configuration file that the parser should use

    Returns:
        ConfigParser: A loaded ConfigParser object with the requested
            configuration file
    """
    config = configparser.ConfigParser()
    conf_file = CONFIG_FILES[config_type]
    with open(conf_file) as config_file:
        config.read_file(config_file, conf_file)
    return config


def get_mapping(mapping_section: str) -> Union[Dict[str, str], None]:
    """
    Return all of the keyword to job mappings

    Args:
        mapping_section (str): the section of the config file to load

    Returns:
        Optional(Dict[str,str]): The key / value mapping object or None if it
            does not exist
    """
    config = get_config()

    section = f'mapping "{mapping_section}"'
    if section in config.sections():
        return dict(config.items(section))

    return None


def get_replication_remotes() -> ReplicationRemotes:
    """
    Get the replication remotes available.

    Returns:
        ReplicationRemotes: All the replication remotes defined the Gerrit
            configuration file
    """
    remotes_config = get_config(REPLICATION)
    remotes: ReplicationRemotes = {}

    for section in remotes_config.sections():
        if 'remote "' not in section:
            continue

        subsect = r'"(.*)"'
        subsection = re.findall(subsect, section)[0]
        url = remotes_config.get(section, "url")
        try:
            authgroup = remotes_config.get(section, "authgroup")
        except NoOptionError:
            authgroup = ""
        try:
            namestyle = remotes_config.get(section, "remotenamestyle")
        except NoOptionError:
            namestyle = "slash"

        if (
            "github" in section.lower()
            or "github" in subsection.lower()
            or "github" in authgroup.lower()
        ):
            platform_type = Platform.GITHUB.value
        elif (
            "gitlab" in section.lower()
            or "gitlab" in subsection.lower()
            or "gitlab" in authgroup.lower()
        ):
            platform_type = Platform.GITLAB.value
        else:
            continue

        url_regex = r":(.*)/(.*)$"
        owner, repo = re.findall(url_regex, url)[0]

        if platform_type in remotes.keys():
            remotes[platform_type][subsection] = {  # type: ignore
                "owner": owner,
                "remotenamestyle": namestyle,
                "repo": repo,
            }
        else:
            remotes[platform_type] = {  # type: ignore
                subsection: {
                    "owner": owner,
                    "remotenamestyle": namestyle,
                    "repo": repo,
                }
            }

    return remotes


def has_section(section: str) -> bool:
    """
    Indicate if section exists in config file.

    Args:
        section (str): config section to lookup

    Returns:
        bool: True if the section exists in configuration, False otherwise
    """
    config = get_config()
    return config.has_section(section)


def get_setting(section: str, option: Optional[str] = None) -> Union[list, str]:
    """
    Get all configuration options from a section, or specific option from a
    section.

    Args:
        section (str): config section to use
        option (Optional[str]): a suboption to get from the section

    Returns:
        list: all of the configuration for a section
        str: the single sub-option of a section
    """
    config = get_config()

    if option:
        return config.get(section, option)

    return config.options(section)


def get_boolean_setting(section: str, option: str, fallback: bool = False) -> bool:
    """
    Get a boolean configuration option from a section.

    Args:
        section (str): config section to use
        option (str): the option to get from the section
        fallback (bool): default value if option doesn't exist

    Returns:
        bool: the boolean value of the option, or fallback if not found
    """
    config = get_config()

    try:
        return config.getboolean(section, option)
    except (NoOptionError, configparser.NoSectionError):
        return fallback


def get_project_workflow_filter(project: str, event_type: str) -> Optional[str]:
    """
    Get workflow filter for a specific project and event type.

    Checks configuration for project-specific workflow filters that narrow
    down which workflow to trigger for a given event type.

    Args:
        project (str): Gerrit project name (e.g., "releng/builder")
        event_type (str): Event type ("verify" or "merge")

    Returns:
        str: workflow filter (e.g., "packer") if configured
        None: no filter configured for this project/event combination

    Example:
        >>> get_project_workflow_filter("releng/builder", "verify")
        'packer'  # From config: [project "releng/builder"] verify_filter = packer
    """
    try:
        config = get_config()
        section = f'project "{project}"'

        if not config.has_section(section):
            return None

        option = f"{event_type}_filter"
        return config.get(section, option)
    except (configparser.NoOptionError, configparser.NoSectionError):
        return None
