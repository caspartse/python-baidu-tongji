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

    def insertDocument(self, index_name: str, doc_id: str, data: dict) -> dict:
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

    def updateDocument(self,index_name: str, doc_id: str, data: dict) -> dict:
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

    def sqlQuery(self, query: str) -> dict:
        params = {
            'path': '/_sql?format=json',
            'method': 'POST'
        }
        data = {
            'query': query
        }
        resp = self.sess.post(self.url, params=params, json=data)
        result = resp.json()
        return result

def saveToES(self, entity: dict) -> bool:

    ## insert or update visitors
    data = entity['visitor']
    index_name = 'visitors'
    doc_id = data['visitor_id']
    try:
        result = self.insertDocument(index_name, doc_id, data)
        print(result)
    except:
        traceback.print_exc()
        print('insert or update visitors')

    ## insert or update sessions
    data = entity['session']
    index_name = 'sessions'
    doc_id = data['session_id']
    try:
        result = self.insertDocument(index_name, doc_id, data)
        print(result)
    except:
        traceback.print_exc()
        print('insert or update sessions')

    ## insert or update events
    event_list = entity['event_list']
    index_name = 'events'
    for event in event_list:
        doc_id = event['event_id']
        try:
            result = self.insertDocument(index_name, doc_id, event)
            print(result)
        except:
            traceback.print_exc()
            print('insert or update events')

    return True


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

    ## query by visitor_id which has negative event_duration
    ## you can change the order by condition to get the latest data, or change the limit to get more data
    query = '''
        SELECT visitor_id, event_id, MIN(receive_time) AS min_receive_time
        FROM events
        WHERE event_duration < 0
        GROUP BY visitor_id, event_id
        ORDER BY min_receive_time DESC
        LIMIT 100
    '''
    content = kb.sqlQuery(query)
    rows = content['rows']
    l = len(rows)
    for idx, row in enumerate(rows):
        print(f'query visitor - {idx+1}/{l}')
        visitor_id = row[0]
        try:
            result = bd.fetchRealTimeData('16847648', page_size=100, visitor_id=visitor_id)
        except:
            traceback.print_exc()
            continue
        for item in result:
            print(item)
            saveToES(kb, item)

    ## fetch new data
    result = bd.fetchRealTimeData('16847648', page_size=100)
    l = len(result)
    for idx, item in enumerate(result):
        print(f'fetch new data - {idx+1}/{l}')
        print(item)
        saveToES(kb, item)
