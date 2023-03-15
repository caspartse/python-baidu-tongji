#!/usr/bin/env python3
# -*- coding:utf-8 -*-
""""
update visitor's profile.
run this script every day at 01:00:00
"""
import os
import sys
import traceback
from os.path import abspath, dirname, join

import psycopg2

sys.path.insert(0, abspath(join(dirname(__file__), '../../package')))

from baidu_tongji import baiduTongji
from utils import loadConfig

CONFIG = loadConfig()

pg_host = CONFIG['postgresql']['host']
pg_port = CONFIG['postgresql']['port']
pg_dbname = CONFIG['postgresql']['dbname']
pg_username = CONFIG['postgresql']['username']
pg_password = CONFIG['postgresql']['password']
conn = psycopg2.connect(host=pg_host, port=pg_port, dbname=pg_dbname, user=pg_username, password=pg_password)
cur = conn.cursor()


if __name__ == '__main__':
    # update visitor's profile
    # high frequency ip, country, province, city
    q = '''
        WITH info AS (
            SELECT visitor_id, ip, country, province, city
            FROM (
            SELECT visitor_id,
                ip,
                country,
                province,
                city,
                COUNT(*) AS count_ip, RANK() OVER (PARTITION BY visitor_id ORDER BY COUNT(*) DESC) AS rank_ip,
                COUNT(*) AS count_country, RANK() OVER (PARTITION BY visitor_id ORDER BY COUNT(*) DESC) AS rank_country,
                COUNT(*) AS count_province, RANK() OVER (PARTITION BY visitor_id ORDER BY COUNT(*) DESC) AS rank_province,
                COUNT(*) AS count_city, RANK() OVER (PARTITION BY visitor_id ORDER BY COUNT(*) DESC) AS rank_city
            FROM sessions
            GROUP BY visitor_id, ip, country, province, city
            ) t1
            WHERE t1.rank_ip = 1
            AND t1.rank_country = 1
            AND t1.rank_province = 1
            AND t1.rank_city = 1
        )
        UPDATE visitors v
        SET hf_ip = info.ip, hf_country= info.country, hf_province= info.province, hf_city= info.city
        FROM info
        WHERE v.visitor_id = info.visitor_id
        AND latest_visit_time >= (NOW() - INTERVAL '48 HOURS'); -- visitors in the last 48 hours only
    '''
    cur.execute(q)
    conn.commit()

    # frequency, total_duration, total_visit_pages
    q = '''
        WITH info AS (
            SELECT visitor_id,
                COUNT(*) AS frequency,
                SUM(GREATEST(duration, 0)) AS total_duration,
                SUM(visit_pages) AS total_visit_pages
            FROM sessions
            GROUP BY visitor_id
        )
        UPDATE visitors v
        SET frequency = info.frequency, total_duration = info.total_duration, total_visit_pages = info.total_visit_pages
        FROM info
        WHERE v.visitor_id = info.visitor_id
        AND latest_visit_time >= (NOW() - INTERVAL '48 HOURS'); -- visitors in the last 48 hours only
    '''
    cur.execute(q)
    conn.commit()

    cur.close()
    conn.close()
    print('done.')
