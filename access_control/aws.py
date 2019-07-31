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

from awacs.aws import (Action, Allow, Condition, Policy, Principal, Statement,
                       StringEquals)
from awacs.sts import AssumeRole, AssumeRoleWithSAML
from troposphere.iam import Policy as IAMPolicy
from troposphere.iam import Role

from .config import accounts_with_role, conf


def camel_case(snake_case):
    """ Convert hyphenated snake-case into capitalised CamelCase """
    parts = snake_case.split("-")
    return "".join(map(lambda x: x.capitalize(), parts))


def awacs_actions(literals):
    for s in literals:
        prefix, action = s.split(':')
        yield Action(prefix, action)


def environment_policy(name, actions, regions):
    if regions:
        for region in regions:
            yield IAMPolicy(
                PolicyName="{}@{}".format(name, region),
                PolicyDocument=Policy(
                    Statement=[Statement(
                        Effect=Allow,
                        Action=actions,
                        Resource=["*"],
                        Condition=Condition(
                            StringEquals({
                                'aws:RequestedRegion': region,
                            })
                        )
                    )]
                ))
    else:
        yield IAMPolicy(
            PolicyName=name,
            PolicyDocument=Policy(
                Statement=[Statement(
                    Effect=Allow,
                    Action=actions,
                    Resource=["*"],
                )]
            )
        )


def make_environment_role(name, regions=[]):
    role = conf['environment-roles'][name]
    arns = role.get('policies', [])

    if 'allow' in role:
        actions = list(awacs_actions(role['allow']))
        policy = list(environment_policy(name, actions, regions))
    else:
        policy = []

    return Role(
        name,
        RoleName=name,
        ManagedPolicyArns=arns,
        Policies=policy,
        MaxSessionDuration=43200,
        AssumeRolePolicyDocument=Policy(
            Statement=[
                Statement(
                    Effect=Allow,
                    Principal=Principal(
                        "AWS",
                        "arn:aws:iam::{}:root".format(conf['master-aws-account'])
                    ),
                    Action=[AssumeRole]
                )
            ]
        ),
    )


def make_role(role_name):
    arns = []
    role = conf['roles'][role_name]

    if 'profiles' in role:
        for profile in role['profiles']:
            account = profile['account']
            dest_role = profile['role']
            if account == '*':
                accounts = accounts_with_role(dest_role)
                for account in accounts:
                    account_id = conf['accounts'][account]['account']
                    arns.append("arn:aws:iam::{}:role/{}".format(account_id, dest_role))
            else:
                account_id = conf['accounts'][account]['account']
                arns.append("arn:aws:iam::{}:role/{}".format(account_id, dest_role))

    if arns:
        policy = [IAMPolicy(
            PolicyName=role_name,
            PolicyDocument=Policy(
                Statement=[Statement(
                    Effect=Allow,
                    Action=[AssumeRole],
                    Resource=arns,
                )]
            )
        )]
    else:
        policy = []

    arns = role['policies'] if 'policies' in role else []

    return Role(
        role_name,
        RoleName=role_name,
        ManagedPolicyArns=arns,
        Policies=policy,
        MaxSessionDuration=43200,
        AssumeRolePolicyDocument=Policy(
            Statement=[
                Statement(
                    Effect=Allow,
                    Principal=Principal(
                        "Federated",
                        conf['saml-provider'],
                    ),
                    Action=[AssumeRoleWithSAML],
                    Condition=Condition(
                        StringEquals({
                            "SAML:aud": "https://signin.aws.amazon.com/saml"
                        })
                    )
                )
            ]
        ),
    )
