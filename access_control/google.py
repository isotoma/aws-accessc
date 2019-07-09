from __future__ import print_function

import os
import sys

from apiclient.discovery import build
from httplib2 import Http
from oauth2client import client, file, tools


class GoogleRoleManager:

    SCOPES = 'https://www.googleapis.com/auth/admin.directory.user'
    token_file = os.path.expanduser('~/.google_token.json')
    creds_file = os.path.join(os.path.dirname(__file__), '..', 'google_credentials.json')

    def __init__(self, provider, prefix):
        self.provider = provider
        self.prefix = prefix
        self.store = file.Storage(self.token_file)
        if os.path.exists(self.token_file):
            self.creds = self.store.get()
            if not self.creds or self.creds.invalid:
                self.authenticate()
        else:
            self.authenticate()
        self.service = build('admin', 'directory_v1', http=self.creds.authorize(Http()))

    def authenticate(self):
        flow = client.flow_from_clientsecrets(self.creds_file, self.SCOPES)
        # run_flow is quite weird and does things to argv
        old_args = sys.argv
        sys.argv = sys.argv[:1]
        self.creds = tools.run_flow(flow, self.store)
        sys.argv = old_args

    def get_roles_for_user(self, user):
        if 'customSchemas' not in user:
            return []
        else:
            return [x['customType'] for x in user['customSchemas']['SSO']['role']]

    def _get_all_roles(self):
        results = self.service.users().list(
            customer='my_customer',
            maxResults=100,
            orderBy='email', 
            projection="full"
        ).execute()
        users = results.get('users', [])
        for user in users:
            roles = self.get_roles_for_user(user)
            yield user['primaryEmail'], roles

    def get_roles(self):
        return dict(self._get_all_roles())

    def role_to_schema(self, role):
        return {
            'value':  "{}/{},{}".format(self.prefix, role, self.provider),
            'customType': role
        }

    def set_roles(self, username, roles):
        customSchemas = {
            'customSchemas': {
                'SSO': {
                    'role': list(map(self.role_to_schema, roles)),
                    'SessionDuration': 43200,
                }
            }
        }
        results = self.service.users().patch(userKey=username, body=customSchemas).execute()
        return results
