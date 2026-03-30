/**
 * THE HOLE -- Slop Shield (content script)
 * Injected into every page loaded in the BLOOM browser.
 *
 * Responsibilities:
 *   1. Send page HTML + URL to the Tauri backend for slop analysis
 *   2. Display warning banners for high-slop pages
 *   3. Show subtle badges for moderate-slop pages
 *   4. Dim affiliate links and label them
 *   5. Show source tier badges for known domains
 *
 * All injected UI uses Shadow DOM so it cannot break page styles.
 */

(function () {
  'use strict';

  // === TAURI IPC ===

  var invoke = null;

  try {
    if (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) {
      invoke = window.__TAURI__.core.invoke;
    } else if (window.__TAURI__ && window.__TAURI__.invoke) {
      invoke = window.__TAURI__.invoke;
    }
  } catch (e) {
    // Not in Tauri -- exit silently
    return;
  }

  if (!invoke) return;

  // === KNOWN DOMAINS AND THEIR TIERS ===

  var DOMAIN_TIERS = {
    // T1 -- Primary sources
    'arxiv.org': { tier: 1, label: 'T1 arXiv' },
    'github.com': { tier: 1, label: 'T1 GitHub' },
    'pubmed.ncbi.nlm.nih.gov': { tier: 1, label: 'T1 PubMed' },
    'tools.ietf.org': { tier: 1, label: 'T1 RFC' },
    'datatracker.ietf.org': { tier: 1, label: 'T1 RFC' },
    'rfc-editor.org': { tier: 1, label: 'T1 RFC' },
    'doi.org': { tier: 1, label: 'T1 DOI' },
    'scholar.google.com': { tier: 1, label: 'T1 Scholar' },
    // T2 -- Practitioner sources
    'news.ycombinator.com': { tier: 2, label: 'T2 HN' },
    'stackoverflow.com': { tier: 2, label: 'T2 SO' },
    'lobste.rs': { tier: 2, label: 'T2 Lobsters' },
    'jvns.ca': { tier: 2, label: 'T2 Blog' },
    'danluu.com': { tier: 2, label: 'T2 Blog' },
    'rachelbythebay.com': { tier: 2, label: 'T2 Blog' },
    'fasterthanli.me': { tier: 2, label: 'T2 Blog' },
    'blog.cloudflare.com': { tier: 2, label: 'T2 Blog' },
    'engineering.fb.com': { tier: 2, label: 'T2 Blog' },
    'netflixtechblog.com': { tier: 2, label: 'T2 Blog' },
    'aws.amazon.com/blogs': { tier: 2, label: 'T2 Blog' },
    // T3 -- Journalism
    'arstechnica.com': { tier: 3, label: 'T3 News' },
    'lwn.net': { tier: 3, label: 'T3 LWN' },
    'theregister.com': { tier: 3, label: 'T3 News' },
  };

  // === AFFILIATE LINK PATTERNS ===

  var AFFILIATE_PATTERNS = [
    /[?&]tag=[A-Za-z0-9_-]+-20/i,
    /amzn\.to\//i,
    /amazon\.[a-z.]+\/.*[?&]linkCode=/i,
    /shareasale\.com\/[rmu]\.cfm/i,
    /anrdoezrs\.net\//i,
    /dpbolvw\.net\//i,
    /jdoqocy\.com\//i,
    /tkqlhce\.com\//i,
    /click\.linksynergy\.com\//i,
    /go\.skimresources\.com\//i,
    /go\.redirectingat\.com\//i,
    /awin1\.com\//i,
    /impact\.com\//i,
    /sjv\.io\//i,
    /7eer\.net\//i,
    /geni\.us\//i,
    /howl\.me\//i,
    /rstyle\.me\//i,
    /[?&]affiliate[_-]?id=/i,
    /[?&]aff[_-]?id=/i,
    /[?&]partner[_-]?id=/i,
  ];

  // === SHADOW DOM HOST ===

  function createShadowHost(id) {
    var host = document.createElement('div');
    host.id = id;
    host.style.cssText = 'all:initial;position:fixed;z-index:2147483647;pointer-events:none;';
    document.documentElement.appendChild(host);
    var shadow = host.attachShadow({ mode: 'closed' });
    return { host: host, shadow: shadow };
  }

  // === SLOP ANALYSIS ===

  function analyzePageSlop() {
    var html = document.documentElement.outerHTML;
    var url = window.location.href;

    // Don't analyze internal pages
    if (url.indexOf('hole://') === 0) return;
    if (url.indexOf('tauri://') === 0) return;
    if (url.indexOf('about:') === 0) return;

    // Truncate HTML to avoid sending megabytes over IPC
    var maxLen = 200000;
    if (html.length > maxLen) {
      html = html.substring(0, maxLen);
    }

    invoke('get_slop_report', { html: html, url: url })
      .then(function (report) {
        if (!report) return;
        handleSlopReport(report);
      })
      .catch(function () {
        // Slop analysis unavailable -- fail silently
      });
  }

  function handleSlopReport(report) {
    var score = report.slop_score || 0;

    if (score < -50) {
      showSlopWarning(report);
    } else if (score < -30) {
      showSlopBadge(report);
    }
  }

  // === SLOP WARNING BANNER (score < -50) ===

  function showSlopWarning(report) {
    var container = createShadowHost('hole-slop-warning');
    container.host.style.cssText +=
      'top:0;left:0;right:0;pointer-events:auto;';

    var style = document.createElement('style');
    style.textContent = [
      '.slop-banner{',
      '  font-family:system-ui,-apple-system,sans-serif;',
      '  background:#dc3545;color:#fff;',
      '  padding:8px 16px;font-size:13px;font-weight:600;',
      '  display:flex;align-items:center;justify-content:space-between;',
      '  line-height:1.4;',
      '}',
      '.slop-banner-msg{flex:1}',
      '.slop-banner-score{',
      '  font-size:11px;opacity:0.85;margin-left:12px;white-space:nowrap;',
      '}',
      '.slop-banner-close{',
      '  background:none;border:none;color:#fff;font-size:18px;',
      '  cursor:pointer;padding:0 0 0 12px;line-height:1;opacity:0.8;',
      '}',
      '.slop-banner-close:hover{opacity:1}',
    ].join('\n');

    var banner = document.createElement('div');
    banner.className = 'slop-banner';

    var msg = document.createElement('span');
    msg.className = 'slop-banner-msg';
    msg.textContent = 'Slop shield: this page has indicators of low-quality or generated content.';
    if (report.reasons && report.reasons.length > 0) {
      msg.textContent += ' (' + report.reasons.join(', ') + ')';
    }

    var scoreEl = document.createElement('span');
    scoreEl.className = 'slop-banner-score';
    scoreEl.textContent = 'score: ' + report.slop_score;

    var closeBtn = document.createElement('button');
    closeBtn.className = 'slop-banner-close';
    closeBtn.textContent = '\u00D7';
    closeBtn.addEventListener('click', function () {
      container.host.remove();
      // Shift body back down
      document.body.style.marginTop = '';
    });

    banner.appendChild(msg);
    banner.appendChild(scoreEl);
    banner.appendChild(closeBtn);
    container.shadow.appendChild(style);
    container.shadow.appendChild(banner);

    // Push body down so the banner doesn't cover content
    document.body.style.marginTop = '40px';
  }

  // === SLOP BADGE (score < -30) ===

  function showSlopBadge(report) {
    var container = createShadowHost('hole-slop-badge');
    container.host.style.cssText +=
      'top:8px;right:8px;';

    var style = document.createElement('style');
    style.textContent = [
      '.badge{',
      '  font-family:system-ui,-apple-system,sans-serif;',
      '  background:#fff3cd;color:#856404;border:1px solid #ffc107;',
      '  padding:4px 8px;border-radius:4px;font-size:11px;font-weight:600;',
      '  pointer-events:auto;cursor:default;',
      '  box-shadow:0 1px 4px rgba(0,0,0,0.15);',
      '}',
    ].join('\n');

    var badge = document.createElement('div');
    badge.className = 'badge';
    badge.textContent = 'SLOP ' + report.slop_score;
    badge.title = (report.reasons || []).join(', ') || 'Low quality signals detected';

    container.shadow.appendChild(style);
    container.shadow.appendChild(badge);
  }

  // === SOURCE TIER BADGE ===

  function showSourceTierBadge() {
    var hostname = window.location.hostname.replace(/^www\./, '');
    var tierInfo = DOMAIN_TIERS[hostname];

    if (!tierInfo) return;

    var container = createShadowHost('hole-tier-badge');
    // Position below slop badge if it exists, otherwise top-right
    var topOffset = document.getElementById('hole-slop-badge') ? 36 : 8;
    container.host.style.cssText +=
      'top:' + topOffset + 'px;right:8px;';

    var colors = {
      1: { bg: '#d4edda', fg: '#155724', border: '#28a745' },
      2: { bg: '#cce5ff', fg: '#004085', border: '#007bff' },
      3: { bg: '#e2e3e5', fg: '#383d41', border: '#6c757d' },
    };
    var c = colors[tierInfo.tier] || colors[3];

    var style = document.createElement('style');
    style.textContent = [
      '.tier-badge{',
      '  font-family:system-ui,-apple-system,sans-serif;',
      '  background:' + c.bg + ';color:' + c.fg + ';border:1px solid ' + c.border + ';',
      '  padding:4px 8px;border-radius:4px;font-size:11px;font-weight:700;',
      '  pointer-events:auto;cursor:default;text-transform:uppercase;',
      '  box-shadow:0 1px 4px rgba(0,0,0,0.1);letter-spacing:0.5px;',
      '}',
    ].join('\n');

    var badge = document.createElement('div');
    badge.className = 'tier-badge';
    badge.textContent = tierInfo.label;

    container.shadow.appendChild(style);
    container.shadow.appendChild(badge);
  }

  // === AFFILIATE LINK DIMMING ===

  function dimAffiliateLinks() {
    var links = document.querySelectorAll('a[href]');
    var dimmed = 0;

    for (var i = 0; i < links.length; i++) {
      var href = links[i].href || '';
      if (isAffiliateLink(href)) {
        links[i].style.opacity = '0.3';
        links[i].style.transition = 'opacity 0.2s';

        // Add [affiliate] label if not already present
        if (!links[i].dataset.holeAffiliate) {
          links[i].dataset.holeAffiliate = '1';
          var label = document.createElement('span');
          label.textContent = ' [affiliate]';
          label.style.cssText =
            'font-size:10px;color:#999;font-weight:normal;font-style:italic;opacity:1;';
          links[i].appendChild(label);
          dimmed++;
        }
      }
    }

    return dimmed;
  }

  function isAffiliateLink(href) {
    for (var i = 0; i < AFFILIATE_PATTERNS.length; i++) {
      if (AFFILIATE_PATTERNS[i].test(href)) {
        return true;
      }
    }
    return false;
  }

  // === RUN ON PAGE LOAD ===

  function init() {
    // Run after a short delay so the page has time to render
    setTimeout(function () {
      showSourceTierBadge();
      dimAffiliateLinks();
      analyzePageSlop();
    }, 500);

    // Re-check affiliate links periodically for dynamically loaded content
    var checkCount = 0;
    var affiliateInterval = setInterval(function () {
      dimAffiliateLinks();
      checkCount++;
      if (checkCount >= 10) {
        clearInterval(affiliateInterval);
      }
    }, 3000);
  }

  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
