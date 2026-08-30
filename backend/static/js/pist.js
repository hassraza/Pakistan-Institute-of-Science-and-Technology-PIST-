document.addEventListener('DOMContentLoaded', () => {
  const menuToggle = document.getElementById('mobile-menu-toggle') || document.querySelector('[data-menu-toggle]');
  const mobileDrawer = document.getElementById('mobile-nav-drawer') || document.querySelector('[data-site-nav]');
  const menuBackdrop = document.getElementById('mobile-menu-backdrop');
  const menuCloseBtn = document.getElementById('mobile-menu-close');

  function openMobileMenu() {
    if (!mobileDrawer) return;
    mobileDrawer.classList.remove('translate-x-full');
    mobileDrawer.classList.add('translate-x-0', 'is-open');
    if (menuBackdrop) {
      menuBackdrop.classList.remove('opacity-0', 'pointer-events-none');
      menuBackdrop.classList.add('opacity-100', 'pointer-events-auto');
    }
    if (menuToggle) {
      menuToggle.setAttribute('aria-expanded', 'true');
    }
    document.body.classList.add('overflow-hidden');
  }

  function closeMobileMenu() {
    if (!mobileDrawer) return;
    mobileDrawer.classList.remove('translate-x-0', 'is-open');
    mobileDrawer.classList.add('translate-x-full');
    if (menuBackdrop) {
      menuBackdrop.classList.remove('opacity-100', 'pointer-events-auto');
      menuBackdrop.classList.add('opacity-0', 'pointer-events-none');
    }
    if (menuToggle) {
      menuToggle.setAttribute('aria-expanded', 'false');
    }
    document.body.classList.remove('overflow-hidden');
  }

  if (menuToggle) {
    menuToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = mobileDrawer && mobileDrawer.classList.contains('is-open');
      if (isOpen) {
        closeMobileMenu();
      } else {
        openMobileMenu();
      }
    });
  }

  if (menuCloseBtn) {
    menuCloseBtn.addEventListener('click', closeMobileMenu);
  }

  if (menuBackdrop) {
    menuBackdrop.addEventListener('click', closeMobileMenu);
  }

  // Close when clicking any nav link in drawer
  if (mobileDrawer) {
    mobileDrawer.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', closeMobileMenu);
    });
  }

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && mobileDrawer && mobileDrawer.classList.contains('is-open')) {
      closeMobileMenu();
      if (menuToggle) menuToggle.focus();
    }
  });

  document.querySelectorAll('[data-confirm]').forEach((element) => {
    element.addEventListener('submit', (event) => {
      const message = element.getAttribute('data-confirm');
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll('[data-print-roll-slip]').forEach((button) => {
    button.addEventListener('click', () => window.print());
  });
});
