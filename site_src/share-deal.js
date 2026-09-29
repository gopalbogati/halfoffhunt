// Share buttons on pre-rendered deal cards (home "standouts" strip, category and store pages).
// The shared link opens Half Off Hunt filtered to that deal, not the retailer, so visits come back here.
(() => {
  document.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-share-url]");
    if (!b) return;
    const url = b.dataset.shareUrl, text = b.dataset.shareText || "";
    const label = b.textContent;
    try {
      if (navigator.share) {
        await navigator.share({ title: text, text, url });
      } else {
        await navigator.clipboard.writeText(text ? `${text} ${url}` : url);
        b.textContent = "Link copied";
        setTimeout(() => (b.textContent = label), 2000);
      }
    } catch (err) {
      if (err && err.name === "AbortError") return;   // user closed the share sheet
      window.prompt("Copy this link to share:", url);
    }
  });
})();
