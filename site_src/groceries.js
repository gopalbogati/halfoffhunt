(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safe = s => { try { const u = new URL(s); return u.protocol === 'https:' ? u.href : ''; } catch { return ''; } };
  const labels = {'pickup':'Pickup / Click & Collect','delivery':'Delivery','in-store':'In-store'};
  let sources = [];
  const q = $('#grocery-query'), mode = $('#grocery-mode'), category = $('#grocery-category');
  const params = new URLSearchParams(location.search);
  q.value = params.get('q') || ''; mode.value = params.get('mode') || ''; category.value = params.get('category') || '';
  function render() {
    const query = q.value.trim().toLowerCase();
    const list = sources.filter(s => (!mode.value || s.modes.includes(mode.value)) && (!category.value || category.value === s.category) && (!query || `${s.name} ${s.title} ${s.description}`.toLowerCase().includes(query)));
    $('#grocery-count').textContent = `${list.length} offer page${list.length === 1 ? '' : 's'} · prices and stock confirmed at the retailer`;
    $('#grocery-grid').innerHTML = list.length ? list.map(s => `<article class="grocery-card"><div class="retailer-heading"><span class="retailer-initial" style="--retailer:${/^#[0-9a-f]{6}$/i.test(s.colour) ? s.colour : '#333'}" aria-hidden="true">${esc(s.initials)}</span><div><p class="eyebrow">${esc(s.category)}</p><h3>${esc(s.name)}</h3></div></div><h4>${esc(s.title)}</h4><p>${esc(s.description)}</p><div class="mode-tags">${s.modes.map(m => `<span>${esc(labels[m] || m)}</span>`).join('')}</div><p class="small">${esc(s.note)}</p><div class="retailer-actions"><a class="btn" href="${esc(safe(s.url))}" target="_blank" rel="noopener noreferrer">View official offers ↗</a>${s.catalogue ? `<a href="${esc(safe(s.catalogue))}" target="_blank" rel="noopener noreferrer">Catalogue ↗</a>` : ''}</div></article>`).join('') : '<div class="empty">No offer pages match. Clear the filters to see all retailers.</div>';
    const p = new URLSearchParams();
    if (q.value) p.set('q', q.value); if (mode.value) p.set('mode', mode.value); if (category.value) p.set('category', category.value);
    history.replaceState(null, '', location.pathname + (p.size ? '?' + p : '') + location.hash);
  }
  $('#grocery-filters').onsubmit = e => e.preventDefault();
  $('#grocery-filters').onreset = () => { q.value = ''; mode.value = ''; category.value = ''; render(); };
  for (const el of [q, mode, category]) el.addEventListener(el === q ? 'input' : 'change', render);
  fetch('data/groceries.json', {cache:'no-store'}).then(r => { if (!r.ok) throw Error(); return r.json(); }).then(data => {
    sources = data.sources;
    category.innerHTML = '<option value="">All categories</option>' + [...new Set(sources.map(s => s.category))].sort().map(c => `<option>${esc(c)}</option>`).join('');
    category.value = params.get('category') || ''; render();
    const now = Date.now();
    const catalogues = data.catalogues.filter(c => Date.parse(c.starts_at) <= now && now < Date.parse(c.ends_at) && safe(c.url));
    $('#catalogue-list').innerHTML = catalogues.length ? catalogues.map(c => `<article class="catalogue-card"><div class="mode-tags"><span>MEMBERSHIP REQUIRED</span><span>IN-WAREHOUSE</span></div><h3>${esc(c.title)}</h3><p class="catalogue-dates">${esc(c.date_label)}</p><p>Browse the official catalogue for products, savings and exclusions. Warehouse stock varies.</p><a class="btn" href="${esc(safe(c.url))}" target="_blank" rel="noopener noreferrer">Open catalogue ↗</a><p class="small">Link checked ${esc(new Date(c.checked_at).toLocaleDateString('en-AU', {timeZone:'Australia/Sydney'}))}${c.stale ? ' · refresh unavailable' : ''}</p></article>`).join('') : '<p>No current dated catalogue is available here. <a href="https://www.costco.com.au/warehouse-savings" target="_blank" rel="noopener noreferrer">Check Costco warehouse savings ↗</a></p>';
    $('#catalogue-status').textContent = 'Warehouse shopping is not click-and-collect. ' + (data.catalogue_status === 'ok' ? 'Catalogue links refresh when the site builds; expired catalogues are hidden automatically.' : 'Catalogue refresh could not confirm new links. Any retained catalogue keeps its original check date.');
  }).catch(() => {
    $('#grocery-grid').innerHTML = '<p class="notice">The directory could not load. <a href="https://www.woolworths.com.au/shop/browse/specials/half-price">Woolworths specials</a> · <a href="https://www.coles.com.au/on-special">Coles specials</a> · <a href="https://www.aldi.com.au/special-buys">ALDI Special Buys</a>. Reload to try again.</p>';
    $('#catalogue-list').innerHTML = '<p><a href="https://www.costco.com.au/warehouse-savings">Open Costco warehouse savings ↗</a></p>';
  });
})();
