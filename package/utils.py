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
import redis
import requests
import yaml

try:
    from pymongo import MongoClient
except:
    pass

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


def loadConfig() -> dict:
    """
    加载配置文件
    :return: 配置信息字典
    """
    with open(f'{CURRENT_PATH}/config.yaml', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

CONFIG = loadConfig()

rd_host = CONFIG['redis']['host']
rd_port = CONFIG['redis']['port']
rd_password = CONFIG['redis']['password']
rd_db = CONFIG['redis']['db']
rd_pool = redis.ConnectionPool(host=rd_host, port=rd_port, password=rd_password, db=rd_db, decode_responses=True)
rd = redis.Redis(connection_pool=rd_pool)

def loadDimensions() -> dict:
    """
    加载自定义维度
    :return: 自定义维度字典
    """
    with open(f'{CURRENT_PATH}/dimensions.yaml', encoding='utf-8') as f:
         dimension = yaml.safe_load(f)
    return dimension

DIMENSIONS = loadDimensions()

def queryTokenInfo() -> dict:
    """
    查询 token 信息
    :return: token 信息字典
    """
    with sqlite3.connect(f'{CURRENT_PATH}/data/data.db') as con:
        cur = con.cursor()
        cur.execute('''SELECT name, value, COALESCE(expires, 0) FROM token_info''')
        rows = cur.fetchall()

    result = {
        row[0]: {"value": row[1], "expires": row[2]}
        for row in rows
    }

    return result

def saveTokenInfo(token_info: dict) -> None:
    """
    保存 token 信息
    :return: None
    """
    with sqlite3.connect(f'{CURRENT_PATH}/data/data.db') as con:
        cur = con.cursor()
        for key, value in token_info.items():
            cur.execute(
                '''INSERT OR REPLACE INTO token_info(name, value, expires, _updated_at) VALUES(?, ?, ?, datetime('now','localtime'))''',
                (key, value['value'], value['expires'])
            )
    return None

def saveRawData(site_id: str, content: dict) -> None:
    """
    保存原始数据
    :param site_id: 站点 ID
    :param content: 原始数据
    :return: None
    """
    # save raw data as json file for debug.
    try:
        with codecs.open(f'{CURRENT_PATH}/data/{site_id}_raw_data.json', 'w', 'utf-8') as f:
            f.write(json.dumps(content, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode('utf-8'))
    except:
        traceback.print_exc()

    # save raw data to mongodb
    if CONFIG['mongodb']['enable']:
        try:
            log = {
                'site_id': site_id,
                'timestamp': arrow.now().format('YYYY-MM-DD HH:mm:ss'),
                'items': content.get('data', content.get('result'))['items']
            }
            mongodb_uri = CONFIG['mongodb']['uri']
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
    """
    处理时间信息
    :param start_time: 开始时间
    :return: 时间信息元组, (start_time, date_time, unix_timestamp)
    """
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
    """
    查询地区信息
    :param name: 地区名称
    :param ip: IP 地址
    :return: 地区信息元组, (country, province, city)
    """
    is_ipv4 = re.fullmatch(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip)
    country, province, city = '', '', ''

    # 直辖市
    if name in ['北京', '上海', '天津', '重庆']:
        country = '中国'
        province = name + '市'
        city = province
    # 港澳台
    if name in ['香港', '澳门', '台湾']:
        country = '中国'
        province = name
        city = province

    # 非直辖市、非港澳台
    if province not in ['北京市', '上海市', '天津市', '重庆市', '香港', '澳门', '台湾']:
        with sqlite3.connect(f'{CURRENT_PATH}/data/divisions.db') as con:
            cur = con.cursor()

            # 优先使用城市名称查询
            rows = cur.execute('SELECT name, code FROM city WHERE name LIKE ?', (f'%{name}%',)).fetchall()
            if not rows:
                # 有可能是省直辖县级行政区划
                rows = cur.execute('SELECT name, code FROM area WHERE name LIKE ?', (f'%{name}%',)).fetchall()
            # 有且仅有一个结果
            if len(rows) == 1:
                city, cityCode = rows[0]
                provinceCode = cityCode[:2]
                province = cur.execute('''SELECT name FROM province WHERE code = ?''', (provinceCode,)).fetchone()[0]
                country = '中国'
            # 未查询到结果，或查询到多个结果，转为 IP 查询
            else:
                # 查询 Redis
                location = rd.hget('ip_location', ip)
                if location:
                    country, province, city = location.split(',')
                elif is_ipv4:
                    provinceCode = ''
                    cityCode = ''

                    try:
                        # 查询淘宝接口
                        url = 'https://ip.taobao.com/outGetIpInfo'
                        params = {
                            'ip': ip,
                            'accessKey': 'alibaba-inc'
                        }
                        resp = requests.get(url, params=params, timeout=(10, 30))
                        content = resp.json()
                        data = content['data']
                        country = data['country']
                        country = '' if country == 'XX' else country
                        province = data['region']
                        province = '' if province == 'XX' else province
                        city = data['city']
                        city = '' if city == 'XX' else city
                        if country == '中国':
                            provinceCode = data['region_id'][:2]
                            cityCode = data['city_id'][:4]
                    except:
                        try:
                            # 查询太平洋接口
                            url = 'https://whois.pconline.com.cn/ipJson.jsp'
                            params = {
                                'ip': ip,
                                'json': 'true'
                            }
                            resp = requests.get(url, params=params, timeout=(10, 30))
                            data = resp.json()
                            if data['proCode'] == '999999':
                                country = data['addr'].strip()
                                country = re.sub(r'(?<=国)\S+', '', country)
                            else:
                                country = '中国'
                                province = data['pro'].strip()
                                provinceCode = data['proCode'][:2]
                                city = data['city'].strip()
                                cityCode = data['cityCode'][:4]
                        except:
                            pass

                    if all([provinceCode, cityCode]) and (province not in ['香港', '澳门', '台湾']):
                        # 城市名称规范化
                        try:
                            row = None
                            if cityCode not in ['xx', '0', '999999']:
                                q = f'''SELECT name FROM city WHERE code = {cityCode}'''
                                row = cur.execute(q).fetchone()
                            elif provinceCode not in ['xx', '0', '999999']:
                                # 有可能是省直辖县级行政区划
                                q = f'''SELECT name FROM area WHERE name LIKE '%{name}%' AND provinceCode = {provinceCode}'''
                                row = cur.execute(q).fetchone()
                            city = row[0] if row else ''
                        except:
                            traceback.print_exc()
                            print(name, ip)
                        # 省份名称规范化
                        try:
                            row = None
                            row = cur.execute('''SELECT name FROM province WHERE code = ?''', (provinceCode,)).fetchone()
                            province = row[0] if row else ''
                        except:
                            traceback.print_exc()
                            print(name, ip)

    if all([country, province, city]):
        rd.hset('ip_location', ip, f'{country},{province},{city}')

    return (country, province, city)

def parseTrafficSource(source_from_type: str, source_url: str) -> dict:
    """
    解析来源信息
    :param source_from_type: 流量来源类型
    :param source_url: 前向地址
    :return: 来源信息字典, {referrer, referrer_host, search_engine, search_keyword, traffic_source_type}
    """
    search_engine = ''
    se_pattern = re.compile(r'(百度自然搜索|百度|Google|搜狗|Yahoo|中国雅虎|搜搜|有道|狗狗搜索|Bing|360搜索|即刻搜索|奇虎搜索|一淘搜索|搜酷|宜搜|UC搜索|好搜|神马搜索|中国搜索|头条|夸克搜索)')
    paid_pattern = re.compile(r'(百度搜索推广|百度信息流推广|百度品牌植入)')

    if source_from_type == '直接访问':
        traffic_source_type = '直接访问'
    elif paid_pattern.search(source_from_type):
        traffic_source_type = '百度推广'
        paid_type = paid_pattern.search(source_from_type).group(1)
        traffic_source_type = f'{traffic_source_type}-{paid_type}'
    elif se_pattern.search(source_from_type):
        traffic_source_type = '搜索引擎'
        search_engine = se_pattern.search(source_from_type).group(1)
    elif 'bing.com' in source_from_type:
        traffic_source_type = '搜索引擎'
        search_engine = 'Bing'
    elif 'http' in source_from_type:
        traffic_source_type = '外部链接'
    elif source_from_type == '自定义来源':
        traffic_source_type = '自定义来源'
    else:
        traffic_source_type = '其他'

    if source_url:
        referrer = source_url
        referrer_host = urlparse(referrer).netloc
    else:
        referrer = ''
        referrer_host = ''

    search_keyword = ''
    try:
        search_keyword = re.search(r'搜索词:([^\)]+))', source_from_type).group(1)
        search_keyword = unquote_plus(search_keyword)
    except:
        pass
    if (not search_keyword) and (traffic_source_type == '搜索引擎'):
        try:
            search_keyword = re.search(r'(kw｜keyword|q|query|wd|word)=([^&]+)', source_url).group(2)
            search_keyword = unquote_plus(search_keyword)
        except:
            pass

    traffic_source = {
        'referrer': referrer,
        'referrer_host': referrer_host,
        'search_engine': search_engine,
        'search_keyword': search_keyword,
        'traffic_source_type': traffic_source_type
    }

    return traffic_source

def parseSLD(host: str) -> str:
    """
    解析主域名
    :param host: 域名
    :return: 二级域名或主域名
    """
    ccTLD = ['ac', 'ad', 'ae', 'af', 'ag', 'ai', 'al', 'am', 'ao', 'aq', 'ar', 'as', 'at', 'au', 'aw', 'ax', 'az', 'ba', 'bb', 'bd', 'be', 'bf', 'bg', 'bh', \
            'bi', 'bj', 'bm', 'bn', 'bo', 'br', 'bs', 'bt', 'bw', 'by', 'bz', 'ca', 'cc', 'cd', 'cf', 'cg', 'ch', 'ci', 'ck', 'cl', 'cm', 'cn', 'co', 'cr', \
            'cu', 'cv', 'cw', 'cx', 'cy', 'cz', 'de', 'dj', 'dk', 'dm', 'do', 'dz', 'ec', 'ee', 'eg', 'er', 'es', 'et', 'eu', 'fi', 'fj', 'fk', 'fm', 'fo', \
            'fr', 'ga', 'gd', 'ge', 'gf', 'gg', 'gh', 'gi', 'gl', 'gm', 'gn', 'gp', 'gq', 'gr', 'gs', 'gt', 'gu', 'gw', 'gy', 'hk', 'hm', 'hn', 'hr', 'ht', \
            'hu', 'id', 'ie', 'il', 'im', 'in', 'io', 'iq', 'ir', 'is', 'it', 'je', 'jm', 'jo', 'jp', 'ke', 'kg', 'kh', 'ki', 'km', 'kn', 'kp', 'kr', 'kw', \
            'ky', 'kz', 'la', 'lb', 'lc', 'li', 'lk', 'lr', 'ls', 'lt', 'lu', 'lv', 'ly', 'ma', 'mc', 'md', 'me', 'mg', 'mh', 'mk', 'ml', 'mm', 'mn', 'mo', \
            'mp', 'mq', 'mr', 'ms', 'mt', 'mu', 'mv', 'mw', 'mx', 'my', 'mz', 'na', 'nc', 'ne', 'nf', 'ng', 'ni', 'nl', 'no', 'np', 'nr', 'nu', 'nz', 'om', \
            'pa', 'pe', 'pf', 'pg', 'ph', 'pk', 'pl', 'pm', 'pn', 'pr', 'ps', 'pt', 'pw', 'py', 'qa', 're', 'ro', 'rs', 'ru', 'rw', 'sa', 'sb', 'sc', 'sd', \
            'se', 'sg', 'sh', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sr', 'ss', 'st', 'su', 'sv', 'sx', 'sy', 'sz', 'tc', 'td', 'tf', 'tg', 'th', 'tj', 'tk', \
            'tl', 'tm', 'tn', 'to', 'tr', 'tt', 'tv', 'tw', 'tz', 'ua', 'ug', 'uk', 'us', 'uy', 'uz', 'va', 'vc', 've', 'vg', 'vi', 'vn', 'vu', 'wf', 'ws', \
            'ye', 'yt', 'za', 'zm', 'zw', 'bl', 'bq', 'bv', 'eh', 'gb', 'mf', 'sj', 'um']
    TLD = ['com', 'net', 'org', 'gov', 'edu']
    terms = host.split('.')
    if (terms[-1] in ccTLD) and (terms[-2] in TLD):
        sld = '.'.join(terms[-3:])
    else:
        sld = '.'.join(terms[-2:])
    return sld

def parsetUrlPath(url: str) -> tuple:
    """
    解析url路径信息
    :param url: url
    :return: 路径信息元组, (url_path, url_full_path)
    """
    try:
        url_path = '/' + re.sub(r'[\?#%&]\S*', '', url.split('/')[3])
        url_full_path = urlparse(url).path
    except IndexError:
        url_path = '/'
        url_full_path = '/'
    return (url_path, url_full_path)

def parsetracking_arams(url: str) -> dict:
    """
    解析 url 中的 tracking 参数信息
    :param url: url
    :return: tracking 参数信息字典, {utm_source, utm_medium, utm_campaign, utm_term, utm_content, hmsr, hmpl, hmcu, hmkw, hmci, ct_params}
    """
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
        'ct_params': {**{param: query_params.get(param, '') for param in DIMENSIONS['custom_tracking_params']}} # custom tracking params in dimensions.yaml
    }

    return tracking_params

def getDuration(duration: str) -> int:
    """
    修正时长
    :param duration: 时长
    :return: 修正后的时长
    """
    if duration == '正在访问':
        duration = -10000
    elif duration == '未知':
        duration = -20000
    else:
        duration = int(duration)
    return duration

def saveFistVisitTime(visitor_id: str, start_time: str, is_first_time: bool) -> None:
    """
    保存首次访问时间
    :param visitor_id: 访客id
    :param start_time: 会话开始时间
    :param is_first_time: 是否首次访问
    :return: None
    """
    if is_first_time:
        rd.set(f'first_day_{visitor_id}', arrow.get(start_time).format('YYYY-MM-DD'), ex=60*60*24*2) # expire in 2 days.
    return None

def getScreenSize(resolution: str) -> tuple:
    """
    获取屏幕宽高
    :param resolution: 屏幕尺寸
    :return: 屏幕宽高元祖
    """
    try:
        screen_width, screen_height = resolution.split('x')
        screen_width = int(screen_width)
        screen_height = int(screen_height)
    except:
        screen_height, screen_width = 0, 0
    return (screen_height, screen_width)

def parseOnSiteSearchTerm(url: str) -> str:
    """
    解析 url 中的搜索词
    :param url: url
    :return: 搜索词
    """
    onsite_search_term = ''
    query_params = parse_qs(urlparse(url).query, keep_blank_values=True)
    query_params = {k: v[0] for k, v in query_params.items()}
    onsite_search_params = DIMENSIONS['onsite_search_params']
    for k, v in query_params.items():
        term = unquote_plus(v)
        onsite_search_term = '' if k not in onsite_search_params else term
        if onsite_search_term:
            break
    return onsite_search_term

def parseEnhancedEvent(url: str, duration: int, is_first_time: bool, is_session_start: bool) -> list:
    """
    解析 url, 生成增强型事件列表
    :param url: url
    :param duration: 时长
    :param is_first_time: 是否首次访问
    :param is_session_start: 是否会话开始
    :return: 增强型事件列表
    """
    enhanced_event_list = ['page_view']
    if duration > 1:
        enhanced_event_list.append('user_engagement')
    if is_first_time:
        enhanced_event_list.append('first_visit')
    if is_session_start:
        enhanced_event_list.append('session_start')
    query_params = parse_qs(urlparse(url).query, keep_blank_values=True)
    onsite_search_params = DIMENSIONS['onsite_search_params']
    if any(param in query_params for param in onsite_search_params):
        enhanced_event_list.append('view_search_results')
    enhanced_event_list = sorted(enhanced_event_list)
    return enhanced_event_list

def querySourceCategory(referrer_host: str) -> str:
    """
    匹配流量渠道组
    :param referrer_host: 首次前向域名
    :return: 流量渠道组
    """
    category = ''
    referrer_host = re.sub(r'^links?\.', '', referrer_host) # e.g. link.zhihu.com -> zhihu.com
    sld = '.'.join(referrer_host.split('.')[-2:]) # Second-level domain, e.g. book.douban.com -> douban.com
    brand = sld.split('.')[0] # e.g. douban.com -> douban
    with sqlite3.connect(f'{CURRENT_PATH}/data/data.db') as con:
        cur = con.cursor()
        # match full referrer_host
        cur.execute(
            f'''
                SELECT category
                FROM source_category
                WHERE source = '{referrer_host}'
            '''
        )
        source_category = cur.fetchone()
        if source_category:
            category = source_category[0]
        else:
            # match Second-level domain
            cur.execute(
                f'''
                    SELECT category
                    FROM source_category
                    WHERE source = '{sld}'
                '''
            )
            source_category = cur.fetchone()
            if source_category:
                category = source_category[0]
            else:
                # match brand
                cur.execute(
                    f'''
                        SELECT category
                        FROM source_category
                        WHERE source = '{brand}'
                    '''
                )
                source_category = cur.fetchone()
                if source_category:
                    category = source_category[0]
    return category

def parseEnhancedTrafficGroup(traffic_source_type, referrer_host, utm_source, utm_medium, utm_campaign) -> str:
    """
    解析增强型流量渠道分组
    :param traffic_source_type: 流量来源类型
    :param referrer_host: 前向域名
    :param utm_source: utm_source
    :param utm_medium: utm_medium
    :param utm_campaign: utm_campaign
    :return: 增强型流量渠道分组
    """
    traffic_channel_group = DIMENSIONS['traffic_channel_group']
    traffic_channel_group = {x: True for x in traffic_channel_group}
    group = ''
    referrer_host = referrer_host.lower()
    utm_source = utm_source.lower()
    utm_medium = utm_medium.lower()
    utm_campaign = utm_campaign.lower()
    category = querySourceCategory(referrer_host)
    is_paid = re.search(r'^(.*cp.*|ppc|retargeting|paid.*)$', utm_medium) or re.search(r'百度推广', traffic_source_type)

    if utm_medium == 'affiliate':
        group = 'affiliates'
    if utm_medium == 'audio':
        group = 'audio'
    if 'cross-network' in utm_campaign:
        group = 'cross-network'
    if (traffic_source_type == '直接访问') and (not utm_medium):
        group = 'direct'
    if utm_medium in ['display', 'banner', 'expandable', 'interstitial', 'cpm']:
        group = 'display'
    if re.search(r'email|e-mail|e_mail|mail|newsletter', utm_source) or re.search(r'email|e-mail|e_mail|mail|newsletter', utm_medium):
        group = 'email'
    if re.search(r'push$|mobile|notification', utm_medium) or (utm_source == 'firebase'):
        group = 'mobile_push_notifications'
    if not is_paid:
        if (category == 'search') or (traffic_source_type == '搜索引擎'):
            group = 'organic_search'
        elif (category == 'shopping' or re.search(r'^(.*(([^a-df-z]|^)shop|shopping).*)$', utm_campaign)):
            group = 'organic_shopping'
        elif (category == 'social') or (utm_medium in ['social', 'social-network', 'social-media', 'sm', 'social network', 'social media', 'social_network', 'social_media']):
            group = 'organic_social'
        elif (category == 'video') or re.search(r'^(.*video.*)$', utm_medium):
            group = 'organic_video'
    else:
        if category == 'search':
            group = 'paid_search'
        elif (category == 'shopping') or re.search(r'^(.*(([^a-df-z]|^)shop|shopping).*)$', utm_campaign):
            group = 'paid_shopping'
        elif category == 'social':
            group = 'paid_social'
        elif category == 'video':
            group = 'paid_video'
        else:
            group = 'paid_other'
    if utm_medium in ['referral', 'app', 'link']:
        group = 'referral'
    if (utm_source == 'sms') or (utm_medium == 'sms'):
        group = 'sms'

    if not group:
        if traffic_source_type == '直接访问':
            group = 'direct'
        elif '百度搜索推广' in traffic_source_type:
            group = 'paid_search'
        elif re.search(r'百度信息流推广|百度品牌植入', traffic_source_type):
            group = 'paid_other'
        elif traffic_source_type == '搜索引擎':
            group = 'organic_search'
        elif traffic_source_type == '外部链接':
            group = 'referral'
        elif traffic_source_type == '自定义来源':
            group = 'direct'
        elif traffic_source_type == '站内来源':
            group = 'internal'
        else:
            group = 'other'

    if group not in traffic_channel_group:
        group = 'not_set'

    return group

def parseWXShareFrom(browser_type, referrer_host, url) -> str:
    """
    解析微信分享来源
    :param browser_type: 浏览器类型
    :param referrer_host: 前向域名
    :param url: 页面地址
    :return: 微信分享来源
    """
    share_from = ''
    if browser_type == 'weixin':
        if referrer_host in ['mp.weixin.qq.com', 'mp.weixinbridge.com']:
            share_from = '公众号'
        elif 'from=timeline' in url:
            share_from = '朋友圈'
        elif 'from=groupmessage' in url:
            share_from = '群聊'
        elif 'from=singlemessage' in url:
            share_from = '单聊'
        else:
            share_from = '其他'
    return share_from


if __name__ == '__main__':
    print(f'- CONFIG\n{CONFIG}\n- DIMENSIONS\n{DIMENSIONS}')
