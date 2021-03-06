# stdlib
import requests
import json
import pickle
import os.path

# project
from checks import AgentCheck



class Akamai(AgentCheck):
    METRICS = {
        "akamai.dp.count": ("rate", "indices.docs.count"),
    }

    BASURL = 'https://control.akamai.com/home/content/gadgets'

    LOGINURL ='https://control.akamai.com/EdgeAuth/asyncUserLogin'

    FIELDS = [
        'prop_ffedgebw',
        'prop_fferrorcodes',
        'prop_ffedgereqs',
        'prop_fforiginoff',
        'prop_fforiginbw'
    ]


    def __init__(self, name, init_config, agentConfig, instances=None):

        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)

    def check(self, instance):

        if instance.get("site", None) is None:
            raise Exception("Check is not configured")

        site = instance.get('site')
        username = self.init_config.get('username')
        password = self.init_config.get('password')
        tags = instance.get('tags', [])

        #reuse the Loggedin Session
        if (os.path.isfile('/tmp/AkamaiSession.pickle') and os.path.isfile('/tmp/AkamaiLogin.pickle')):
            self.Session = pickle.load(open('/tmp/AkamaiSession.pickle', 'rb'))
            self.Login = pickle.load(open('/tmp/AkamaiLogin.pickle', 'rb'))
        else:
            self.Session = requests.Session()
            loginFields = {'username': username, 'password': password, 'login': 'Log+In'}
            loginHeaders = {'Content-Type': 'application/x-www-form-urlencoded'}
            self.Login = self.Session.post(self.LOGINURL, params=loginFields, headers=loginHeaders)

            pickle.dump(self.Session, open('/tmp/AkamaiSession.pickle', 'wb'))
            pickle.dump(self.Login, open('/tmp/AkamaiLogin.pickle', 'wb'))

        self._query_data(site)

    def _query_data(self, site):
        dataHeaders = {'Content-Type': 'application/json;charset=UTF-8'}
        for field in self.FIELDS:
            dataRequest = self.Session.get(self.BASURL+'/properties/'+site+'/soms/items/'+field+'/data', cookies=self.Login.cookies, headers=dataHeaders)
            self.log.debug(dataRequest.text)
            try:
                res = json.loads(dataRequest.text)
                data = str(res['contents']['data']).translate(None, ',%')
            except ValueError:
                self.log.error("Failed to load json data")
                os.remove('/tmp/AkamaiSession.pickle')
                os.remove('/tmp/AkamaiLogin.pickle')
                exit(1)

            self.log.debug(data)

            tags = ['site:%s' % site]
            self.gauge('akamai.site.'+res['contents']['id'], data, tags=tags)
