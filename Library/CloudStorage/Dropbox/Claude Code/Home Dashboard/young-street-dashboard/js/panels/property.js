export async function initProperty() {
  const container = document.getElementById('panel-property');

  const [contactsResult, propertyResult] = await Promise.allSettled([
    fetch('contacts.json').then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
    fetch('property.json').then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
  ]);

  const contacts = contactsResult.status === 'fulfilled'
    ? (contactsResult.value.contacts ?? []) : [];
  const property = propertyResult.status === 'fulfilled'
    ? propertyResult.value : null;

  container.innerHTML = `
    <div class="prop-tabs">
      <button class="prop-tab active" data-tab="overview">Overview</button>
      <button class="prop-tab"        data-tab="contacts">Contacts</button>
      <button class="prop-tab"        data-tab="documents">Documents</button>
    </div>
    <div class="prop-body">
      <div id="tab-overview">${renderOverview(property)}</div>
      <div id="tab-contacts"  class="hidden">${renderContacts(contacts)}</div>
      <div id="tab-documents" class="hidden">${renderDocuments(property)}</div>
    </div>
  `;

  container.querySelectorAll('.prop-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.prop-tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.prop-body > div').forEach(c => c.classList.add('hidden'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.remove('hidden');
    });
  });

  const filterInput = container.querySelector('.prop-search');
  const contactsList = container.querySelector('.contact-list');
  if (filterInput) {
    filterInput.addEventListener('input', () => {
      contactsList.innerHTML = buildContactCards(contacts, filterInput.value.trim());
    });
  }
}

function initials(contact) {
  const name = contact.contact || contact.company || contact.trade;
  return name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();
}

function renderOverview(property) {
  if (!property) return '<div class="contacts-empty">Property data unavailable.</div>';

  const row = (k, v) => `
    <div class="prop-row">
      <span class="k">${k}</span>
      <span class="v">${v ?? '—'}</span>
    </div>`;
  const section = label => `<div class="prop-section">${label}</div>`;
  const utilityRows = (property.utilities ?? []).map(u => row(u.type, u.provider)).join('');

  return [
    section('Address'),
    row('Address', property.address),
    row('Legal', property.legal),
    section('Land & Build'),
    row('Builder', property.builder),
    row('Year Built', property.buildYear),
    section('Rates'),
    row('Provider', property.rates?.provider),
    row('Ref', property.rates?.assessmentNumber),
    row('Land Value', property.valuations?.landValue),
    row('Cap. Value', property.valuations?.capitalValue),
    utilityRows ? section('Utilities') : '',
    utilityRows,
  ].join('');
}

function renderContacts(contacts) {
  return `
    <input class="prop-search" type="text" placeholder="Search contacts…">
    <div class="contact-list">${buildContactCards(contacts, '')}</div>
  `;
}

function buildContactCards(contacts, query) {
  const q = query.toLowerCase();
  const filtered = q
    ? contacts.filter(c =>
        c.trade?.toLowerCase().includes(q) ||
        c.company?.toLowerCase().includes(q) ||
        c.contact?.toLowerCase().includes(q))
    : contacts;

  if (filtered.length === 0) return '<div class="contacts-empty">No matches found.</div>';

  return filtered.map(c => {
    const name    = c.contact || c.company || c.trade;
    const role    = [c.trade, c.detail ? c.detail.split(/[,·]/)[0].trim() : ''].filter(Boolean).join(' · ');
    const phoneHref = c.phone ? `tel:${c.phone.replace(/\s/g, '')}` : '';

    return `
      <div class="contact">
        <div class="avatar">${initials(c)}</div>
        <div class="meta">
          <div class="name">${name}</div>
          <div class="role">${role}</div>
        </div>
        ${phoneHref ? `
          <div class="call">
            <a href="${phoneHref}" style="color:inherit;display:flex;align-items:center">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
              </svg>
            </a>
          </div>` : ''}
      </div>
    `;
  }).join('');
}

function renderDocuments(property) {
  const folder = property?.documentsFolder;
  const DOC_SVG = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>`;

  const docs = [
    { name: 'LIM Report',             info: 'Auckland Council' },
    { name: 'Title & Easements',      info: 'LINZ' },
    { name: 'DRH Build Documents',    info: 'David Reid Homes' },
    { name: 'Insurance Summary',      info: 'AMI' },
    ...(property?.floorPlan?.pageCount ? [{ name: 'Floor Plans', info: 'PNG · on device' }] : []),
  ];

  return `
    <div style="display:flex;flex-direction:column;gap:6px">
      ${docs.map(d => `
        <div class="doc">
          <div class="icon">${DOC_SVG}</div>
          <div class="meta">
            <div class="name">${d.name}</div>
            <div class="info">${d.info}</div>
          </div>
        </div>
      `).join('')}
      ${folder ? `
        <a class="doc" href="${folder}" target="_blank" style="text-decoration:none">
          <div class="icon" style="font-size:16px">📁</div>
          <div class="meta">
            <div class="name">Open Dropbox Folder</div>
            <div class="info">All property documents</div>
          </div>
        </a>` : ''}
    </div>
  `;
}
