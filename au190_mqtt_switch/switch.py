import functools
import voluptuous as vol
import sys
import logging
import datetime
import time
import json
import os
from homeassistant.helpers.event import async_track_time_change


from homeassistant.components import switch
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    CONF_NAME,
    CONF_OPTIMISTIC,
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
    CONF_VALUE_TEMPLATE,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType

from homeassistant.components.mqtt import (
    CONF_COMMAND_TOPIC,
    CONF_QOS,
    CONF_RETAIN,
    CONF_STATE_TOPIC,
    PLATFORMS,
    subscription,
)
from homeassistant.components import mqtt
from homeassistant.components.mqtt.debug_info import log_messages
from homeassistant.components.mqtt.mixins import (
    MQTT_ENTITY_COMMON_SCHEMA,
    MqttEntity,
    async_setup_entry_helper,
)
MQTT_SWITCH_ATTRIBUTES_BLOCKED = frozenset(
    {
        switch.ATTR_CURRENT_POWER_W,
        switch.ATTR_TODAY_ENERGY_KWH,
    }
)


from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

_LOGGER = logging.getLogger(__name__)
from . import DOMAIN, SERVICE_AU190

SERVICE_GET_INFO = "get_info"
SERVICE_SET_TIMERS = "set_timers"
JSON_FILE = "_data.json"
JSON_DIR = "au190"

DEFAULT_NAME = "au190 MQTT Switch"
DEFAULT_PAYLOAD_ON = "ON"
DEFAULT_PAYLOAD_OFF = "OFF"
DEFAULT_OPTIMISTIC = False
CONF_STATE_ON = "state_on"
CONF_STATE_OFF = "state_off"


PLATFORM_SCHEMA = mqtt.MQTT_RW_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC): cv.boolean,
        vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
        vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
        vol.Optional(CONF_STATE_OFF): cv.string,
        vol.Optional(CONF_STATE_ON): cv.string,
    }
).extend(MQTT_ENTITY_COMMON_SCHEMA.schema)


