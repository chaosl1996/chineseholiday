#! usr/bin/python
#coding=utf-8
"""
中国节假日
版本：0.1.0
"""
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import logging
from homeassistant.util import Throttle
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
     CONF_NAME)
from homeassistant.helpers.entity import generate_entity_id
import datetime
from datetime import timedelta
from . import holiday
from . import lunar

"""
    cal = lunar.CalendarToday()
    print(cal.solar_Term())
    print(cal.festival_description())
    print(cal.solar_date_description())
    print(cal.week_description())
    print(cal.lunar_date_description())
    print(cal.solar())
    print(cal.lunar())
"""

_Log=logging.getLogger(__name__)

DEFAULT_NAME = 'chinese_holiday'
CONF_UPDATE_INTERVAL = 'update_interval'
CONF_SOLAR_ANNIVERSARY = 'solar_anniversary'
CONF_LUNAR_ANNIVERSARY = 'lunar_anniversary'
CONF_CALCULATE_AGE = 'calculate_age'
CONF_CALCULATE_AGE_DATE = 'date'
CONF_CALCULATE_AGE_NAME = 'name'


# CALCULATE_AGE_DEFAULTS_SCHEMA = vol.Any(None, vol.Schema({
#     vol.Optional(CONF_TRACK_NEW, default=DEFAULT_TRACK_NEW): cv.boolean,
#     vol.Optional(CONF_AWAY_HIDE, default=DEFAULT_AWAY_HIDE): cv.boolean,
# }))
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SOLAR_ANNIVERSARY, default=[]): cv.ensure_list_csv,
    vol.Optional(CONF_LUNAR_ANNIVERSARY, default=[]): cv.ensure_list_csv,
    vol.Optional(CONF_CALCULATE_AGE,default=[]): [
        {
            vol.Optional(CONF_CALCULATE_AGE_DATE): cv.string,
            vol.Optional(CONF_CALCULATE_AGE_NAME): cv.string,
        }
    ],
    vol.Optional(CONF_UPDATE_INTERVAL, default=timedelta(minutes=360)): (vol.All(cv.time_period, cv.positive_timedelta)),
})


#公历 纪念日 每年都有的
SOLAR_ANNIVERSARY = [
]
#农历 纪念日 每年都有的
LUNAR_ANNIVERSARY = [
]

