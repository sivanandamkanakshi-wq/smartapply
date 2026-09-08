// SmartApply — app_shell.js
// Shared behaviour for the navbar + sidebar wrapper used on every
// logged-in page. Kept dependency-free (no build step) on purpose.

document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('appSidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const menuBtn = document.getElementById('navbarMenuBtn');
  const backdrop = document.getElementById('sidebarBackdrop');
  const userMenu = document.getElementById('userMenu');
  const userMenuTrigger = document.getElementById('userMenuTrigger');

  // Desktop collapse/expand
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('is-collapsed');
    });
  }

  // Mobile slide-in
  function openMobileSidebar() {
    sidebar?.classList.add('is-mobile-open');
    backdrop?.classList.add('is-visible');
  }
  function closeMobileSidebar() {
    sidebar?.classList.remove('is-mobile-open');
    backdrop?.classList.remove('is-visible');
  }
  menuBtn?.addEventListener('click', openMobileSidebar);
  backdrop?.addEventListener('click', closeMobileSidebar);

  // User dropdown
  userMenuTrigger?.addEventListener('click', (e) => {
    e.stopPropagation();
    userMenu?.classList.toggle('is-open');
  });
  document.addEventListener('click', (e) => {
    if (userMenu && !userMenu.contains(e.target)) {
      userMenu.classList.remove('is-open');
    }
  });

  // Auto-dismiss flash messages after a few seconds
  document.querySelectorAll('.app-flash-stack .flash-message').forEach((msg, i) => {
    setTimeout(() => {
      msg.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      msg.style.opacity = '0';
      msg.style.transform = 'translateY(-6px)';
      setTimeout(() => msg.remove(), 400);
    }, 4500 + i * 300);
  });
});
