-- Function structure for trigger_set_timestamp

DROP FUNCTION IF EXISTS "public"."trigger_set_timestamp"() CASCADE;
CREATE OR REPLACE FUNCTION "public"."trigger_set_timestamp"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
BEGIN
  NEW._updated_at = NOW();
  RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- public.visitors definition

-- Drop table

DROP TABLE IF EXISTS public.visitors CASCADE;

CREATE TABLE public.visitors (
	visitor_id varchar(255) NOT NULL, -- 访客ID，即百度的访客标识码
	first_visit_time timestamp(6) NULL, -- 首次访问时间
	channel_id varchar(255) NULL, -- 渠道ID
	first_landing_page text NULL, -- 首次落地页
	first_referrer text NULL, -- 首次前向地址
	first_referrer_host varchar(255) NULL, -- 首次前向域名
	first_search_engine varchar(255) NULL, -- 首次搜索引擎名称
	first_search_keyword text NULL, -- 首次搜索引擎关键词
	first_traffic_source_type varchar(255) NULL, -- 首次流量来源类型
	latest_visit_time timestamp NULL, -- 最近一次访问时间
	utm_campaign varchar(255) NULL, -- 广告系列名称
	utm_content varchar(255) NULL, -- 广告系列内容
	utm_medium varchar(255) NULL, -- 广告系列媒介
	utm_source varchar(255) NULL, -- 广告系列来源
	utm_term varchar(255) NULL, -- 广告系列字词
	hf_ip varchar(255) NULL, -- 高频IP
	hf_country varchar(255) NULL, -- 高频国家
	hf_province varchar(255) NULL, -- 高频省份
	hf_city varchar(255) NULL, -- 高频城市
	frequency int8 NULL, -- 访问频次
	total_duration int8 NULL, -- 累计访问时长
	total_visit_pages int8 NULL, -- 累计访问页数
	"_created_at" timestamp(6) NULL DEFAULT now(),
	"_updated_at" timestamp(6) NULL DEFAULT now(),
	CONSTRAINT visitors_pkey PRIMARY KEY (visitor_id)
);
CREATE INDEX visitors_latest_visit_time_idx ON public.visitors USING brin (latest_visit_time);
COMMENT ON TABLE public.visitors IS '访客表';

-- Column comments

COMMENT ON COLUMN public.visitors.visitor_id IS '访客ID，即百度的访客标识码';
COMMENT ON COLUMN public.visitors.first_visit_time IS '首次访问时间';
COMMENT ON COLUMN public.visitors.channel_id IS '渠道ID';
COMMENT ON COLUMN public.visitors.first_landing_page IS '首次落地页';
COMMENT ON COLUMN public.visitors.first_referrer IS '首次前向地址';
COMMENT ON COLUMN public.visitors.first_referrer_host IS '首次前向域名';
COMMENT ON COLUMN public.visitors.first_search_engine IS '首次搜索引擎名称';
COMMENT ON COLUMN public.visitors.first_search_keyword IS '首次搜索引擎关键词';
COMMENT ON COLUMN public.visitors.first_traffic_source_type IS '首次流量来源类型';
COMMENT ON COLUMN public.visitors.latest_visit_time IS '最近一次访问时间';
COMMENT ON COLUMN public.visitors.utm_campaign IS '广告系列名称';
COMMENT ON COLUMN public.visitors.utm_content IS '广告系列内容';
COMMENT ON COLUMN public.visitors.utm_medium IS '广告系列媒介';
COMMENT ON COLUMN public.visitors.utm_source IS '广告系列来源';
COMMENT ON COLUMN public.visitors.utm_term IS '广告系列字词';
COMMENT ON COLUMN public.visitors.hf_ip IS '高频IP';
COMMENT ON COLUMN public.visitors.hf_country IS '高频国家';
COMMENT ON COLUMN public.visitors.hf_province IS '高频省份';
COMMENT ON COLUMN public.visitors.hf_city IS '高频城市';
COMMENT ON COLUMN public.visitors.frequency IS '访问频次';
COMMENT ON COLUMN public.visitors.total_duration IS '累计访问时长';
COMMENT ON COLUMN public.visitors.total_visit_pages IS '累计访问页数';

-- Table Triggers

CREATE TRIGGER trigger_set_timestamp BEFORE
UPDATE
    ON
    public.visitors FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();


-- public.sessions definition

-- Drop table

DROP TABLE IF EXISTS public.sessions CASCADE;

