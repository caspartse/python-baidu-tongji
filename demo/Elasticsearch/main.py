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

from baidu_tongji import BaiduTongji
from utils import loadConfig

CONFIG = loadConfig()
kb_scheme = CONFIG['kibana']['scheme']
kb_host = CONFIG['kibana']['host']
kb_port = CONFIG['kibana']['port']
kb_username = CONFIG['kibana']['username']
kb_password = CONFIG['kibana']['password']

site_id = '16847648' # change to your site_id
page_size = 100 # change page_size if you want, max is 1000
debug = True # set debug=False if useing in production environment


# you could also use the Elasticsearch Python Client (https://github.com/elastic/elasticsearch-py), but it may take some time to configure.
class Kibana(object):
    def __init__(self):
        super(Kibana, self).__init__()
        self.url = f'{kb_scheme}://{kb_host}:{kb_port}/api/console/proxy'
        self.sess = requests.Session()
        self.sess.auth = requests.auth.HTTPBasicAuth(kb_username, kb_password)
        self.sess.headers.update({'kbn-xsrf': 'kibana'})

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
                if k in ['date_time', 'first_visit_time', 'last_visit_time', 'receive_time', 'session_start_time', 'start_time']:
                    data[k] = changeToUTC(v)
            result = self.insertDocument(index_name, doc_id, data)
            print(result)
        except:
            print(f'insert or update {index_name}')
            traceback.print_exc()

    return True


if __name__ == '__main__':
    kb = Kibana()
    bd = BaiduTongji(debug=debug)

    # query by visitor_id which "duration" is -10000 (means the visitor is still online)
    # you could change the order by condition to get the latest data, or change the limit to get more data
    query = '''
        SELECT visitor_id, event_id, MIN(receive_time) AS min_receive_time
        FROM events
        WHERE duration = -10000
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
                result = bd.fetchRealTimeData(site_id, page_size=page_size, visitor_id=visitor_id)
            except:
                traceback.print_exc()
                continue
            for item in result:
                saveToES(kb, item)

    # fetch new data
    result = bd.fetchRealTimeData(site_id, page_size=page_size)
    l = len(result)
    for idx, item in enumerate(result):
        print(f'fetch new data - {idx+1}/{l}')
        saveToES(kb, item)

    print('done.')