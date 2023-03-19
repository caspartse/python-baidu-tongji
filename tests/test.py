
#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import codecs
import os
import sys
from os.path import abspath, dirname, join

import orjson
import orjson as json

sys.path.insert(0, abspath(join(dirname(__file__), '../package')))

from baidu_tongji import BaiduTongji

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

site_id = '16847648'
page_size = 100


if __name__ == '__main__':
    try:
        os.remove(f'{CURRENT_PATH}/result.json')
    except:
        pass

    bd = BaiduTongji(debug=True)
    result = bd.fetchRealTimeData(site_id, page_size=page_size)
    with codecs.open(f'{CURRENT_PATH}/result.json', 'w', 'utf-8') as f:
        f.write(json.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode('utf-8'))

    print('done.')