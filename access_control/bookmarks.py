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

import sys
import time
from collections import defaultdict
from operator import itemgetter

bookmark = """<DT><A HREF="javascript:%28function%28roleName%2C%20account%2C%20displayName%2C%20color%29%20%7B%20if%20%28window.AWSC%20%3D%3D%20undefined%20%7C%7C%20window.AWSC.Auth%20%3D%3D%20undefined%29%20%7B%20alert%28%27Please%20go%20to%20the%20AWS%20Console%20to%20use%20this%20bookmark.%27%29%3B%20return%3B%20%7D%20var%20p%20%3D%20%7B%20%22roleName%22%3A%20roleName%2C%20%22account%22%3A%20account%2C%20%22displayName%22%3A%20displayName%2C%20%22color%22%3A%20color%2C%20%22action%22%3A%20%22switchFromBasis%22%2C%20%22src%22%3A%20%22nav%22%2C%20%22mfaNeeded%22%3A%200%2C%20%22csrf%22%3A%20window.AWSC.Auth.getMbtc%28%29%2C%20%22redirect_uri%22%3A%20escape%28window.location.href%29%20%7D%3B%20var%20f%20%3D%20document.createElement%28%22form%22%29%3B%20f.setAttribute%28%22method%22%2C%20%22post%22%29%3B%20f.setAttribute%28%22action%22%2C%20%22https%3A//signin.aws.amazon.com/switchrole%22%29%3B%20for%20%28var%20k%20in%20p%29%20%7B%20if%20%28p.hasOwnProperty%28k%29%29%20%7B%20var%20i%20%3D%20document.createElement%28%22input%22%29%3B%20i.setAttribute%28%22type%22%2C%20%22hidden%22%29%3B%20i.setAttribute%28%22name%22%2C%20k%29%3B%20i.setAttribute%28%22value%22%2C%20p%5Bk%5D%29%3B%20f.appendChild%28i%29%3B%20%7D%20%7D%20document.body.appendChild%28f%29%3B%20f.submit%28%29%3B%20%7D%29%28%22{role}%22%2C%22{account_id}%22%2C%22{name}%22%2C%226666FF%22%29" ADD_DATE="{timestamp}" LAST_MODIFIED="{timestamp}">{name}</A>"""  # noqa


def write_bookmarks(profiles, filename, idpid, spid):
    if filename == '-':
        outfile = sys.stdout
    else:
        outfile = open(filename, 'w')
    idpurl = "https://accounts.google.com/o/saml2/initsso?idpid={}&spid={}&forceauthn=false".format(idpid, spid)
    print("<DL>", file=outfile)
    print("<DT><H3>AWS</H3>", file=outfile)
    print("<DL>", file=outfile)
    print('<DT><A HREF="{}">AWS Login</A>'.format(idpurl), file=outfile)
    print('<HR>', file=outfile)
    byaccount = defaultdict(lambda: [])
    for profile in profiles:
        byaccount[profile['account']].append(profile)
    for account, profiles in sorted(byaccount.items()):
        if len(profiles) == 1:
            b = bookmark.format(timestamp=str(int(time.time())), **profiles[0])
            print(b, file=outfile)
        else:
            # folder
            print("<DT><H3>{}</H3>".format(account), file=outfile)
            print("<DL>")
            for profile in sorted(profiles, key=itemgetter('role')):
                # profile['name'] = profile['role']
                b = bookmark.format(timestamp=str(int(time.time())), **profile)
                print(b, file=outfile)
            print("</DL>", file=outfile)
    print("</DL>", file=outfile)
    print("</DL>", file=outfile)
