/* Rank comparable, dated AUD quotes; never treat headline maximums as quotes. */
const BuybackComparison = (() => {
  const MAX_AGE = 48 * 3600000;
  const kinds = {cash: 0, gift_card: 1, purchase_credit: 2};
  function rankQuotes(quotes, profile, now = Date.now()) {
    const latest = new Map();
    for (const q of quotes) {
      const age = now - Date.parse(q.checked_at);
      if (q.profile !== profile || q.currency !== 'AUD' || !Object.prototype.hasOwnProperty.call(kinds,q.payout) || !q.provider ||
          !Number.isFinite(q.amount) || !Number.isFinite(q.fees) || q.amount < 0 || q.fees < 0 || q.fees > q.amount ||
          !Number.isFinite(age) || age < 0 || age > MAX_AGE) continue;
      const key = q.provider.trim().toLowerCase() + ':' + q.payout;
      if (!latest.has(key) || Date.parse(q.checked_at) >= Date.parse(latest.get(key).checked_at)) latest.set(key, {...q, net: Math.round((q.amount - q.fees) * 100) / 100});
    }
    return [...latest.values()].sort((a,b) => kinds[a.payout] - kinds[b.payout] || b.net - a.net || a.provider.localeCompare(b.provider));
  }
  return {rankQuotes};
})();
if (typeof module !== 'undefined') module.exports = BuybackComparison;
if (typeof document !== 'undefined') (async () => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = n => new Intl.NumberFormat('en-AU',{style:'currency',currency:'AUD'}).format(n);
  const safeUrl = s => {try {const u=new URL(s);return u.protocol==='https:' && !u.username && !u.password ? u.href : '';} catch {return '';}};
  const labels={cash:'Cash / bank transfer',gift_card:'Gift card',purchase_credit:'Purchase credit'};
  let personal={profiles:[],quotes:[]}, data;
  try {
    const saved=JSON.parse(localStorage.getItem('hoh-buyback') || '{}');
    if(Array.isArray(saved.profiles)&&Array.isArray(saved.quotes)) personal=saved;
  } catch {}
  const persist=()=>{try{localStorage.setItem('hoh-buyback',JSON.stringify(personal));$('#quote-message').textContent='Saved in this browser only.';}catch{$('#quote-message').textContent='Saved for this visit only; browser storage is unavailable.';}};
  const profiles=()=>[...data.profiles,...personal.profiles];
  function options(selected) {
    $('#quote-profile').innerHTML=profiles().map(p=>`<option value="${esc(p.id)}">${esc(p.label)}</option>`).join('');
    if(selected) $('#quote-profile').value=selected;
  }
  function render() {
    const profile=profiles().find(p=>p.id===$('#quote-profile').value);
    if(!profile)return;
    $('#quote-condition').textContent=profile.condition;
    const ranked=BuybackComparison.rankQuotes([...data.quotes,...personal.quotes],profile.id);
    const cash=ranked.filter(q=>q.payout==='cash');
    $('#quote-summary').textContent=cash.length>1 ? `${cash.length} comparable cash quotes · highest payout first after known fees. This compares the quotes below, not every buyer in Australia.` : cash.length===1 ? 'Only one comparable cash quote is available. More quotes are needed to compare buyers.' : 'No current cash quotes for this device and condition. Get matching quotes below and add them to compare.';
    $('#quote-ranking').innerHTML=ranked.map(q=>`<article class="store-tile quote-card${q.payout==='cash'&&cash.length>1&&q.net===cash[0].net?' best-quote':''}">
      <p class="eyebrow">${q.payout==='cash'&&cash.length>1&&q.net===cash[0].net?'Highest entered / checked cash payout':esc(labels[q.payout])}</p>
      <h3>${esc(q.provider)}</h3><p class="quote-value">${money(q.net)}</p><p>${esc(labels[q.payout])} · after ${money(q.fees)} known fees</p>
      <p class="small">${q.personal?'Your entered quote':'Manually checked on the buyer’s site'} · ${esc(new Date(q.checked_at).toLocaleString('en-AU'))}</p>
      <p>${esc(q.note||'Subject to device assessment and the buyer’s terms.')}</p>
      ${safeUrl(q.url)?`<a href="${esc(safeUrl(q.url))}" target="_blank" rel="noopener noreferrer">Recheck offer ↗</a>`:''}
      ${q.personal?`<button class="ghost" type="button" data-remove-quote="${esc(q.id)}">Remove your quote</button>`:''}</article>`).join('');
    $('#quote-ranking').hidden=!ranked.length;
    const quoted=new Set(ranked.map(q=>q.provider.toLowerCase()));
    $('#quote-missing').textContent='No comparable current quote collected: '+data.providers.filter(p=>!quoted.has(p.name.toLowerCase())).map(p=>p.name).join(', ')+'. Use the official links below. Gift cards and purchase credit rank separately from cash.';
  }
  try {
    const response=await fetch('data/buyback.json',{cache:'no-store'});
    if(!response.ok)throw new Error('No quote data');
    data=await response.json();
    options();render();
    setInterval(render,60000);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)render();});
    window.addEventListener('focus',render);
    $('#quote-profile').onchange=()=>{render();$('#add-quote-form').reset();};
    $('#new-profile-form').onsubmit=e=>{
      e.preventDefault();const label=$('#new-device').value.trim(),condition=$('#new-condition').value.trim();
      if(!label||!condition)return;
      const id='local-'+Date.now();personal.profiles.push({id,label,condition});persist();options(id);render();e.target.reset();$('#add-quote-form').reset();
    };
    $('#add-quote-form').onsubmit=e=>{
      e.preventDefault();
      const provider=$('#quote-provider').value.trim(),amount=Number($('#quote-amount').value),fees=Number($('#quote-fees').value);
      if(!provider||!Number.isFinite(amount)||!Number.isFinite(fees)||fees<0||amount<fees){$('#quote-message').textContent='Enter a valid amount and fees no higher than the offer.';return;}
      const official=data.providers.find(p=>p.name.toLowerCase()===provider.toLowerCase());
      personal.quotes.push({id:'quote-'+Date.now(),profile:$('#quote-profile').value,provider,amount,fees,currency:'AUD',payout:$('#quote-payout').value,checked_at:new Date().toISOString(),personal:true,url:official?.url||'',note:'Entered by you for the condition above. Reconfirm before accepting.'});
      persist();render();e.target.reset();
    };
    $('#quote-ranking').onclick=e=>{const button=e.target.closest('[data-remove-quote]');if(!button)return;personal.quotes=personal.quotes.filter(q=>q.id!==button.dataset.removeQuote);persist();render();};
    $('#quote-providers').innerHTML=data.providers.map(p=>`<option value="${esc(p.name)}"></option>`).join('');
    $('#comparison-controls').hidden=false;
  } catch {
    $('#quote-summary').textContent='Quote comparison is unavailable. Use the official services below to obtain current offers.';
  }
})();
