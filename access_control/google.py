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

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


class GoogleRoleManager:

    SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']
    SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), '..', 'service_credentials.json')

    def __init__(self, provider, prefix, delegate_email):
        self.creds = None
        self.provider = provider
        self.prefix = prefix
        self.creds = service_account.Credentials.from_service_account_file(self.SERVICE_ACCOUNT_FILE,
                                                                           scopes=self.SCOPES)
        if not self.creds.valid:
            self.creds.refresh(Request())

        delegated_creds = self.creds.with_subject(delegate_email)
        self.service = build('admin', 'directory_v1', credentials=delegated_creds)

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
