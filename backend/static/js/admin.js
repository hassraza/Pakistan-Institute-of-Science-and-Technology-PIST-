// PIST Academic ERP Admin JS Helpers
document.addEventListener('DOMContentLoaded', () => {
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
    document.querySelectorAll('.admin-modal-backdrop.is-active').forEach(modal => {
      modal.classList.remove('is-active');
    });
  }
});
