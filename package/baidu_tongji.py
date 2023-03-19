#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from hashlib import md5

from utils import *


class BaiduTongji(object):
    def __init__(self, debug: bool = False ):
        self.debug = debug
        self.sess = requests.Session()
        self.client_id = CONFIG['baidu']['api_key']
        self.client_secret = CONFIG['baidu']['secret_key']
        self.auth_code = CONFIG['baidu']['auth_code']
        token_info = queryTokenInfo()
        self.access_token = token_info['access_token']['value']
        self.refresh_token = token_info['refresh_token']['value']
        self.access_token_expires = token_info['access_token']['expires']
        if not self.debug:
            if not self.access_token:
                self.genToken()
            if self.access_token_expires < arrow.utcnow().timestamp():
                self.refreshAccessToken()

    def genToken(self) -> dict:
        """
        生成 token
        :return: token 信息字典
        """
        url = 'http://openapi.baidu.com/oauth/2.0/token'
        params = {
            'grant_type': 'authorization_code',
            'code': self.auth_code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': 'oob'
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

    def refreshAccessToken(self) -> dict:
        """
        刷新 token
        :return: token 信息字典
        """
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

    def getSiteList(self) -> list:
        """
        获取站点信息列表
        :return: 站点信息列表
        """
        url = f'https://openapi.baidu.com/rest/2.0/tongji/config/getSiteList'
        params = {
            'access_token': self.access_token,
        }
        resp = self.sess.get(url, params=params)
        content = resp.json()
        site_list = content['list']
        return site_list

    def fetchRealTimeData(self, site_id: str, page_size: int=1000, visitor_id: str='') -> list:
        """
        获取实时数据
        :param site_id: 站点 ID
        :param page_size: 每页条数
        :param visitor_id: 访客 ID
        :return: 实时数据列表， [visitor, session, event_list]
        """
        if self.debug:
            url = 'https://tongji.baidu.com/web5/demo/ajax/post'
            data = {
                'siteId': site_id,
                'order': 'start_time,desc',
                'offset': 0,
                'pageSize': page_size,
                'tab': 'visit',
                'timeSpan': 14,
                'indicators': 'area,source,access_page,keyword,searchword,is_ad,visitorId,ip,visit_time,visit_pages,start_time',
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
        result = []
        for i in range(len(outline)):
            o = outline[i]
            d = detail[i][0]['detail']

            """
            session info
            """
            start_time, area, source, access_page, search_word, ip, visitor_id, duration, visit_pages = o

            start_time, date_time, unix_timestamp= getTime(start_time)
            raw_area = area
            country, province, city = queryDivision(area, ip)
            landing_page = access_page
            source = d['fromType'] # Use the fromType from detail because the outline does not contain the search_keyword information.
            source_from_type = source.get('fromType', '')
            source_tip = source.get('tip', '')
            source_url = source.get('url', '')
            source_url = '' if not source_url else source_url
            traffic_source = parseTrafficSource(source_from_type, source_url)
            traffic_source_type = traffic_source['traffic_source_type']
            referrer = traffic_source['referrer']
            referrer_host = traffic_source['referrer_host']
            referrer_host_sld = '.'.join(referrer_host.split('.')[-2:]) # Second-level domain, e.g. book.douban.com -> douban.com, movie.douban.com -> douban.com
            search_engine = traffic_source['search_engine']
            access_host = urlparse(access_page).netloc
            access_path, access_full_path = parsetUrlPath(access_page)
            access_page_query = urlparse(access_page).query
            tracking_arams = parsetracking_arams(access_page)
            utm_source = tracking_arams['utm_source']
            utm_medium = tracking_arams['utm_medium']
            utm_campaign = tracking_arams['utm_campaign']
            utm_term = tracking_arams['utm_term']
            utm_content = tracking_arams['utm_content']
            hmsr = tracking_arams['hmsr']
            hmpl = tracking_arams['hmpl']
            hmcu = tracking_arams['hmcu']
            hmkw = tracking_arams['hmkw']
            hmci = tracking_arams['hmci']
            ct_params = tracking_arams['ct_params']
            search_keyword = unquote_plus(search_word)
            search_keyword = '' if search_keyword == '--' else search_keyword
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
            utm_term = from_word if (from_word and not utm_term) else utm_term
            ip_status = d['ipStatus']
            isp = d['isp']
            ip_isp = isp
            java = d['java']
            java_enable = True if java == '支持' else False
            browser_language = d['language']
            last_visit_time = d['lastVisitTime']
            is_first_time = True if last_visit_time == '首次访问' else False
            saveFistVisitTime(visitor_id, start_time, is_first_time)
            first_day = rd.get(f'first_day_{visitor_id}') or False
            start_day = arrow.get(start_time).format('YYYY-MM-DD')
            is_first_day = start_day == first_day or False
            last_visit_time = start_time if is_first_time else last_visit_time
            last_visit_time = arrow.get(last_visit_time).format('YYYY-MM-DD HH:mm:ss')
            _os = d['os']
            os_type = d['osType']
            resolution = d['resolution']
            screen_width, screen_height = getScreenSize(resolution)
            b_user_id = d['userId']
            visitor_frequency = int(d['visitorFrequency'])
            visitor_status = d['visitorStatus']
            visitor_type = d['visitorType']
            visitor_type = 1 if visitor_type == '老访客' else 0
            enhanced_traffic_group = parseEnhancedTrafficGroup(traffic_source_type, referrer_host, utm_source, utm_medium, utm_campaign)
            wx_share_from = parseWXShareFrom(browser_type, referrer_host, access_page)

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
                'browser_language': browser_language,
                'browser_type': browser_type,
                'city': city,
                'color_depth': color_depth,
                'cookie_enable': cookie_enable,
                'country': country,
                'device_type': device_type,
                'duration': duration,
                'end_page': end_page,
                'enhanced_traffic_group': enhanced_traffic_group,
                'first_event_id': '',
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
                'last_event_id': '',
                'last_visit_time': last_visit_time,
                'os': _os,
                'os_type': os_type,
                'province': province,
                'raw_area': raw_area,
                'referrer': referrer,
                'referrer_host': referrer_host,
                'referrer_host_sld': referrer_host_sld,
                'resolution': resolution,
                'screen_height': screen_height,
                'screen_width': screen_width,
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
                'wx_share_from': wx_share_from,
                **ct_params
             }


            """
            visitor info
            """
            if visitor_type == 0:
                first_visit_time = start_time
                utm_source = utm_source
                utm_medium = utm_medium
                utm_campaign = utm_campaign
                utm_term = utm_term
                utm_content = utm_content
                first_referrer = referrer
                first_referrer_host = referrer_host
                first_search_engine = search_engine
                first_search_keyword = search_keyword
                first_landing_page = landing_page
                first_traffic_source_type = traffic_source_type
            else:
                first_visit_time = '1970-01-01 00:00:01'
                utm_source = ''
                utm_medium = ''
                utm_campaign = ''
                utm_term = ''
                utm_content = ''
                first_referrer = ''
                first_referrer_host = ''
                first_search_engine = ''
                first_search_keyword = ''
                first_landing_page = ''
                first_traffic_source_type = ''

            visitor = {
                'visitor_id': visitor_id,
                'first_visit_time': first_visit_time,
                'last_visit_time': start_time,
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
                'utm_term': utm_term
            }


            """
            event info
            """
            latest_landing_page = landing_page
            latest_referrer = referrer
            latest_referrer_host = referrer_host
            latest_referrer_host_sld = referrer_host_sld
            latest_search_engine = search_engine
            latest_search_keyword = search_keyword
            latest_traffic_source_type = traffic_source_type
            latest_utm_source = utm_source
            latest_utm_medium = utm_medium
            latest_utm_campaign = utm_campaign
            latest_utm_term = utm_term
            latest_utm_content = utm_content
            session_duration = duration
            session_start_time = start_time

            paths = sorted(d['paths'], key=lambda x: x[0]) # sort by event start_time asc
            event_list = []
            l = len(paths)
            for idx, path in enumerate(paths):
                start_time, duration, url = path

                receive_time, date_time, unix_timestamp= getTime(start_time)
                event_id = 'p_' + md5(f'{session_id}_{int(unix_timestamp)}_{url}'.encode('utf-8')).hexdigest().lower()

                if idx == 0:
                    is_session_start = True
                    session['first_event_id'] = event_id
                    referrer = latest_referrer_host
                    referrer_host = latest_referrer_host
                else:
                    is_session_start = False
                    is_first_time = False
                    referrer = paths[idx - 1][2] # previous url
                    referrer_host = urlparse(referrer).netloc

                if (idx == l - 1) and (session_duration > 0) and (url == end_page):
                    is_session_end = True
                    session['last_event_id'] = event_id
                else:
                    is_session_end = False

                duration = getDuration(duration)
                referrer_host_sld = '.'.join(referrer_host.split('.')[-2:])
                url_host = urlparse(url).netloc
                url_host_sld = '.'.join(url_host.split('.')[-2:])
                traffic_source_type = '站内来源' if url_host_sld == referrer_host_sld else traffic_source_type
                url_path, url_full_path = parsetUrlPath(url)
                url_query = urlparse(url).query
                tracking_arams = parsetracking_arams(url)
                utm_source = tracking_arams['utm_source']
                utm_medium = tracking_arams['utm_medium']
                utm_campaign = tracking_arams['utm_campaign']
                utm_term = tracking_arams['utm_term']
                utm_content = tracking_arams['utm_content']
                hmsr = tracking_arams['hmsr']
                hmpl = tracking_arams['hmpl']
                hmcu = tracking_arams['hmcu']
                hmkw = tracking_arams['hmkw']
                hmci = tracking_arams['hmci']
                ct_params = tracking_arams['ct_params']
                onsite_search_term = parseOnSiteSearchTerm(url)
                enhanced_event_list = parseEnhancedEvent(url, duration, is_first_day, is_session_start)
                enhanced_traffic_group = parseEnhancedTrafficGroup(traffic_source_type, referrer_host, utm_source, utm_medium, utm_campaign)
                wx_share_from = parseWXShareFrom(browser_type, referrer_host, access_page)

                event = {
                    'event_id': event_id,
                    'session_id': session_id,
                    'visitor_id': visitor_id,
                    'receive_time': receive_time,
                    'date_time': date_time,
                    'unix_timestamp': unix_timestamp,
                    'event': 'page_view',
                    'browser': browser,
                    'browser_language': browser_language,
                    'browser_type': browser_type,
                    'city': city,
                    'country': country,
                    'device_type': device_type,
                    'duration': duration,
                    'enhanced_event_list': enhanced_event_list,
                    'enhanced_traffic_group': enhanced_traffic_group,
                    'hmci': hmci,
                    'hmcu': hmcu,
                    'hmkw': hmkw,
                    'hmpl': hmpl,
                    'hmsr': hmsr,
                    'ip': ip,
                    'is_first_day': is_first_day,
                    'is_first_time': is_first_time,
                    'is_session_end': is_session_end,
                    'is_session_start': is_session_start,
                    'latest_landing_page': latest_landing_page,
                    'latest_referrer': latest_referrer,
                    'latest_referrer_host': latest_referrer_host,
                    'latest_referrer_host_sld': latest_referrer_host_sld,
                    'latest_search_engine': latest_search_engine,
                    'latest_search_keyword': latest_search_keyword,
                    'latest_traffic_source_type': latest_traffic_source_type,
                    'latest_utm_campaign': latest_utm_campaign,
                    'latest_utm_content': latest_utm_content,
                    'latest_utm_medium': latest_utm_medium,
                    'latest_utm_source': latest_utm_source,
                    'latest_utm_term': latest_utm_term,
                    'onsite_search_term': onsite_search_term,
                    'os': _os,
                    'os_type': os_type,
                    'province': province,
                    'referrer': referrer,
                    'referrer_host': referrer_host,
                    'referrer_host_sld': referrer_host_sld,
                    'resolution': resolution,
                    'screen_height': screen_height,
                    'screen_width': screen_width,
                    'session_start_time': session_start_time,
                    'traffic_source_type': traffic_source_type,
                    'url': url,
                    'url_full_path': url_full_path,
                    'url_host': url_host,
                    'url_host_sld': url_host_sld,
                    'url_path': url_path,
                    'url_query': url_query,
                    'utm_campaign': utm_campaign,
                    'utm_content': utm_content,
                    'utm_medium': utm_medium,
                    'utm_source': utm_source,
                    'utm_term': utm_term,
                    'visitor_type': visitor_type,
                    'wx_share_from': wx_share_from,
                    **ct_params
                }
                event_list.append(event)

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
