// SmartApply — auth.js
// Shared behaviour for login/register forms: password visibility toggle,
// button ripple effect, and a loading state on submit. Validation stays
// server-side (Flask flash messages); this only adds UX polish and never
// blocks a legitimately-filled form from submitting.

document.addEventListener('DOMContentLoaded', () => {
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // Password show/hide
  document.querySelectorAll('.toggle-eye').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (!input) return;
      const isHidden = input.type === 'password';
      input.type = isHidden ? 'text' : 'password';
      btn.setAttribute('aria-pressed', String(isHidden));
      btn.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
      const openIcon = btn.querySelector('.eye-open');
      const closedIcon = btn.querySelector('.eye-closed');
      if (openIcon) openIcon.hidden = isHidden;
      if (closedIcon) closedIcon.hidden = !isHidden;
    });
  });

  // Ripple effect on buttons
  document.querySelectorAll('.btn-ripple').forEach((btn) => {
    btn.addEventListener('click', function (e) {
      const circle = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      circle.style.width = circle.style.height = `${size}px`;
      circle.style.left = `${e.clientX - rect.left - size / 2}px`;
      circle.style.top = `${e.clientY - rect.top - size / 2}px`;
      circle.classList.add('ripple');
      this.appendChild(circle);
      setTimeout(() => circle.remove(), 600);
    });
  });

  // Loading spinner on submit. The form still does a normal POST — Flask
  // handles the redirect (to /dashboard on success, back to /login with a
  // flash message on failure) — this just gives instant visual feedback
  // instead of a page that looks frozen while the request is in flight.
  document.querySelectorAll('form.auth-form').forEach((form) => {
    form.addEventListener('submit', (e) => {
      // Basic required-field check so we don't show a spinner for a form
      // the browser is about to block anyway.
      const requiredFields = form.querySelectorAll('[required]');
      let valid = true;
      requiredFields.forEach((field) => {
        if (!field.value.trim()) {
          valid = false;
          field.classList.add('field-error');
        } else {
          field.classList.remove('field-error');
        }
      });
      if (!valid) return;

      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.classList.contains('is-loading')) {
        submitBtn.classList.add('is-loading');
        submitBtn.disabled = true;
      }
    });
  });

  // Clear the red error outline as soon as the person starts fixing a field
  document.querySelectorAll('.input-wrap input').forEach((input) => {
    input.addEventListener('input', () => input.classList.remove('field-error'));
  });
});
