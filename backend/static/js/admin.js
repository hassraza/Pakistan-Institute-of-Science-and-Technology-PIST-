// PIST Academic ERP Admin JS Helpers
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('admin-sidebar');
  const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
  const sidebarClose = document.querySelector('[data-sidebar-close]');

  const setSidebarOpen = (isOpen) => {
    if (!sidebar || !sidebarToggle || !sidebarClose) return;
    sidebar.classList.toggle('is-open', isOpen);
    sidebarClose.classList.toggle('is-visible', isOpen);
    sidebarToggle.setAttribute('aria-expanded', String(isOpen));
  };

  sidebarToggle?.addEventListener('click', () => {
    setSidebarOpen(!sidebar.classList.contains('is-open'));
  });
  sidebarClose?.addEventListener('click', () => setSidebarOpen(false));
  sidebar?.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => setSidebarOpen(false));
  });

  // 1. Data-confirm confirmation popups
  document.querySelectorAll('[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.getAttribute('data-confirm');
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  // 2. Ctrl+K / Cmd+K Omnisearch shortcut
  const searchInput = document.getElementById('erp-global-search');
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    }
  });

  // 3. Omnisearch Enter key search redirect
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (query) {
          window.location.href = `/university-admin/applications/?q=${encodeURIComponent(query)}`;
        }
      }
    });
  }

  // 4. Select All Checkboxes in data tables
  const selectAllBox = document.getElementById('select-all-applicants');
  if (selectAllBox) {
    selectAllBox.addEventListener('change', () => {
      document.querySelectorAll('.applicant-select-checkbox').forEach(cb => {
        cb.checked = selectAllBox.checked;
      });
    });
  }
});

// Modal helpers
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('is-active');
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('is-active');
}

// Escape key to close modals
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
      setSidebarOpen(false);
    document.querySelectorAll('.admin-modal-backdrop.is-active').forEach(modal => {
      modal.classList.remove('is-active');
    });
  }
});
