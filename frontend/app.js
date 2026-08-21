const API_BASE = '/api/v1';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function cardBadge(text, type = 'muted') {
  const badge = el('span', `badge badge--${type}`, text);
  return badge;
}

function renderCampus(cardData) {
  const card = el('article', 'info-card');
  const top = el('div', 'info-card__top');
  top.appendChild(cardBadge(cardData.code, 'muted'));
  top.appendChild(cardBadge(cardData.admissions_open ? 'Admissions Open' : 'Admissions Closed', cardData.admissions_open ? 'success' : 'muted'));
  card.appendChild(top);
  card.appendChild(el('h3', '', cardData.name));
  card.appendChild(el('p', 'meta', `${cardData.city} - ${cardData.address}`));
  card.appendChild(el('p', 'meta', `${cardData.departments.length} departments`));
  return card;
}

function renderProgram(program) {
  const card = el('article', 'program-card');
  const meta = el('div', 'program-card__meta');
  meta.appendChild(cardBadge(program.campus_code, 'muted'));
  meta.appendChild(cardBadge(program.admissions_open ? 'Admissions Open' : 'Admissions Closed', program.admissions_open ? 'success' : 'muted'));
  card.appendChild(meta);
  card.appendChild(el('h3', '', program.name));
  card.appendChild(el('p', '', `${program.department} • ${program.campus_name}`));
  card.appendChild(el('p', 'meta', `${program.duration} • ${program.required_test_type}`));
  return card;
}

async function loadSiteData() {
  const campusGrid = document.getElementById('campus-grid');
  const programGrid = document.getElementById('program-grid');

  try {
    const response = await fetch(`${API_BASE}/public/site/`);
    const data = await response.json();

    if (campusGrid) {
      campusGrid.innerHTML = '';
      data.campuses.forEach((campus) => campusGrid.appendChild(renderCampus(campus)));
    }

    if (programGrid) {
      programGrid.innerHTML = '';
      data.featured_programs.forEach((program) => programGrid.appendChild(renderProgram(program)));
    }
  } catch (error) {
    if (campusGrid) {
      campusGrid.innerHTML = '<div class="empty">Unable to load campus data.</div>';
    }
    if (programGrid) {
      programGrid.innerHTML = '<div class="empty">Unable to load program data.</div>';
    }
  }
}

async function trackApplication(event) {
  event.preventDefault();
  const reference = document.getElementById('reference').value.trim();
  const result = document.getElementById('track-result');
  if (!reference) {
    result.classList.remove('hidden');
    result.innerHTML = '<p>Please enter a roll number or application ID.</p>';
    return;
  }

  result.classList.remove('hidden');
  result.innerHTML = '<p>Looking up application...</p>';

  try {
    const response = await fetch(`${API_BASE}/public/track/?reference=${encodeURIComponent(reference)}`);
    const data = await response.json();

    if (!response.ok) {
      result.innerHTML = `<p>${data.message || 'No matching application was found.'}</p>`;
      return;
    }

    result.innerHTML = `
      <div class="detail-card__header">
        <div>
          <h3>${data.full_name}</h3>
          <p class="meta">${data.program} • ${data.campus}</p>
        </div>
        <span class="status status--open">${data.status}</span>
      </div>
      <dl class="definition-list">
        <div><dt>Roll Number</dt><dd>${data.roll_number || 'Pending'}</dd></div>
        <div><dt>Test Date</dt><dd>${data.test_date || 'To be scheduled'}</dd></div>
        <div><dt>Reporting Time</dt><dd>${data.reporting_time || 'TBA'}</dd></div>
        <div><dt>Venue</dt><dd>${data.test_venue || 'TBA'}</dd></div>
      </dl>
      <p><a class="button button--secondary" href="${data.verification_url}">View Verification Page</a></p>
    `;
  } catch (error) {
    result.innerHTML = '<p>Unable to reach the tracking service.</p>';
  }
}

function setupMenu() {
  const menuToggle = document.querySelector('[data-menu-toggle]');
  const siteNav = document.querySelector('[data-site-nav]');
  if (!menuToggle || !siteNav) return;
  menuToggle.addEventListener('click', () => {
    siteNav.classList.toggle('is-open');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupMenu();
  loadSiteData();
  const form = document.getElementById('track-form');
  if (form) {
    form.addEventListener('submit', trackApplication);
  }
});
