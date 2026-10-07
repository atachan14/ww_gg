"use strict";

const formatInputs = document.querySelectorAll('input[name="probability-format"]');
let probabilityFormat = "percent";
try {
  if (localStorage.getItem("ww_gg.probability-format") === "fraction") probabilityFormat = "fraction";
} catch (_) { /* Display still works if browser storage is unavailable. */ }

function applyProbabilityFormat() {
  document.querySelectorAll(".probability").forEach((element) => {
    element.textContent = probabilityFormat === "fraction" ? element.dataset.fraction : element.dataset.percent;
  });
  formatInputs.forEach((input) => { input.checked = input.value === probabilityFormat; });
}

formatInputs.forEach((input) => {
  input.addEventListener("change", () => {
    probabilityFormat = input.value;
    try { localStorage.setItem("ww_gg.probability-format", probabilityFormat); } catch (_) {}
    applyProbabilityFormat();
  });
});
applyProbabilityFormat();

window.addEventListener("pageshow", (event) => {
  if (event.persisted) window.location.reload();
});

document.querySelectorAll("form[data-submit-once]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!event.submitter?.formNoValidate && !form.checkValidity()) {
      event.preventDefault();
      form.reportValidity();
      return;
    }
    if (form.dataset.submitting === "true") {
      event.preventDefault();
      return;
    }
    form.dataset.submitting = "true";
    form.querySelectorAll('button[type="submit"]').forEach((button) => {
      button.disabled = true;
    });
  });
});

document.querySelectorAll('input[name="target"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    const preview = document.querySelector("[data-target-preview]");
    if (preview) preview.textContent = `Player ${radio.value}`;
  });
});

const count = document.querySelector('#player-count');
if (count) count.addEventListener('change', () => {
  document.querySelector('#villager-count').innerHTML = `${Number(count.value) - 1}<small>人</small>`;
  document.querySelector('#total-count').innerHTML = `${Number(count.value)}<small>人</small>`;
});
const permission = document.querySelector('#allow-self-bite');
const inclusion = document.querySelector('#include-self-bite');
if (permission && inclusion) permission.addEventListener('change', () => {
  inclusion.disabled = !permission.checked;
  if (!permission.checked) inclusion.checked = false;
});
