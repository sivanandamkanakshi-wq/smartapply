/* =========================================================
   SmartApply — home.js
   Vanilla JavaScript only — no frameworks, no libraries
   ========================================================= */

document.addEventListener('DOMContentLoaded', () => {
  initFooterYear();
  initNavbarScroll();
  initHamburgerMenu();
  initSmoothScrollClose();
  initActiveNavOnScroll();
  initScrollReveal();
  initDashboardAnimation();
  initDemoModal();
});

/* ---------- Footer year ---------- */
function initFooterYear() {
  const yearEl = document.getElementById('year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }
}

/* ---------- Navbar scroll effect ---------- */
function initNavbarScroll() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const toggleScrolled = () => {
    if (window.scrollY > 12) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  };

  toggleScrolled();
  window.addEventListener('scroll', toggleScrolled, { passive: true });
}

/* ---------- Mobile hamburger menu ---------- */
function initHamburgerMenu() {
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('navLinks');
  if (!hamburger || !navLinks) return;

  hamburger.addEventListener('click', () => {
    const isOpen = navLinks.classList.toggle('open');
    hamburger.classList.toggle('open', isOpen);
    hamburger.setAttribute('aria-expanded', String(isOpen));
  });

  /* Close menu on Escape */
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && navLinks.classList.contains('open')) {
      navLinks.classList.remove('open');
      hamburger.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
      hamburger.focus();
    }
  });
}

/* ---------- Close mobile menu after clicking a nav link ---------- */
function initSmoothScrollClose() {
  const navLinks = document.getElementById('navLinks');
  const hamburger = document.getElementById('hamburger');
  if (!navLinks) return;

  navLinks.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      navLinks.classList.remove('open');
      if (hamburger) {
        hamburger.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      }
    });
  });
}

/* ---------- Highlight active nav link based on scroll position ---------- */
function initActiveNavOnScroll() {
  const sections = document.querySelectorAll('main section[id], header[id]');
  const navAnchors = document.querySelectorAll('.nav-link');
  if (!sections.length || !navAnchors.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('id');
          navAnchors.forEach((anchor) => {
            anchor.classList.toggle('active', anchor.getAttribute('href') === `#${id}`);
          });
        }
      });
    },
    { rootMargin: '-45% 0px -50% 0px', threshold: 0 }
  );

  sections.forEach((section) => observer.observe(section));
}

/* ---------- Scroll reveal for fade-up elements below the fold ---------- */
function initScrollReveal() {
  const revealTargets = document.querySelectorAll(
    '.features-grid .feature-card, .timeline-step, .company-card, .stat-block, .testimonial-card, .cta-inner'
  );

  if (!revealTargets.length) return;

  revealTargets.forEach((el) => el.classList.add('reveal'));

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );

  revealTargets.forEach((el) => observer.observe(el));
}

/* ---------- Animate hero dashboard: progress bar, score ring, counters ---------- */
function initDashboardAnimation() {
  const dashboardCard = document.querySelector('.dashboard-card');
  const progressFill = document.getElementById('progressFill');
  const progressValue = document.getElementById('progressValue');
  const counters = document.querySelectorAll('.stat-num[data-count]');

  if (!dashboardCard) return;

  const targetProgress = 87;
  let hasAnimated = false;

  const animateCounters = () => {
    counters.forEach((counter) => {
      const target = parseInt(counter.getAttribute('data-count'), 10) || 0;
      const duration = 1400;
      const start = performance.now();

      const step = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        counter.textContent = Math.round(eased * target);
        if (progress < 1) {
          requestAnimationFrame(step);
        }
      };
      requestAnimationFrame(step);
    });
  };

  const animateProgress = () => {
    if (!progressFill || !progressValue) return;
    let current = 0;
    progressFill.style.width = `${targetProgress}%`;

    const duration = 1400;
    const start = performance.now();

    const step = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      current = Math.round(progress * targetProgress);
      progressValue.textContent = `${current}%`;
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  };

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !hasAnimated) {
          hasAnimated = true;
          animateProgress();
          animateCounters();
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.4 }
  );

  observer.observe(dashboardCard);
}

/* ---------- Watch Demo modal ---------- */
function initDemoModal() {
  const openBtn = document.getElementById('watchDemoBtn');
  const modal = document.getElementById('demoModal');
  const closeBtn = document.getElementById('demoModalClose');

  if (!openBtn || !modal || !closeBtn) return;

  let lastFocused = null;

  const openModal = () => {
    lastFocused = document.activeElement;
    modal.hidden = false;
    closeBtn.focus();
    document.body.style.overflow = 'hidden';
  };

  const closeModal = () => {
    modal.hidden = true;
    document.body.style.overflow = '';
    if (lastFocused) lastFocused.focus();
  };

  openBtn.addEventListener('click', openModal);
  closeBtn.addEventListener('click', closeModal);

  modal.addEventListener('click', (event) => {
    if (event.target === modal) closeModal();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !modal.hidden) closeModal();
  });
}