async def async_setup_platform(hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None):
    """Set up MQTT switch through configuration.yaml."""
    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    await _async_setup_entity(hass, async_add_entities, config)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up MQTT switch dynamically through MQTT discovery."""
    setup = functools.partial(_async_setup_entity, hass, async_add_entities, config_entry=config_entry)
    await async_setup_entry_helper(hass, switch.DOMAIN, setup, PLATFORM_SCHEMA)


async def _async_setup_entity(hass, async_add_entities, config, config_entry=None, discovery_data=None):
    """Set up the MQTT switch."""

    devices = []
    devices.append(Au190_MqttSwitch(hass, config, config_entry, discovery_data))
    async_add_entities(devices)

    # - register Services
    async def async_service_get_data(service_name, service_data):
        """Handle the service call."""
        try:
            kwargs = dict(service_data)
            entity_id = service_data.get("entity_id")

            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", service_name, entity_id, kwargs)

            for device in devices:
                if device.entity_id == entity_id:
                    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "] [%s][%s][%s]", device.entity_id, entity_id, kwargs)
                    if service_name == SERVICE_AU190:
                        await device.async_au190(**kwargs)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e) )

    async_dispatcher_connect(hass, DOMAIN, async_service_get_data)


class Au190_MqttSwitch(MqttEntity, SwitchEntity, RestoreEntity):
    """Representation of a switch that can be toggled using MQTT."""

    _attributes_extra_blocked = MQTT_SWITCH_ATTRIBUTES_BLOCKED

    def __init__(self, hass, config, config_entry, discovery_data):
        """Initialize the MQTT switch."""
        self._state = False

        self._state_on = None
        self._state_off = None
        self._optimistic = None

        # au190
        self._switch = {}  # Holds local data
        self._filename = None
        self.enable_countDown: bool = False
        self._countDown = 0
        self._scheduler_fc = []

        self._topic = None
        self._value_templates = None
        self._pulseTime = -1     # Force to update at the first time. Pulstime from the device, this walue is already set and confirmed
        self._attrs = {}

        MqttEntity.__init__(self, hass, config, config_entry, discovery_data)

    @staticmethod
    def config_schema():
        """Return the config schema."""
        return PLATFORM_SCHEMA

    def _setup_from_config(self, config):
        """(Re)Setup the entity."""
        state_on = config.get(CONF_STATE_ON)
        self._state_on = state_on if state_on else config[CONF_PAYLOAD_ON]

        state_off = config.get(CONF_STATE_OFF)
        self._state_off = state_off if state_off else config[CONF_PAYLOAD_OFF]

        self._optimistic = config[CONF_OPTIMISTIC]

        template = self._config.get(CONF_VALUE_TEMPLATE)
        if template is not None:
            template.hass = self.hass

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return self._optimistic

    # ---------------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------------

    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""

        await self._create_data()
        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s [%s]", self.entity_id, self.name)

        my_dir = self.hass.config.path(JSON_DIR)
        self._filename = my_dir + os.sep + self.entity_id + JSON_FILE
        if not os.path.exists(my_dir):
            os.makedirs(my_dir)

        await self._load_from_file()

        topics = {}
        qos = self._config[CONF_QOS]

        def add_subscription(topics, topic, msg_callback):

            if self.my_hasattr(topics, topic):
                _LOGGER.fatal("[" + sys._getframe().f_code.co_name + "]--> [Yaml config is not good. This topic [%s] is aleardy assigned to a function. You have to use different topic for each sensor !]", topic)
                return False

            topics[topic] = {
                "topic": topic,
                "msg_callback": msg_callback,
                "qos": qos,
            }
            return True

        @callback
        @log_messages(self.hass, self.entity_id)
        def state_message_zone(msg):
            """Handle new MQTT state messages."""
            payload = msg.payload
            template = self._config.get(CONF_VALUE_TEMPLATE)
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s %s", msg, payload)

            if template is not None:
                payload = template.async_render_with_possible_json_value(payload)
            if payload == self._state_on:
                self._state = True
            elif payload == self._state_off:
                self._state = False

            self.myasync_write_ha_state()

        '''
           State topic PulseTime for zones

           stat/basic/RESULT = {"PulseTime1":{"Set":220,"Remaining":220}}

        '''
        @callback
        def state_message_pulsetime(msg):
            """Handle new MQTT state messages."""
            try:
                #payload = msg.payload
                topic = msg.topic
                pL_o = {}
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", topic, payload, msg)

                if msg.payload[0] == "{":  # is json ?

                    pL_o = json.loads(msg.payload)  # decode json data
                    first_element = list(pL_o.keys())[0]
                    first_elementidx = topic + '/' + first_element

                    if self._switch["state_pulse_times_idx"] == first_elementidx:

                        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)

                        self._pulseTime = pL_o[first_element]["Set"]

                        '''
                            Send turn ON msg to the zone
                        '''
                        self._publish(self._config[CONF_COMMAND_TOPIC], self._state_on)

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        @callback
        def state_message_info(msg):
            """Handle new MQTT state messages."""
            '''
            12:53:44 MQT: stat/basic/STATUS = {"Status":{"Module":1,"FriendlyName":["Basic"],"Topic":"basic","ButtonTopic":"0","Power":0,"PowerOnState":0,"LedState":1,"LedMask":"FFFF","SaveData":1,"SaveState":1,"SwitchTopic":"0","SwitchMode":[1,0,0,0,0,0,0,0],"ButtonRetain":0,"SwitchRetain":0,"SensorRetain":0,"PowerRetain":0}}
            12:53:44 MQT: stat/basic/STATUS1 = {"StatusPRM":{"Baudrate":115200,"GroupTopic":"tasmotas","OtaUrl":"http://thehackbox.org/tasmota/release/tasmota.bin","RestartReason":"Power on","Uptime":"0T03:18:43","StartupUTC":"2021-05-03T08:35:01","Sleep":50,"CfgHolder":4621,"BootCount":12,"SaveCount":324,"SaveAddress":"F8000"}}
            12:53:44 MQT: stat/basic/STATUS2 = {"StatusFWR":{"Version":"7.2.0(tasmota)","BuildDateTime":"2020-02-10T18:26:43","Boot":31,"Core":"2_6_1","SDK":"2.2.2-dev(5ab15d1)","Hardware":"ESP8266EX","CR":"273/1151"}}
            12:53:45 MQT: stat/basic/STATUS3 = {"StatusLOG":{"SerialLog":2,"WebLog":2,"MqttLog":0,"SysLog":0,"LogHost":"","LogPort":514,"SSId":["Roby",""],"TelePeriod":300,"Resolution":"558180C0","SetOption":["0000A009","2805C8000100060000005A00000000000000","00008000","00000000"]}}
            12:53:45 MQT: stat/basic/STATUS4 = {"StatusMEM":{"ProgramSize":594,"Free":344,"Heap":23,"ProgramFlashSize":1024,"FlashSize":1024,"FlashChipId":"14405E","FlashMode":3,"Features":["00000809","8FDAE397","003683A0","22B617CD","01001BC0","00007881"],"Drivers":"1,2,3,4,5,6,7,8,9,10,12,16,18,19,20,21,22,24,26,29","Sensors":"1,2,3,4,5,6,7,8,9,10,14,15,17,18,20,22,26,34"}}
            12:53:45 MQT: stat/basic/STATUS5 = {"StatusNET":{"Hostname":"basic-5911","IPAddress":"192.168.2.45","Gateway":"192.168.2.1","Subnetmask":"255.255.255.0","DNSServer":"192.168.2.190","Mac":"B4:E6:2D:3A:B7:17","Webserver":2,"WifiConfig":4}}
            12:53:45 MQT: stat/basic/STATUS6 = {"StatusMQT":{"MqttHost":"192.168.2.190","MqttPort":1883,"MqttClientMask":"Basic","MqttClient":"Basic","MqttUser":"au190","MqttCount":1,"MAX_PACKET_SIZE":1000,"KEEPALIVE":30}}
            12:53:45 MQT: stat/basic/STATUS7 = {"StatusTIM":{"UTC":"Mon May 03 11:53:45 2021","Local":"Mon May 03 12:53:45 2021","StartDST":"Sun Mar 28 02:00:00 2021","EndDST":"Sun Oct 31 03:00:00 2021","Timezone":"+01:00","Sunrise":"05:25","Sunset":"20:08"}}
            12:53:45 MQT: stat/basic/STATUS10 = {"StatusSNS":{"Time":"2021-05-03T12:53:45"}}
            12:53:45 MQT: stat/basic/STATUS11 = {"StatusSTS":{"Time":"2021-05-03T12:53:45","Uptime":"0T03:18:44","UptimeSec":11924,"Heap":24,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"OFF","Wifi":{"AP":1,"SSId":"Roby","BSSId":"84:16:F9:D3:3C:80","Channel":2,"RSSI":64,"Signal":-68,"LinkCount":1,"Downtime":"0T00:00:06"}}}

            12:55:13 MQT: tele/basic/STATE = {"Time":"2021-05-03T12:55:13","Uptime":"0T03:20:12","UptimeSec":12012,"Heap":24,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":1,"POWER":"OFF","Wifi":{"AP":1,"SSId":"Roby","BSSId":"84:16:F9:D3:3C:80","Channel":2,"RSSI":60,"Signal":-70,"LinkCount":1,"Downtime":"0T00:00:06"}}

            # My special hardware
            15:54:21 --> {"topic":"stat/x1/STATUS0","Time":"2021-09-26T15:54:22","Uptime":"00T00:00:19","SSId":"Roby","Ip":"192.168.2.155","RSSI":66}

            '''
            # _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)
            try:
                if msg.payload[0] == "{":
                    pL_o = json.loads(msg.payload)  # decode json data

                    #o = {}
                    #o_1 = {}

                    if self.my_hasattr_Idx(pL_o, 'StatusNET'):

                        t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                        self._attrs['i'][t_topic].update({'IpAddress': pL_o['StatusNET']['IPAddress']})

                    elif self.my_hasattr_Idx(pL_o, 'StatusSTS'):

                        t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                        self._attrs['i'][t_topic].update({'SSId': pL_o['StatusSTS']['Wifi']['SSId'] + " (" + str(pL_o['StatusSTS']['Wifi']['RSSI']) + "%)"})
                        self._attrs['i'][t_topic].update({'Uptime': pL_o['StatusSTS']['Uptime']})
                        self._attrs['i'][t_topic].update({'Time': pL_o['StatusSTS']['Time']})

                    elif self.my_hasattr_Idx(pL_o, 'Wifi'):

                        t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                        self._attrs['i'][t_topic].update({'SSId': pL_o['Wifi']['SSId'] + " (" + str(pL_o['Wifi']['RSSI']) + "%)"})
                        self._attrs['i'][t_topic].update({'Uptime': pL_o['Uptime']})
                        self._attrs['i'][t_topic].update({'Time': pL_o['Time']})

                    elif self.my_hasattr_Idx(pL_o, 'Ip'):# My special hardware

                        t_topic = self.conv_power_to_pulseTime(3, msg.topic)
                        self._attrs['i'][t_topic].update({'IpAddress': pL_o['Ip']})
                        self._attrs['i'][t_topic].update({'SSId': pL_o['SSId'] + " (" + str(pL_o['RSSI']) + "%)"})
                        self._attrs['i'][t_topic].update({'Uptime': pL_o['Uptime']})
                        self._attrs['i'][t_topic].update({'Time': pL_o['Time']})

                    self.myasync_write_ha_state()

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        '''
        --------------------------------------------------------------------------------------------------------------------------------------

            Set listeners

            Cannot use the same topic for multiple functions !!!

        --------------------------------------------------------------------------------------------------------------------------------------
        '''

        if self._config.get(CONF_STATE_TOPIC) is None:
            # Force into optimistic mode.
            self._optimistic = True
        else:
            None

        if self._optimistic:
            last_state = await self.async_get_last_state()
            if last_state:
                self._state = last_state.state == STATE_ON

        add_subscription(topics, self._config.get(CONF_STATE_TOPIC), state_message_zone)
        add_subscription(topics, self._switch["state_pulse_time"], state_message_pulsetime)

        for item in self._switch["state_info"]:
            add_subscription(topics, item, state_message_info)

        self._sub_state = await subscription.async_subscribe_topics(self.hass, self._sub_state, topics)

        '''
            Init data

            1.  Get the IP of the Tasmota devices
            2.  Get the System actual status

        '''
        self._publish(self._switch["command_info"], 0)
        self._publish(self._config[CONF_COMMAND_TOPIC], "")


    async def _create_data(self):
        try:
            # Attr config
            self._attrs.update({"au190": {"status": []}})
            self._attrs.update({'i': {}})  # For info
            self._attrs["au190"].update({"enable_countDown": False})
            self._attrs["au190"].update({"countDown": 400})
            self._attrs["au190"].update({"enable_scheduler": False})
            self._attrs["au190"].update({"scheduler": []})

            state_info_list = []

            '''
                Command PulseTime is working with cmnd/PulseTime

                10:21:38 CMD: PulseTime 10
                10:21:38 MQT: stat/basic/RESULT = {"PulseTime1":{"Set":10,"Remaining":10}}

            '''
            cmnd_pulseTime = self._config.get(CONF_COMMAND_TOPIC).replace("POWER", "PulseTime")
            self._switch.update({"command_pulse_time": cmnd_pulseTime})

            '''
                PulseTime payload message
            '''
            state_pulseTime = self.conv_power_to_pulseTime(1, self._config.get(CONF_STATE_TOPIC))
            self._switch.update({"state_pulse_times_idx": state_pulseTime})

            '''
                Stat PulseTime event message.
                This msg is different event msg for PulseTime  -> stat/basic/RESULT = {"PulseTime1":{"Set":220,"Remaining":220}}

                10:21:38 CMD: PulseTime 10
                10:21:38 MQT: stat/basic/RESULT = {"PulseTime1":{"Set":10,"Remaining":10}}
            '''
            state_pulseTime = self._config.get(CONF_STATE_TOPIC)
            tidx = state_pulseTime.rfind("/")
            state_pulseTime = state_pulseTime[0:tidx] + '/RESULT'
            self._switch.update({"state_pulse_time": state_pulseTime})

            '''
                command_info: "cmnd/basic/Status"
            '''
            command_info = state_pulseTime.replace("RESULT", "Status")
            command_info = command_info.replace("stat", "cmnd")
            self._switch.update({"command_info": command_info})

            '''
                Stat Info event message.

                state_info: 'stat/basic/STATUS5'
                state_info: 'stat/basic/STATUS11'

                state_info: tele/basic/STATE
            '''
            state_info = command_info.replace("cmnd", "stat")
            state_info = state_info.replace("Status", "STATUS0") # My special hardware
            if state_info not in state_info_list:
                state_info_list.append(state_info)

            state_info = state_info.replace("STATUS0", "STATUS5")
            if state_info not in state_info_list:
                state_info_list.append(state_info)

            state_info = state_info.replace("STATUS5", "STATUS11")
            if state_info not in state_info_list:
                state_info_list.append(state_info)

            state_info = state_info.replace("stat", "tele")
            state_info = state_info.replace("STATUS11", "STATE")
            if state_info not in state_info_list:
                state_info_list.append(state_info)

            self._switch.update({"state_info": state_info_list})  # Calculate events msg for info.

            '''
               Stat Info data
            '''
            t_topic = self.conv_power_to_pulseTime(3, state_info)
            self._attrs['i'].update({t_topic: {}})

            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s [%s]", self._switch, self._switch)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
    '''
    @property
    def state_attributes(self):
        """Return the optional state attributes."""
        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s", self._attrs)
        return self._attrs

    async def async_turn_on(self, **kwargs):
        """
        Turn the device on.
        This method is a coroutine.
        """

        if self.enable_countDown:
            new_pulseTime = self._getDuration(self._countDown)
        else:
            new_pulseTime = 0

        if kwargs.get('duration'):
            new_pulseTime = kwargs['duration']
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s] [%s]", self._pulseTime, new_pulseTime, kwargs)

        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s] [%s]", self._pulseTime, new_pulseTime, (self._pulseTime != new_pulseTime))

        if (self._pulseTime != new_pulseTime):

            self._publish(self._switch["command_pulse_time"], new_pulseTime)

        else:

            #Just turn ON
            self._publish(self._config[CONF_COMMAND_TOPIC], self._config[CONF_PAYLOAD_ON])

            if self._optimistic:
                # Optimistically assume that switch has changed state.
                self._state = True
                self.myasync_write_ha_state()


    async def async_turn_off(self, **kwargs):
        """
            Turn the device off.
            This method is a coroutine.
        """

        self._publish(self._config[CONF_COMMAND_TOPIC], self._config[CONF_PAYLOAD_OFF])

        if self._optimistic:
            # Optimistically assume that switch has changed state.
            self._state = False
            self.myasync_write_ha_state()


    def _publish(self, topic, payload):
        mqtt.async_publish(
            self.hass,
            topic,
            payload,
            self._config[CONF_QOS],
            self._config[CONF_RETAIN],
        )


    async def _scheduler_wake_up(self, acction_time):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", acction_time)

            duration = None
            for entry in self._attrs["au190"]['scheduler']:

                start_time = entry['start_time']
                starttime = time.strptime(start_time, '%H:%M')  # '%H:%M:%S'

                if starttime.tm_hour == acction_time.hour and starttime.tm_min == acction_time.minute:
                    duration = self._getDuration(entry['duration'])
                    break

            if duration != None:
                kwargs = {}
                kwargs['duration'] = duration
                await self.async_turn_on(**kwargs)
            else:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: Invalid Time: [%s]", acction_time)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    '''

        {"au190": {
        "status": [],
        "enable_countDown": true,
        "countDown": 20,
        "enable_scheduler": true,
        "scheduler": [{"start_time": "08:32", "duration": 160}, {"start_time": "10:00", "duration": 220}]}}

    '''
    async def _setSchedulerTask(self):
        try:

            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]%s", self.entity_id, self._attrs["au190"])

            # remove all listener
            for fc_listener in self._scheduler_fc:
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]-- [%s]", fc_listener)
                fc_listener()
            self._scheduler_fc = []

            self.enable_countDown = self._attrs["au190"]['enable_countDown']
            self._countDown = self._attrs["au190"]['countDown']

            if self.my_hasattr_Idx(self._attrs["au190"], 'scheduler') and self._attrs["au190"]['enable_scheduler']:
                for entry in self._attrs["au190"]['scheduler']:
                    start_time = entry['start_time']
                    x = time.strptime(start_time, '%H:%M') #'%H:%M:%S'
                    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s:%s][%s] [%s]", x.tm_hour, x.tm_min, duration, entry)

                    fc_listener = async_track_time_change(self.hass, self._scheduler_wake_up, hour=x.tm_hour, minute=x.tm_min, second=0)
                    self._scheduler_fc.append(fc_listener)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def _load_from_file(self):
        """Load data from a file or return None."""
        try:
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", self.entity_id, self._filename)

            with open(self._filename) as fptr:
                jsonf = json.loads(fptr.read())
                self._attrs.update(jsonf)
                await self._setSchedulerTask()
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", self.entity_id, self._filename, jsonf['au190'])

        except IOError:
            await self._setSchedulerTask()
            #_LOGGER.warning("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    '''
        data = {"time": json_obj["time"]}

    '''
    async def _save_to_file(self, data):
        """Create json and save it in a file."""

        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", self.entity_id, self._filename, data)
        try:
            with open(self._filename, "w") as fptr:
                fptr.write(json.dumps({"au190": data}))

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    '''
        Check if a json object (o) has attribute (k)

    '''
    def my_hasattr(self, o, k):
        try:
            # log.info("my_hasattr________:[" + str(o) + "][" + str(k) + "]")
            o[k]
            # log.info("my_hasattr___x___:[" + str(o) + "][" + str(k) + "]")
            return True

        except Exception:
            return False


    '''
          Check if a json object (o) contains the first x character attribute (k) or if the object has a part of an attribute then return the attribute

          PulseTime1
          PulseTime2
          PulseTime3

        self.my_hasattr_Idx(pL_o, 'PulseTime')
    '''
    def my_hasattr_Idx(self, o, k):
        ret = False
        try:

            l = len(k)
            for key in o:
                # log.info('[' + key + ']=' + o[key])
                if key[:l] == k:
                    ret = key
                    # log.info('---x---[' + key + ']=' + o[key])

        except Exception:
            return False
        return ret


    '''
       Force HA to send the status msg

       must be: FMT = '%Y-%m-%dT%H:%M:%S.%f'
    '''
    def myasync_write_ha_state(self):
        FMT = '%Y-%m-%dT%H:%M:%S.%f'
        self._attrs["Time"] = datetime.datetime.now().strftime(FMT)
        self.async_write_ha_state()


    '''
        Tasmota time 0 - infinite
        Force to 0,1 sec

        0 / OFF = disable use of PulseTime for Relay<x>
        1..111 = set PulseTime for Relay<x> in 0.1 second increments
        112..64900 = set PulseTime for Relay<x>, offset by 100, in 1 second increments. Add 100 to desired interval in seconds, e.g., PulseTime 113 = 13 seconds and PulseTime 460 = 6 minutes (i.e., 360 seconds)
    '''
    def _getDuration(self, duration):
        if duration == 0:
            duration = 1
        return duration


    '''
        Create PulseTime msg form Power msg

        fc = 1
            Needs to identify the Pulstime response
            "stat/basic/POWER1" -> "'stat/basic/RESULT/PulseTime1'"
            "stat/basic/POWER2" -> "stat/basic/RESULT/PulseTime2"

            "stat/basic/POWER" -> "stat/basic/RESULT/PulseTime1"
        fc = 2
            "stat/basic/POWER1" -> "'stat/basic/PulseTime1'"
            "stat/basic/POWER2" -> "stat/basic/PulseTime2"

            "stat/basic/POWER" -> "stat/basic/PulseTime1"

        fc = 3
            Get the topic from msg

            "stat/basic/POWER" -> "stat/basic/PulseTime1"

            return basic

    '''
    def conv_power_to_pulseTime(self, fc, msg):
        try:
            ret = None
            if fc == 1:

                tidx = msg.rfind("POWER") + 5
                if len(msg) == tidx:  # if "stat/basic/POWER" -> "stat/basic/PulseTime1"
                    ret = msg.replace("POWER", "PulseTime1")
                else:
                    ret = msg.replace("POWER", "PulseTime")

                tidx = ret.rfind("/")
                ret = ret[0:tidx] + '/RESULT' + ret[tidx:]

            elif fc == 2:

                tidx = msg.rfind("POWER") + 5
                if len(msg) == tidx:  # if "stat/basic/POWER" -> "stat/basic/PulseTime1"
                    ret = msg.replace("POWER", "PulseTime1")
                else:
                    ret = msg.replace("POWER", "PulseTime")

                # tidx = ret.rfind("/")
                # ret = ret[0:tidx] + '/RESULT' + ret[tidx:]

            # _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s - %s", msg, ret)

            elif fc == 3:
                v = msg.split('/')
                if len(v) == 3:
                    ret = v[1]

            return ret
        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))


    async def async_au190(self, **kwargs):
        """
            Turn the device on.
            This method is a coroutine.
        """
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", kwargs)
            fc = int(kwargs["fc"])

            if (fc == 1):
                '''
                    Toggle

                '''

                if self._state == True :
                    await self.async_turn_off()
                else:
                    await self.async_turn_on()

            elif (fc == 2):
                '''
                    Save data to server  - what we have in the au190 obj will be saved

                    1.  Get data from client
                    2.  Save to file
                    3.  Load data from file
                    4.  Update the attributes local var
                    5.  Sends back to client the new variable and updates the client

                '''
                await self._save_to_file(kwargs["au190"])
                await self._load_from_file()
                self.myasync_write_ha_state()

            elif (fc == 3):
                '''
                    Request info

                '''
                self._publish(self._switch["command_info"], 0)
                self.myasync_write_ha_state()



        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))
