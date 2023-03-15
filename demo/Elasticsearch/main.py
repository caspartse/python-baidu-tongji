#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import codecs
import os
import sys
import traceback
from os.path import abspath, dirname, join

import arrow
import orjson as json
import requests

sys.path.insert(0, abspath(join(dirname(__file__), '../../package')))

from baidu_tongji import baiduTongji
from utils import loadConfig

CONFIG = loadConfig()
kb_scheme = CONFIG['kibana']['scheme']
kb_host = CONFIG['kibana']['host']
kb_port = CONFIG['kibana']['port']
kb_username = CONFIG['kibana']['username']
kb_password = CONFIG['kibana']['password']

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


# you can also use the Elasticsearch Python Client (https://github.com/elastic/elasticsearch-py), but it may take some time to configure.
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
            resp = self.sess.post(self.url, params=params, json=data, timeout=(10, 30))
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

def changeToUTC(local_time: str, tzinfo: str='Asia/Shanghai') -> str:
    try:
        utc_time = arrow.get(local_time, tzinfo=tzinfo).to('UTC').format('YYYY-MM-DD HH:mm:ss')
        return utc_time
    except:
        return local_time

def saveToES(self, entity: dict) -> bool:
    # index_name, doc_id, data
    doc_lits = [
        ('visitors', entity['visitor']['visitor_id'], entity['visitor']),
        ('sessions', entity['session']['session_id'], entity['session']),
    ]
    doc_lits.extend([('events', event['event_id'], event) for event in entity['event_list']])

    # insert or update documents
    for index_name, doc_id, data in doc_lits:
        try:
            # change time zone from UTC+8 to UTC, because Elasticsearch is in UTC
            for k, v in data.items():
                if k in ['date_time', 'first_visit_time', 'latest_visit_time', 'receive_time', 'start_time']:
                    data[k] = changeToUTC(v)
            result = self.insertDocument(index_name, doc_id, data)
            print(result)
        except:
            print(f'insert or update {index_name}')
            traceback.print_exc()

    return True


if __name__ == '__main__':
    kb = Kibana()

    # # delete index ('visitors', 'sessions', 'events')
    # for index_name in ['visitors', 'sessions', 'events']:
    #     try:
    #         result = kb.deleteIndex(index_name, {})
    #         print(result)
    #     except:
    #         traceback.print_exc()
    #         continue

    # # load mappings from json file and create index ('visitors', 'sessions', 'events')
    # # uncomment the following code if you're trying this demo for the first time.
    # for index_name in ['visitors', 'sessions', 'events']:
    #     try:
    #         with codecs.open(f'{CURRENT_PATH}/mappings/{index_name}.json', encoding='utf-8') as f:
    #             raw = json.loads(f.read())
    #         mappings = raw['mappings']
    #         result = kb.createIndex(index_name, mappings)
    #         print(result)
    #     except:
    #         traceback.print_exc()
    #         continue

    bd = baiduTongji(debug=True) # set debug=False if useing in production environment

    # query by visitor_id which "event_duration" is -10000 (means the visitor is still online)
    # you can change the order by condition to get the latest data, or change the limit to get more data
    query = '''
        SELECT visitor_id, event_id, MIN(receive_time) AS min_receive_time
        FROM events
        WHERE event_duration = -10000
        GROUP BY visitor_id, event_id
        ORDER BY min_receive_time DESC
        LIMIT 10;
    '''
    content = kb.sqlQuery(query)
    rows = content.get('rows', [])
    if rows:
        l = len(rows)
        for idx, row in enumerate(rows):
            print(f'query visitor - {idx+1}/{l}')
            visitor_id = row[0]
            try:
                result = bd.fetchRealTimeData('16847648', page_size=100, visitor_id=visitor_id) # Change your site_id here
            except:
                traceback.print_exc()
                continue
            for item in result:
                print(item)
                saveToES(kb, item)

    # fetch new data
    result = bd.fetchRealTimeData('16847648', page_size=100) # Change your site_id here
    l = len(result)
    for idx, item in enumerate(result):
        print(f'fetch new data - {idx+1}/{l}')
        print(item)
        saveToES(kb, item)

    print('done.')