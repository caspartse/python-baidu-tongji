
#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import codecs
import os
import shutil
import sys
from os.path import abspath, dirname, join

import orjson
import orjson as json

sys.path.insert(0, abspath(join(dirname(__file__), '../package')))

from baidu_tongji import BaiduTongji

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.dirname(CURRENT_PATH)
print(ROOT_PATH)


site_id = '16847648' # change to your site_id
page_size = 100 # change page_size if you want, max is 1000
debug = True # set debug=False if useing in production environment


if __name__ == '__main__':
    try:
        os.remove(f'{CURRENT_PATH}/{site_id}_result_data.json')
        os.remove(f'{CURRENT_PATH}/{site_id}_raw_data.json')
    except:
        pass

    bd = BaiduTongji(debug=debug)
    result = bd.fetchRealTimeData(site_id, page_size=page_size)
    with codecs.open(f'{CURRENT_PATH}/{site_id}_result_data.json', 'w', 'utf-8') as f:
        f.write(json.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode('utf-8'))

    shutil.copy2(f'{ROOT_PATH}/package/data/{site_id}_raw_data.json', f'{CURRENT_PATH}/{site_id}_raw_data.json')

    print(f'raw data saved to {CURRENT_PATH}/data/{site_id}_raw_data.json')
    print(f'result data saved to {CURRENT_PATH}/{site_id}_result_data.json')

    print('done.')