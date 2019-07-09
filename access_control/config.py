import os

import yaml

config_pathname = os.path.join(os.path.dirname(__file__), '..', 'roles.yaml')

with open(config_pathname) as f:
    conf = yaml.load(f)


def accounts_with_role(role_name):
    """ Return the list of account names that have a role or managed role with the specified name """

    for name, a in conf['accounts'].items():
        if role_name in a.get('roles', []) or role_name in [x['name'] for x in a.get('managed-roles', [])]:
            yield name
