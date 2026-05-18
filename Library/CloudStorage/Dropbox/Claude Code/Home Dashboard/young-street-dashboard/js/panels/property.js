export async function initProperty() {
  const container = document.getElementById('panel-property');

  const [contactsResult, propertyResult] = await Promise.allSettled([
    fetch('contacts.json').then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
    fetch('property.json').then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
  ]);

  const contacts = contactsResult.status === 'fulfilled'
    ? (contactsResult.value.contacts ?? [])
    : [];

  const property = propertyResult.status === 'fulfilled'
    ? propertyResult.value
    : null;

  container.innerHTML = `
    <div class="tabs">
      <button class="tab active" data-tab="overview">Overview</button>
      <button class="tab"        data-tab="contacts">Contacts</button>
      <button class="tab"        data-tab="documents">Documents</button>
    </div>
    <div class="tab-content"        id="tab-overview">${renderOverview(property)}</div>
    <div class="tab-content hidden" id="tab-contacts">${renderContacts(contacts)}</div>
    <div class="tab-content hidden" id="tab-documents">${renderDocuments(property)}</div>
  `;

  container.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.remove('hidden');
    });
  });

  const filterInput = container.querySelector('.contacts-filter');
  const contactsList = container.querySelector('.contacts-list');
  if (filterInput) {
    filterInput.addEventListener('input', () => {
      contactsList.innerHTML = buildContactRows(contacts, filterInput.value.trim());
    });
  }
}

function renderOverview(property) {
  if (!property) {
    return '<div class="contacts-empty">Property data unavailable.</div>';
  }

  const row = (label, value) => `
    <div class="overview-row">
      <span class="overview-label">${label}</span>
      <span class="overview-value">${value ?? '—'}</span>
    </div>
  `;

  const section = label => `<div class="overview-section">${label}</div>`;

  const utilityRows = (property.utilities ?? []).map(u => row(u.type, u.provider)).join('');

  return [
    row('Address',    property.address),
    row('Legal',      property.legal),
    row('Builder',    property.builder),
    row('Build year', property.buildYear),
    section('Rates'),
    row('Provider',   property.rates?.provider),
    row('Rates ref',  property.rates?.assessmentNumber),
    row('Land value', property.valuations?.landValue),
    row('Cap. value', property.valuations?.capitalValue),
    utilityRows ? section('Utilities') : '',
    utilityRows,
  ].join('');
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

function renderDocuments(property) {
  const folder = property?.documentsFolder;
  return `
    ${folder ? `
      <a class="docs-folder-link" href="${folder}" target="_blank">
        <span class="docs-folder-icon">📁</span>
        <span>Open 11 Young Street folder</span>
      </a>
    ` : ''}
    <p class="docs-note">
      Warranty documents, council links, and other property records.
    </p>
  `;
}
