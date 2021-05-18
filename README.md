# Dynamic mqtt switch for Homeassistant


You can use as a count down switch, you can Trun On automatically using schedule time from the GUI.
This component contains the server componenet and the client component.
https://github.com/au190/au190_mqtt_dynamic_switch


**Example**
Lovelace UI:<br />
<img src='https://raw.githubusercontent.com/au190/au190_mqtt_dynamic_switch/master/1.jpg'/>
[![Watch the video](https://img.youtube.com/vi/D6Lkr_acK_s/0.jpg)](https://www.youtube.com/watch?v=D6Lkr_acK_s "Watch the video")

### Count Down
This feauture can be: Enable|Disable
Count Down timer can be set from (1 sec - 18 hours). Setting to 0 = 0,1 sec



### Scheduler
Start time: Can be set only hours and minutes.
Duration: Can be set from (1 sec - 18 hours). Setting to 0 = 0,1 sec



#### Info

- [ ] ⚠️ The output will be ON only the time what is in configuraiton, even if the Ha is crashing druring the output is ON, or even if the Wifi router is crashing druring the output is ON.
- [ ] ⚠️ Working only with MQTT
- [ ] ⚠️ Working only with Tasmota(https://github.com/arendst/Tasmota) software.
```
Tested:
Home Assistant version: 0.105.1
Tasmota v7.1.2
Python_version	3.7.5
```


#### Installation
1.  Copy the au190_mqtt_switch dir into $homeassistant_config_dir/custom_components/ <br/>
2.  Copy the au190-mqtt_card dir into $homeassistant_config_dir/www/community/ <br/>


#### 1. Server side configuration:

**Options**

| Name | Type | Default | Example | Description
| ---- | ---- | ------- | ----------- | -----------
| platform | string | **Required** | `au190_mqtt_switch`
| name | string | optional | 
| icon | string | optional | mdi:power
| command_topic | string | **Required** | "cmnd/perfume/POWER"
| state_topic | string | **Required** | "stat/perfume/POWER"
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
    availability_topic: "tele/perfume/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    qos: 1 

```


#### 2. Client side configuration:

Lovelace UI configuration


Adding the resource to Client:

```
resources:

  - type: module
    url: /local/community/au190-mqtt_card/au190-mqtt_card.js
```


Card configuration:

```
  entity: switch.x_1
  icon: 'mdi:lightbulb'
  name: Test
  type: 'custom:au190-mqtt_card'


cards:
  - entity: switch.plug_perfume
    icon: 'mdi:water'
    lock: true
    secondary_info: last-changed
    type: 'custom:au190-mqtt_card'
  - entity: switch.led
    secondary_info: last-changed
    type: 'custom:au190-mqtt_card'
type: horizontal-stack

```


