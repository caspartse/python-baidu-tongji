#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import codecs
import os
import re
import sqlite3
import traceback
from urllib.parse import parse_qs, unquote_plus, urlparse

import arrow
import orjson
import orjson as json
import requests
import yaml

try:
    from pymongo import MongoClient
except:
    pass

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
mongodb_uri = 'mongodb://localhost:27017/' # Change this to your own MongoDB URI


def loadConfig() -> dict:
    with open(f'{CURRENT_PATH}/config.yaml', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def queryTokenInfo() -> dict:
    with sqlite3.connect(f'{CURRENT_PATH}/data/cache.db') as con:
        cur = con.cursor()
        cur.execute('''SELECT name, value, COALESCE(expires, 0) FROM token_info''')
        rows = cur.fetchall()

    result = {
        row[0]: {"value": row[1], "expires": row[2]}
        for row in rows
    }

    return result

def saveTokenInfo(token_info) -> bool:
    with sqlite3.connect(f'{CURRENT_PATH}/data/cache.db') as con:
        cur = con.cursor()
        for key, value in token_info.items():
            cur.execute(
                '''INSERT OR REPLACE INTO token_info(name, value, expires, _updated_at) VALUES(?, ?, ?, datetime('now','localtime'))''',
                (key, value['value'], value['expires'])
            )
    return True

def saveRawData(site_id: str, content: dict) -> None:
    print(content)
    # save raw data as json file in data/raw_data.json
    try:
        with codecs.open(f'{CURRENT_PATH}/data/raw_data.json', 'w', 'utf-8') as f:
            f.write(json.dumps(content, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode('utf-8'))
    except Exception as e:
        print(e)
        pass

    # save raw data to mongodb
        log = {
            'site_id': site_id,
            'timestamp': arrow.now().format('YYYY-MM-DD HH:mm:ss'),
            'items': content.get('data', content.get('result'))['items']
        }
        client = MongoClient(mongodb_uri)
        db = client['website_traffic']
        collection = db['log']
        if isinstance(log, list):
            collection.insert_many(log)
        else:
            collection.insert_one(log)
    except:
        traceback.print_exc()

    return None

def getTime(start_time: str) -> tuple:
    # handle no date in start_time
    try:
        start_time = arrow.get(start_time).format('YYYY-MM-DD HH:mm:ss')
    except:
        start_time = f'{arrow.now().format("YYYY-MM-DD")} {start_time}'
    start_time = arrow.get(start_time).format('YYYY-MM-DD HH:mm:ss')
    date_time = arrow.get(start_time).format('YYYY-MM-DD HH:mm:ss')
    unix_timestamp = arrow.get(start_time).timestamp()
    return (start_time, date_time, unix_timestamp)

def queryDivision(name: str, ip: str='') -> tuple:
    is_ipv4 = re.fullmatch(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip)
    country, province, city = '', '', ''

    # ?????????
    if name in ['??????', '??????', '??????', '??????']:
        province = name + '???'
        country = '??????'
    if name in ['??????', '??????', '??????']:
        province = name
        country = '??????'

    if not country:
        with sqlite3.connect(f'{CURRENT_PATH}/data/divisions.db') as con:
            cur = con.cursor()

            rows = cur.execute('SELECT name, code FROM city WHERE name LIKE ?', (f'%{name}%',)).fetchall()

            if len(rows) == 1:
                city, cityCode = rows[0]
                provinceCode = cityCode[:2]
                province = cur.execute('''SELECT name FROM province WHERE code = ?''', (provinceCode,)).fetchone()[0]
                country = '??????'
            elif is_ipv4:
                url = 'https://ip.taobao.com/outGetIpInfo'
                params = {
                    'ip': ip,
                    'accessKey': 'alibaba-inc'
                }
                try:
                    resp = requests.get(url, params=params, timeout=(10, 30))
                    content = resp.json()
                    data = content['data']
                    country = data['country']
                    province = data['region']
                    provinceCode = data['region_id'][:2]
                    city = data['city']
                    cityCode = data['city_id'][:4]
                    if (country == '??????') and (province not in ['??????', '??????', '??????', 'XX']):
                        try:
                            if city != 'XX':
                                q = f'''SELECT name FROM city WHERE code = {cityCode}'''
                            else:
                                # ???????????????????????????????????????
                                q = f'''SELECT name FROM area WHERE name LIKE '%{name}%' AND provinceCode = {provinceCode}'''
                            city = cur.execute(q).fetchone()[0]
                        except:
                            traceback.print_exc()
                            print(name, ip)
                            print(data)
                        # ???????????????
                        try:
                            province = cur.execute('''SELECT name FROM province WHERE code = ?''', (provinceCode,)).fetchone()[0]
                        except:
                            traceback.print_exc()
                            print(name, ip)
                            print(data)
                except:
                    traceback.print_exc()
                    print(name, ip)

    if province in ['?????????', '?????????', '?????????', '?????????']:
        city = province
    if province in ['??????', '??????', '??????']:
        city = province
    if province == 'XX':
        province = ''
    if city == 'XX':
        city = ''

    return (country, province, city)

def parseTrafficSource(source_from_type: str, source_url: str) -> dict:
    search_engine = ''
    if source_from_type == '????????????':
        traffic_source_type = '????????????'
    elif re.search(r'(Google|??????|360??????|??????|????????????|Bing|??????|????????????|??????)', source_from_type):
        traffic_source_type = '????????????'
        try:
            search_engine = re.search(r'(Google|??????|360??????|??????|????????????|Bing|??????|????????????|??????)', source_from_type).group(1)
        except:
            search_engine = '??????'
    elif 'bing.com' in source_from_type:
        traffic_source_type = '????????????'
        search_engine = 'Bing'
    elif 'http' in source_from_type:
        traffic_source_type = '????????????'
    elif source_from_type == '???????????????':
        traffic_source_type = '???????????????'
    else:
        traffic_source_type = '??????'

    if source_url:
        referrer = source_url
        referrer_host = urlparse(referrer).netloc
    else:
        referrer = ''
        referrer_host = ''

    search_keyword = ''
    try:
        search_keyword = re.search(r'?????????:([^\)]+))', source_from_type).group(1)
        search_keyword = unquote_plus(search_keyword)
    except:
        pass
    if (not search_keyword) and (traffic_source_type == '????????????'):
        pattern = re.compile(r'(wd|word|q|query|kw???keyword)=([^&]+)')
        try:
            search_keyword = pattern.search(source_url).group(2)
            search_keyword = unquote_plus(search_keyword)
        except:
            pass

    traffic_source = {
        'traffic_source_type': traffic_source_type,
        'referrer': referrer,
        'search_engine': search_engine,
        'referrer_host': referrer_host,
        'search_keyword': search_keyword,
    }

    return traffic_source

def parsetUrlPath(url: str) -> tuple:
    try:
        url_path = '/' + re.sub(r'[\?#%&]\S*', '', url.split('/')[3])
        url_full_path = urlparse(url).path
    except IndexError:
        url_path = '/'
        url_full_path = '/'
    return (url_path, url_full_path)

def parseTrackingParams(url: str) -> dict:
        query_params = parse_qs(urlparse(url).query, keep_blank_values=True)
        query_params = {k: v[0] for k, v in query_params.items()}
        hmsr = query_params.get('hmsr', '')
        utm_source = query_params.get('utm_source', hmsr)
        hmpl = query_params.get('hmpl', '')
        utm_medium = query_params.get('utm_medium', hmpl)
        hmcu = query_params.get('hmcu', '')
        utm_campaign = query_params.get('utm_campaign', hmcu)
        hmkw = query_params.get('hmkw', '')
        utm_term = query_params.get('utm_term', hmkw)
        hmci = query_params.get('hmci', '')
        utm_content = query_params.get('utm_content', hmci)
        # you can add more custom params here, such as: channel_id, channel_name, activity_id, etc.
        channel_id = query_params.get('channel_id', '')

        tracking_params = {
            'utm_source': utm_source,
            'hmsr': hmsr,
            'utm_medium': utm_medium,
            'hmpl': hmpl,
            'utm_campaign': utm_campaign,
            'hmcu': hmcu,
            'utm_term': utm_term,
            'hmkw': hmkw,
            'utm_content': utm_content,
            'hmci': hmci,
            'channel_id': channel_id
        }

        return tracking_params

def getDuration(duration: str) -> int:
    if duration == '????????????':
        duration = -10000
    elif duration == '??????':
        duration = -20000
    else:
        duration = int(duration)
    return duration


if __name__ == '__main__':
    pass