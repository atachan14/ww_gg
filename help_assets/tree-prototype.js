"use strict";
let step=0;
const phases=['Day1','Day2へ分岐','決着まで分岐','末端の勝率','Day2の勝率','Day1の勝率'];
const el=id=>document.getElementById(id);
function visible(id,show){el(id).classList.toggle('stage-hidden',!show);el(id).setAttribute('aria-hidden',String(!show));}
function render(){
el('phase').textContent=`${step+1} / 6　${phases[step]}`;
el('back').disabled=step===0;el('next').disabled=step===5;
el('stepnav').innerHTML=phases.map((name,i)=>`<button data-step="${i}" ${i===step?'aria-current="step"':''}>${i+1}. ${name}</button>`).join('');
['firstwin','three','e1','e2','p1','p2','l1','l2','night-note1','night-note2'].forEach(id=>visible(id,step>=1));
['lastwin','lastloss','e3','e4','p3','p4','l3','l4'].forEach(id=>visible(id,step>=2));
['c1','c2'].forEach(id=>visible(id,step===5));['c3','c4'].forEach(id=>visible(id,step>=4));
['v1','v2','v3'].forEach((id,i)=>el(id).textContent=step>=3?['1','1','0'][i]:'');
el('threevalue').textContent=step>=4?'1/3':'';
el('rootvalue').textContent=step>=5?'7/15':'';el('rootpercent').textContent=step>=5?'46.7%':'';
['e1','e2','e3','e4'].forEach((id,i)=>{
 const active=step===1&&i<2||step===2&&i>=2||step===4&&i>=2||step===5&&i<2;
 el(id).classList.toggle('active',active);
 el(id).classList.toggle('reverse',step===4&&i>=2||step===5&&i<2);
});
['l1','l2','l3','l4'].forEach((id,i)=>el(id).classList.toggle('highlight',step===4&&i>=2||step===5&&i<2));
['root','three','firstwin','lastwin','lastloss'].forEach(id=>el(id).classList.toggle('value-active',step===0&&id==='root'||step===3&&['firstwin','lastwin','lastloss'].includes(id)||step===4&&id==='three'||step===5&&id==='root'));
el('e2').classList.toggle('final',step===5);el('l2').classList.toggle('final',step===5);
el('calculation').innerHTML=step===4?'<span>1/3 × 1 + 2/3 × 0 = 1/3</span>':step===5?'<span class="term1">1/5</span><b>+</b><span class="term2">4/5 × 1/3</span><b>= 7/15</b>':'';
}
el('next').onclick=()=>{step=Math.min(5,step+1);render()};
el('back').onclick=()=>{step=Math.max(0,step-1);render()};
el('stepnav').addEventListener('click',e=>{const button=e.target.closest('[data-step]');if(!button)return;step=+button.dataset.step;render();el('stepnav').querySelector(`[data-step="${step}"]`).focus();});
document.addEventListener('keydown',e=>{if(e.altKey||e.ctrlKey||e.metaKey)return;if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();step=Math.max(0,Math.min(5,step+(e.key==='ArrowRight'?1:-1)));render()}});
render();
