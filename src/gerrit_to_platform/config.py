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
from configparser import ConfigParser

from xdg import XDG_CONFIG_HOME

G2P_CONFIG_FILE = os.path.join(
    XDG_CONFIG_HOME, "gerrit_to_platform", "gerrit_to_platform.ini"
)


def get_config() -> ConfigParser:
    """Get the config object."""
    config = configparser.ConfigParser()
    with open(G2P_CONFIG_FILE) as config_file:
        config.read_file(config_file, G2P_CONFIG_FILE)
    return config
