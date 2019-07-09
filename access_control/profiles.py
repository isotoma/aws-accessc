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
