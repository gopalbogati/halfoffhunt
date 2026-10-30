(() => {
  const controls = Object.fromEntries(['query','store','type','kind'].map(k => [k, document.querySelector('#discount-' + k)]));
  const params = new URLSearchParams(location.search);
  for (const [k, el] of Object.entries(controls)) el.value = params.get(k) || '';
  const cards = [...document.querySelectorAll('.discount-store')];
  function render() {
    const q = controls.query.value.trim().toLocaleLowerCase();
    let links = 0, stores = 0;
    for (const card of cards) {
      let count = 0;
      for (const row of card.querySelectorAll('li')) {
        const types = JSON.parse(row.dataset.types);
        const visible = (!controls.store.value || card.dataset.store === controls.store.value) &&
          (!controls.type.value || types.includes(controls.type.value)) &&
          (!controls.kind.value || row.dataset.kind === controls.kind.value) &&
          (!q || `${card.dataset.store} ${row.textContent} ${types.join(' ')}`.toLocaleLowerCase().includes(q));
        row.hidden = !visible;
        if (visible) count++;
      }
      card.hidden = count === 0;
      links += count; if (count) stores++;
    }
    document.querySelector('#discount-count').textContent = `${links} discount link${links === 1 ? '' : 's'} across ${stores} retailer section${stores === 1 ? '' : 's'}`;
    document.querySelector('#discount-empty').hidden = links !== 0;
    const p = new URLSearchParams();
    for (const [k,el] of Object.entries(controls)) if (el.value) p.set(k,el.value);
    history.replaceState(null,'',location.pathname+(p.size?'?'+p:'')+location.hash);
  }
  for (const [k,el] of Object.entries(controls)) el.addEventListener(k === 'query' ? 'input' : 'change', render);
  const form = document.querySelector('#discount-filters');
  form.onsubmit = e => e.preventDefault();
  form.onreset = e => { e.preventDefault(); for (const el of Object.values(controls)) el.value = ''; render(); };
  render();
})();
