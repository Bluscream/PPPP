from datetime import datetime
from re import compile

from ..enums import *

_versionRegex = compile(r"(.*)(\d{8} \d{2}:\d{2}:\d{2})")
_versionCompileTimeFormat = '%Y%m%d %H:%M:%S'
class SystemVersion(object):
    _raw: str
    name: str
    compile_time: datetime

    @classmethod
    def from_string(cls, input: str):
        found = _versionRegex.match(input)
        name = None
        if found and found.groups().count == 3:
            name = found.group(1)
            compile_time = datetime.strptime(found.group(2), _versionCompileTimeFormat)
        return cls(_raw=input, name=name, compile_time=compile_time)
    
    def __str__(self) -> str: return f"{self.name}_{self.compile_time.strftime(_versionCompileTimeFormat)}" if self.name else self._raw


class Response(object):
    cmd: CommandType
    result: CommandResult


class GetParamsResponse(Response):
    cmd = CommandType.GET_PARMS
    timezone: int # Timezone
    time: datetime
    infrared: bool # IR lights?
    battery_percentage: int
    battery_status: BatteryState
    system_version: SystemVersion
    mcu_version: str
    is_show_4k_menu: bool
    is_show_infrared_auto: bool # IR lights auto?
    rotmir: str # PTZ?
    signal: int # Beep?
    lamp: bool # LED indicator light?

    @classmethod
    def from_json(cls, data: dict):
        c = cls()
        c.cmd = CommandType(data['cmd'])
        c.result = CommandResult(data['result'])
        c.timezone = data['tz']
        c.time = datetime.utcfromtimestamp(data['time'])
        c.infrared = data['icut']
        c.battery_percentage = data['batValue']
        c.battery_status = data['batStatus']
        c.system_version = SystemVersion.from_string(data['sysver'])
        c.mcu_version = data['mcuver']
        c.is_show_4k_menu = data['isShow4KMenu']
        c.is_show_infrared_auto = data['isShowIcutAuto']
        c.rotmir = data['rotmir']
        c.signal = data['signal']
        c.lamp = data['lamp']
        return c
    
    def to_json(self):
        return {
            'cmd': self.cmd.value,
            'result': self.result.value,
            'tz': self.timezone,
            'time': self.time.timestamp(),
            'icut': self.infrared,
            'batValue': self.battery_percentage,
            'batStatus': self.battery_status.value,
            'sysver': str(self.system_version),
            'mcuver': self.mcu_version,
            'isShow4KMenu': self.is_show_4k_menu,
            'isShowIcutAuto': self.is_show_infrared_auto,
            'rotmir': self.rotmir,
            'signal': self.signal,
            'lamp': self.lamp
        }
    
    def has_no_battery_or_full(self):
        return self.battery_percentage == 100 and self.battery_status == 1
    
    """
        {
            "cmd":  101,
            "result":       0,
            "tz":   -8,
            "time": 1699397280,
            "icut": 0,
            "batValue":     90,
            "batStatus":    1,
            "sysver":       "HQLS_HK66_DP_20230802 20:08:13",
            "mcuver":       "1.1.1.1",
            "isShow4KMenu": 0,
            "isShowIcutAuto":       1,
            "rotmir":       0,
            "signal":       100,
            "lamp": 0
    }
    """

class GetDeviceFirmwareInfoResponse(Response):
    cmd = CommandType.GET_CLOUD_SUPPORT
    flash_or_transflash: bool
    uploadType: int
    is_exist_transflash: bool
    product_name: str
    firmware_version: int
    support_new_up: bool

    @classmethod
    def from_json(cls, data: dict):
        c = cls()
        c.cmd = CommandType(data['cmd'])
        c.result = CommandResult(data['result'])
        c.flash_or_transflash = data['flashOrTf']
        c.uploadType = data['uploadType']
        c.is_exist_transflash = data['isExistTf']
        c.product_name = data['productName']
        c.firmware_version = data['fwVer']
        c.support_new_up = data['supportNewUp']
        return c
    
    def to_json(self):
        return {
            'cmd': self.cmd.value,
            'result': self.result.value,
            'flashOrTf': self.flash_or_transflash,
            'uploadType': self.uploadType,
            'isExistTf': self.is_exist_transflash,
            'productName': self.product_name,
            'fwVer': self.firmware_version,
            'supportNewUp': self.support_new_up
        }

    """
    the command name is a mis-nomer. this is more like TF card support,
    firmware version and flashability. Returns something like:
    {
        "cmd":  9000,
        "result":       0,
        "flashOrTf":    1,
        "uploadType":   0,
        "isExistTf":    0,
        "productName":  "HQLS_HK66_DP230802",
        "fwVer":        10000,
        "supportNewUp": 1
    }
    """

