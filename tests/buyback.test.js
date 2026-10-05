const {test} = require('node:test');
const assert = require('node:assert/strict');
const {rankQuotes} = require('../site_src/buyback.js');
const now = Date.parse('2026-10-05T01:00:00Z');
const row = (provider, amount, extra={}) => ({provider, amount, fees:0, profile:'phone', payout:'cash', currency:'AUD', checked_at:'2026-10-05T00:00:00Z', ...extra});
test('highest cash payout after fees is first; gift cards stay separate', () => {
 const ranked=rankQuotes([row('A',530),row('B',555),row('C',600,{fees:100}),row('Voucher',900,{payout:'gift_card'})],'phone',now);
 assert.deepEqual(ranked.map(r=>r.provider),['B','A','C','Voucher']);
 assert.equal(ranked[0].net,555);
});
test('different devices, expired quotes, future dates and invalid money cannot rank',()=>{
 const ranked=rankQuotes([row('Other',900,{profile:'other'}),row('Old',1000,{checked_at:'2026-10-01T00:00:00Z'}),row('Future',1200,{checked_at:'2030-01-01T00:00:00Z'}),row('Bad',NaN),row('Wrong currency',1000,{currency:'USD'}),row('No amount',null),row('Negative',20,{fees:30}),row('Valid',530)],'phone',now);
 assert.deepEqual(ranked.map(r=>r.provider),['Valid']);
});
test('keep latest quote per provider and payout, not an older higher quote',()=>{
 const ranked=rankQuotes([row('A',800,{checked_at:'2026-10-04T20:00:00Z'}),row('A',530)],'phone',now);
 assert.equal(ranked.length,1);assert.equal(ranked[0].amount,530);
});
