// PIST Academic ERP Admin JS Helpers
function setSidebarOpen(isOpen) {
  const sidebar = document.getElementById('admin-sidebar');
  const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
  const sidebarClose = document.querySelector('[data-sidebar-close]');

  if (!sidebar || !sidebarToggle || !sidebarClose) return;
  sidebar.classList.toggle('is-open', isOpen);
  sidebarClose.classList.toggle('is-visible', isOpen);
  sidebarToggle.setAttribute('aria-expanded', String(isOpen));
}

document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('admin-sidebar');
  const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
  const sidebarClose = document.querySelector('[data-sidebar-close]');

  sidebarToggle?.addEventListener('click', () => {
    setSidebarOpen(!sidebar.classList.contains('is-open'));
  });
  sidebarClose?.addEventListener('click', () => setSidebarOpen(false));
  sidebar?.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => setSidebarOpen(false));
  });

  document.querySelectorAll('[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.getAttribute('data-confirm');
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

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

  const selectAllBox = document.getElementById('select-all-applicants');
  if (selectAllBox) {
    selectAllBox.addEventListener('change', () => {
      document.querySelectorAll('.applicant-select-checkbox').forEach(cb => {
        cb.checked = selectAllBox.checked;
      });
    });
  }
});

function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('is-active');
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('is-active');
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    setSidebarOpen(false);
    document.querySelectorAll('.admin-modal-backdrop.is-active').forEach(modal => {
      modal.classList.remove('is-active');
    });
  }
});
