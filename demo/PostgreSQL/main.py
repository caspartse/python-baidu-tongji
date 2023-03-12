#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import os
import sys
import traceback
from os.path import abspath, dirname, join

import psycopg2

sys.path.insert(0, abspath(join(dirname(__file__), '../../package')))

from baidu_tongji import baiduTongji

conn = psycopg2.connect(host='localhost', port='5432', dbname='website_traffic', user='postgres', password='123456') # Change this to your own PostgreSQL settings
cur = conn.cursor()


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
        except:
            print(f'insert or update {table_name}')
            traceback.print_exc()
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

    bd = baiduTongji(debug=True) # set debug=False if useing in production environment

    # query by visitor_id which "event_duration" is -10000 (means the visitor is still online)
    # you can change the order by condition to get the latest data, or change the limit to get more data
    q = '''
        SELECT visitor_id, MIN(receive_time) AS min_receive_time
        FROM events
        WHERE event_duration = -10000
        GROUP BY visitor_id
        ORDER BY min_receive_time DESC
        LIMIT 10;
    '''
    cur.execute(q)
    rows = cur.fetchall()
    l = len(rows)
    for idx, row in enumerate(rows):
        print(f'query visitor - {idx+1}/{l}')
        visitor_id = row[0]
        try:
            result = bd.fetchRealTimeData('16847648', page_size=100, visitor_id=visitor_id) # change your site_id here
        except:
            traceback.print_exc()
            continue
        for item in result:
            print(item)
            saveToDB(item)

    # fetch new data
    result = bd.fetchRealTimeData('16847648', page_size=100) # change your site_id here
    l = len(result)
    for idx, item in enumerate(result):
        print(f'fetch new data - {idx+1}/{l}')
        print(item)
        saveToDB(item)

    cur.close()
    conn.close()
    print('done.')
