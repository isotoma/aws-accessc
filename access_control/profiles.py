# Copyright (C) 2019 Isotoma Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


def backup(path):
    with open("{}.old".format(path), 'w') as dest:
        with open(path) as source:
            dest.write(source.read())


def update_profiles(profiles):
    config_path = os.path.expanduser('~/.aws/config')
    config = ConfigParser()
    if os.path.exists(config_path):
        backup(config_path)
        config.read(config_path)
    for profile in profiles:
        name = "profile {}".format(profile['name'])
        if not config.has_section(name):
            config.add_section(name)

        config.set(name, 'role_arn', profile['role_arn'])
        config.set(name, 'source_profile', 'default')
        config.set(name, 'region', profile['region'])

    with open(config_path, 'w') as out:
        config.write(out)
