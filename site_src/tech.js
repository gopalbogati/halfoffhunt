(() => {
  const buttons = [...document.querySelectorAll('[data-tech]')];
  const cards = [...document.querySelectorAll('[data-categories]')];
  const search = document.querySelector('#tech-search');
  let category = 'All';
  function render() {
    const query = search.value.trim().toLowerCase();
    let count = 0;
    for (const card of cards) {
      const match = (category === 'All' || card.dataset.categories.split('|').includes(category)) && (!query || card.textContent.toLowerCase().includes(query));
      card.hidden = !match; if(match) count++;
    }
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.tech === category)));
    document.querySelector('#tech-result').textContent = `${count} retailer${count === 1 ? '' : 's'}`;
    document.querySelector('#tech-empty').hidden = count > 0;
  }
  buttons.forEach(button => button.onclick = () => {category = button.dataset.tech; render();});
  search.oninput = render; render();
})();
