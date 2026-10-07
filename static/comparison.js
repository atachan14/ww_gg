"use strict";
const comparisonForm = document.querySelector('#comparison-form');
let comparisonFormat="fraction";
function applyComparisonFormat() {
  document.querySelectorAll('#comparison-results [data-fraction]').forEach(e=>e.textContent=comparisonFormat==='fraction'?e.dataset.fraction:e.dataset.percent);
}
document.querySelectorAll('input[name="comparison-format"]').forEach(input=>input.addEventListener('change',()=>{comparisonFormat=input.value;applyComparisonFormat();}));
let comparisonBusy = false;
let comparisonPending = false;
let comparisonVersion = 0;
const comparisonStatus = document.querySelector('#comparison-status');
function showComparisonPlayers() {
  const total=['citizens','mediums','seers','hunters','wolves'].reduce((n,key)=>n+Number(comparisonForm.elements[key].value),0);
  document.querySelectorAll('[data-comparison-player]').forEach(label=>{
    label.hidden=Number(label.dataset.comparisonPlayer)>total;
    label.querySelector('select').disabled=label.hidden;
  });
}
async function updateComparison(event) {
  if (event) event.preventDefault();
  showComparisonPlayers();
  comparisonVersion++;
  comparisonPending=true;
  document.querySelector('#comparison-results').hidden=true;
  comparisonStatus.textContent='比較を再計算しています。現行ゲームは進みません。';
  if (comparisonBusy) return;
  comparisonBusy=true;
  while (comparisonPending) {
    comparisonPending=false;
    const version=comparisonVersion;
    try {
      const response=await fetch(comparisonForm.action,{method:'POST',body:new FormData(comparisonForm),headers:{'X-Comparison':'partial'}});
      const html=new DOMParser().parseFromString(await response.text(),'text/html');
      if (version!==comparisonVersion) continue;
      const result=html.querySelector('#comparison-results');
      if (!result) throw new Error('No comparison result');
      document.querySelector('#comparison-results').replaceWith(result);
      applyComparisonFormat();
      comparisonStatus.textContent='';
    } catch (_) {
      if (version===comparisonVersion) comparisonStatus.textContent='比較を更新できませんでした。再計算してください。旧結果は非表示です。';
    }
  }
  comparisonBusy=false;
}
comparisonForm.addEventListener('change',updateComparison);
comparisonForm.addEventListener('submit',updateComparison);
showComparisonPlayers();
