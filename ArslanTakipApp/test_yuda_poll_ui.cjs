// Run with: node ArslanTakipApp/test_yuda_poll_ui.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, 'templates/ArslanTakipApp/yudaPollScript.html'), 'utf8');

function setup(groups) {
  const cards = {};
  const requests = [];
  function element(extra = {}) {
    return {addEventListener(type, fn) {this[type] = fn;}, ...extra};
  }
  groups.forEach(group => {
    const radios = [element({value: 'onay'}), element({value: 'ret'})];
    const parts = {
      '[data-vote-submit]': element(),
      '[data-vote-status]': element(),
      '[data-vote-feedback]': element(),
    };
    cards[group.id] = {
      radios, button: parts['[data-vote-submit]'],
      status: parts['[data-vote-status]'], feedback: parts['[data-vote-feedback]'],
      querySelectorAll: () => radios,
      querySelector: selector => selector.includes(':checked') ? radios.find(radio => radio.checked) : parts[selector],
    };
  });
  const context = {
    document: {
      getElementById: () => ({textContent: JSON.stringify(groups)}),
      querySelector: selector => cards[selector.match(/"(\d+)"/)[1]],
    },
    $: {ajax(options) {requests.push(options);}}, data: [{id: 42}],
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  return {cards, requests};
}

function choose(card, choice) {
  card.radios.forEach(radio => {radio.checked = radio.value === choice;});
  card.radios.find(radio => radio.checked).change();
}
const {cards, requests} = setup([
  {id: 20, name: 'Boyahane Bolumu', vote: null},
  {id: 30, name: 'Paketleme Bolumu', vote: null},
]);
assert(cards[20].radios.every(radio => !radio.checked));
choose(cards[20], 'onay');
assert.equal(cards[20].button.disabled, false);
assert.equal(cards[30].button.disabled, true);
cards[20].button.click();
cards[20].button.click();
assert.equal(requests.length, 1, 'Prevent duplicate requests for the same card');
assert.equal(requests[0].method, 'POST');
assert.equal(JSON.parse(requests[0].data.params).group_id, 20);

// Another department can submit while the first one is pending.
choose(cards[30], 'ret');
cards[30].button.click();
assert.equal(JSON.parse(requests[1].data.params).group_id, 30);
requests[1].success({group_id: 30, vote: false});
requests[1].complete();
requests[0].success({group_id: 20, vote: true});
requests[0].complete();
assert.match(cards[20].status.textContent, /ONAY/);
assert.match(cards[30].status.textContent, /RET/);
assert.match(cards[20].feedback.textContent, /Boyahane Bolumu/);
assert.match(cards[30].feedback.textContent, /Paketleme Bolumu/);

choose(cards[30], 'onay');
cards[30].button.click();
requests[2].error({responseJSON: {error: 'Test kayıt hatası'}});
requests[2].complete();
assert.equal(cards[30].feedback.textContent, 'Test kayıt hatası');
assert.equal(cards[30].radios[1].checked, true, 'Failed requests preserve the saved decision');
assert.equal(cards[20].radios[0].checked, true);

// Reloading restores the separate saved decisions; no groups is also valid.
const reload = setup([{id: 20, vote: true}, {id: 30, vote: false}]);
assert.equal(reload.cards[20].radios[0].checked, true);
assert.equal(reload.cards[30].radios[1].checked, true);
assert.equal(Object.keys(setup([]).cards).length, 0);
console.log('PASS: independent cards, concurrent submissions, saved decisions and error handling');
