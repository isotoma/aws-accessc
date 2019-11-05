# aws-accessc
Accessc is a command-line tool that lets you manage mappings between federated logins and roles in AWS. It also generates AWS config profiles for individuals users and a set of bookmarklets for easy access to roles in the AWS console.

## Access and profiles for end users
Currently only Google is supported as a SAML identity provider (IdP).

### Federated access setup
For command line access, install [aws-google-auth](https://github.com/cevoaustralia/aws-google-auth) in your login environment, e.g.:

`sudo pip install aws-google-auth`

Add the details of your google SAML account to your environment (your admin will be able to supply you with the IdP ID and SP ID):

```bash
export GOOGLE_USERNAME=<YOUR_GOOGLE_EMAIL>
export GOOGLE_IDP_ID=<YOUR_IDP_ID>
export GOOGLE_SP_ID=<YOUR_SP_ID>
export AWS_DEFAULT_REGION=<YOUR_AWS_REGION>
export DURATION=43200
alias aws-auth='aws-google-auth -p default'
```

This will setup an alias `aws-auth` which will store these details in your default AWS profile upon logging in, and set the expiry of your access to 12 hours (this expiry must be increased from the default of 1 hour by your AWS admin for each login role you use). See the [aws-google-auth](https://github.com/cevoaustralia/aws-google-auth) documentation for additional details about that tool.

To authenticate to AWS with your Google login from the command line run:

```bash
aws-auth
```

Enter your Google password, complete a captcha if this is your first login, and any 2FA steps. You will be offered a list of the login roles in AWS you have access to. It is a good idea to use the least priveleged role for the tasks you have in mind.

### Generating AWS profiles

First you will need to install `accessc` - currently this has to be done from source. Make sure that whatever environment you run it in has been setup for federated access as above. (Make sure you have [pipenv](https://github.com/pypa/pipenv) installed in your environment also).

```bash
git clone git@github.com:isotoma/aws-accessc.git
cd aws-accessc
pipenv install
```

and to spawn a shell environment to use the tool:

```bash
pipenv shell
```

You will need to obtain a `roles.yaml` file from your admin that specifies the AWS accounts and roles you will have access to. This also specifies which of these account roles you can assume from each login role. The account roles will be added to your AWS config as profiles when you run `accessc profiles`. It should look something like this:

```yaml
saml-provider-name: GoogleApps
default-region: <YOUR_AWS_REGION>
default-account: 'my-aws-account'

google:
  idpid: <YOUR_IDP_ID>
  spid: <YOUR_SP_ID>

accounts:
  my-aws-account: 
    account-id: '1234567890'
    regions:
    - us-west-1
    - eu-west-2

  my-other-aws-account:
    account-id: '9876543210'
    regions:
    - eu-west-1

roles:
  Root:
    assume-profiles:
    - account: my-aws-account
      role: root
    - account: my-other-aws-account
      role: root
  Developer:
    assume-profiles:
    - account: my-other-aws-account
      role: developer

users:
  <YOUR_GOOGLE_EMAIL>:
  - Developer
```

Here, you would have access to the `Developer` login role, which would let you assume the `developer` role in the secondary account. The login role gets added to your profile by running `aws-auth` and logging in as above. To add the roles you can assume as additional profiles run:

```bash
accessc profiles
```

This will add any profiles to your aws config (located at `~/.aws/config`) if they don't already exist. If you wish to replace all existing profiles use the `-r` or `--replace` options, and if you want to print out what your config would be without updating it use the `-d` or `--dry-run` options.

You can use the `AWS_PROFILE` environment variable to select a profile as usual.

### Generating bookmarks

You can also use `accessc` to generate HTML bookmarks which will include a login link to AWS via your IdP auth (Google), and bookmarklets for each role you can assume, which will switch to that role in the AWS console. These links will be grouped by account, but which ones you can actual use to switch in practice will be restricted by the login role you choose. You should refer to your `roles.yaml` file or ask your admin for more details.

To generate bookmarks:

```bash
accessc bookmarks > ~/bookmarks.html
```

The HTML will be printed on standard out and can be redirected to a file of your choice, in this example `~/bookmarks.html`. This can then be imported into your web browser and then the AWS folder moved to your bookmarks toolbar.

To use bookmarks to access the AWS console:

1. Go to AWS &rightarrow; AWS Login in your bookmarks toolbar.
2. Select the login role to access the AWS console as. It is a good idea to use the least priveleged role for the tasks you have in mind.
3. If you need switch to a different role, go to the AWS folder in your bookmarks toolbar and select the role to switch to.
4. To return to your login Role, click on the role name in the AWS console and then `Back to <YOUR_LOGIN_ROLE>`. 


## Adding roles to a Google G Suite directory

### Configure SSO via SAML from G Suite to AWS

In order to use Google logins to authenticate with AWS, you must set up G Suite (formerly Google Apps) as a SAML identity provider in AWS, and make changes to the schema of the directory that G Suite uses for user management. There is configuration needed on both the Google end and AWS end, and the following references will help you set them up:

* [How to Set Up Federated Single Sign-On to AWS Using Google Apps](https://aws.amazon.com/blogs/security/how-to-set-up-federated-single-sign-on-to-aws-using-google-apps/)
* [Using Google Apps SAML SSO to do one-click login to AWS](https://blog.faisalmisle.com/2015/11/using-google-apps-saml-sso-to-do-one-click-login-to-aws/)
* [Set up SSO via SAML for Amazon Web Services](https://support.google.com/a/answer/6194963)

Note that to be able to customise the duration of a login session, the custom attributes in the schema of the Google directory needs an additional field. Instead of the JSON used in the above guides, use this instead:

```json
{
  "fields": 
  [
    {
      "fieldName": "role",
      "fieldType": "STRING",
      "readAccessType": "ADMINS_AND_SELF",
      "multiValued": true
    },
    {
      "fieldName": "duration",
      "fieldType": "INT64",
      "readAccessType": "ADMINS_AND_SELF",
    }
  ],
  "schemaName": "SSO"
}
```

The schema setup is planned to be added to the `accessc` tool in the future.

### Create authentication credentials for accessc to use Google Directory API

In order to make changes to the user directory in G Suite, `accessc` authenticates itself using a Service Account in the Google APIs console for your GSuite domain. This uses "delegated access", so you will need a G Suite admin to authorise the specific APIs that the application needs to use, and add the email of an admin to your `roles.yaml` configuration.

First go to the [Google developers console](https://console.developers.google.com) and create a new project, and create an IAM service account in that project - see https://cloud.google.com/iam/docs/creating-managing-service-accounts. To download the credentials for `accessc` to use, make sure you click on `Create Key` in the service account details, select JSON format, download and rename this `service_credentials.json`. This file needs to be placed in the root directory of the this project to enable API access for the tool. Make sure that domain-wide delegation is aenabled on the account (see instructions below).

To allow the service account to access the directory API, you need to enable delegation of authority in the G Suite admin console. This must be done by an admin user. For instructions see [https://developers.google.com/admin-sdk/directory/v1/guides/delegation](https://developers.google.com/admin-sdk/directory/v1/guides/delegation). The client name field should match the ID of the service account, and the API scopes to add are `'https://www.googleapis.com/auth/admin.directory.user','https://www.googleapis.com/auth/admin.directory.userschema'`.

### Create `roles.yaml` configuration file

You now need to create a `roles.yaml` configuration file like the one shown in the AWS profiles section above. Each section of this file is explained below.

#### Preamble

```yaml
saml-provider-name: GoogleApps
default-region: 'us-west-1'
default-account: 'my-aws-account'
```

<dl>
<dt>saml-provider-name</dt>
<dd>The name of the SAML IdP in your AWS account.</dd>
<dt>default-region</dt>
<dd>The AWS region of the default profile.</dd>
<dt>default-account</dt>
<dd>The account where login roles are located if not otherwise specified. A typical setup might have all login roles in one account (this one), and all additional roles are assumed in other accounts.</dd>
</dl>

#### Google SAML configuration

```yaml
google:
  idpid: C53flrny8
  spid: '123456789'
  delegate-email: 'admin@yourdomain.com'
```

<dl>
<dt>idpid</dt>
<dd>The IdP ID of the G Suite domain (same as the customer ID).</dd>
<dt>spid</dt>
<dd>The Service Provider ID of the AWS SAML App. This can be found in the url of the service config.</dd>
<dt>delegate-email</dt>
<dd>The email of a G Suite admin user whose permissions are delegate to the tool for API access. The tool itself can only access APIs specified in the `scopes` field of the delegation setup.</dd>
</dl>

#### AWS accounts

```yaml
accounts:
  my-aws-account: 
    account-id: '1234567890'
    regions:
    - us-west-1
    - eu-west-2

  my-other-aws-account:
    account-id: '9876543210'
    regions:
    - eu-west-1
```

These accounts are referenced by name elsewhere in the configuration.

<dl>
<dt>account-id</dt>
<dd>The numeric id of the AWS account (used to construct role ARNs).</dd>
<dt>regions</dt>
<dd>The regions in which to create roles and profiles for this account.</dd>
</dl>

#### AWS role definitions

```yaml
roles:
  Root:
    assume-profiles:
    - account: my-aws-account
      role: root
    - account: my-other-aws-account
      role: root
  Developer:
    assume-profiles:
    - account: my-other-aws-account
      role: developer
```

Login roles are referenced by name in role mappings. 

<dl>
<dt>assume-profiles</dt>
<dd>Roles that the login role can assume that will added as profiles to the AWS config of users with the login role</dd>
<dt>account</dt>
<dd>Reference to an account in the `accounts` section of `roles.yaml`.<dd>
<dt>role</dt>
<dd>The name of a role in that account</dd>
</dl>

#### User role mapping

```yaml
users:
  user@yourdomain.com:
  - Developer
```

Each user is identified by Google login email, and has a list of login roles referencing definitions in the `roles` section of `roles.yaml`.

### Setting user roles using `acccessc`

*NB: All the following commands need the `service_credentials.json` file and a delegate email set in `roles.yaml`.*

To list all existing role mappings:

```bash
accessc roles
```

To set roles for all users as per `roles.yaml`:

```bash
accessc roles --all
```

To set a single user's roles:

```bash
accessc roles user@yourdomain.com Developer Admin
```

Roles are not created automatically in the AWS accounts by the tool, and must already exist. Role creation may be added in future releases.

### Viewing schema of G Suite directory

The custom schema attributes of the SAML setup can be verified by running:

```bash
accessc schema
```

You should see something like the following:

```json
{
    "etag": "\"XAsypnOPUm9mxokHB31cC07VbXs/hDT2ACjbO2nrT_uVUpNU3VQ_QzU\"",
    "fields": [
        {
            "etag": "\"XRsypGOPUmlmxokHB51cC07Vb3s/mF8fcTzvlteJZ0DIlUljKGlhlfw\"",
            "fieldId": "CfnqfA4pRxqP8i8ueR1wew==",
            "fieldName": "role",
            "fieldType": "STRING",
            "kind": "admin#directory#schema#fieldspec",
            "multiValued": true,
            "readAccessType": "ADMINS_AND_SELF"
        },
        {
            "displayName": "duration",
            "etag": "\"nsb5Diw5qFeijkJuCE2Y6_ahoFE/vYn0fh2xzBCMELA2n-0MQPmFtWI\"",
            "fieldId": "A4ckT32QFSXXMngBk7H5w==",
            "fieldName": "duration",
            "fieldType": "INT64",
            "kind": "admin#directory#schema#fieldspec",
            "readAccessType": "ADMINS_AND_SELF"
        }
    ],
    "kind": "admin#directory#schema",
    "schemaId": "JfLx5all7--VnMs-H39aNQ==",
    "schemaName": "SSO"
}
```

Currently, schema attributes cannot be created/updated using the tool, but this may be added in future releases. 
