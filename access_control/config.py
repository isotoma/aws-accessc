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

import yaml

config_pathname = os.path.join(os.path.dirname(__file__), '..', 'roles.yaml')

with open(config_pathname) as f:
    conf = yaml.load(f, Loader=yaml.FullLoader)


def accounts_with_role(role_name):
    """ Return the list of account names that have a role or managed role with the specified name """

    for name, a in conf['accounts'].items():
        if role_name in a.get('roles', []) or role_name in [x['name'] for x in a.get('managed-roles', [])]:
            yield name
