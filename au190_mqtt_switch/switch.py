"""Support for MQTT switches."""
import logging
import sys
import json
import voluptuous as vol
import time
import homeassistant.helpers.config_validation as cv
import os

from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchDevice
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.helpers.event import async_track_time_change

from homeassistant.const import (
    CONF_DEVICE,
    CONF_ICON,
    CONF_NAME,
    CONF_OPTIMISTIC,
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
    CONF_VALUE_TEMPLATE,
    STATE_ON,
)
from homeassistant.components.mqtt import (
    CONF_COMMAND_TOPIC,
    CONF_QOS,
    CONF_RETAIN,
    CONF_STATE_TOPIC,
    CONF_UNIQUE_ID,
    MqttAttributes,
    MqttAvailability,
    MqttDiscoveryUpdate,
    MqttEntityDeviceInfo,
    subscription,
)

from . import (
    SERVICE_ATTRIBUTES,
    SERVICE_GET_INFO,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "au190_mqtt_switch"

SERVICE_GET_INFO = "get_info"
SERVICE_SET_TIMERS = "set_timers"
JSON_FILE = "_schedule_data.json"
JSON_DIR = "au190"

DEFAULT_NAME = "au190 MQTT Switch"
DEFAULT_PAYLOAD_ON = "ON"
DEFAULT_PAYLOAD_OFF = "OFF"
DEFAULT_OPTIMISTIC = False
CONF_STATE_ON = "state_on"
CONF_STATE_OFF = "state_off"


CONF_CMND_PULSE_TIME = "command_pulse_time"
CONF_STATE_PULSE_TIME = "state_pulse_time"
CONF_TEMPLATE_PULSE_TIME = "template_pulse_time"
CONF_CMND_INFO = "command_info"
CONF_STATE_INFO = "state_info"

TOPIC_KEYS = (
    CONF_COMMAND_TOPIC,
    CONF_STATE_TOPIC,
    CONF_CMND_PULSE_TIME,
    CONF_STATE_PULSE_TIME,
    CONF_TEMPLATE_PULSE_TIME,
    CONF_CMND_INFO,
    CONF_STATE_INFO,
)


PLATFORM_SCHEMA = (
    mqtt.MQTT_RW_PLATFORM_SCHEMA.extend(
        {
            vol.Optional(CONF_DEVICE): mqtt.MQTT_ENTITY_DEVICE_INFO_SCHEMA,
            vol.Optional(CONF_ICON): cv.icon,
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
            vol.Optional(CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC): cv.boolean,
            vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
            vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
            vol.Optional(CONF_CMND_PULSE_TIME): cv.string,
            vol.Optional(CONF_STATE_PULSE_TIME): cv.string,
            vol.Optional(CONF_STATE_INFO): cv.string,
            vol.Optional(CONF_TEMPLATE_PULSE_TIME): cv.template,
            vol.Optional(CONF_CMND_INFO): cv.string,
            vol.Optional(CONF_STATE_OFF): cv.string,
            vol.Optional(CONF_STATE_ON): cv.string,
            vol.Optional(CONF_UNIQUE_ID): cv.string,
        }
    )
    .extend(mqtt.MQTT_AVAILABILITY_SCHEMA.schema)
    .extend(mqtt.MQTT_JSON_ATTRS_SCHEMA.schema)
)



async def async_setup_platform(  hass: HomeAssistantType, config: ConfigType, async_add_entities, discovery_info=None):
    """Set up MQTT switch through configuration.yaml."""
    await _async_setup_entity(hass, config, async_add_entities, discovery_info)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up MQTT switch dynamically through MQTT discovery."""

#    async def async_discover(discovery_payload):
#        """Discover and add a MQTT switch."""
#        try:
#            discovery_hash = discovery_payload.pop(ATTR_DISCOVERY_HASH)
#            config = PLATFORM_SCHEMA(discovery_payload)
#            await _async_setup_entity(hass, config, async_add_entities, config_entry, discovery_hash )
#        except Exception:
#            if discovery_hash:
#                clear_discovery_hash(hass, discovery_hash)
#            raise
#
#    async_dispatcher_connect(
#        hass, MQTT_DISCOVERY_NEW.format(DOMAIN, "mqtt"), async_discover
#    )


async def _async_setup_entity(hass, config, async_add_entities, config_entry=None, discovery_hash=None):
    """Set up the MQTT switch."""

    devices = []

    devices.append(Au190_MqttSwitch(config, config_entry, discovery_hash))
    async_add_entities(devices, True)

    #- register Services
    async def async_service_get_data(service_name, service_data):
        """Handle the service call."""
        try:
            attr = dict(service_data)
            entity_id = service_data.get('entity_id')

            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s][%s]", service_name, entity_id, attr)

            for device in devices:
                if device.entity_id == entity_id :
                    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "] [%s][%s][%s]", device.entity_id, entity_id, attr)
                    if service_name == SERVICE_ATTRIBUTES:
                        await device.async_set_attributes(attr)
                    elif service_name == SERVICE_GET_INFO:
                        await device._reqInfo(attr)


        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async_dispatcher_connect(hass, DOMAIN, async_service_get_data)


# pylint: disable=too-many-ancestors
class Au190_MqttSwitch(
    MqttAttributes,
    MqttAvailability,
    MqttDiscoveryUpdate,
    MqttEntityDeviceInfo,
    SwitchDevice,
    RestoreEntity,

):
    """Representation of a switch that can be toggled using MQTT."""

    def __init__(self, config, config_entry, discovery_hash):
        """Initialize the MQTT switch."""
        self._state = False
        self._sub_state = None

        self._state_on = None
        self._state_off = None
        self._optimistic = None
        self._unique_id = config.get(CONF_UNIQUE_ID)

        # au190
        self._filename = None
        self.enable_countDown: bool = False
        self._countDown = 0
        self._scheduler_fc = []

        self._topic = None
        self._value_templates = None
        self._pulseTime: int = None     # Pulstime from the device, this walue is already set and confirmed
        self._attrs = {}


        # Load config
        self._setup_from_config(config)
        device_config = config.get(CONF_DEVICE)

        MqttAttributes.__init__(self, config)
        MqttAvailability.__init__(self, config)
        MqttDiscoveryUpdate.__init__(self, discovery_hash, self.discovery_update)
        MqttEntityDeviceInfo.__init__(self, device_config, config_entry)

    async def async_added_to_hass(self):
        """Subscribe to MQTT events."""
        await self._create_data()
        await super().async_added_to_hass()
        await self._subscribe_topics()
        await self._load_from_file()
        await self._reqInfo("")

    async def discovery_update(self, discovery_payload):
        """Handle updated discovery message."""
        config = PLATFORM_SCHEMA(discovery_payload)
        self._setup_from_config(config)
        await self.attributes_discovery_update(config)
        await self.availability_discovery_update(config)
        await self.device_info_discovery_update(config)
        await self._subscribe_topics()
        self.async_write_ha_state()

    async def _create_data(self):
        try:

            # Attr config
            self._attrs.update({"au190": {"type":1}})
            self._attrs["au190"].update({"status": []})
            self._attrs["au190"].update({"enable_countDown": False})
            self._attrs["au190"].update({"countDown": 20})
            self._attrs["au190"].update({"enable_scheduler": False})
            self._attrs["au190"].update({"scheduler": []})

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    def _setup_from_config(self, config):
        """(Re)Setup the entity."""

        self._config = config

        state_on = config.get(CONF_STATE_ON)
        self._state_on = state_on if state_on else config[CONF_PAYLOAD_ON]

        state_off = config.get(CONF_STATE_OFF)
        self._state_off = state_off if state_off else config[CONF_PAYLOAD_OFF]

        self._optimistic = config[CONF_OPTIMISTIC]
        self._topic = {key: config.get(key) for key in TOPIC_KEYS}


    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""

        _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s [%s]", self.entity_id, self.name)

        my_dir = self.hass.config.path(JSON_DIR)
        self._filename = my_dir + os.sep + self.entity_id + JSON_FILE
        if not os.path.exists(my_dir):
            os.makedirs(my_dir)

        topics = {}
        qos = self._config[CONF_QOS]

        def add_subscription(topics, topic, msg_callback):
            if self._topic[topic] is not None:
                topics[topic] = {
                    "topic": self._topic[topic],
                    "msg_callback": msg_callback,
                    "qos": qos,
                }

        def render_template(msg, template_name):

            payload = None
            template = self._config.get(template_name)
            if template is not None:
                template.hass = self.hass
                payload = template.async_render_with_possible_json_value(msg.payload, "unknown")
            return payload

        @callback
        def state_message_received(msg):
            """Handle new MQTT state messages."""

            payload = msg.payload
            if self._config.get(CONF_VALUE_TEMPLATE) is not None:
                payload = render_template(msg, CONF_VALUE_TEMPLATE)
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s %s", msg, payload)

            if payload == self._state_on:
                self._state = True
            elif payload == self._state_off:
                self._state = False

            self.async_write_ha_state()

        if self._config.get(CONF_STATE_TOPIC) is None:
            # Force into optimistic mode.
            self._optimistic = True
        else:

            add_subscription(topics, CONF_STATE_TOPIC, state_message_received)

        if self._optimistic:
            last_state = await self.async_get_last_state()
            if last_state:
                self._state = last_state.state == STATE_ON

        @callback
        def state_PulseTime_received(msg):
            """Handle new MQTT state messages."""

            try:
                payload = None
                pL_o = json.loads(msg.payload)  # decode json data
                #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s] [%s] [%s]", self.entity_id, msg, pL_o)

                if self.my_hasattr_Idx(pL_o, 'PulseTime'):

                    payload = render_template(msg, CONF_TEMPLATE_PULSE_TIME)

                    if(payload == "unknown"):
                        return

                    self._pulseTime = int(payload)

                    # turn ON for while
                    self._publish(CONF_COMMAND_TOPIC, self._state_on )

                    # _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s [%s]", msg, payload)


            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: [%s][%s]", msg, str(e))

        add_subscription(topics, CONF_STATE_PULSE_TIME, state_PulseTime_received)

        @callback
        def state_Info_received(msg):
            """Handle new MQTT state messages."""

            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", msg)
            try:
                if msg.payload[0] == "{":
                    pL_o = json.loads(msg.payload)  # decode json data

                    if self.my_hasattr_Idx(pL_o, 'StatusNET'):
                        self._attrs.update({'IpAddress': pL_o['StatusNET']['IPAddress']})
                    if self.my_hasattr_Idx(pL_o, 'StatusSTS'):
                        self._attrs.update({'SSId': pL_o['StatusSTS']['Wifi']['SSId'] + " (" + str(pL_o['StatusSTS']['Wifi']['RSSI']) + "%)"})
                        self._attrs.update({'Uptime': pL_o['StatusSTS']['Uptime'] })
                        self._attrs.update({'Time': pL_o['StatusSTS']['Time']})

                    self.async_write_ha_state()

            except Exception as e:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

        add_subscription(topics, CONF_STATE_INFO, state_Info_received)


        self._sub_state = await subscription.async_subscribe_topics(
            self.hass, self._sub_state, topics
        )


    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(
            self.hass, self._sub_state
        )
        await MqttAttributes.async_will_remove_from_hass(self)
        await MqttAvailability.async_will_remove_from_hass(self)


    @property
    def state_attributes(self):
        """Return the optional state attributes."""
        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s", self._attrs)
        return self._attrs

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the switch."""
        return self._config[CONF_NAME]

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return self._optimistic

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def icon(self):
        """Return the icon."""
        return self._config.get(CONF_ICON)


    async def async_turn_on(self, **kwargs):
        """
        Turn the device on.
        This method is a coroutine.
        """

        if self.enable_countDown:
            new_pulseTime = self._countDown
        else:
            new_pulseTime = 0

        if kwargs.get('duration'):
            new_pulseTime = kwargs['duration']
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s] [%s]", self._pulseTime, new_pulseTime, kwargs)

        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s] [%s]", self._pulseTime, new_pulseTime, (self._pulseTime != new_pulseTime))

        if (self._pulseTime != new_pulseTime):

            self._publish(CONF_CMND_PULSE_TIME, new_pulseTime)

        else:

            #Just turn ON
            self._publish(CONF_COMMAND_TOPIC, self._config[CONF_PAYLOAD_ON])

            if self._optimistic:
                # Optimistically assume that switch has changed state.
                self._state = True
                self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the device off.

        This method is a coroutine.
        """

        self._publish(CONF_COMMAND_TOPIC, self._config[CONF_PAYLOAD_OFF])

        if self._optimistic:
            # Optimistically assume that switch has changed state.
            self._state = False
            self.async_write_ha_state()


    def _publish(self, topic, payload):
        if self._topic[topic] is not None:
            mqtt.async_publish(
                self.hass,
                self._topic[topic],
                payload,
                self._config[CONF_QOS],
                self._config[CONF_RETAIN],
            )

    async def _reqInfo(self, data):
        #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s", self.entity_id)
        self._publish(CONF_CMND_INFO, 0)

    '''
        1.  Get data from client
        2.  Save to file
        3.  Load data from file
        4.  Update the attributes local var
        5.  Sends back to client the new variable and updates the client
        6.  Updates the 
    '''
    async def async_set_attributes(self, data):
        """ ."""
        try:
            #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", data)
            await self._save_to_file(data["au190"])
            await self._load_from_file()
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async def _async_wake_up(self, acction_time):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s]", acction_time)

            duration = None
            for entry in self._attrs["au190"]['scheduler']:

                start_time = entry['start_time']
                starttime = time.strptime(start_time, '%H:%M')  # '%H:%M:%S'

                if starttime.tm_hour == acction_time.hour and starttime.tm_min == acction_time.minute:
                    duration = entry['duration']
                    break

            if duration != None:
                kwargs = {}
                kwargs['duration'] = duration
                await self.async_turn_on(**kwargs)
            else:
                _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: Invalid Time: [%s]", acction_time)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async def _async_T1(self, acction_time):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", self.entity_id, acction_time)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    async def _async_T2(self, acction_time):
        try:
            _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s][%s]", self.entity_id, acction_time)

            await self._async_wake_up(self, acction_time)

        except Exception as e:
            _LOGGER.error("[" + sys._getframe().f_code.co_name + "] Exception: " + str(e))

    '''
      
        {"au190": {"type": 1, 
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
                    #duration = entry['duration']
                    start_time = entry['start_time']
                    x = time.strptime(start_time, '%H:%M') #'%H:%M:%S'
                    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> [%s:%s][%s] [%s]", x.tm_hour, x.tm_min, duration, entry)

                    fc_listener = async_track_time_change(self.hass, self._async_wake_up, hour=x.tm_hour, minute=x.tm_min, second=0)
                    self._scheduler_fc.append(fc_listener)

                    #--- Test

                   #@callback
                   #def time_automation_listener(acction_time):
                   #    """Call action with right context."""
                   #    _LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s", acction_time)
                   #    self.hass.async_run_job(self._async_wake_up, {"trigger": {"platform": "time", "acction_time": acction_time}})

                   #remove_listener = async_track_time_change(self.hass, time_automation_listener, hour=x.tm_hour, minute=x.tm_min, second=0)
                   #self._scheduler_fc.append(remove_listener)


                   #fc_listener = async_track_time_change(self.hass, self._async_T1, hour=x.tm_hour, minute=x.tm_min, second=0)
                   #self._scheduler_fc.append(fc_listener)

                    # --- Test


                    # fc_listener()
                    #_LOGGER.debug("[" + sys._getframe().f_code.co_name + "]--> %s", fc_listener)

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

        except IOError as e:
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
            t = o[k]
            # log.info("my_hasattr___x___:[" + str(o) + "][" + str(k) + "]")
            return True

        except Exception as e:
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

        except Exception as e:
            return False
        return ret