class CheckUserResponse(Response):
    cmd = CommandType.CHECK_USER
    admin: bool
    mode: int # ?
    type: int # ?
    restrict: bool
    checkstr: str
    cloud_key: str

    @classmethod
    def from_json(cls, data: dict):
        c = cls()
        c.cmd = CommandType(data['cmd'])
        c.result = CommandResult(data['result'])
        c.admin = data['admin']
        c.mode = data['mode']
        c.type = data['type']
        c.restrict = data['restrict']
        c.checkstr = data['checkstr']
        c.cloud_key = data['cloudKey']
        return c
    
    def to_json(self):
        return {
            'cmd': self.cmd.value,
            'result': self.result.value,
            'admin': self.admin,
            'mode': self.mode,
            'type': self.type,
            'restrict': self.restrict,
            'checkstr': self.checkstr,
            'cloudKey': self.cloud_key
        }
    
    """
    [::ffff:192.168.2.48] GET: /func/sendCMDCheckUser?pw=p4%24%24w%C3%B6rd
    p.sendCMDCheckUser()
    DRW packet sent (len: 74)
    CMD sent: {"pro":"check_user","cmd":100,"user":"admin","pwd":"6666"}
    CMD Response received
    {
        cmd: 100,
        admin: 1,
        result: 0,
        mode: 3,
        type: 0,
        restrict: 0,
        checkstr: 'SYB',
        cloud_key: '404784'
    }
"""

class GetWifiResponse(Response):
    cmd = CommandType.GET_WIFI
    ssid: str
    conmode: int # ?

    @classmethod
    def from_json(cls, data: dict):
        c = cls()
        c.cmd = CommandType(data['cmd'])
        c.result = CommandResult(data['result'])
        c.ssid = data['ssid']
        c.conmode = data['conmode']
        return c
    
    def to_json(self):
        return {
            'cmd': self.cmd.value,
            'result': self.result.value,
            'ssid': self.ssid,
            'conmode': self.conmode
        }
    
    """
    [::ffff:192.168.2.48] GET: /func/sendCMDgetWifi?pw=p4%24%24w%C3%B6rd
    p.sendCMDgetWifi()
    DRW packet sent (len: 72)
    CMD sent: {"pro":"get_wifi","cmd":112,"user":"admin","pwd":"6666"}
    CMD Response received
    { cmd: 112, result: 0, ssid: 'LH', conmode: 1 }
    """

class GetRecordParamResponse(Response):
    cmd = CommandType.GET_RECORD_PARAM

    @classmethod
    def from_json(cls, data: dict):
        c = cls()
        c.cmd = CommandType(data['cmd'])
        c.result = CommandResult(data['result'])
        return c
    
    def to_json(self):
        return {
            'cmd': self.cmd.value,
            'result': self.result.value            
        }
    
    """
    [::ffff:192.168.2.48] GET: /func/sendCMDgetRecordParam?pw=p4%24%24w%C3%B6rd
    p.sendCMDgetRecordParam()
    DRW packet sent (len: 80)
    CMD sent: {"pro":"get_record_param","cmd":199,"user":"admin","pwd":"6666"}
    """

class GetWhiteLightResponse(Response):
    cmd = CommandType.GET_WHITELIGHT
    status: int # ?

    @classmethod
    def from_json(cls, data: dict):
        c = cls()
        c.cmd = CommandType(data['cmd'])
        c.result = CommandResult(data['result'])
        c.status = data['status']
        return c
    
    def to_json(self):
        return {
            'cmd': self.cmd.value,
            'result': self.result.value,
            'status': self.status
        }
    
    """
    [::ffff:192.168.2.48] GET: /func/sendCMDGetWhiteLight?pw=p4%24%24w%C3%B6rd
    p.sendCMDGetWhiteLight()
    DRW packet sent (len: 78)
    CMD sent: {"pro":"get_whiteLight","cmd":305,"user":"admin","pwd":"6666"}
    CMD Response received
    { cmd: 305, result: 0, status: 0 }
    """

class GetAlarmResponse(Response):
    cmd = CommandType.GET_ALARM
    pir_enable: bool
    pir_sensitive: int
    pir_video: bool
    pir_push: bool
    pir_video_time: int
    pir_delay_time: int
    alarm_interval: int
    pir_cloud_up_count: int

    @classmethod
    def from_json(cls, data: dict):
        c = cls()
        c.cmd = CommandType(data['cmd'])
        c.result = CommandResult(data['result'])
        c.pir_enable = data['pirenable']
        c.pir_sensitive = data['pirsensitive']
        c.pir_video = data['pirvideo']
        c.pir_push = data['pirPush']
        c.pir_video_time = data['pirvideotime']
        c.pir_delay_time = data['pirDelayTime']
        c.alarm_interval = data['AalarmInterval']
        c.pir_cloud_up_count = data['pirCloudUpCount']
        return c
    
    def to_json(self):
        return {
            'cmd': self.cmd.value,
            'result': self.result.value,
            'pirenable': self.pir_enable,
            'pirsensitive': self.pir_sensitive,
            'pirvideo': self.pir_video,
            'pirPush': self.pir_push,
            'pirvideotime': self.pir_video_time,
            'pirDelayTime': self.pir_delay_time,
            'AalarmInterval': self.alarm_interval,
            'pirCloudUpCount': self.pir_cloud_up_count
        }
    
    """
    {
        "cmd":  107,
        "result":       0,
        "pirenable":    0,
        "pirsensitive": 3,
        "pirvideo":     0,
        "pirPush":      0,
        "pirvideotime": 10,
        "pirDelayTime": 120,
        "AalarmInterval":       2,
        "pirCloudUpCount":      50
    }
    """

"""
class GetParamsResponse(Response):

    @classmethod
    def from_json(cls, data: dict):
        c = cls()
        c.cmd = CommandType(data['cmd'])
        c.result = CommandResult(data['result'])

        return c
    
    def to_json(self):
        return {
            'cmd': self.cmd.value,
            'result': self.result.value,
            
        }
"""