#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from utils import *
from hashlib import md5
import redis


rd_pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
rd = redis.Redis(connection_pool=rd_pool)


class baiduTongji(object):
    def __init__(self, debug=False):
        super(baiduTongji, self).__init__()
        self.debug = debug
        self.sess = requests.Session()
        config = loadConfig()
        self.client_id = config['api_key']
        self.client_secret = config['secret_key']
        self.auth_code = config['auth_code']
        token_info = queryTokenInfo()
        self.access_token = token_info['access_token']['value']
        self.refresh_token = token_info['refresh_token']['value']
        self.access_token_expires = token_info['access_token']['expires']
        if not self.debug:
            if not self.access_token:
                self.genToken()
            if self.access_token_expires < arrow.utcnow().timestamp():
                self.refreshToken()

    def genToken(self) -> dict:
        url = 'http://openapi.baidu.com/oauth/2.0/token'
        params = {
            'grant_type' : 'authorization_code',
            'code' : self.auth_code,
            'client_id' : self.client_id,
            'client_secret' : self.client_secret,
            'redirect_uri' : 'oob'
        }
        resp = self.sess.get(url, params=params)
        content = resp.json()
        if content.get('error'):
            print(content)
            return content
        self.refresh_token = content['refresh_token']
        self.access_token = content['access_token']
        self.access_token_expires = arrow.utcnow().timestamp() + content['expires_in']
        token_info = {
            'access_token': {
                'value': self.access_token,
                'expires': self.access_token_expires
            },
            'refresh_token': {
                'value': self.refresh_token,
                'expires': 0
            }
        }
        saveTokenInfo(token_info)
        return content

    def refreshToken(self) -> dict:
        url = f'http://openapi.baidu.com/oauth/2.0/token'
        params = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token
        }
        resp = self.sess.get(url, params=params)
        content = resp.json()
        if content.get('error'):
            print(content)
            return content
        self.refresh_token = content['refresh_token']
        self.access_token = content['access_token']
        self.access_token_expires = arrow.utcnow().timestamp() + content['expires_in']
        token_info = {
            'access_token': {
                'value': self.access_token,
                'expires': self.access_token_expires
            },
            'refresh_token': {
                'value': self.refresh_token,
                'expires': 0
            }
        }
        saveTokenInfo(token_info)
        return content

    def getSiteList(self) -> dict:
        url = f'https://openapi.baidu.com/rest/2.0/tongji/config/getSiteList'
        params = {
            'access_token': self.access_token,
        }
        resp = self.sess.get(url, params=params)
        content = resp.json()
        return content

    def fetchRealTimeData(self, site_id, page_size=1000, visitor_id='') -> list:
        if self.debug:
            url = 'https://tongji.baidu.com/web5/demo/ajax/post'
            data = {
                'siteId': site_id,
                'order': 'start_time,desc',
                'offset': 0,
                'pageSize': page_size,
                'tab': 'visit',
                'timeSpan': 14,
                'indicators': 'start_time,area,source,access_page,searchword,visitorId,ip,visit_time,visit_pages',
                'anti': 0,
                'reportId': 4,
                'method': 'trend/latest/a',
                'queryId': '',
                'visitorId': visitor_id
            }
            resp = self.sess.post(url, data=data, timeout=(10, 30))
            content = resp.json()
            items = content['data']['items']
        else:
            url = 'https://openapi.baidu.com/rest/2.0/tongji/report/getData'
            params = {
                'access_token': self.access_token,
                'site_id': site_id,
                'method': 'trend/latest/a',
                'metrics': 'area,source,access_page,keyword,searchword,is_ad,visitorId,ip,visit_time,visit_pages,start_time',
                'order': 'start_time,desc',
                'max_results': page_size, # max allowed is 1000
                'visitorId': visitor_id
            }
            resp = self.sess.get(url, params=params, timeout=(10, 30))
            content = resp.json()
            items = content['result']['items']

        saveRawData(site_id, content)

        outline = items[1]
        detail = items[0]
        l = len(outline)
        result = []
        for i in range(l):
            o = outline[i]
            d = detail[i][0]['detail']

            ## session info
            start_time, area, source, access_page, search_word, ip, visitor_id, duration, visit_pages = o

            start_time, date_time, unix_timestamp = getTime(start_time)
            country, province, city = queryDivision(area, ip)

            if access_page != d['accessPage']:
                access_page = d['accessPage']
            landing_page = access_page
            if source != d['fromType']:
                source = d['fromType']

            source_from_type = source['fromType']
            source_tip = source.get('tip', '')
            source_url = source.get('url', '')
            source_url = '' if not source_url else source_url
            traffic_source = parseTrafficSource(source_from_type, source_url)
            traffic_source_type = traffic_source['traffic_source_type']
            referrer = traffic_source['referrer']
            referrer_host = traffic_source['referrer_host']
            search_engine = traffic_source['search_engine']
            access_host = urlparse(access_page).netloc
            access_path, access_full_path = parsetUrlPath(access_page)
            access_page_query = urlparse(access_page).query

            trackingParams = parseTrackingParams(access_page)
            utm_source = trackingParams['utm_source']
            utm_medium = trackingParams['utm_medium']
            utm_campaign = trackingParams['utm_campaign']
            utm_term = trackingParams['utm_term']
            utm_content = trackingParams['utm_content']
            hmsr = trackingParams['hmsr']
            hmpl = trackingParams['hmpl']
            hmcu = trackingParams['hmcu']
            hmkw = trackingParams['hmkw']
            hmci = trackingParams['hmci']
            channel_id = trackingParams['channel_id']

            search_keyword = unquote_plus(search_word)
            search_keyword = '' if search_keyword == '--' else search_keyword
            search_keyword = re.sub(r'[\'\"]', '', search_keyword)
            search_keyword = traffic_source['search_keyword'] if not search_keyword else search_keyword
            duration = getDuration(duration)
            visit_pages = int(visit_pages)
            anti_code = d['antiCode']
            anti_code = '' if anti_code == '--' else anti_code
            browser = d['browser']
            browser_type = d['browserType']
            color_depth = d['color']
            cookie = d['cookie']
            cookie_enable = True if cookie == '支持' else False
            device_type = d['deviceType']
            end_page = d['endPage']
            flash_version = d['flash']
            from_word = d['from_word']
            from_word = unquote_plus(from_word)
            from_word = '' if from_word == '--' else from_word
            from_word = re.sub(r'[\'\"]', '', from_word)
            ip_status = d['ipStatus']
            isp = d['isp']
            ip_isp = isp
            java = d['java']
            java_enable = True if java == '支持' else False
            language = d['language']
            latest_visit_time = d['lastVisitTime']
            is_first_time = True if latest_visit_time == '首次访问' else False

            if is_first_time:
                rd.set(f'first_day_{visitor_id}', arrow.get(start_time).format('YYYY-MM-DD'), ex=60*60*24*2)
            first_day = rd.get(f'first_day_{visitor_id}') or False
            start_day = arrow.get(start_time).format('YYYY-MM-DD')
            is_first_day = start_day == first_day or False

            latest_visit_time = start_time if is_first_time else latest_visit_time
            latest_visit_time = arrow.get(latest_visit_time).format('YYYY-MM-DD HH:mm:ss')
            _os = d['os']
            os_type = d['osType']
            resolution = d['resolution']
            b_user_id = d['userId']
            visitor_frequency = int(d['visitorFrequency'])
            visitor_status = d['visitorStatus']
            visitor_type = d['visitorType']
            visitor_type = 1 if visitor_type == '老访客' else 0

            session_id = 's_' + md5(f'{visitor_id}_{int(unix_timestamp)}_{access_page}'.encode('utf-8')).hexdigest().lower()

            session = {
                'session_id': session_id,
                'visitor_id': visitor_id,
                'start_time': start_time,
                'date_time': date_time,
                'unix_timestamp': unix_timestamp,
                'access_full_path': access_full_path,
                'access_host': access_host,
                'access_page': access_page,
                'access_page_query': access_page_query,
                'access_path': access_path,
                'anti_code': anti_code,
                'b_user_id': b_user_id,
                'browser': browser,
                'browser_type': browser_type,
                'channel_id': channel_id,
                'city': city,
                'color_depth': color_depth,
                'cookie_enable': cookie_enable,
                'country': country,
                'device_type': device_type,
                'duration': duration,
                'end_page': end_page,
                'flash_version': flash_version,
                'from_word': from_word,
                'hmci': hmci,
                'hmcu': hmcu,
                'hmkw': hmkw,
                'hmpl': hmpl,
                'hmsr': hmsr,
                'ip': ip,
                'ip_isp': ip_isp,
                'ip_status': ip_status,
                'is_first_day': is_first_day,
                'is_first_time': is_first_time,
                'java_enable': java_enable,
                'landing_page': landing_page,
                'language': language,
                'latest_visit_time': latest_visit_time,
                'os': _os,
                'os_type': os_type,
                'province': province,
                'raw_area': area,
                'referrer': referrer,
                'referrer_host': referrer_host,
                'resolution': resolution,
                'search_engine': search_engine,
                'search_keyword': search_keyword,
                'source_from_type': source_from_type,
                'source_tip': source_tip,
                'source_url': source_url,
                'traffic_source_type': traffic_source_type,
                'utm_campaign': utm_campaign,
                'utm_content': utm_content,
                'utm_medium': utm_medium,
                'utm_source': utm_source,
                'utm_term': utm_term,
                'visit_pages': visit_pages,
                'visitor_frequency': visitor_frequency,
                'visitor_status': visitor_status,
                'visitor_type': visitor_type,
             }


            ## visitor info
            if visitor_type == 0:
                first_visit_time = start_time
                utm_source = utm_source
                utm_medium = utm_medium
                utm_campaign = utm_campaign
                utm_term = utm_term
                utm_content = utm_content
                channel_id = channel_id
                first_referrer = referrer
                first_referrer_host = referrer_host
                first_search_engine = search_engine
                first_search_keyword = search_keyword
                first_landing_page = landing_page
                first_traffic_source_type = traffic_source_type
            else:
                first_visit_time = None
                utm_source = ''
                utm_medium = ''
                utm_campaign = ''
                utm_term = ''
                utm_content = ''
                channel_id = ''
                first_referrer = ''
                first_referrer_host = ''
                first_search_engine = ''
                first_search_keyword = ''
                first_landing_page = ''
                first_traffic_source_type = ''

            visitor = {
                'visitor_id': visitor_id,
                'first_visit_time': first_visit_time,
                'channel_id': channel_id,
                'first_landing_page': first_landing_page,
                'first_referrer': first_referrer,
                'first_referrer_host': first_referrer_host,
                'first_search_engine': first_search_engine,
                'first_search_keyword': first_search_keyword,
                'first_traffic_source_type': first_traffic_source_type,
                'utm_campaign': utm_campaign,
                'utm_content': utm_content,
                'utm_medium': utm_medium,
                'utm_source': utm_source,
                'utm_term': utm_term,
            }


            ## pageview info
            latest_channel_id = channel_id
            latest_landing_page = landing_page
            latest_referrer = referrer
            latest_referrer_host = referrer_host
            latest_search_engine = search_engine
            latest_search_keyword = search_keyword
            latest_traffic_source_type = traffic_source_type
            latest_utm_source = utm_source
            latest_utm_medium = utm_medium
            latest_utm_campaign = utm_campaign
            latest_utm_term = utm_term
            latest_utm_content = utm_content

            paths = sorted(d['paths'], key=lambda x: x[0]) # sort by start_time asc
            event_list = []
            for idx, path in enumerate(paths):
                start_time, duration, url = path

                if idx > 0:
                    referrer = paths[idx - 1][2] # previous url
                    referrer_host = urlparse(referrer).netloc
                    is_first_time = False

                receive_time, date_time, unix_timestamp = getTime(start_time)
                event_duration = getDuration(duration)
                url_host = urlparse(url).netloc
                traffic_source_type = '站内来源' if url_host == referrer_host else traffic_source_type
                url_path, url_full_path = parsetUrlPath(url)
                url_query = urlparse(url).query
                trackingParams = parseTrackingParams(url)
                utm_source = trackingParams['utm_source']
                utm_medium = trackingParams['utm_medium']
                utm_campaign = trackingParams['utm_campaign']
                utm_term = trackingParams['utm_term']
                utm_content = trackingParams['utm_content']
                hmsr = trackingParams['hmsr']
                hmpl = trackingParams['hmpl']
                hmcu = trackingParams['hmcu']
                hmkw = trackingParams['hmkw']
                hmci = trackingParams['hmci']

                event_id = 'p_' + md5(f'{session_id}_{int(unix_timestamp)}_{url}'.encode('utf-8')).hexdigest().lower()

                pageview = {
                    'event_id': event_id,
                    'session_id': session_id,
                    'visitor_id': visitor_id,
                    'receive_time': receive_time,
                    'date_time': date_time,
                    'unix_timestamp': unix_timestamp,
                    'browser': browser,
                    'browser_type': browser_type,
                    'channel_id': channel_id,
                    'city': city,
                    'country': country,
                    'event': 'pageview',
                    'event_duration': event_duration,
                    'hmci': hmci,
                    'hmcu': hmcu,
                    'hmkw': hmkw,
                    'hmpl': hmpl,
                    'hmsr': hmsr,
                    'ip': ip,
                    'is_first_time': is_first_time,
                    'latest_channel_id': latest_channel_id,
                    'latest_landing_page': latest_landing_page,
                    'latest_referrer': latest_referrer,
                    'latest_referrer_host': latest_referrer_host,
                    'latest_search_engine': latest_search_engine,
                    'latest_search_keyword': latest_search_keyword,
                    'latest_traffic_source_type': latest_traffic_source_type,
                    'latest_utm_campaign': latest_utm_campaign,
                    'latest_utm_content': latest_utm_content,
                    'latest_utm_medium': latest_utm_medium,
                    'latest_utm_source': latest_utm_source,
                    'latest_utm_term': latest_utm_term,
                    'os': _os,
                    'os_type': os_type,
                    'province': province,
                    'referrer': referrer,
                    'referrer_host': referrer_host,
                    'traffic_source_type': traffic_source_type,
                    'url': url,
                    'url_full_path': url_full_path,
                    'url_host': url_host,
                    'url_path': url_path,
                    'url_query': url_query,
                    'utm_campaign': utm_campaign,
                    'utm_content': utm_content,
                    'utm_medium': utm_medium,
                    'utm_source': utm_source,
                    'utm_term': utm_term,
                }
                event_list.append(pageview)

            result.append(
                {
                    'visitor': visitor,
                    'session': session,
                    'event_list': event_list
                }
            )

        return result


if __name__ == '__main__':
    pass
