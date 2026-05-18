export async function initProperty() {
  const container = document.getElementById('panel-property');

  // Load contact data
  let contacts = [];
  try {
    const res = await fetch('contacts.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    contacts = (await res.json()).contacts ?? [];
  } catch {
    // Contacts tab will show the empty state
  }

  container.innerHTML = `
    <div class="tabs">
      <button class="tab active" data-tab="overview">Overview</button>
      <button class="tab"        data-tab="contacts">Contacts</button>
      <button class="tab"        data-tab="documents">Documents</button>
    </div>
    <div class="tab-content"        id="tab-overview">${renderOverview()}</div>
    <div class="tab-content hidden" id="tab-contacts">${renderContacts(contacts)}</div>
    <div class="tab-content hidden" id="tab-documents">${renderDocuments()}</div>
  `;

  // Tab switching
  container.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.remove('hidden');
    });
  });

  // Contacts filter
  const filterInput = container.querySelector('.contacts-filter');
  const contactsList = container.querySelector('.contacts-list');
  if (filterInput) {
    filterInput.addEventListener('input', () => {
      contactsList.innerHTML = buildContactRows(
        contacts,
        filterInput.value.trim()
      );
    });
  }
}

function renderOverview() {
  const fields = [
    ['Address',    '11 Young Street, Scotts Landing, Mahurangi East'],
    ['Builder',    'David Reid Homes (DRH)'],
    ['Build year', '—'],
    ['Section',    '—'],
    ['Floor area', '—'],
    ['Rates ref',  '—'],
  ];
  return fields.map(([label, value]) => `
    <div class="overview-row">
      <span class="overview-label">${label}</span>
      <span class="overview-value">${value}</span>
    </div>
  `).join('');
}

function renderContacts(contacts) {
  return `
    <input class="contacts-filter" type="text" placeholder="Search contacts…" />
    <div class="contacts-list">
      ${buildContactRows(contacts, '')}
    </div>
  `;
}

function buildContactRows(contacts, query) {
  const q = query.toLowerCase();
  const filtered = q
    ? contacts.filter(c =>
        c.trade.toLowerCase().includes(q) ||
        c.company.toLowerCase().includes(q) ||
        (c.contact && c.contact.toLowerCase().includes(q))
      )
    : contacts;

  if (filtered.length === 0) {
    return '<div class="contacts-empty">No matches found.</div>';
  }

  return filtered.map(c => {
    const phone = c.phone
      ? `<a href="tel:${c.phone.replace(/\s/g, '')}">${c.phone}</a>`
      : '';

    // If the email field is a URL, skip it (per spec) — just show nothing
    const email = c.email && !c.email.startsWith('http')
      ? `<a href="mailto:${c.email}">${c.email}</a>`
      : '';

    return `
      <div class="contact-row">
        <div class="contact-trade">${c.trade}</div>
        ${c.company  ? `<div class="contact-company">${c.company}</div>` : ''}
        ${c.contact  ? `<div class="contact-person">${c.contact}</div>` : ''}
        <div class="contact-links">${phone}${email}</div>
      </div>
    `;
  }).join('');
}

function renderDocuments() {
  return `
    <p class="docs-note">
      This tab is reserved for future use — warranty documents,
      council links, and other property records.
    </p>
  `;
}