CREATE TABLE public.sessions (
	session_id varchar(255) NOT NULL, -- 会话ID
	visitor_id varchar(255) NULL, -- 访客ID，即百度的访客标识码
	start_time timestamp(6) NULL, -- 开始时间
	date_time timestamp(6) NULL, -- 日期时间
	unix_timestamp int8 NULL, -- Unix 时间戳
	access_full_path varchar(255) NULL, -- 入口页面完整页面路径
	access_host varchar(255) NULL, -- 入口页面域名
	access_page text NULL, -- 入口页面地址
	access_page_query text NULL, -- 入口页面参数
	access_path varchar(255) NULL, -- 入口页面一级路径
	anti_code varchar(255) NULL, -- antiCode
	b_user_id varchar(255) NULL, -- 开发者设置的用户id
	browser varchar(255) NULL, -- 浏览器
	browser_type varchar(255) NULL, -- 浏览器类型
	channel_id varchar(255) NULL, -- 渠道ID
	city varchar(255) NULL, -- 城市
	color_depth varchar(255) NULL, -- 屏幕颜色
	cookie_enable bool NULL, -- 是否支持Cookie
	country varchar(255) NULL, -- 国家
	device_type varchar(255) NULL, -- 设备类型
	duration int8 NULL, -- 时长
	end_page text NULL, -- 最后停留页面
	flash_version varchar(255) NULL, -- Flash版本
	from_word text NULL, -- 广告关键词
	hmci varchar(255) NULL, -- 创意参数，对应utm_content
	hmcu varchar(255) NULL, -- 单元名称参数，对应utm_campaign
	hmkw varchar(255) NULL, -- 关键词参数，对应utm_term
	hmpl varchar(255) NULL, -- 计划名称参数，对应utm_medium
	hmsr varchar(255) NULL, -- 媒体平台参数，对应utm_source
	ip varchar(255) NULL, -- IP
	ip_isp varchar(255) NULL, -- IP 运营商
	ip_status varchar(255) NULL, -- IP状态
	is_first_day bool NULL, -- 是否首日访问
	is_first_time bool NULL, -- 是否首次触发事件
	java_enable bool NULL, -- 是否支持Java
	landing_page text NULL, -- 落地页，等价于access_page
	"language" varchar(255) NULL, -- 浏览器语言
	latest_visit_time timestamp(6) NULL, -- 最近一次访问时间
	os varchar(255) NULL, -- 操作系统
	os_type varchar(255) NULL, -- 操作系统类型
	province varchar(255) NULL, -- 省份
	raw_area varchar(255) NULL, -- 地域
	referrer text NULL, -- 前向地址
	referrer_host varchar(255) NULL, -- 前向域名
	resolution varchar(255) NULL, -- 屏幕分辨率
	search_engine varchar(255) NULL, -- 搜索引擎名称
	search_keyword text NULL, -- 搜索关键词
	source_from_type text NULL, -- 流量来源类型
	source_tip varchar(255) NULL, -- fromType_tip
	source_url text NULL, -- 前向地址
	traffic_source_type varchar(255) NULL, -- 流量来源类型
	utm_campaign varchar(255) NULL, -- 广告系列名称
	utm_content varchar(255) NULL, -- 广告系列内容
	utm_medium varchar(255) NULL, -- 广告系列媒介
	utm_source varchar(255) NULL, -- 广告系列来源
	utm_term varchar(255) NULL, -- 广告系列字词
	visit_pages int4 NULL, -- 访问页数
	visitor_frequency int4 NULL, -- 当天访问频次
	visitor_status varchar(255) NULL, -- 访客状态
	visitor_type int2 NULL, -- 访客类型（0: 新访客, 1: 老访客）
	"_created_at" timestamp(6) NULL DEFAULT now(),
	"_updated_at" timestamp(6) NULL DEFAULT now(),
	CONSTRAINT result_pkey PRIMARY KEY (session_id),
	CONSTRAINT sessions_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(visitor_id) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX sessions_date_time_idx ON public.sessions USING brin (date_time);
CREATE INDEX sessions_start_time_idx ON public.sessions USING brin (start_time);
CREATE INDEX sessions_unix_timestamp_idx ON public.sessions USING brin (unix_timestamp);
CREATE INDEX sessions_visitor_id_idx ON public.sessions USING hash (visitor_id);
COMMENT ON TABLE public.sessions IS '会话表';

-- Column comments

COMMENT ON COLUMN public.sessions.session_id IS '会话ID';
COMMENT ON COLUMN public.sessions.visitor_id IS '访客ID，即百度的访客标识码';
COMMENT ON COLUMN public.sessions.start_time IS '开始时间';
COMMENT ON COLUMN public.sessions.date_time IS '日期时间';
COMMENT ON COLUMN public.sessions.unix_timestamp IS 'Unix 时间戳';
COMMENT ON COLUMN public.sessions.access_full_path IS '入口页面完整页面路径';
COMMENT ON COLUMN public.sessions.access_host IS '入口页面域名';
COMMENT ON COLUMN public.sessions.access_page IS '入口页面地址';
COMMENT ON COLUMN public.sessions.access_page_query IS '入口页面参数';
COMMENT ON COLUMN public.sessions.access_path IS '入口页面一级路径';
COMMENT ON COLUMN public.sessions.anti_code IS 'antiCode';
COMMENT ON COLUMN public.sessions.b_user_id IS '开发者设置的用户id';
COMMENT ON COLUMN public.sessions.browser IS '浏览器';
COMMENT ON COLUMN public.sessions.browser_type IS '浏览器类型';
COMMENT ON COLUMN public.sessions.channel_id IS '渠道ID';
COMMENT ON COLUMN public.sessions.city IS '城市';
COMMENT ON COLUMN public.sessions.color_depth IS '屏幕颜色';
COMMENT ON COLUMN public.sessions.cookie_enable IS '是否支持Cookie';
COMMENT ON COLUMN public.sessions.country IS '国家';
COMMENT ON COLUMN public.sessions.device_type IS '设备类型';
COMMENT ON COLUMN public.sessions.duration IS '时长';
COMMENT ON COLUMN public.sessions.end_page IS '最后停留页面';
COMMENT ON COLUMN public.sessions.flash_version IS 'Flash版本';
COMMENT ON COLUMN public.sessions.from_word IS '广告关键词';
COMMENT ON COLUMN public.sessions.hmci IS '创意参数，对应utm_content';
COMMENT ON COLUMN public.sessions.hmcu IS '单元名称参数，对应utm_campaign';
COMMENT ON COLUMN public.sessions.hmkw IS '关键词参数，对应utm_term';
COMMENT ON COLUMN public.sessions.hmpl IS '计划名称参数，对应utm_medium';
COMMENT ON COLUMN public.sessions.hmsr IS '媒体平台参数，对应utm_source';
COMMENT ON COLUMN public.sessions.ip IS 'IP';
COMMENT ON COLUMN public.sessions.ip_isp IS 'IP 运营商';
COMMENT ON COLUMN public.sessions.ip_status IS 'IP状态';
COMMENT ON COLUMN public.sessions.is_first_day IS '是否首日访问';
COMMENT ON COLUMN public.sessions.is_first_time IS '是否首次触发事件';
COMMENT ON COLUMN public.sessions.java_enable IS '是否支持Java';
COMMENT ON COLUMN public.sessions.landing_page IS '落地页，等价于access_page';
COMMENT ON COLUMN public.sessions."language" IS '浏览器语言';
COMMENT ON COLUMN public.sessions.latest_visit_time IS '最近一次访问时间';
COMMENT ON COLUMN public.sessions.os IS '操作系统';
COMMENT ON COLUMN public.sessions.os_type IS '操作系统类型';
COMMENT ON COLUMN public.sessions.province IS '省份';
COMMENT ON COLUMN public.sessions.raw_area IS '地域';
COMMENT ON COLUMN public.sessions.referrer IS '前向地址';
COMMENT ON COLUMN public.sessions.referrer_host IS '前向域名';
COMMENT ON COLUMN public.sessions.resolution IS '屏幕分辨率';
COMMENT ON COLUMN public.sessions.search_engine IS '搜索引擎名称';
COMMENT ON COLUMN public.sessions.search_keyword IS '搜索关键词';
COMMENT ON COLUMN public.sessions.source_from_type IS '流量来源类型';
COMMENT ON COLUMN public.sessions.source_tip IS 'fromType_tip';
COMMENT ON COLUMN public.sessions.source_url IS '前向地址';
COMMENT ON COLUMN public.sessions.traffic_source_type IS '流量来源类型';
COMMENT ON COLUMN public.sessions.utm_campaign IS '广告系列名称';
COMMENT ON COLUMN public.sessions.utm_content IS '广告系列内容';
COMMENT ON COLUMN public.sessions.utm_medium IS '广告系列媒介';
COMMENT ON COLUMN public.sessions.utm_source IS '广告系列来源';
COMMENT ON COLUMN public.sessions.utm_term IS '广告系列字词';
COMMENT ON COLUMN public.sessions.visit_pages IS '访问页数';
COMMENT ON COLUMN public.sessions.visitor_frequency IS '当天访问频次';
COMMENT ON COLUMN public.sessions.visitor_status IS '访客状态';
COMMENT ON COLUMN public.sessions.visitor_type IS '访客类型（0: 新访客, 1: 老访客）';

-- Table Triggers

CREATE TRIGGER trigger_set_timestamp BEFORE
UPDATE
    ON
    public.sessions FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();


-- public.events definition

-- Drop table

DROP TABLE IF EXISTS public.events CASCADE;

CREATE TABLE public.events (
	event_id varchar(255) NOT NULL, -- 事件ID
	session_id varchar(255) NULL, -- 会话ID
	visitor_id varchar(255) NULL, -- 访客ID，即百度的访客标识码
	receive_time timestamp(6) NULL, -- 服务端接收到该条事件的时间
	date_time timestamp(6) NULL, -- 日期时间
	unix_timestamp int8 NULL, -- Unix 时间戳
	traffic_source_type varchar(255) NULL, -- 流量来源类型
	browser varchar(255) NULL, -- 浏览器
	browser_type varchar(255) NULL, -- 浏览器类型
	channel_id varchar(255) NULL, -- 渠道ID
	city varchar(255) NULL, -- 城市
	country varchar(255) NULL, -- 国家
	"event" varchar(255) NULL, -- 事件名称
	event_duration int4 NULL, -- 事件时长
	hmci varchar(255) NULL, -- 创意参数，对应utm_content
	hmcu varchar(255) NULL, -- 单元名称参数，对应utm_campaign
	hmkw varchar(255) NULL, -- 关键词参数，对应utm_term
	hmpl varchar(255) NULL, -- 计划名称参数，对应utm_medium
	hmsr varchar(255) NULL, -- 媒体平台参数，对应utm_source
	ip varchar(255) NULL, -- IP
	is_first_time bool NULL, -- 是否首次触发事件
	latest_channel_id varchar(255) NULL, -- 最近一次渠道ID
	latest_landing_page text NULL, -- 最近一次落地页
	latest_referrer text NULL, -- 最近一次站外地址
	latest_referrer_host varchar(255) NULL, -- 最近一次站外域名
	latest_search_engine varchar(255) NULL, -- 最近一次搜索引擎名称
	latest_search_keyword text NULL, -- 最近一次搜索引擎关键词
	latest_traffic_source_type varchar(255) NULL, -- 最近一次流量来源类型
	latest_utm_campaign varchar(255) NULL, -- 最近一次广告系列名称
	latest_utm_content varchar(255) NULL, -- 最近一次广告系列内容
	latest_utm_medium varchar(255) NULL, -- 最近一次广告系列媒介
	latest_utm_source varchar(255) NULL, -- 最近一次广告系列来源
	latest_utm_term varchar(255) NULL, -- 最近一次广告系列字词
	os varchar(255) NULL, -- 操作系统
	os_type varchar(255) NULL, -- 操作系统类型
	province varchar(255) NULL, -- 省份
	referrer text NULL, -- 前向地址
	referrer_host varchar(255) NULL, -- 前向域名
	url text NULL, -- 页面地址
	url_full_path varchar(255) NULL, -- 页面完整路径
	url_host varchar(255) NULL, -- 页面地址域名
	url_path varchar(255) NULL, -- 页面路径
	url_query text NULL, -- 页面参数
	utm_campaign varchar(255) NULL, -- 广告系列名称
	utm_content varchar(255) NULL, -- 广告系列内容
	utm_medium varchar(255) NULL, -- 广告系列媒介
	utm_source varchar(255) NULL, -- 广告系列来源
	utm_term varchar(255) NULL, -- 广告系列字词
	"_created_at" timestamp(6) NULL DEFAULT now(),
	"_updated_at" timestamp(6) NULL DEFAULT now(),
	CONSTRAINT events_pkey PRIMARY KEY (event_id),
	CONSTRAINT events_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(session_id) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT events_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(visitor_id) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX events_date_time_idx ON public.events USING brin (date_time);
CREATE INDEX events_receive_time_idx ON public.events USING brin (receive_time);
CREATE INDEX events_session_id_idx ON public.events USING hash (session_id);
CREATE INDEX events_unix_timestamp_idx ON public.events USING brin (unix_timestamp);
CREATE INDEX events_visitor_id_idx ON public.events USING hash (visitor_id);
COMMENT ON TABLE public.events IS '事件表';

-- Column comments

COMMENT ON COLUMN public.events.event_id IS '事件ID';
COMMENT ON COLUMN public.events.session_id IS '会话ID';
COMMENT ON COLUMN public.events.visitor_id IS '访客ID，即百度的访客标识码';
COMMENT ON COLUMN public.events.receive_time IS '服务端接收到该条事件的时间';
COMMENT ON COLUMN public.events.date_time IS '日期时间';
COMMENT ON COLUMN public.events.unix_timestamp IS 'Unix 时间戳';
COMMENT ON COLUMN public.events.traffic_source_type IS '流量来源类型';
COMMENT ON COLUMN public.events.browser IS '浏览器';
COMMENT ON COLUMN public.events.browser_type IS '浏览器类型';
COMMENT ON COLUMN public.events.channel_id IS '渠道ID';
COMMENT ON COLUMN public.events.city IS '城市';
COMMENT ON COLUMN public.events.country IS '国家';
COMMENT ON COLUMN public.events."event" IS '事件名称';
COMMENT ON COLUMN public.events.event_duration IS '事件时长';
COMMENT ON COLUMN public.events.hmci IS '创意参数，对应utm_content';
COMMENT ON COLUMN public.events.hmcu IS '单元名称参数，对应utm_campaign';
COMMENT ON COLUMN public.events.hmkw IS '关键词参数，对应utm_term';
COMMENT ON COLUMN public.events.hmpl IS '计划名称参数，对应utm_medium';
COMMENT ON COLUMN public.events.hmsr IS '媒体平台参数，对应utm_source';
COMMENT ON COLUMN public.events.ip IS 'IP';
COMMENT ON COLUMN public.events.is_first_time IS '是否首次触发事件';
COMMENT ON COLUMN public.events.latest_channel_id IS '最近一次渠道ID';
COMMENT ON COLUMN public.events.latest_landing_page IS '最近一次落地页';
COMMENT ON COLUMN public.events.latest_referrer IS '最近一次站外地址';
COMMENT ON COLUMN public.events.latest_referrer_host IS '最近一次站外域名';
COMMENT ON COLUMN public.events.latest_search_engine IS '最近一次搜索引擎名称';
COMMENT ON COLUMN public.events.latest_search_keyword IS '最近一次搜索引擎关键词';
COMMENT ON COLUMN public.events.latest_traffic_source_type IS '最近一次流量来源类型';
COMMENT ON COLUMN public.events.latest_utm_campaign IS '最近一次广告系列名称';
COMMENT ON COLUMN public.events.latest_utm_content IS '最近一次广告系列内容';
COMMENT ON COLUMN public.events.latest_utm_medium IS '最近一次广告系列媒介';
COMMENT ON COLUMN public.events.latest_utm_source IS '最近一次广告系列来源';
COMMENT ON COLUMN public.events.latest_utm_term IS '最近一次广告系列字词';
COMMENT ON COLUMN public.events.os IS '操作系统';
COMMENT ON COLUMN public.events.os_type IS '操作系统类型';
COMMENT ON COLUMN public.events.province IS '省份';
COMMENT ON COLUMN public.events.referrer IS '前向地址';
COMMENT ON COLUMN public.events.referrer_host IS '前向域名';
COMMENT ON COLUMN public.events.url IS '页面地址';
COMMENT ON COLUMN public.events.url_full_path IS '页面完整路径';
COMMENT ON COLUMN public.events.url_host IS '页面地址域名';
COMMENT ON COLUMN public.events.url_path IS '页面路径';
COMMENT ON COLUMN public.events.url_query IS '页面参数';
COMMENT ON COLUMN public.events.utm_campaign IS '广告系列名称';
COMMENT ON COLUMN public.events.utm_content IS '广告系列内容';
COMMENT ON COLUMN public.events.utm_medium IS '广告系列媒介';
COMMENT ON COLUMN public.events.utm_source IS '广告系列来源';
COMMENT ON COLUMN public.events.utm_term IS '广告系列字词';

-- Table Triggers

CREATE TRIGGER trigger_set_timestamp BEFORE
UPDATE
    ON
    public.events FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();