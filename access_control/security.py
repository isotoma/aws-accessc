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

import yaml
from awacs import s3, sns, sts
from awacs.aws import (Allow, Condition, Policy, PolicyDocument, Principal,
                       Statement, StringEquals)
from troposphere import Parameter, Ref, Sub
from troposphere.cloudtrail import Trail
from troposphere.config import (AggregationAuthorization, ConfigRule,
                                ConfigurationRecorder, DeliveryChannel,
                                RecordingGroup, Scope, Source)
from troposphere.iam import Role
from troposphere.s3 import Bucket, BucketPolicy
from troposphere.sns import Topic, TopicPolicy

import inflection

aws_rules = yaml.load(open('rules.yaml'), Loader=yaml.FullLoader)
roles = yaml.load(open('../AccessControl/roles.yaml'), Loader=yaml.FullLoader)


def ac_subs():
    for account in roles['accounts'].values():
        yield Sub("${AuditBucket.Arn}/AWSLogs/%s/*" % (account['account'],))


class TemplateGenerator:

    awscloudtrail = Principal('Service', 'cloudtrail.amazonaws.com')
    awsconfig = Principal('Service', 'config.amazonaws.com')

    def __init__(self, rules=[], security=False, central=False, aggregated=False, cloudtrail=True, config=True):
        self.security = security
        self.central = central
        self.aggregated = aggregated
        self.cloudtrail = cloudtrail
        self.config = config
        self.parse_rules(rules)

    def parse_rules(self, rules):
        self.rules = []
        for rule_data in rules:
            if type(rule_data) == type({}):  # noqa
                rule_name = rule_data.pop('name')
                args = rule_data
            else:
                rule_name = rule_data
                args = {}
            rule = aws_rules[rule_name].copy()
            rule['name'] = rule_name
            rule['args'] = args
            self.rules.append(rule)

    def gen_bucket(self):
        if self.central and self.security:
            ac_resources = [Sub("${AuditBucket.Arn}/AWSLogs/${AWS::AccountId}/*")]
            ac_resources.extend(ac_subs())
            self.AuditBucket = Bucket("AuditBucket", BucketName="isotoma-audit")
            self.AuditBucketPolicy = BucketPolicy(
                "AuditBucketPolicy",
                Bucket=Ref(self.AuditBucketName),
                PolicyDocument=PolicyDocument(
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Effect="Allow",
                            Principal=self.awscloudtrail,
                            Action=[s3.GetBucketAcl],
                            Resource=[Sub("${AuditBucket.Arn}")]
                        ),
                        Statement(
                            Effect="Allow",
                            Principal=self.awscloudtrail,
                            Action=[s3.PutObject],
                            Resource=ac_resources,
                            Condition=Condition(
                                StringEquals({'s3:x-amz-acl': 'bucket-owner-full-control'})
                            )
                        ),
                        Statement(
                            Effect="Allow",
                            Principal=self.awsconfig,
                            Action=[s3.GetBucketAcl],
                            Resource=[Sub("${AuditBucket.Arn}")]
                        ),
                        Statement(
                            Effect="Allow",
                            Principal=self.awsconfig,
                            Action=[s3.PutObject],
                            Resource=ac_resources,
                            Condition=Condition(
                                StringEquals({'s3:x-amz-acl': 'bucket-owner-full-control'})
                            )
                        )]))
            yield self.AuditBucket
            yield self.AuditBucketPolicy

    def gen_topic(self):
        if self.security:
            self.AuditTopic = Topic(
                "AuditTopic",
                TopicName=Ref(self.AuditTopicName)
            )
            self.AuditTopicPolicy = TopicPolicy(
                "AuditTopicPolicy",
                PolicyDocument=PolicyDocument(
                    Id="AuditTopicPolicy",
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Sid="AllowCloudTrail",
                            Effect="Allow",
                            Principal=self.awscloudtrail,
                            Action=[sns.Publish],
                            Resource=["*"]
                        ),
                        Statement(
                            Sid="AllowConfig",
                            Effect="Allow",
                            Principal=self.awsconfig,
                            Action=[sns.Publish],
                            Resource=["*"]
                        ),
                    ],
                ),
                Topics=[Sub("${AuditTopic}")],
            )
            yield self.AuditTopic
            yield self.AuditTopicPolicy

    def gen_config_recorder(self):
        # we create the role for the security account
        # and for the one-and-only-one aggregation region
        if self.aggregated or (self.security and self.central):
            self.ConfigRecorderRole = Role(
                "ConfigRecorderRole",
                RoleName="ConfigRecorder",
                ManagedPolicyArns=['arn:aws:iam::aws:policy/service-role/AWSConfigRole'],
                AssumeRolePolicyDocument=Policy(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Principal=self.awsconfig,
                            Action=[sts.AssumeRole],
                        )
                    ],
                ),
                Path='/',
            )
            yield self.ConfigRecorderRole
        self.ConfigRecorder = ConfigurationRecorder(
            'ConfigRecorder',
            RoleARN=Sub("arn:aws:iam::${AWS::AccountId}:role/ConfigRecorder"),
            RecordingGroup=RecordingGroup(
                AllSupported=True,
                IncludeGlobalResourceTypes=True,
            ))
        depends = []
        if self.security and self.central:
            depends.append("AuditBucketPolicy")
        if self.aggregated:
            depends.append("ConfigRecorderRole")
        if depends:
            self.ConfigRecorder.DependsOn = depends
        yield self.ConfigRecorder
        self.DeliveryChannel = DeliveryChannel(
            "DeliveryChannel",
            Name="default",
            S3BucketName=Ref(self.AuditBucketName),
            SnsTopicARN=Sub("arn:aws:sns:${AWS::Region}:${AggregationAccount}:${AuditTopicName}"),
        )
        yield self.DeliveryChannel

    def parameters(self):
        self.AggregationAccount = Parameter("AggregationAccount", Type="String")
        yield self.AggregationAccount
        self.AggregationRegion = Parameter("AggregationRegion", Type="String")
        yield self.AggregationRegion
        self.AuditBucketName = Parameter("AuditBucketName", Type="String")
        yield self.AuditBucketName
        self.AuditTopicName = Parameter("AuditTopicName", Type="String")
        yield self.AuditTopicName

    def resources(self):
        for resource in self.gen_bucket():
            yield resource
        for resource in self.gen_topic():
            yield resource
        if self.cloudtrail:
            yield Trail(
                "Trail",
                DependsOn=["AuditBucket", "AuditBucketPolicy"] if self.security and self.central else [],
                S3BucketName=Ref(self.AuditBucketName),
                EnableLogFileValidation=True,
                IncludeGlobalServiceEvents=True,
                IsMultiRegionTrail=True,
                IsLogging=True,
            )
        if self.config:
            for resource in self.gen_config_recorder():
                yield resource
            for rule in self.rules:
                resource_name = inflection.camelize(rule['source'].lower()) + "Rule"
                resource = ConfigRule(
                    resource_name,
                    DependsOn="ConfigRecorder",
                    ConfigRuleName=rule['name'],
                    Description=rule['description'],
                    Source=Source(Owner='AWS', SourceIdentifier=rule['source'])
                )

                if rule['scope']:
                    resource.properties['Scope'] = Scope(
                        ComplianceResourceTypes=rule['scope'],
                    )
                if rule['args'] is not None:
                    resource.properties['InputParameters'] = rule['args']
                yield resource
            if self.aggregated:
                yield AggregationAuthorization(
                    "Authorization",
                    AuthorizedAccountId=Ref("AggregationAccount"),
                    AuthorizedAwsRegion=Ref("AggregationRegion"),
                )
