#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import logging
import os
import sys
import traceback
from os.path import abspath, dirname, join

import psycopg

sys.path.insert(0, abspath(join(dirname(__file__), '../../package')))

from baidu_tongji import BaiduTongji
from utils import loadConfig, loadDimensions

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(filename=f'{CURRENT_PATH}/pgmain.log', encoding='utf-8', level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
CONFIG = loadConfig()
DIMENSIONS = loadDimensions()


pg_host = CONFIG['postgresql']['host']
pg_port = CONFIG['postgresql']['port']
pg_dbname = CONFIG['postgresql']['dbname']
pg_username = CONFIG['postgresql']['username']
pg_password = CONFIG['postgresql']['password']
conn = psycopg.connect(host=pg_host, port=pg_port, dbname=pg_dbname, user=pg_username, password=pg_password)
cur = conn.cursor()

site_id = '16847648' # change to your site_id
page_size = 100 # change page_size if you want, max is 1000
debug = True # set debug=False if useing in production environment


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

def saveToDB(entity: dict) -> bool:
    # table_name, primary_key, data
    record_list = [
        ('visitors', 'visitor_id', entity['visitor']),
        ('sessions', 'session_id', entity['session'])
    ]
    record_list.extend([('events', 'event_id', x) for x in entity['event_list']])

    # insert or update records
    for table_name, primary_key, data in record_list:
        template = getTableColumns(table_name)
        obj = {k: v for k, v in data.items() if k in template.keys()}
        try:
            q = f'''
                INSERT INTO {table_name} ({','.join(obj.keys())})
                VALUES ({','.join(['%s'] * len(obj))})
                ON CONFLICT ({primary_key}) DO UPDATE
                SET {','.join(['{}=EXCLUDED.{}'.format(k, k) for k in obj.keys()])}
            '''
            cur.execute(q, tuple(obj.values()))
            conn.commit()
        except Exception as e:
            traceback.print_exc()
            logging.error(e, exc_info=True)
            conn.rollback()

    return True


if __name__ == '__main__':
    # # truncate tables
    # q = '''
    #     TRUNCATE TABLE visitors CASCADE;
    #     TRUNCATE TABLE sessions CASCADE;
    #     TRUNCATE TABLE events CASCADE;
    # '''
    # cur.execute(q)
    # conn.commit()

    bd = BaiduTongji(debug=debug)

    # ADD COLUMN from custom_tracking_params
    custom_tracking_params = DIMENSIONS['custom_tracking_params']
    for column_name in custom_tracking_params:
        try:
            q = f'''
                ALTER TABLE sessions ADD COLUMN IF NOT EXISTS {column_name} VARCHAR(255) NULL;
                ALTER TABLE events ADD COLUMN IF NOT EXISTS {column_name} VARCHAR(255) NULL;
            '''
            cur.execute(q)
            conn.commit()
        except:
            conn.rollback()

    # query by visitor_id which "duration" is -10000 (visiting)
    # you can change the order by condition to get the latest data, or change the limit to get more data
    q = '''
        SELECT visitor_id, MIN(receive_time) AS min_receive_time
        FROM events
        WHERE duration = -10000
        GROUP BY visitor_id
        ORDER BY min_receive_time DESC -- change order by condition to get the latest data
        LIMIT 10; -- change limit to get more data
    '''
    cur.execute(q)
    rows = cur.fetchall()
    l = len(rows)
    for idx, row in enumerate(rows):
        print(f'query visitor - {idx+1}/{l}')
        visitor_id = row[0]
        try:
            result = bd.fetchRealTimeData(site_id, page_size=page_size, visitor_id=visitor_id)
        except Exception as e:
            traceback.print_exc()
            logging.error(e, exc_info=True)
            continue
        for item in result:
            saveToDB(item)

    # fetch new data
    result = bd.fetchRealTimeData(site_id, page_size=page_size)
    l = len(result)
    for idx, item in enumerate(result):
        print(f'fetch new data - {idx+1}/{l}')
        saveToDB(item)

    cur.close()
    conn.close()
    print('done.')
