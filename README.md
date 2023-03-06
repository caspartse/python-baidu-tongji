# python-baidu-tongji

A modern-style implementation of Baidu Analytics (Tongji) in Python programming language.


## 功能简介

利用百度统计API，获取网站实时访客数据，解析并构建 Visitor 、Session 、Event 三个对象，方便后续数据分析。

```json
[
  {
    "event_list": [
      {
        "browser": "Safari移动版",
        "browser_type": "safari",
        "channel_id": "",
        "city": "六安市",
        "country": "中国",
        "date_time": "2023-03-06 23:08:39",
        "event": "pageview",
        "event_duration": -10000,
        "event_id": "p_2246809f1cb82f1a9ce40e5d6dbbf9e8",
        "hmci": "",
        "hmcu": "",
        "hmkw": "",
        "hmpl": "",
        "hmsr": "",
        "ip": "223.215.219.78",
        "is_first_time": false,
        "latest_channel_id": "",
        "latest_landing_page": "https://demo.tongji.baidu.com/web/custom/subdir",
        "latest_referrer": "",
        "latest_referrer_host": "",
        "latest_search_engine": "",
        "latest_search_keyword": "",
        "latest_traffic_source_type": "直接访问",
        "latest_utm_campaign": "",
        "latest_utm_content": "",
        "latest_utm_medium": "",
        "latest_utm_source": "",
        "latest_utm_term": "",
        "os": "iOS 15.1",
        "os_type": "ios",
        "province": "安徽省",
        "receive_time": "2023-03-06 23:08:39",
        "referrer": "",
        "referrer_host": "",
        "session_id": "s_4aeb5e562f976b0e4facbcfd82a5f369",
        "traffic_source_type": "直接访问",
        "unix_timestamp": 1678144119.0,
        "url": "https://demo.tongji.baidu.com/web/custom/subdir",
        "url_full_path": "/web/custom/subdir",
        "url_host": "demo.tongji.baidu.com",
        "url_path": "/web",
        "url_query": "",
        "utm_campaign": "",
        "utm_content": "",
        "utm_medium": "",
        "utm_source": "",
        "utm_term": "",
        "visitor_id": "8682358015659239834"
      }
    ],
    "session": {
      "access_full_path": "/web/custom/subdir",
      "access_host": "demo.tongji.baidu.com",
      "access_page": "https://demo.tongji.baidu.com/web/custom/subdir",
      "access_page_query": "",
      "access_path": "/web",
      "anti_code": "",
      "b_user_id": "0",
      "browser": "Safari移动版",
      "browser_type": "safari",
      "channel_id": "",
      "city": "六安市",
      "color_depth": "32-bit",
      "cookie_enable": true,
      "country": "中国",
      "date_time": "2023-03-06 23:08:39",
      "device_type": "mobile",
      "duration": -10000,
      "end_page": "https://demo.tongji.baidu.com/web/custom/subdir",
      "flash_version": "",
      "from_word": "",
      "hmci": "",
      "hmcu": "",
      "hmkw": "",
      "hmpl": "",
      "hmsr": "",
      "ip": "223.215.219.78",
      "ip_isp": "",
      "ip_status": 0,
      "is_first_day": false,
      "is_first_time": false,
      "java_enable": false,
      "landing_page": "https://demo.tongji.baidu.com/web/custom/subdir",
      "language": "中文(简体)",
      "latest_visit_time": "2023-03-06 16:26:33",
      "os": "iOS 15.1",
      "os_type": "ios",
      "province": "安徽省",
      "raw_area": "六安",
      "referrer": "",
      "referrer_host": "",
      "resolution": "375x812",
      "search_engine": "",
      "search_keyword": "",
      "session_id": "s_4aeb5e562f976b0e4facbcfd82a5f369",
      "source_from_type": "直接访问",
      "source_tip": "",
      "source_url": "",
      "start_time": "2023-03-06 23:08:39",
      "traffic_source_type": "直接访问",
      "unix_timestamp": 1678144119.0,
      "utm_campaign": "",
      "utm_content": "",
      "utm_medium": "",
      "utm_source": "",
      "utm_term": "",
      "visit_pages": 1,
      "visitor_frequency": 5,
      "visitor_id": "8682358015659239834",
      "visitor_status": 0,
      "visitor_type": 1
    },
    "visitor": {
      "channel_id": "",
      "first_landing_page": "",
      "first_referrer": "",
      "first_referrer_host": "",
      "first_search_engine": "",
      "first_search_keyword": "",
      "first_traffic_source_type": "",
      "first_visit_time": null,
      "utm_campaign": "",
      "utm_content": "",
      "utm_medium": "",
      "utm_source": "",
      "utm_term": "",
      "visitor_id": "8682358015659239834"
    }
  }
]
```


## 使用方法

0. 使用**普通**百度账号开通百度统计数据API，获得 `API Key` 和 `Secret Key`。
1. 按照[文档说明](https://tongji.baidu.com/api/manual/Chapter2/openapi.html)获得`CODE`（一次性授权码）。
2. 将 `API Key`, `Secret Key`, `CODE` 填入 `config.yaml` 中。
3. 安装依赖 `python3 -m pip install -r requirements.txt`。
4. 调用 `baidu_tongji.py` 即可。


## Demo 介绍
Demo 使用了 `baidu_tongji.py` 获取的数据，并存储到 PostgreSQL 数据库中。

0. 创建一个名为 `website_traffic` 的数据库。
1. 执行 `DDL_website_traffic.sql` 创建表结构。
2. 运行 `main.py` 即可。


## 软件要求
- SQLite
- Redis
- MongoDB (可选，用于存储过程数据)
- PostgreSQL (可选，用于 Demo)


## 参考资料
- [百度统计 Tongji API 用户首次](https://tongji.baidu.com/api/manual/)
- [百度统计产品使用指南](https://tongji.baidu.com/holmes/Analytics/%E4%BA%A7%E5%93%81%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97/%E6%A6%82%E8%A7%88/%E6%B5%81%E9%87%8F%E5%88%86%E6%9E%90/%E5%AE%9E%E6%97%B6%E8%AE%BF%E5%AE%A2/)
- [神策分析帮助文档](https://manual.sensorsdata.cn/sa/latest/tech_sdk_all_preset_properties-89620676.html)


## TODO
- [ ] Elasticsearch Demo


## Thanks
[GitHub Copilot](https://github.com/features/copilot), [vscode-chatgpt](https://github.com/gencay/vscode-chatgpt)