#纪念日 指定时间的（出生日到今天的计时或今天到某一天还需要的时间例如金婚）
CALCULATE_AGE = [
    {
        'date':'2010-10-10 08:23:12',
        'name':'xxx'
    }
]
    # '2010-10-10 08:23:12': 'xx',

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the movie sensor."""

    name = config[CONF_NAME]
    interval = config.get(CONF_UPDATE_INTERVAL)

    global SOLAR_ANNIVERSARY
    global LUNAR_ANNIVERSARY
    SOLAR_ANNIVERSARY = config[CONF_SOLAR_ANNIVERSARY]
    LUNAR_ANNIVERSARY = config[CONF_LUNAR_ANNIVERSARY]

    sensors = [ChineseHolidaySensor(hass, name, interval)]
    add_devices(sensors, True)

class ChineseHolidaySensor(Entity):

    _holiday = None
    _lunar = None

    def __init__(self, hass, name, interval):
        """Initialize the sensor."""
        self.client_name = name
        self._state = None
        self._hass = hass
        self._holiday = holiday.Holiday()
        self._lunar = lunar.CalendarToday()
        self.attributes = {}
        self.entity_id = generate_entity_id(
            'sensor.{}', self.client_name, hass=self._hass)
        self.update = Throttle(interval)(self._update)

    @property
    def name(self):
        """Return the name of the sensor."""
        return '节假日'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return 'mdi:calendar-today'

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self.attributes

    #计算纪念日（每年都有的）
    def calculate_anniversary(self):
        """
            {
                '20200101':[{'anniversary':'0101#xx生日#','solar':True}]
            }
        """
        anniversaries = {}

        for l in LUNAR_ANNIVERSARY:
            date_str = l.split('#')[0]
            month = int(date_str[:2])
            day = int(date_str[2:])
            solar_date = lunar.CalendarToday.lunar_to_solar(self._lunar.solar()[0],month,day)#下标和位置
            date_str = solar_date.strftime('%Y%m%d')
            try:
                list = anniversaries[date_str]
            except Exception as e:
                anniversaries[date_str] = []
                list = anniversaries[date_str]
            list.append({'anniversary':l,'solar':False})

        for s in SOLAR_ANNIVERSARY:
            date_str = s.split('#')[0]
            date_str = str(self._lunar.solar()[0])+date_str #20200101
            try:
                list = anniversaries[date_str]
            except Exception as e:
                anniversaries[date_str] = []
                list = anniversaries[date_str]
            list.append({'anniversary':s,'solar':True})


    #根据key 排序 因为key就是日期字符串
        list=sorted(anniversaries.items(),key=lambda x:x[0])
        #找到第一个大于今天的纪念日
        for item in list:
            key = item[0]
            annis = item[1] #纪念日数组
            now_str = datetime.datetime.now().strftime('%Y-%m-%d')
            today = datetime.datetime.strptime(now_str, "%Y-%m-%d")
            last_update = datetime.datetime.strptime(key,'%Y%m%d')
            days = (last_update - today).days
            if days > 0:
                return key,days,annis
        return None,None,None

    #今天是否是自定义的纪念日（阴历和阳历）
    def custom_anniversary(self):
        lunar_month = self._lunar.lunar()[1]
        lunar_day = self._lunar.lunar()[2]
        solar_month = self._lunar.solar()[1]
        solar_day = self._lunar.solar()[2]
        lunar_anni = lunar.festival_handle(LUNAR_ANNIVERSARY,lunar_month,lunar_day)
        solar_anni = lunar.festival_handle(SOLAR_ANNIVERSARY,solar_month,solar_day)
        anni = ''
        if lunar_anni:
            anni += lunar_anni
        if solar_anni:
            anni += solar_anni
        return anni


    def calculate_age(self):
        if not CALCULATE_AGE:
            return
        now_day = datetime.datetime.now()
        count_dict = {}
        for item in CALCULATE_AGE:
            date = item[CONF_CALCULATE_AGE_DATE]
            name = item[CONF_CALCULATE_AGE_NAME]
            key = datetime.datetime.strptime(date,'%Y-%m-%d %H:%M:%S')
            if (now_day - key).total_seconds() > 0:
                total_seconds = int((now_day - key).total_seconds())
                year, remainder = divmod(total_seconds,60*60*24*365)
                day, remainder = divmod(remainder,60*60*24)
                hour, remainder = divmod(remainder,60*60)
                minute, second = divmod(remainder,60)
                self.attributes['离'+name+'过去'] = '{}年 {} 天 {} 小时 {} 分钟 {} 秒'.format(year,day,hour,minute,second)
            if (now_day - key).total_seconds() < 0:
                total_seconds = int((key - now_day ).total_seconds())
                year, remainder = divmod(total_seconds,60*60*24*365)
                day, remainder = divmod(remainder,60*60*24)
                hour, remainder = divmod(remainder,60*60)
                minute, second = divmod(remainder,60)
                self.attributes['离'+name+'还差']  = '{}年 {} 天 {} 小时 {} 分钟 {} 秒'.format(year,day,hour,minute,second)


    def nearest_holiday(self):
        '''查找离今天最近的法定节假日，并显示天数'''
        now_day = datetime.date.today()
        count_dict = {}
        results = self._holiday.getHoliday()
        for key in results.keys():
            if (key - now_day).days > 0:
                count_dict[key] = (key - now_day).days
        nearest_holiday_dict = {}
        if count_dict:
            nearest_holiday_dict['name'] = results[min(count_dict)]
            nearest_holiday_dict['date'] = min(count_dict).isoformat()
            nearest_holiday_dict['day'] = str((min(count_dict)-now_day).days)+'天'

        return nearest_holiday_dict

    def _update(self):
        self._state = self._holiday.is_holiday_today()
        self.attributes['今天'] = self._lunar.solar_date_description()
        # self.attributes['今天'] = datetime.date.today().strftime('%Y{y}%m{m}%d{d}').format(y='年', m='月', d='日')
        self.attributes['星期'] = self._lunar.week_description()
        self.attributes['农历'] = self._lunar.lunar_date_description()
        term = self._lunar.solar_Term()
        if term:
            self.attributes['节气'] = term
        festival = self._lunar.festival_description()
        if festival:
            self.attributes['节日'] = festival

        custom = self.custom_anniversary()
        if custom:
            self.attributes['纪念日'] = custom

        key,days,annis = self.calculate_anniversary()
        s = ''
        if key and days and annis:
            for anni in annis:
                s += anni['anniversary']

            self.attributes['离最近的纪念日'] = s + '还有' + str(days) + '天'

        nearest = self.nearest_holiday()
        if nearest:
            self.attributes['离今天最近的法定节日'] = nearest['name']
            self.attributes['法定节日日期'] = nearest['date']
            self.attributes['还有'] = nearest['day']

        self.calculate_age()
