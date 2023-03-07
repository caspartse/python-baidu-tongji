#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import os, sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '../../package')))

import traceback
from baidu_tongji import baiduTongji
import psycopg2


host = 'localhost' # Change this to your own host
dbName = 'website_traffic'
dbUser = 'postgres' # Change this to your own user
dbPwd = '123456' # Change this to your own password
conn = psycopg2.connect(host=host, dbname=dbName, user=dbUser, password=dbPwd)
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
    ## insert or update visitors
    data= entity['visitor']
    table_name = 'visitors'
    primary_key = 'visitor_id'
    template = getTableColumns(table_name)
    template = getTableColumns('visitors')
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
        print('insert or update visitors')
        traceback.print_exc()
        conn.rollback()

    ## insert or update sessions
    data = entity['session']
    table_name = 'sessions'
    primary_key = 'session_id'
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
        print('insert or update sessions')
        traceback.print_exc()
        conn.rollback()

    ## insert or update events
    event_list = entity['event_list']
    table_name = 'events'
    primary_key = 'event_id'
    template = getTableColumns(table_name)
    for data in event_list:
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
            print('insert or update events')
            traceback.print_exc()
            conn.rollback()

    return True


if __name__ == '__main__':
    ## truncate tables
    # q = '''
    #     TRUNCATE TABLE visitors CASCADE;
    #     TRUNCATE TABLE sessions CASCADE;
    #     TRUNCATE TABLE events CASCADE;
    # '''
    # cur.execute(q)
    # conn.commit()

    bd = baiduTongji(debug=True)

    ## query by visitor_id which has negative event_duration
    q = '''
        SELECT visitor_id, MIN(receive_time) AS min_receive_time
        FROM events
        WHERE event_duration < 0
        GROUP BY visitor_id
        ORDER BY min_receive_time
    '''
    cur.execute(q)
    rows = cur.fetchall()
    l = len(rows)
    for idx, row in enumerate(rows):
        print(f'query visitor - {idx+1}/{l}')
        visitor_id = row[0]
        try:
            result = bd.fetchRealTimeData('16847648', page_size=10, visitor_id=visitor_id)
        except:
            traceback.print_exc()
            continue
        for item in result:
            print(item)
            saveToDB(item)

    ## fetch new data
    result = bd.fetchRealTimeData('16847648', page_size=100)
    l = len(result)
    for idx, item in enumerate(result):
        print(f'fetch new data - {idx+1}/{l}')
        print(item)
        saveToDB(item)

    ## update sessions duration which is negative
    q = '''
        UPDATE sessions t2
        SET duration = t1.total_duration
        FROM (
            SELECT session_id, sum(event_duration) AS total_duration
            FROM events
            WHERE event_duration >= 0
            AND session_id IN (
                SELECT session_id
                FROM sessions
                WHERE duration <= 0
            )
            GROUP BY session_id
        ) t1
        WHERE t2.session_id = t1.session_id
        ;
    '''
    cur.execute(q)
    conn.commit()

    cur.close()
    conn.close()
    print('done.')
