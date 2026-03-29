/**
 * Donation page renderer.
 * Reads config.json and builds the page dynamically.
 * To add a new payment method: just edit config.json and set enabled: true.
 */

(function () {
  'use strict';

  var CONFIG_PATH = 'config.json';

  function init() {
    fetch(CONFIG_PATH)
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function (e) {
        console.error('Failed to load donation config:', e);
        document.getElementById('donate-buttons').innerHTML =
          '<p style="color:#c00">Failed to load config. Check donations/config.json.</p>';
      });
  }

  function render(config) {
    renderButtons(config.accounts);
    renderCosts(config.costs, config.monthly_burn);
    renderPromises(config.promises);

    if (config.tagline) {
      var el = document.getElementById('donate-tagline');
      if (el) el.textContent = config.tagline;
    }
  }

  // ═══ BUTTONS ═══

  function renderButtons(accounts) {
    var container = document.getElementById('donate-buttons');
    if (!container) return;

    var html = '';
    var keys = Object.keys(accounts);

    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
      var acct = accounts[key];

      // Skip crypto with no address
      if (key.startsWith('crypto_') && !acct.address) continue;
      // Skip non-crypto with no username and not enabled
      if (!key.startsWith('crypto_') && !acct.enabled) {
        // Show disabled placeholder
        html += '<span class="donate-btn disabled" style="' +
          'background:' + acct.color + ';' +
          'color:' + acct.text_color + ';' +
          'border-color:' + acct.color + '">' +
          acct.label +
          '</span>';
        continue;
      }

      var url = acct.url || '';
      if (key.startsWith('crypto_') && acct.address) {
        // Crypto: copy address on click
        html += '<a class="donate-btn" href="#" data-crypto="' + escapeAttr(acct.address) + '" ' +
          'onclick="copyAddress(this);return false" style="' +
          'background:' + acct.color + ';' +
          'color:' + acct.text_color + ';' +
          'border-color:' + acct.color + '">' +
          acct.label + ': ' + truncateAddr(acct.address) +
          '</a>';
      } else {
        html += '<a class="donate-btn" href="' + escapeAttr(url) + '" ' +
          'target="_blank" rel="noopener" style="' +
          'background:' + acct.color + ';' +
          'color:' + acct.text_color + ';' +
          'border-color:' + acct.color + '">' +
          acct.label +
          (acct.username ? ' (' + escapeHtml(acct.username) + ')' : '') +
          '</a>';
      }
    }

    container.innerHTML = html;
  }

  // ═══ COSTS ═══

  function renderCosts(costs, monthlyBurn) {
    var container = document.getElementById('donate-costs');
    if (!container || !costs) return;

    var html = '';
    for (var i = 0; i < costs.length; i++) {
      html += '<div class="cost-item">' +
        '<span class="cost-label">' + escapeHtml(costs[i].label) + '</span>' +
        '<span class="cost-amount">' + escapeHtml(costs[i].amount) + '</span>' +
        '</div>';
    }

    if (monthlyBurn) {
      html += '<div class="cost-total">' +
        '<span>Total monthly burn</span>' +
        '<span>' + escapeHtml(monthlyBurn) + '</span>' +
        '</div>';
    }

    container.innerHTML = html;
  }

  // ═══ PROMISES ═══

  function renderPromises(promises) {
    var container = document.getElementById('donate-promises');
    if (!container || !promises) return;

    var html = '';
    for (var i = 0; i < promises.length; i++) {
      // Bold the first sentence (up to first period)
      var text = promises[i];
      var dot = text.indexOf('.');
      if (dot > 0) {
        html += '<div class="promise"><strong>' +
          escapeHtml(text.substring(0, dot + 1)) + '</strong> ' +
          escapeHtml(text.substring(dot + 1).trim()) + '</div>';
      } else {
        html += '<div class="promise">' + escapeHtml(text) + '</div>';
      }
    }

    container.innerHTML = html;
  }

  // ═══ CRYPTO COPY ═══

  window.copyAddress = function (el) {
    var addr = el.getAttribute('data-crypto');
    if (!addr) return;

    if (navigator.clipboard) {
      navigator.clipboard.writeText(addr);
    } else {
      var ta = document.createElement('textarea');
      ta.value = addr;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }

    var orig = el.textContent;
    el.textContent = 'Copied!';
    setTimeout(function () { el.textContent = orig; }, 1500);
  };

  // ═══ UTIL ═══

  function escapeHtml(s) {
    if (!s) return '';
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function escapeAttr(s) {
    return escapeHtml(s);
  }

  function truncateAddr(addr) {
    if (addr.length <= 16) return addr;
    return addr.substring(0, 8) + '...' + addr.substring(addr.length - 6);
  }

  // ═══ GO ═══
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
