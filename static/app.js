"use strict";

window.addEventListener("pageshow", (event) => {
  if (event.persisted) window.location.reload();
});

document.querySelectorAll("form[data-submit-once]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!form.checkValidity()) {
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
