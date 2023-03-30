#!/usr/bin/env python3
# -*- coding:utf-8 -*-
""""
This script is used to insert data from PostgreSQL to Elasticsearch.
"""
import sys
import traceback
from os.path import abspath, dirname, join

import psycopg
import requests

sys.path.insert(0, abspath(join(dirname(__file__), '../../package')))

from utils import changeToUTC, loadConfig

CONFIG = loadConfig()
kb_scheme = CONFIG['kibana']['scheme']
kb_host = CONFIG['kibana']['host']
kb_port = CONFIG['kibana']['port']
kb_username = CONFIG['kibana']['username']
kb_password = CONFIG['kibana']['password']
pg_host = CONFIG['postgresql']['host']
pg_port = CONFIG['postgresql']['port']
pg_dbname = CONFIG['postgresql']['dbname']
pg_username = CONFIG['postgresql']['username']
pg_password = CONFIG['postgresql']['password']
conn = psycopg.connect(host=pg_host, port=pg_port, dbname=pg_dbname, user=pg_username, password=pg_password)
cur = conn.cursor()


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


def getTableColumns(table_name: str) -> dict:
    q = f'''
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = '{table_name}'
        AND column_name NOT LIKE '\_%'
    '''
    cur.execute(q)
    rows = cur.fetchall()
    template = {x[0]: x[1] for x in rows}
    return template

def saveToES(self, index_name: str, data: dict) -> bool:
    if index_name == 'visitors':
        doc_id = data['visitor_id']
    elif index_name == 'sessions':
        doc_id = data['session_id']
    elif index_name == 'events':
        doc_id = data['event_id']
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

    for index_name in ['visitors', 'sessions', 'events']:
        cloumns = getTableColumns(index_name)
        q = f'''
            SELECT {','.join(cloumns.keys())}
            FROM {index_name}
            WHERE _updated_at >= (NOW() - INTERVAL '30 MINUTES') -- update the data in the last 30 minutes, you can change it to your own time range
        '''
        cur.execute(q)
        rows = cur.fetchall()
        for row in rows:
            data = {k: v for k, v in zip(cloumns.keys(), row)}
            saveToES(kb, index_name, data)

    print('done.')