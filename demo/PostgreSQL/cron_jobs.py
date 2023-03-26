#!/usr/bin/env python3
# -*- coding:utf-8 -*-
""""
run this script every day at 01:00:00
"""
import sys
from os.path import abspath, dirname, join

import psycopg

sys.path.insert(0, abspath(join(dirname(__file__), '../../package')))

from baidu_tongji import BaiduTongji
from utils import loadConfig

CONFIG = loadConfig()

pg_host = CONFIG['postgresql']['host']
pg_port = CONFIG['postgresql']['port']
pg_dbname = CONFIG['postgresql']['dbname']
pg_username = CONFIG['postgresql']['username']
pg_password = CONFIG['postgresql']['password']
conn = psycopg.connect(host=pg_host, port=pg_port, dbname=pg_dbname, user=pg_username, password=pg_password)
cur = conn.cursor()


if __name__ == '__main__':
    # update event duration which "duration" is -20000 (unknown) and "receive_time" is older than 3 hours
    q = '''
        UPDATE events
        SET duration = 1
        WHERE duration = -20000
        AND receive_time < (NOW() - INTERVAL '3 HOURS');
    '''
    cur.execute(q)
    conn.commit()

    # update event duration which "duration" is -10000 (visiting) and "receive_time" is older than 3 hours
    q = '''
        UPDATE events
        SET duration = 1
        WHERE duration = -10000
        AND receive_time < (NOW() - INTERVAL '3 HOURS');
    '''
    cur.execute(q)
    conn.commit()

    # update session duration which "duration" less than 0
    q = '''
        UPDATE sessions s
        SET duration = (
            SELECT SUM(duration)
            FROM events
            WHERE session_id = s.session_id
            AND duration > 0
        )
        WHERE duration < 0;
    '''
    cur.execute(q)
    conn.commit()

    # update session last_event_id which "last_event_id" is empty and "duration" greater than 0
    q = '''
        UPDATE sessions s
        SET last_event_id = (
            SELECT event_id
            FROM events
            WHERE session_id = s.session_id
            ORDER BY date_time DESC
            LIMIT 1
        )
        WHERE last_event_id = ''
        AND duration > 0;
    '''
    cur.execute(q)
    conn.commit()

    # update event is_session_end which "is_session_end" is False and "next_event_id" is empty and "receive_time" is older than 3 hours
    q = '''
        UPDATE events e
        SET is_session_end = TRUE
        WHERE is_session_end = FALSE
        AND next_event_id = ''
        AND receive_time < (NOW() - INTERVAL '3 HOURS');
    '''
    cur.execute(q)
    conn.commit()

    # update event is_session_end, according to the last event of the session
    q = '''
    UPDATE events t
    SET is_session_end = FALSE
    WHERE EXISTS (
        SELECT 1
        FROM events e
        INNER JOIN sessions s USING(session_id)
        WHERE e.is_session_end = TRUE
        AND e.event_id <> s.last_event_id
        AND e.event_id = t.event_id
    );
    '''
    cur.execute(q)

    # update visitor's profile (high frequency ip, country, province, city)
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
        AND last_visit_time >= (NOW() - INTERVAL '48 HOURS'); -- visitors in the last 48 hours only
    '''
    cur.execute(q)
    conn.commit()

    # update visitor's profile (frequency, total_duration, total_visit_pages)
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
        AND last_visit_time >= (NOW() - INTERVAL '48 HOURS'); -- visitors in the last 48 hours only
    '''
    cur.execute(q)
    conn.commit()

    cur.close()
    conn.close()
    print('done.')
