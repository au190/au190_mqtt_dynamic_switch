/*
- type: module
  url: /local/community/au190-mqtt_card/au190-mqtt_card.js


entity: switch.x_1
name: Test
icon: 'mdi:lightbulb'
type: 'custom:au190-mqtt_card'


*/

import {cssData} from './styles.js?v=0.1.1';

class au190_MqttCard extends HTMLElement {
  
  constructor(){
    super();
    this.attachShadow({ mode: 'open' });
  }

  async setConfig(config){
    
    if(!config.entity){
      throw new Error('Please define an entity');
    }

    const root = this.shadowRoot;
    if(root.lastChild) root.removeChild(root.lastChild);

    const cardConfig = Object.assign({}, config);
    const card = document.createElement('ha-card');
    const content = document.createElement('div');
    const style = document.createElement('style');
    style.textContent = cssData();

    //console.log(config)
    
    if(typeof config.icon !== 'undefined'){
      this.icon = config.icon
    }else{
      this.icon = "mdi:power"
    }
    
    content.innerHTML = `
      <ha-card>
        <header>
          <paper-icon-button icon="mdi:dots-vertical" id="pr" class="c_icon clickable" role="button" tabindex="0" aria-disabled="false"></paper-icon-button>
          <div id="name" class="c_title">${this.name}</div>
        </header>
        <div class="status">
          <paper-icon-button id="btns" class="sw OFF" icon=${this.icon}></paper-icon-button>
        </div>
        <div class="sep"></div>
        <div class="status">
          <paper-icon-button id="i_0" class="OFF" icon=${"mdi:timer"}></paper-icon-button>
					<paper-icon-button id="i_1" class="OFF" icon=${"mdi:calendar-clock"}></paper-icon-button>
        </div>
      </ha-card>
    `;
    card.appendChild(style);
    card.appendChild(content);
    root.appendChild(card)
    
    const pr = root.getElementById('pr')
    pr.addEventListener('click', () => this._openProp(cardConfig.entity));
    
    const el = root.getElementById('btns')
    el.addEventListener('click', (e) => this._zoneSwitch(e.target.id));

    this._config = cardConfig;
  }
 
  set hass(hass){

    const config = this._config;
    const root = this.shadowRoot;
    this.stateObj = hass.states[config.entity]

    if(this.stateObj === undefined || !this._isChanged()){
      return
    }
    
    this._hass = hass;
    //console.log(this.stateObj.attributes.au190);
    
    if(typeof config.name === 'string'){
      this.name = config.name
    }else if(config.name === false){
      this.name = false
    }else{
      this.name = this.stateObj.attributes.friendly_name
    }
    
    this._updateName(root.getElementById('name'), this.name);
    this._updateButtons(root);
    
  }

  _isChanged(){
    try{
      var r = false;
      
      const new_state = {
        state: this.stateObj.state,
        enable_countDown: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.enable_countDown : false,
        enable_scheduler: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190.enable_scheduler : false,
      }
      
      if( (this._old_state === undefined)
        || this._old_state.state !== new_state.state
        || this._old_state.enable_countDown !== new_state.enable_countDown
        || this._old_state.enable_scheduler !== new_state.enable_scheduler

      ){
        
        this._old_state = new_state;
        r =  true;
        //console.log('<-- _isChanged:' + r)
      }

    }catch(e){
      console.error('_isChanged: ' + e);
    }

    return r;
  }
  
  _openProp(entityId){
    this.fire('hass-more-info', { entityId });
  }
  
  fire(type, detail, options){
  
    options = options || {}
    detail = detail === null || detail === undefined ? {} : detail
    const e = new Event(type, {
      bubbles: options.bubbles === undefined ? true : options.bubbles,
      cancelable: Boolean(options.cancelable),
      composed: options.composed === undefined ? true : options.composed,
    })
    
    e.detail = detail
    this.dispatchEvent(e)
    return e
  }
  
  _zoneSwitch(zone){
    //console.log('--> _zoneSwitch')
     this._hass.callService("homeassistant", "toggle", {
      entity_id: this.stateObj.entity_id,
    });
  }
  
  _updateName(el, attr){
    el.innerHTML = attr;
  }

  _updateButtons(root){
    //console.log(this.stateObj)
    
    var el = root.getElementById('btns');
    
    if(this.stateObj.state !== 'unavailable'){

      root.getElementById('btns').removeAttribute("class");
      
      if(this.stateObj.state == 'on'){
        root.getElementById('btns').classList.add('ON');
      }else{
        root.getElementById('btns').classList.add('OFF');
      }
      root.getElementById('btns').classList.add('sw');

      
      for(let i=0;i<2;i++){
        root.getElementById('i_'+i).removeAttribute("class");
      }
        
      if(this.stateObj.attributes.au190.enable_countDown){
        root.getElementById('i_0').classList.add('ON');
      }else{
        root.getElementById('i_0').classList.add('OFF');
      }

      if(this.stateObj.attributes.au190.enable_scheduler){
        root.getElementById('i_1').classList.add('ON');
      }else{
        root.getElementById('i_1').classList.add('OFF');
      }

      
    }else{
      
      el.innerHTML = `<button class="OFF">Unavailable</button>`;
      
    }

  }
  
  getCardSize(){
    3;
  }
  
}
customElements.define("au190-mqtt_card", au190_MqttCard);