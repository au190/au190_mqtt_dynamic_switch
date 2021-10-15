/*
- type: module
  url: /local/community/au190-mqtt_card/au190-mqtt_card.js


entity: switch.x_1
name: Test
icon: 'mdi:lightbulb'
type: 'custom:au190-mqtt_card'


*/

import {cssData} from './styles.js?v=0.1.1';



var au190   = {};
/*******************************************************

  Dlg fc

*******************************************************/

/*******************************************************

  Convert cDown time to Tasmota PulseTime1
  
  f = 0 - Time to Tasmota PulseTime1
  f = 1 - Tasmota PulseTime1 to Time
  f = 2 - Force seconds to 0
  f = 3 - Time to sec
  f = 4 - Sec to Time
  
*******************************************************/
function _cfc(f, d){

  var r = null;
  try{
    
    if(f==0){
      var a = d.split(':'); // split it at the colons
      if(a.length == 2){
        r = ( (+a[0]) * 60 * 60 + (+a[1]) * 60 );
      }else if(a.length == 3){
        r = ( (+a[0]) * 60 * 60 + (+a[1]) * 60 + (+a[2]) );
      }
      if(r==0){
        
      }else if(r<12){
        r = r * 10;
      }else{
        r = r + 100;
      }
      if(r>64900){
        r = 64900;
      }
      
    }else if(f==1){
      
      if(d==0){

      }else if(d<=111){
        d = d/10;
      }else if(d>111){
        d = d - 100;
      }
    
      var sec_num = parseInt(d, 10);
      var hours   = Math.floor(sec_num / 3600);
      var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
      var seconds = sec_num - (hours * 3600) - (minutes * 60);

      if (hours   < 10) {hours   = "0"+hours;}
      if (minutes < 10) {minutes = "0"+minutes;}
      if (seconds < 10) {seconds = "0"+seconds;}
      
      r = hours+':'+minutes+':'+seconds;
      
    }else if(f==2){
      var a = d.split(':'); // split it
      if(a.length == 1){
        r = "00:00";
      }else if(a.length == 3){
        r = a[0] + ":" + a[1];
      }else{
        r = d;
      }
    
    }else if(f==3){
      var a = d.split(':'); // split it at the colons
      if(a.length == 2){
        r = ( (+a[0]) * 60 * 60 + (+a[1]) * 60 );
      }else if(a.length == 3){
        r = ( (+a[0]) * 60 * 60 + (+a[1]) * 60 + (+a[2]) );
      }
    }else if(f==4){
      
      var sec_num = parseInt(d, 10);
      var hours   = Math.floor(sec_num / 3600);
      var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
      var seconds = sec_num - (hours * 3600) - (minutes * 60);

      if (hours   < 10) {hours   = "0"+hours;}
      if (minutes < 10) {minutes = "0"+minutes;}
      if (seconds < 10) {seconds = "0"+seconds;}
      
      r = hours+':'+minutes+':'+seconds;
    }
    
  }catch(e){
    console.error('_cfc: ' + e);
  }
  //console.log('<-- _cfc: [' + f + '][' + d + '][' + r + ']');
  return r;
}
/*******************************************************

  Event form card
  
*******************************************************/
function _evC(o){
  try{
    
    if(o.entity_id != au190.o.stateObj.entity_id){
      return;
    }
    //console.log('--> _evC: ' + o.entity_id);
    
    document.getElementById('dlg_btn').removeAttribute('class');
    var el = document.getElementById('dlg_btn');
    el.classList.add('ck');
    el.classList.add('bbtn');
    el.classList.add(o.state);
    
    document.getElementById('en_countDown').removeAttribute('class');
    el = document.getElementById('en_countDown');
    el.classList.add('ck');
    el.classList.add(o.attributes.au190.enable_countDown);

    el = document.getElementById('countDown');
    el.value = _cfc(1, o.attributes.au190.countDown);
    
    document.getElementById('en_scheduler').removeAttribute('class');
    el = document.getElementById('en_scheduler');
    el.classList.add('ck');
    el.classList.add(o.attributes.au190.enable_scheduler);

    document.getElementById('tab_scheduler').removeAttribute('class');
    el = document.getElementById('tab_scheduler');
    if(!o.attributes.au190.enable_scheduler){
      el.classList.add('h_w');
    }

    el = document.getElementById('da_scheduler');
    el.innerHTML = Object.keys(o.attributes.au190.scheduler).map(idx => 
    `<div class="m">
        <div class="t1"><input type="time" id="sht_${(parseInt(idx))}" class="ch_id" step="1" value='${o.attributes.au190.scheduler[idx].start_time}'></div>
        <div class="t1"><input type="time" id="shd_${(parseInt(idx))}" class="ch_id" step="1" value='${_cfc(1, o.attributes.au190.scheduler[idx].duration)}'></div>
        <ha-icon id="del_${(parseInt(idx))}" class="ck_id false" icon=${"mdi:delete"}></ha-icon>
      </div>`
     ).join('');

    el = document.getElementById('inf');
    el.innerHTML = Object.keys(o.attributes.i).map(idx => `
      <div class='m2'>
        <div class="t1">Topic:</div>
        <div class="t5">${idx}</div>
      </div>
      <div class='m2'>
        <div class="t1">IpAddress:</div>
        <div class="t5"><a href="http://${o.attributes.i[idx].IpAddress}" target="_blank" class="flase">${o.attributes.i[idx].IpAddress}</a></div>
      </div>
      <div class='m2'>
        <div class="t1">SSId:</div>
        <div class="t5">${o.attributes.i[idx].SSId}</div>
      </div>
      <div class='m2'>
        <div class="t1">Uptime:</div>
        <div class="t5">${o.attributes.i[idx].Uptime}</div>
      </div>
      <div class='m2'>
        <div class="t1">Time:</div>
        <div class="t5">${o.attributes.i[idx].Time}</div>
      </div>
      <div class='m2'>
        <div class="sep"></div>
      </div>
    `).join('');

  }catch{}
  
}
/*******************************************************

  Event form dialog
  o - card object
  e - event object
  f - type of event click, change ....
  
*******************************************************/
function _ev(o, e, f){

  if(e.classList.contains('ck') || e.classList.contains('ck_id') || f == 2 && e.classList.contains('ch_id')){
    
    //console.log('--> _ev: [' + f + '][' + e.id + '] ' + e.className);


    var fc = '';
    var id = '';
    if(e.classList.contains('ck_id') || e.classList.contains('ch_id')){//has more info
    
      const a = e.id.split('_');
      if(a.length == 2){
        fc = a[0];
        id = a[1];
      }
    }
    
    if(e.id == 'c_w' || e.id == 'r_dlg'){
      
      const d = document.getElementById('r_dlg');
      document.body.removeChild(d);

      /*
      if(o.offsetTop > 1000){
        console.log('--> _ev: [' + o.offsetTop + ']');
        au190.o.scrollIntoView(true);
      }else{
        au190.o.scrollIntoView(false);
      }
      */
      au190   = {};
      return;
      
    }else if(e.id == 'dlg_btn'){
      
      o._au190fc(1);
    
    }else if(e.id == 'en_countDown'){

      o.stateObj.attributes.au190.enable_countDown = !o.stateObj.attributes.au190.enable_countDown;
      
    }else if(e.id == 'countDown'){

      o.stateObj.attributes.au190.countDown = _cfc(0, e.value);

    }else if(e.id == 'en_scheduler'){

      o.stateObj.attributes.au190.enable_scheduler = !o.stateObj.attributes.au190.enable_scheduler;

    }else if(e.id == 'add_scheduler'){
      
      var u = {};
      let inputs = document.getElementById('shi').getElementsByTagName('input');
      
      for (let input of inputs){
        if(input.className == 'duration'){
          u[input.className] = _cfc(0, input.value);
        }else{
          u[input.className] = _cfc(2, input.value);
        }
      }

      o.stateObj.attributes.au190.scheduler.push(u);
      
    }else if(fc == 'del'){

      o.stateObj.attributes.au190.scheduler.splice(id, 1);
      
    }else if(fc == 'sht'){
      
      o.stateObj.attributes.au190.scheduler[id]['start_time'] = _cfc(2, e.value);
      
    }else if(fc == 'shd'){
      
      o.stateObj.attributes.au190.scheduler[id]['duration'] = _cfc(0, e.value);
    
    }


    if(e.id == 'btn_i'){
      o._au190fc(3);
    }else{
      o._au190fc(2, o.stateObj.attributes.au190);
    }
    
  }

}

