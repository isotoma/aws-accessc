# aws-accessc
Accessc is a command-line tool that lets you manage mappings between federated logins and roles in AWS. It also generates AWS config profiles for individuals users and a set of bookmarklets for easy access to roles in the AWS console.

## Access and profiles for end users
Currently only google is supported as a SAML identity provider (IdP).

### Federated Access Setup
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

This will setup an alias `aws-auth` which will store these details in your aws default profile on login, and set the expiry of your access to 12 hours (this expiry must be increased from the default of 1 hour by your AWS admin for each login role you use). See the [aws-google-auth](https://github.com/cevoaustralia/aws-google-auth) documentation for additional details about that tool.

To login run:

```bash
aws-auth
```

Enter your google password, complete a captcha if this is your first login, and any 2FA steps. You will be offered a list of the login roles you have access to. It is a good idea to use the least priveleged role for the tasks you have in mind.

### Generating AWS Profiles

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

You will need to obtain a `roles.yaml` file from your admin that specifies the AWS accounts and roles you will have access to. This also specifies which of these roles you can assume from a particular SAML login role. These roles will be added to your AWS config as profiles when you run the tool. It should look something like this:

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
