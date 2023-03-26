#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import codecs
import os
import sys
import traceback
from os.path import abspath, dirname, join

import orjson as json
import requests

sys.path.insert(0, abspath(join(dirname(__file__), '../../../package')))

from utils import loadConfig

CONFIG = loadConfig()
kb_scheme = CONFIG['kibana']['scheme']
kb_host = CONFIG['kibana']['host']
kb_port = CONFIG['kibana']['port']
kb_username = CONFIG['kibana']['username']
kb_password = CONFIG['kibana']['password']

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


class Kibana(object):
    def __init__(self):
        super(Kibana, self).__init__()
        self.url = f'{kb_scheme}://{kb_host}:{kb_port}/api/console/proxy' # maybe you need use https
        self.sess = requests.Session()
        self.sess.auth = requests.auth.HTTPBasicAuth(kb_username, kb_password)
        self.sess.headers.update({'kbn-xsrf': 'kibana'})

    def deleteIndex(self, index_name: str, mappings: dict) -> bool:
        params = {
            'path': f'/{index_name}',
            'method': 'DELETE'
        }
        resp = self.sess.post(self.url, params=params)
        result = resp.json()
        return result

    def createIndex(self, index_name: str, mappings: dict) -> bool:
        params = {
            'path': f'/{index_name}',
            'method': 'PUT'
        }
        data = {
            'mappings': mappings
        }
        resp = self.sess.post(self.url, params=params, json=data)
        result = resp.json()
        return result


if __name__ == '__main__':
    kb = Kibana()

    # delete index ('visitors', 'sessions', 'events')
    for index_name in ['visitors', 'sessions', 'events']:
        try:
            result = kb.deleteIndex(index_name, {})
            print(result)
        except:
            traceback.print_exc()
            continue

    # load mappings from json file and create index ('visitors', 'sessions', 'events')
    for index_name in ['visitors', 'sessions', 'events']:
        try:
            with codecs.open(f'{CURRENT_PATH}/index_{index_name}.json', encoding='utf-8') as f:
                raw = json.loads(f.read())
            mappings = raw['mappings']
            result = kb.createIndex(index_name, mappings)
            print(result)
        except:
            traceback.print_exc()
            continue
