
#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import os, sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '../package')))

from baidu_tongji import baiduTongji
import codecs
import orjson
import orjson as json

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


if __name__ == '__main__':
    try:
        os.remove(f'{CURRENT_PATH}/result.json')
    except:
        pass
    bd = baiduTongji(debug=True)
    result = bd.fetchRealTimeData('16847648', page_size=10)
    with codecs.open(f'{CURRENT_PATH}/result.json', 'w', 'utf-8') as f:
        f.write(json.dumps(result, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode('utf-8'))
