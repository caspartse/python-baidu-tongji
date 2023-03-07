#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import os, sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '../../package')))

import traceback
import codecs
import requests
import orjson as json
from baidu_tongji import baiduTongji

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


# You can also use the Elasticsearch Python Client (https://github.com/elastic/elasticsearch-py), but it may take some time to configure.
class Kibana(object):
    def __init__(self):
        super(Kibana, self).__init__()
        self.url = 'http://localhost:5601/api/console/proxy'
        self.sess = requests.Session()
        self.sess.auth = requests.auth.HTTPBasicAuth('elastic', 'uOu7t890nmjqVTAPp5kE') # Change this to your own username and password of Kibana
        self.sess.headers.update({'kbn-xsrf': 'kibana'})

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

    def insertDocument(self, index_name, doc_id, data):
        params = {
            'path': f'/{index_name}/_doc/{doc_id}',
            'method': 'POST'
        }
        try:
            resp = self.sess.post(self.url, params=params, json=data, timeout=(10, 30))
            result = resp.json()
        except:
            traceback.print_exc()
        return result

    def updateDocument(self,index_name, doc_id, data):
        params = {
            'path': f'/{index_name}/_update/{doc_id}',
            'method': 'POST'
        }
        data = {
            'doc': data
        }
        try:
            resp = self.sess.post(self.url, params=params, json=json.dumps(data), timeout=(10, 30))
            result = resp.json()
        except:
            traceback.print_exc()
        return result


if __name__ == '__main__':
    kb = Kibana()

    ## load mappings from json file and create index ('visitors', 'sessions', 'events')
    # for index_name in ['visitors', 'sessions', 'events']:
    #     try:
    #         with codecs.open(f'{CURRENT_PATH}/mappings_{index_name}.json', encoding='utf-8') as f:
    #             raw = json.loads(f.read())
    #         mappings = raw['mappings']
    #         result = kb.createIndex(index_name, mappings)
    #         print(result)
    #     except:
    #         traceback.print_exc()
    #         continue

    bd = baiduTongji(debug=True)

    ## fetch new data
    result = bd.fetchRealTimeData('16847648', page_size=1000)
    l = len(result)
    for idx, item in enumerate(result):
        print(f'fetch new data - {idx+1}/{l}')

        # ## insert visitors
        print('insert visitors')
        index_name = 'visitors'
        data = item['visitor']
        doc_id = data['visitor_id']
        resp = kb.insertDocument(index_name, doc_id, data)
        print(resp)

        # ## insert sessions
        print('insert sessions')
        index_name = 'sessions'
        data = item['session']
        doc_id = data['session_id']
        resp = kb.insertDocument(index_name, doc_id, data)
        print(resp)

        ## insert events
        print('insert events')
        index_name = 'events'
        event_list = item['event_list']
        for data in event_list:
            doc_id = data['event_id']
            print(data)
            resp = kb.insertDocument(index_name, doc_id, data)
            print(resp)
