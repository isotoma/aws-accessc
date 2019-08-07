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

import json

import os

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleRoleManager:

    SCOPES = [
        'https://www.googleapis.com/auth/admin.directory.user',
        'https://www.googleapis.com/auth/admin.directory.userschema',
    ]
    SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), '..', 'service_credentials.json')

    def __init__(self, provider_name, delegate_email):
        self.provider_name = provider_name
        self.creds = None
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

    def role_to_schema(self, user_role):
        provider = "arn:aws:iam::{}:saml-provider/{}".format(user_role['account'], self.provider_name)
        role = "arn:aws:iam::{}:role/{}".format(user_role['account'], user_role['role'])
        return {
            'value':  "{},{}".format(role, provider),
            'customType': user_role['role']
        }

    def set_roles(self, username, user_roles):
        customSchemas = {
            'customSchemas': {
                'SSO': {
                    'role': list(map(self.role_to_schema, user_roles)),
                    'duration': 43200
                }
            }
        }
        print("Adding role for {}".format(username))
        results = self.service.users().patch(userKey=username, body=customSchemas).execute()
        return results
