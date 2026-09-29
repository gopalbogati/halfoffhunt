(() => {
  const copy = document.querySelector('#launch-copy');
  document.querySelector('#copy-post').onclick = async () => {
    try { await navigator.clipboard.writeText(copy.value); document.querySelector('#share-status').textContent = 'Draft copied. Review it in LinkedIn before posting.'; }
    catch { copy.focus(); copy.select(); document.querySelector('#share-status').textContent = 'Select and copy the draft manually.'; }
  };
})();