function _openProp(o, c){

  //console.log('--> _openProp: ' + c.entity);
  
  au190.o = o;

  const dlg     = document.createElement('r_dialog');
  const style   = document.createElement('style');
  style.textContent = cssData();


  if(typeof o.stateObj === 'undefined'){
    return;
  }

  if(o.stateObj.state == 'unavailable'){
      
    dlg.innerHTML = `
      <div class='mw'>
        <div class='menu1'>
          <ha-icon icon='mdi:close' id='c_w' class='ck d_icon clickable' role='button' tabindex='0' aria-disabled='false'></ha-icon>
          <div class='d_title'>${o.name}</div>
        </div>
        <div class='wr_dlg'>
          <div class='dst'>
            <button class='off'>Unavailable</button>
          </div>
          <div class='m'>
            <div class='sep'></div>
          </div>
        </div>
      </div>
    `;
    
  }else{
    
    var tab_1 = o.stateObj.attributes.au190.enable_irrig_sys ? '' : 'h_w';
    var tab_2 = o.stateObj.attributes.au190.enable_scheduler ? '' : 'h_w';
    var tab_3 = o.stateObj.attributes.au190.enable_md ?        '' : 'h_w';
    var tab_4 = o.stateObj.attributes.au190.enable_protection ?'' : 'h_w';
    
    dlg.innerHTML = `
      <div class='mw'>
        <div class='menu1'>
          <ha-icon icon='mdi:close' id='c_w' class='ck d_icon clickable' role='button' tabindex='0' aria-disabled='false'></ha-icon>
          <div class='d_title'>${o.name}</div>
        </div>
        <div class='wr_dlg'>
          <div class='dst'>
            <ha-icon id='dlg_btn' class='ck bbtn ${o.stateObj.state}' icon=${o.icon}></ha-icon>
          </div>
          <div class='m'>
            <div class='sep'></div>
          </div>
          <div class='m1'>
            <div class='t3'><p>Count down:</p></div>
            <div class='t1'><input type='time' id='countDown' class='ch_id' step='1' value='${_cfc(1, o.stateObj.attributes.au190.countDown)}'></div>
            <div class='t4'><ha-icon id='en_countDown' class='ck ${o.stateObj.attributes.au190.enable_countDown}' icon=${'mdi:power'}></ha-icon></div>
          </div>
          <div class='m'>
            <div class='sep'></div>
          </div>
          <div class='m1'>
            <div class='t3'>Scheduler</div>
            <p></p>
            <ha-icon id='en_scheduler' class='ck ${o.stateObj.attributes.au190.enable_scheduler}' icon=${'mdi:power'}></ha-icon>
          </div>
          <div id='tab_scheduler' class='${tab_2}'>
            <div class='m'>
              <div class='t1'>Start time</div>
              <div class='t1'>Duration</div>
              <div class='t2'></div>
            </div>
            <div id='shi'>
              <div class='m'>
                <div class='t1'><input step='1' type='time' value='00:00' class='start_time'></div>
                <div class='t1'><input step='1' type='time' value='00:01' class='duration'></div>
                <ha-icon id='add_scheduler' class='ck g' icon=${'mdi:plus-box'}></ha-icon>
              </div>
            </div>
            <div id='da_scheduler'>
              ${Object.keys(o.stateObj.attributes.au190.scheduler).map(idx => 
              `<div class='m'>
                  <div class='t1'><input type='time' id='sht_${(parseInt(idx))}' class='ch_id' step='1' value='${o.stateObj.attributes.au190.scheduler[idx].start_time}'></div>
                  <div class='t1'><input type='time' id='shd_${(parseInt(idx))}' class='ch_id' step='1' value='${_cfc(1, o.stateObj.attributes.au190.scheduler[idx].duration)}'></div>
                  <ha-icon id='del_${(parseInt(idx))}' class='ck_id false' icon=${'mdi:delete'}></ha-icon>
                </div>`
               ).join('')}
            </div>
          </div>
          <div class='m'>
            <div class='sep'></div>
          </div>
          <div class='m1'>
            <div class='t3'>Info</div>
            <div></div>
            <ha-icon id='btn_i' class='ck false' icon=${'mdi:refresh'}></ha-icon>
          </div>
          <div id='inf'>
            ${Object.keys(o.stateObj.attributes.i).map(idx => `
              <div class='m2'>
                <div class='t1'>Topic:</div>
                <div class='t5'>${idx}</div>
              </div>
              <div class='m2'>
                <div class='t1'>IpAddress:</div>
                <div class='t5'><a href='http://${o.stateObj.attributes.i[idx].IpAddress}' target='_blank' class='flase'>${o.stateObj.attributes.i[idx].IpAddress}</a></div>
              </div>
              <div class='m2'>
                <div class='t1'>SSId:</div>
                <div class='t5'>${o.stateObj.attributes.i[idx].SSId}</div>
              </div>
              <div class='m2'>
                <div class='t1'>Uptime:</div>
                <div class='t5'>${o.stateObj.attributes.i[idx].Uptime}</div>
              </div>
              <div class='m2'>
                <div class='t1'>Time:</div>
                <div class='t5'>${o.stateObj.attributes.i[idx].Time}</div>
              </div>
              <div class='m'>
                <div class='sep'></div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }
  
  dlg.appendChild(style);
  dlg.setAttribute('id', 'r_dlg');
  dlg.setAttribute('class', 'ck');
  document.body.appendChild(dlg);


  dlg.addEventListener('click', function(e){
    if(e.target){
      _ev(o, e.target, 1);
    }
  });
  
  dlg.addEventListener('change', function(e){
    if(e.target){
      _ev(o, e.target, 2);
    }
  });

}

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
    const card = document.createElement('div');
    const style = document.createElement('style');
    style.textContent = cssData();

    
    if(typeof config.icon !== 'undefined'){
      this.icon = config.icon;
    }else{
      this.icon = 'mdi:power';
    }
    
    card.innerHTML = `
      <div class='m_c'>
        <div class='m'>
          <ha-icon id='m_1' class='off c_icon' icon='mdi:dots-vertical'></ha-icon>
          <div id='pop1' class='ct0'>
            <div class='ct1'>
              <ha-icon id='i_0' class='off' icon=${'mdi:timer'}></ha-icon>
              <p id='cname'>${this.name}</p>
            </div>
            <div class='ct2'>
              <ha-icon id='i_1' class='off' icon=${'mdi:calendar-clock'}></ha-icon>
              <p id='i_2'></p>
            </div>
          </div>
          <div id='btn_st'></div>
        </div>
        <div id='ov_st'></div>
      </div>
    `;
    card.appendChild(style);
    root.appendChild(card);
    
    this._evbtns(root, config);

    const m_1 = root.getElementById('m_1');
    m_1.addEventListener('click', () => _openProp(this, config));
    
    const p_1 = root.getElementById('pop1');
    p_1.addEventListener('click', () => this._openProp1(cardConfig.entity));

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
    
    if(typeof config.name === 'string'){
      this.name = config.name
    }else if(config.name === false){
      this.name = false
    }else{
      this.name = this.stateObj.attributes.friendly_name
    }
    
    this._updateButtons(root, config);
    //console.log(this.stateObj);
  }

  _isChanged(){
    try{
      var r = false;
      
      const new_state = {
        state: this.stateObj.state,
        au190: (this.stateObj.attributes.au190) ? this.stateObj.attributes.au190 : {},
      }
      
      if( (this._old_state === undefined)
        || this._old_state.state !== new_state.state
        || this._old_state.au190 !== new_state.au190

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
 
  _au190fc(f, o){
    
    //console.log('--> _au190fc: ' + f);
    
    if(typeof this._hass === 'undefined'){
      return;
    }
      
    this._hass.callService('au190_mqtt_switch', 'au190_fc', {
      
      entity_id: this.stateObj.entity_id,
      fc: f,
      au190: o,
    });

  }

  _ckoverlay(el, el1, config){

    el.style.pointerEvents = 'none';
    el.classList.add('fadeOut');
    el1.icon = 'mdi:lock-open-outline';

    window.setTimeout(() => {
      el.style.pointerEvents = '';
      el.classList.remove('fadeOut');
      el1.icon = 'mdi:lock-outline';
    }, 3000);
    
  }

  _openProp1(entityId){

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
  
  last_ch(){
    if (!this.stateObj.last_changed) {
      return '';
    }

    const d1  = new Date();
    const d2  = new Date(this.stateObj.last_changed);
    var d3    = parseInt((d1 - d2) / (1000 * 60 * 60 * 24), 10);
    if(d3 > 0){
      d3 += ' day ago';
      return d3;
    }
    d3    = parseInt((d1 - d2) / (1000 * 60 * 60), 10);
    if(d3 > 0){
      d3 += ' hours ago';
      return d3;
    }
    d3    = parseInt((d1 - d2) / (1000 * 60), 10);
    if(d3 > 0){
      d3 += ' minutes ago';
      return d3;
    }
    d3    = parseInt((d1 - d2) / (1000 * 60), 10);
    if(d3 >= 0){
      d3 += ' seconds ago';
    }
    return d3;
  }

  /*******************************************************

    Card fc
  
  *******************************************************/

  _updateButtons(root, config){
    
    try{
      _evC(this.stateObj);
      
      var el  = root.getElementById('cname');
      el.innerHTML = this.name;
      
      el = root.getElementById('btn');

      if(this.stateObj.state == 'unavailable'){
        
        el = root.getElementById('btn_st');
        el.innerHTML = `Unavailable`;
        
        el = root.getElementById('ov_st');
        el.innerHTML = ``;
        
        root.getElementById('i_2').innerHTML = this.last_ch();
        
      }else{

        this._evbtns(root, config);
        
        el.removeAttribute('class');
        el.classList.add('c_btn');
        el.classList.add(this.stateObj.state);

        el = root.getElementById('i_0');
        el.removeAttribute('class');
        el.classList.add(this.stateObj.attributes.au190.enable_countDown);
        
        el = root.getElementById('i_1');
        el.removeAttribute('class');
        el.classList.add(this.stateObj.attributes.au190.enable_scheduler);
        
        root.getElementById('i_2').innerHTML = this.last_ch();
        
      }
    }catch{}
  }
  
  _evbtns(root, config){
    
    var el = root.getElementById('btn');
    
    if(el == null){
      
      el = root.getElementById('btn_st');
      el.innerHTML = `<ha-icon id='btn' class='c_btn off' icon=${this.icon}></ha-icon>`;
      el = root.getElementById('btn');
      el.addEventListener('click', (e) => this._au190fc(1));

      if(config.lock){
        el = root.getElementById('ov_st');
        el.innerHTML = `<div id='overlay'><ha-icon id='lock' class='lbtn' icon='mdi:lock-outline'></ha-icon></div>`;
          
        var el1 = root.getElementById('lock');
        el = root.getElementById('overlay');
        el.addEventListener('click', (e) => this._ckoverlay(el, el1, config));
      }
    
    }
  }
  
  getCardSize(){
    3;
  }
  
}
customElements.define('au190-mqtt_card', au190_MqttCard);