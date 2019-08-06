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

import argparse
import json
import os
import sys

from .bookmarks import write_bookmarks
from .config import accounts_with_role, conf
from .google import GoogleRoleManager
from .profiles import update_profiles


def handle_roles(args):
    """ Update the list of roles in the Google Directory against each user """
    mgr = GoogleRoleManager(conf['saml-provider-name'], conf['google']['delegate-email'])
    if args.all:
        print("Setting all roles in Google Directory based on configuration")
        for username, roles in conf['users'].items():
            user_roles = []
            for role in roles:
                if role in conf['roles'] and 'role-account' in conf['roles'][role]:
                    account_id = conf['accounts'][conf['roles'][role]['role_account']]['account-id']
                    user_roles.append({'role': role, 'account': conf['roles'][role]['role-account']})
                else:
                    account_id = conf['accounts'][conf['default-account']]['account-id']
                    user_roles.append({'role': role, 'account': account_id})
            print("{}: {}".format(username, ", ".join(["{}/{}".format(role['account'], role['role']) for role in user_roles])))
            mgr.set_roles(username, user_roles)
    else:
        if args.email is None:
            results = mgr.get_roles()
            for email, roles in results.items():
                if roles:
                    print('{0:<30} {1}'.format(email, ", ".join(roles)))
        else:
            if len(args.roles) > 0:
                print("Setting roles to: {}".format(args.roles))
                mgr.set_roles(args.email, args.roles)
            else:
                roles = mgr.get_roles()[args.email]
                print("\n".join(roles))


def get_profiles_for(email):
    chosen = set()
    # Parse account/role_arn for each profile of the roles a user has access to 
    for role in conf['users'][email]:
        if role in conf['roles'] and 'assume-profiles' in conf['roles'][role]:
            for profile in conf['roles'][role]['assume-profiles']:
                account = profile['account']
                role = profile['role']
                if account == '*':
                    for account_name in accounts_with_role(role):
                        chosen.add((account_name, role))
                else:
                    chosen.add((account, role))

    default_region = conf['default-region']
    profiles = []
    for profile in chosen:
        account = profile[0]
        role = profile[1]
        account_id = conf['accounts'][account]['account-id']
        role_arn = "arn:aws:iam::{}:role/{}".format(account_id, role)
        region = conf['accounts'][account].get('region', default_region)
        profiles.append(dict(
            name="{}-{}".format(account, role),
            account=account,
            role=role,
            role_arn=role_arn,
            account_id=account_id,
            region=region,
        ))
    return profiles


def handle_profiles(args):
    """ Update the user's aws config / credentials to match the profiles available to them """
    profiles = get_profiles_for(args.email)
    config = update_profiles(profiles, args.replace, not args.dry_run)
    if args.dry_run:
        # print config
        config.write(sys.stdout)


def handle_bookmarks(args):
    """ Generate a bookmarks file for import into a browser """
    profiles = get_profiles_for(args.email)
    idpid = conf['google']['idpid']
    spid = conf['google']['spid']
    write_bookmarks(profiles, args.filename, idpid, spid)


def handle_schema(args):
    mgr = GoogleRoleManager(conf['saml-provider-name'], conf['google']['delegate-email'])
    customerId = conf['google']['idpid']
    results = mgr.service.schemas().list(customerId=conf['google']['idpid']).execute()
    print(json.dumps(results, sort_keys=True, indent=4))


def main():
    email = os.environ.get('GOOGLE_USERNAME', None)
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers()

    roles = subparsers.add_parser('roles')
    roles.add_argument('-a', '--all', action='store_true', help="Set all roles")
    roles.add_argument('email', nargs='?')
    roles.add_argument('roles', nargs='*')
    roles.set_defaults(func=handle_roles)

    profiles = subparsers.add_parser('profiles')
    profiles.add_argument('-r', '--replace', action='store_true', help="Replace all existing AWS profiles with managed roles")
    profiles.add_argument('--dry-run', action='store_true', help="Display what config would be written, but don't write it to file")
    if email is None:
        profiles.add_argument('email', help="Your email address")
    profiles.set_defaults(email=email, func=handle_profiles)

    bookmarks = subparsers.add_parser('bookmarks')
    bookmarks.add_argument('-f', '--filename', default='-', help="Filename to write to (use - for stdout)")
    if email is None:
        bookmarks.add_argument('email', help="Your email address")
    bookmarks.set_defaults(email=email, func=handle_bookmarks)

    schema = subparsers.add_parser('schema')
    schema.set_defaults(func=handle_schema)

    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
    else:
        args.func(args)
