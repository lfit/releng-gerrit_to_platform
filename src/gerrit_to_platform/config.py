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
    """Get the config object."""
    config = configparser.ConfigParser()
    conf_file = CONFIG_FILES[config_type]
    with open(conf_file) as config_file:
        config.read_file(config_file, conf_file)
    return config


def get_replication_remotes() -> ReplicationRemotes:
    """Get the replication remotes available."""
    remotes_config = get_config(REPLICATION)
    remotes: ReplicationRemotes = {}

    for section in remotes_config.sections():
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
    """Indicate if section exists in config file."""
    config = get_config()
    return config.has_section(section)


def get_setting(section: str, option: Optional[str] = None) -> Union[list, str]:
    """Get all configuration options from a section, or specific option from a section."""
    config = get_config()

    if option:
        return config.get(section, option)

    return config.options(section)
