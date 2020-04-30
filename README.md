# Dynamic mqtt switch for Homeassistant


You can use as a count down switch, you can Trun On automatically using schedule time from the GUI.
This component contains the server componenet and the client component.
https://github.com/au190/au190_mqtt_dynamic_switch


**Example**
Lovelace UI:<br />
<img src='https://raw.githubusercontent.com/au190/au190_mqtt_dynamic_switch/master/1.png'/>
<img src='https://raw.githubusercontent.com/au190/au190_mqtt_dynamic_switch/master/1.jpg'/>
<img src='https://raw.githubusercontent.com/au190/au190_mqtt_dynamic_switch/master/1.mp4'/>


### Count Down
```
This feauture can be: Enable | Disable
Count Down timer can be set from (1 sec - 18 hours). Setting to 0 = 0,1 sec

```


### Scheduler
```
Start time: Can be set only hours and minutes.
Duration: Can be set from (1 sec - 18 hours). Setting to 0 = 0,1 sec
```


#### Info
```
- [ ] ⚠️ Working only with MQTT
- [ ] ⚠️ Working only with Tasmota(https://github.com/arendst/Tasmota) software. 
Tested:
Tasmota v7.1.2
Os: Ubuntu 19.10

Homeassistant: 0.105.1
System Health
arch	x86_64
dev	false
docker	false
hassio	false
os_name	Linux
python_version	3.7.5
timezone	Europe/Budapest
version	0.105.1
virtualenv	true
Lovelace
mode	storage
resources	7
views	5
```


#### Installation
1. Copy the au190_mqtt_switch dir into $homeassistant_config_dir/custom_components/<br />
2. To update the frontend use: https://github.com/au190/au190_homeassistant_frontend


#### 1. Server side configuration:

**Options**

| Name | Type | Default | Example | Description
| ---- | ---- | ------- | ----------- | -----------
| platform | string | **Required** | `au190_mqtt_switch`
| name | string | optional | 
| icon | string | optional | mdi:power
| command_topic | string | **Required** | "cmnd/perfume/POWER"
| state_topic | string | **Required** | "stat/perfume/POWER"
| command_pulse_time | string | **Required** | "cmnd/perfume/PulseTime1"
| state_pulse_time | string | **Required** | "stat/perfume/RESULT"
| template_pulse_time | string | **Required** | "{{ value_json.PulseTime1.Set }}"
| command_info | string | **Required** | "cmnd/perfume/Status"
| state_info | string | **Required** | 'stat/perfume/#'
| availability_topic | string | optional | "tele/perfume/LWT"
| payload_available | string | optional | "Online"
| payload_not_available | string | optional | "Online"


configuration.yaml

```
switch:

#****************************  
# 
#****************************

  - platform: au190_mqtt_switch
    name: "Plug Perfume"
    icon: mdi:power
    command_topic: "cmnd/perfume/POWER"
    state_topic: "stat/perfume/POWER"
    command_pulse_time: "cmnd/perfume/PulseTime1"
    state_pulse_time: "stat/perfume/RESULT"
    template_pulse_time: "{{ value_json.PulseTime1.Set }}"
    command_info: "cmnd/perfume/Status"
    state_info: 'stat/perfume/#'
    availability_topic: "tele/perfume/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    qos: 1


```


#### Client side configuration (mandatory):
For the popup menu I had to create new fronted. You have to replace the with this: https://github.com/au190/au190_homeassistant_frontend


#### Client side configuration (this is optional):
Lovelace UI configuration

```
resources:

  - type: module
    url: /local/community/au190-mqtt_card/au190-mqtt_card.js

    
  entity: switch.x_1
  icon: 'mdi:lightbulb'
  name: Test
  type: 'custom:au190-mqtt_card'


cards:
  - entity: switch.x_1
    small_i: true
    title: Living room
    type: 'custom:au190-mqtt_card'
  - entity: switch.x_1
    small_i: true
    title: Bed room
    type: 'custom:au190-mqtt_card'
type: horizontal-stack

```


