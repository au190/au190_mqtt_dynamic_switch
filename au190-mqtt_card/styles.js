export function cssData(user) {
var css =`

/* popup */

*
{
box-sizing: border-box;
}

#r_dlg
{
z-index: 103;
position: fixed;
top: 0px;
left: 0px;
width: 100%;
height: 100%;
background-color: rgb(0,0,0, 0.6);
transition: opacity 0.2s;
outline: none;
}

.mw
{
position: fixed;
z-index: 104;
box-sizing: border-box;
max-width: 400px;
width: 100%;
height: calc(100% - 40px);
left: 50%;
margin: 20px 0px 20px 0px;
transform: translateX(-50%);
background-color: #ffffff;
text-align: center;
color: #808080;
outline: none;
}

.menu1
{
text-align: center;
--background-color: var(--secondary-background-color);
background-color: var(--primary-color);
color: #ffffff;
height: 64px;
}

.wr_dlg
{
overflow-y: scroll;
height: calc(100% - 64px);
background: var(--primary-background-color);
padding: 0px 16px 0px 24px;
}

.dst
{
display: flex;
flex-wrap: wrap;
justify-content: space-around;
padding: 8px;
margin-bottom: -20px;
}

.sep
{
width: 100%;
height: 1px;
background-image: linear-gradient(to right, transparent, transparent, var(--primary-color), transparent, transparent);
}

.h_w
{
display: none;
}

.m, .m1, .m2
{
display: flex;
justify-content: space-between;
align-items: center;
align-content: center;
flex-basis:100%;
min-height: 40px;
}

.m1
{
min-height: 50px;
}

.m2
{
min-height: 25px;
padding: 0px 8px 0px 0px;
}

.t1, .t3, .t4, .t1 input
{
width: 122px;
text-align: left;
}

.t2
{
width: 40px;
height: 40px;
}

.t3
{
font-weight: bold;
}

.t4
{
text-align: right;
}
/* Menu */

.menu1 a
{
display: inline-block;
color: white;
text-align: center;
padding: 16px;
text-decoration: none;
}

.menu1 a:hover
{
background-color: #777;
}

.mst
{
display: flex;
flex-wrap: wrap;
justify-content: space-around;
padding: 8px 16px;
}
  
button
{
display: inline-block;
max-width: 125px;
min-width: 70px;
height: 36px;
margin-bottom: 16px;
padding: 1px 6px;
border-radius: 4px;
border: 1px solid var(--primary-color);
border-image: initial;
background-color: var(--lovelace-background);
font-family: var(--ha-card-header-font-family, inherit);
font-size: var(--ha-card-header-font-size, 18px);
cursor: pointer;
}

button:focus
{
outline: 0px;
}	 

.d_icon
{
position: absolute;
top: 12px;
left: 16px;
color: var(--text-primary-color);
}

.d_title 
{
color: var(--text-primary-color);
font-family: var(--ha-card-header-font-family, inherit);
font-size: var(--ha-card-header-font-size, 24px);
letter-spacing: -0.012em;
line-height: 64px;
margin: auto;
}


.bbtn
{
height: 80px;
width: 80px;
}

.c_btn
{
height: 48px;
width: 48px;
}

.lbtn
{
margin: 10px;
height: 20px;
width: 20px;
}

.on,.ON,.true
{
color: var(--primary-color);
font-weight: bold;
cursor: pointer;
}

.off,.OFF,.false
{
color: #808080;
cursor: pointer;
}

.g
{
color: green;
cursor: pointer;
}

.error
{
color: red;
}
  
.w_s input
{
display: none!important;
}


.w_s input[type=checkbox] + label
{
display: inline-block;
border-radius: 6px;
border: 1px solid var(--primary-color);
height: 25px;
width: 25px;
margin-right: 3px;
line-height: 25px;
text-align: center;
cursor: pointer;
}

.w_s input[type=checkbox]:checked + label
{
background: var(--primary-color);
color: #ffffff
}

/* card */

.m_c
{
position: relative;
}

.ct0
{
margin-left: 16px;
min-width: 0px;
width: 100%;
cursor: pointer;
}

.ct1, .ct2
{
color: var(--secondary-text-color);
}

.ct1
{
color: var(--ha-card-header-color, --primary-text-color);
}

.ct1 > p, .ct2 > p, .ibox > p
{
display: inline-block;
margin-block-start: 0px;
margin-block-end: 0px;
margin-inline-start: 0px;
margin-inline-end: 0px;
}
	
.c_icon
{
display: inline-block;
width: 47px;
height: 40px;
outline: none;
margin: 0px;
}
/*Lock icon*/

#overlay.fadeOut
{
opacity: 0;
}

#overlay 
{
position: absolute;
right: -24px;
top: 26px;
width: 48px;
height: 48px;
transform: translate(-50%, -50%);
text-align: center;
z-index: 1;
transition: opacity 1s; 
cursor: pointer;
}

#ov_st
{
width: 0px;
height: 0px;
}

#lock
{
  opacity: 1;
  -webkit-animation-duration: 5s;animation-duration 5s;
  -webkit-animation-fill-mode: both;animation-full-mode: both;
}


#i_0, #i_1
{
height: 17px;
width: 17px;
padding: 0px;
margin: 0px;
outline: none;
cursor: default;
}




@media (max-width: 580px)
{
.mw
{
position: fixed;
z-index: 104;
box-sizing: border-box;
max-width: 420px;
width: 100%;
height: 100%;
left: 50%;
margin: 0px;
transform: translateX(-50%);
background-color: #ffffff;
text-align: center;
color: #808080;
outline: none;
}
}
  
`
return css;
}
