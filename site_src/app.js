(() => {
  const $ = (s) => document.querySelector(s);
  const PAGE = 48;
  const CATS = ["Tech", "Shoes", "Fashion", "Home & Kitchen", "Beauty", "Outdoors", "Travel", "Marketplace"];
  const state = { cat: "all", q: "", store: "", max: "", sort: "mix", shown: PAGE, saved: false };
  let deals = [];
  let saved = new Set();
  try { const ids = JSON.parse(localStorage.getItem("hoh-saved") || "[]"); if (Array.isArray(ids)) saved = new Set(ids.filter(x => typeof x === "string")); } catch {}
  const safeUrl = (value) => { try { const u = new URL(value); return u.protocol === "https:" ? u.href : ""; } catch { return ""; } };


  const aud = (n) => "$" + n.toLocaleString("en-AU", { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 });
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ago = (iso) => {
    const m = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
    return m < 1 ? "just now" : m < 60 ? m + " min ago" : Math.round(m / 60) + " h ago";
  };

  // restore filters from the URL so links are shareable (?cat=Shoes&q=nike)
  const params = new URLSearchParams(location.search);
  for (const k of ["cat", "q", "store", "max", "sort"]) if (params.get(k)) state[k] = params.get(k);

  function syncUrl() {
    const p = new URLSearchParams();
    for (const k of ["cat", "q", "store", "max", "sort"]) {
      const v = state[k];
      if (v && !(k === "cat" && v === "all") && !(k === "sort" && v === "mix")) p.set(k, v);
    }
    history.replaceState(null, "", p.toString() ? "?" + p : location.pathname);
  }

  function filtered() {
    const q = state.q.trim().toLowerCase();
    let list = deals.filter((d) =>
      (!state.saved || saved.has(d.id)) &&
      (state.cat === "all" || (state.cat === "errors" ? d.error : d.cat === state.cat)) &&
      (!state.store || d.store === state.store) &&
      (!state.max || d.price <= +state.max) &&
      (!q || (d.title + " " + d.brand + " " + d.store + " " + d.type).toLowerCase().includes(q)));
    const by = {
      pct: (a, b) => b.pct - a.pct || a.price - b.price,
      save: (a, b) => (b.was - b.price) - (a.was - a.price),
      new: (a, b) => b.first_seen - a.first_seen,
      low: (a, b) => a.price - b.price,
    }[state.sort];
    if (state.sort !== "mix") return list.sort(by);
    // Top picks: best deal from each store in turn, so no single store floods the page
    const groups = new Map();
    for (const d of list.sort(by || ((a, b) => b.pct - a.pct))) {
      if (!groups.has(d.store)) groups.set(d.store, []);
      groups.get(d.store).push(d);
    }
    const lanes = [...groups.values()].sort((a, b) => b[0].pct - a[0].pct);
    const out = list.filter((d) => d.error);
    const seen = new Set(out.map((d) => d.id));
    for (let i = 0; out.length < list.length; i++)
      for (const lane of lanes) if (lane[i] && !seen.has(lane[i].id)) { out.push(lane[i]); seen.add(lane[i].id); }
    return out;
  }

  function card(d) {
    const fresh = Date.now() / 1000 - d.first_seen < 6 * 3600;
    return `<article class="card${d.error ? " error" : ""}"><a class="deal-link" href="${esc(safeUrl(d.url))}" target="_blank" rel="noopener noreferrer${d.affiliate ? " sponsored" : ""}">
      <div class="ph">${safeUrl(d.img) ? `<img src="${esc(safeUrl(d.img))}" alt="" loading="lazy" decoding="async">` : ""}
        <span class="pct">-${d.pct}%</span>${fresh ? '<span class="new">NEW</span>' : ""}
        ${d.error ? '<span class="flag">Possible error</span>' : ""}</div>
      <div class="info">
        <div class="meta">${esc(d.brand && d.brand !== d.store ? d.brand + " · " : "")}${esc(d.store)}</div>
        <div class="title">${esc(d.title)}${d.variant ? ` <span class="meta">(${esc(d.variant)})</span>` : ""}</div>
        <div class="prices"><span class="now">${aud(d.price)}</span><span class="was">${aud(d.was)}</span>
        <span class="save">Save ${aud(Math.round(d.was - d.price))}</span></div>
        <p class="small">Retailer’s “was” price · delivery extra unless stated</p>
        ${d.checked_at ? `<span class="meta">Checked ${ago(d.checked_at * 1000)}</span>` : ""}
      </div></a><div class="card-actions"><button class="ghost" data-save="${esc(d.id)}" aria-pressed="${saved.has(d.id)}">${saved.has(d.id) ? "♥ Saved" : "♡ Save"}</button><button class="ghost" data-share="${esc(d.id)}">Share</button></div></article>`;
  }

  function render() {
    const list = filtered();
    $("#grid").innerHTML = list.length
      ? list.slice(0, state.shown).map(card).join("")
      : '<div class="empty">No deals match those filters right now. Try clearing filters or browsing the store directory.</div>';
    $("#more").hidden = list.length <= state.shown;
    $("#result").textContent = `${list.length.toLocaleString()} deal${list.length === 1 ? "" : "s"}` +
      (state.cat !== "all" ? ` in ${state.cat === "errors" ? "possible pricing errors" : state.cat}` : "") +
      (state.q ? ` matching “${state.q}”` : "");
    document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", c.dataset.cat === state.cat));
    $("#saved-toggle").textContent = `Saved (${saved.size})`;
    $("#saved-toggle").setAttribute("aria-pressed", state.saved);
    syncUrl();
  }

  function chips() {
    const count = (c) => deals.filter((d) => d.cat === c).length;
    const errs = deals.filter((d) => d.error).length;
    const items = [["all", "All", deals.length]];
    if (errs) items.push(["errors", "Possible errors", errs]);
    for (const c of CATS) if (count(c)) items.push([c, c, count(c)]);
    $("#cats").innerHTML = items.map(([v, l, n]) =>
      `<button class="chip${v === "errors" ? " err" : ""}" data-cat="${esc(v)}">${esc(l)}<small>${n}</small></button>`).join("");
    $("#cats").onclick = (e) => {
      const b = e.target.closest(".chip"); if (!b) return;
      state.cat = b.dataset.cat; state.shown = PAGE; render();
    };
  }

  function bind() {
    $("#saved-toggle").onclick = () => { state.saved = !state.saved; state.shown = PAGE; render(); };
    $("#clear").onclick = () => { Object.assign(state, {cat:"all", q:"", store:"", max:"", sort:"mix", saved:false, shown:PAGE}); for (const k of ["q","store","max","sort"]) $("#"+k).value=state[k]; render(); };
    $("#grid").onclick = async (e) => {
      const save = e.target.closest("[data-save]");
      if (save) { const id = save.dataset.save; saved.has(id) ? saved.delete(id) : saved.add(id); try { localStorage.setItem("hoh-saved", JSON.stringify([...saved])); } catch { $("#notice").textContent = "Saved for this visit only: browser storage is unavailable."; } render(); }
      const share = e.target.closest("[data-share]");
      if (share) {
        const d = deals.find(d => d.id === share.dataset.share);
        const url = new URL(location.pathname, location.origin); url.searchParams.set("q", d.title); url.searchParams.set("store", d.store);
        try { if (navigator.share) await navigator.share({title:d.title, url:url.href}); else { await navigator.clipboard.writeText(url.href); share.textContent="Copied!"; } } catch (e) { if (e.name !== "AbortError") $("#notice").textContent = "To share, copy this link: " + url.href; }
      }
    };

    const q = $("#q"); q.value = state.q;
    let t; q.oninput = () => { clearTimeout(t); t = setTimeout(() => { state.q = q.value; state.shown = PAGE; render(); }, 150); };
    for (const k of ["store", "max", "sort"]) {
      const el = $("#" + k); el.value = state[k];
      el.onchange = () => { state[k] = el.value; state.shown = PAGE; render(); };
    }
    $("#more").onclick = () => { state.shown += PAGE; render(); };
    document.querySelectorAll("[data-copy]").forEach((b) => b.onclick = async () => {
      try { await navigator.clipboard.writeText(b.dataset.copy); b.textContent = "Copied"; } catch { b.textContent = b.dataset.copy; }
    });
    const tg = $("#tg-way"); if (tg && !tg.dataset.tg) tg.hidden = true;
  }

  async function load() {
    $("#grid").innerHTML = Array(8).fill('<div class="skeleton"></div>').join("");
    try {
      const r = await fetch("data/deals.json", { cache: "no-store" });
      if (!r.ok) throw new Error("Unavailable feed");
      const data = await r.json();
      if (!Array.isArray(data.deals)) throw new Error("Invalid feed");
      deals = data.deals.filter(d => safeUrl(d.url) && Number.isFinite(d.price) && Number.isFinite(d.was));
      const age = Date.now() - new Date(data.updated).getTime();
      $("#notice").textContent = age > 2 * 3600000 ? "Updates are delayed. These prices were last checked " + ago(data.updated) + "; verify at checkout." : "Prices in AUD. Discounts use the retailer’s comparison price, not a verified historical low.";
      const sources = data.sources || [];
      $("#source-status").textContent = sources.length ? `${sources.filter(s => s.status === "ok").length} of ${sources.length} feeds completed the last scan. Unavailable feeds are not listed as current deals.` : "Feed-level status will appear after the next scan.";

      $("#s-count").textContent = data.count.toLocaleString();
      $("#s-stores").textContent = data.stores.length;
      $("#s-best").textContent = deals.length ? "-" + Math.max(...deals.map((d) => d.pct)) + "%" : "–";
      $("#s-updated").textContent = ago(data.updated);
      $("#store").innerHTML = '<option value="">All stores</option>' +
        [...new Set(deals.map((d) => d.store))].sort().map((s) => `<option>${esc(s)}</option>`).join("");
      chips(); bind(); render();
    } catch (e) {
      $("#grid").innerHTML = '<div class="empty">The deal feed is unavailable. <button id="retry">Try again</button> or <a href="stores.html">browse stores directly</a>.</div>';
      $("#retry").onclick = load;
    }
  }
  load();

})();
