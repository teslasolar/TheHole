/**
 * THE HOLE — Client-side search engine
 * Lunr.js-powered, zero-server search.
 *
 * Data files (built by build_index.py):
 *   index/lunr_index.json  — pre-built Lunr index
 *   index/documents.json   — full document metadata
 *   index/meta.json        — index stats
 */

(function () {
  'use strict';

  // ═══ CONFIG ═══
  var INDEX_PATH = 'index/lunr_index.json';
  var DOCS_PATH = 'index/documents.json';
  var META_PATH = 'index/meta.json';
  var RESULTS_PER_PAGE = 20;

  // ═══ STATE ═══
  var lunrIndex = null;
  var documents = [];
  var meta = null;
  var indexReady = false;
  var currentQuery = '';
  var currentFilter = 'all';
  var currentPage = 0;
  var filteredResults = [];

  // ═══ DOM REFS ═══
  var homeView = document.getElementById('home-view');
  var resultsView = document.getElementById('results-view');
  var queryInput = document.getElementById('q');
  var queryInput2 = document.getElementById('q2');
  var resultsDiv = document.getElementById('results');
  var statsDiv = document.getElementById('stats');
  var filtersDiv = document.getElementById('filters');
  var paginationDiv = document.getElementById('pagination');

  // ═══ INIT ═══
  loadIndex();
  setupFilters();
  setupKeyboard();
  handleUrlState();

  // ═══ INDEX LOADING ═══

  function loadIndex() {
    var loaded = 0;
    var needed = 2;

    fetchJSON(DOCS_PATH, function (err, data) {
      if (err) {
        // Try sample data fallback
        fetchJSON('sample_data/documents.json', function (err2, data2) {
          if (err2) {
            showError('Index not built yet. Run: python scripts/build_index.py');
            return;
          }
          documents = data2;
          loaded++;
          if (loaded >= needed) onIndexReady();
        });
        return;
      }
      documents = data;
      loaded++;
      if (loaded >= needed) onIndexReady();
    });

    fetchJSON(INDEX_PATH, function (err, data) {
      if (err) {
        // Fallback: build index from documents at runtime
        fetchJSON('sample_data/documents.json', function () {
          // Documents already loaded by the other branch; build in onIndexReady
          loaded++;
          if (loaded >= needed) onIndexReady();
        });
        return;
      }
      try {
        lunrIndex = lunr.Index.load(data);
      } catch (e) {
        // Will build at runtime in onIndexReady
      }
      loaded++;
      if (loaded >= needed) onIndexReady();
    });

    fetchJSON(META_PATH, function (err, data) {
      if (!err) meta = data;
    });
  }

  function onIndexReady() {
    if (!documents || documents.length === 0) {
      showError('No documents found. Run: python scripts/build_index.py');
      return;
    }

    // Build Lunr index at runtime if pre-built index failed to load
    if (!lunrIndex) {
      lunrIndex = lunr(function () {
        this.ref('id');
        this.field('title', { boost: 3 });
        this.field('author', { boost: 1 });
        this.field('snippet', { boost: 1 });
        this.field('tags', { boost: 2 });

        for (var i = 0; i < documents.length; i++) {
          this.add({
            id: i,
            title: documents[i].title || '',
            author: documents[i].author || '',
            snippet: documents[i].snippet || '',
            tags: (documents[i].tags || []).join(' '),
          });
        }
      });
    }

    indexReady = true;

    // If there's a pending query from URL, execute it
    if (currentQuery) {
      drill();
    }
  }

  // ═══ SEARCH ═══

  /**
   * Main search function — called by DRILL button and Enter key.
   */
  function drill() {
    var q = (queryInput2.value || queryInput.value || '').trim();
    if (!q) return;

    currentQuery = q;
    currentPage = 0;

    // Sync both inputs
    queryInput.value = q;
    queryInput2.value = q;

    // Update URL
    var params = new URLSearchParams();
    params.set('q', q);
    if (currentFilter !== 'all') params.set('f', currentFilter);
    history.pushState(null, '', '?' + params.toString());

    if (!indexReady) {
      showView('results');
      resultsDiv.innerHTML = '<div class="loading">Loading index...</div>';
      return;
    }

    var t0 = performance.now();

    // Search with Lunr
    var raw;
    try {
      raw = lunrIndex.search(q);
    } catch (e) {
      // If Lunr query syntax fails, try as plain terms
      try {
        var escaped = q.replace(/[:\*\~\^+-]/g, ' ').trim();
        raw = lunrIndex.search(escaped);
      } catch (e2) {
        raw = [];
      }
    }

    // Map to documents
    var results = [];
    for (var i = 0; i < raw.length; i++) {
      var idx = parseInt(raw[i].ref, 10);
      if (documents[idx]) {
        results.push({
          doc: documents[idx],
          lunrScore: raw[i].score,
        });
      }
    }

    // Sort by composite score (from our ranker), using lunr score as tiebreaker
    results.sort(function (a, b) {
      var sa = a.doc.score || 0;
      var sb = b.doc.score || 0;
      if (sb !== sa) return sb - sa;
      return b.lunrScore - a.lunrScore;
    });

    // Apply filters
    filteredResults = applyFilter(results, currentFilter);

    var elapsed = Math.round(performance.now() - t0);

    // Render
    showView('results');
    statsDiv.textContent = filteredResults.length + ' results \u00B7 ' + elapsed + 'ms';
    renderResults(filteredResults, currentPage);
    renderPagination(filteredResults.length);
  }

  // Expose globally for onclick
  window.drill = drill;

  // ═══ FILTERS ═══

  function applyFilter(results, filter) {
    if (filter === 'all' || filter === 'ever') return results;

    var now = new Date();
    return results.filter(function (r) {
      var d = r.doc;
      switch (filter) {
        case 't1': return d.tier === 1;
        case 't2': return d.tier === 2;
        case 'code': return d.has_code === true;
        case 'papers':
          return d.source === 'arxiv' || d.source === 'pubmed' || d.source === 'rfc';
        case 'month':
          return d.date && daysSince(d.date) <= 30;
        case 'year':
          return d.date && daysSince(d.date) <= 365;
        default: return true;
      }
    });
  }

  function daysSince(dateStr) {
    var then = new Date(dateStr);
    var now = new Date();
    return Math.floor((now - then) / 86400000);
  }

  function setupFilters() {
    filtersDiv.addEventListener('click', function (e) {
      if (e.target.tagName !== 'BUTTON') return;

      // Toggle active class
      var buttons = filtersDiv.querySelectorAll('button');
      for (var i = 0; i < buttons.length; i++) {
        buttons[i].classList.remove('active');
      }
      e.target.classList.add('active');

      currentFilter = e.target.getAttribute('data-filter');
      currentPage = 0;

      if (currentQuery && indexReady) {
        drill();
      }
    });
  }

  // ═══ RENDERING ═══

  function renderResults(results, page) {
    var start = page * RESULTS_PER_PAGE;
    var end = Math.min(start + RESULTS_PER_PAGE, results.length);
    var slice = results.slice(start, end);

    if (slice.length === 0) {
      resultsDiv.innerHTML = '<div class="empty">No results. Try different terms or filters.</div>';
      return;
    }

    var html = '';
    for (var i = 0; i < slice.length; i++) {
      html += renderResult(slice[i].doc);
    }
    resultsDiv.innerHTML = html;
  }

  function renderResult(doc) {
    var tierClass = 't' + (doc.tier || 4);
    var tierLabel = 'T' + (doc.tier || 4);

    var scores = '';
    if (doc.practitioner && doc.practitioner > 0) {
      scores += '<span class="practitioner">\uD83D\uDD27' + doc.practitioner + '</span> ';
    }
    if (doc.source === 'arxiv' || doc.source === 'pubmed' || doc.source === 'rfc') {
      scores += '<span class="academic">\uD83C\uDF93' + (doc.score || 0) + '</span> ';
    }

    var tags = '';
    if (doc.tags && doc.tags.length > 0) {
      tags = '<div class="result-tags">';
      var maxTags = Math.min(doc.tags.length, 5);
      for (var j = 0; j < maxTags; j++) {
        tags += '<span>' + escapeHtml(doc.tags[j]) + '</span>';
      }
      tags += '</div>';
    }

    var domain = extractDomain(doc.url);
    var dateStr = doc.date ? formatDate(doc.date) : '';
    var metaParts = [domain, escapeHtml(doc.author || 'Unknown'), dateStr].filter(Boolean);

    return (
      '<div class="result">' +
        '<div class="result-header">' +
          '<span class="result-tier ' + tierClass + '">' + tierLabel + '</span>' +
          '<span class="result-title"><a href="' + escapeHtml(doc.url) + '" rel="noopener">' +
            escapeHtml(doc.title) + '</a></span>' +
        '</div>' +
        '<div class="result-meta">' + metaParts.join(' \u00B7 ') + '</div>' +
        (scores ? '<div class="result-scores">' + scores + '</div>' : '') +
        '<div class="result-snippet">' + escapeHtml(doc.snippet || '') + '</div>' +
        tags +
      '</div>'
    );
  }

  // ═══ PAGINATION ═══

  function renderPagination(totalResults) {
    var totalPages = Math.ceil(totalResults / RESULTS_PER_PAGE);
    if (totalPages <= 1) {
      paginationDiv.classList.add('hide');
      return;
    }

    paginationDiv.classList.remove('hide');
    var html = '';

    html += '<button onclick="prevPage()" ' + (currentPage === 0 ? 'disabled' : '') + '>&laquo; Prev</button>';
    html += '<span class="current">' + (currentPage + 1) + ' / ' + totalPages + '</span>';
    html += '<button onclick="nextPage()" ' + (currentPage >= totalPages - 1 ? 'disabled' : '') + '>Next &raquo;</button>';

    paginationDiv.innerHTML = html;
  }

  window.nextPage = function () {
    var totalPages = Math.ceil(filteredResults.length / RESULTS_PER_PAGE);
    if (currentPage < totalPages - 1) {
      currentPage++;
      renderResults(filteredResults, currentPage);
      renderPagination(filteredResults.length);
      window.scrollTo(0, 0);
    }
  };

  window.prevPage = function () {
    if (currentPage > 0) {
      currentPage--;
      renderResults(filteredResults, currentPage);
      renderPagination(filteredResults.length);
      window.scrollTo(0, 0);
    }
  };

  // ═══ VIEW MANAGEMENT ═══

  function showView(view) {
    if (view === 'results') {
      homeView.classList.add('hide');
      resultsView.classList.remove('hide');
      queryInput2.focus();
    } else {
      resultsView.classList.add('hide');
      homeView.classList.remove('hide');
      queryInput.focus();
    }
  }

  function goHome(e) {
    if (e) e.preventDefault();
    currentQuery = '';
    currentFilter = 'all';
    queryInput.value = '';
    queryInput2.value = '';
    history.pushState(null, '', window.location.pathname);
    showView('home');

    // Reset filter buttons
    var buttons = filtersDiv.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].classList.remove('active');
    }
    filtersDiv.querySelector('[data-filter="all"]').classList.add('active');
  }
  window.goHome = goHome;

  function toggleAbout(e) {
    if (e) e.preventDefault();
    var about = document.getElementById('about');
    about.classList.toggle('hide');
  }
  window.toggleAbout = toggleAbout;

  // ═══ URL STATE ═══

  function handleUrlState() {
    var params = new URLSearchParams(window.location.search);
    var q = params.get('q');
    var f = params.get('f');

    if (q) {
      currentQuery = q;
      queryInput.value = q;
      queryInput2.value = q;

      if (f) {
        currentFilter = f;
        var buttons = filtersDiv.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {
          buttons[i].classList.remove('active');
          if (buttons[i].getAttribute('data-filter') === f) {
            buttons[i].classList.add('active');
          }
        }
      }

      // drill() will be called by onIndexReady if index isn't loaded yet
      if (indexReady) drill();
    }
  }

  window.addEventListener('popstate', function () {
    handleUrlState();
    var params = new URLSearchParams(window.location.search);
    if (!params.get('q')) {
      goHome();
    }
  });

  // ═══ KEYBOARD ═══

  function setupKeyboard() {
    queryInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') drill();
    });
    queryInput2.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') drill();
    });

    // Global: / to focus search
    document.addEventListener('keydown', function (e) {
      if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        var input = resultsView.classList.contains('hide') ? queryInput : queryInput2;
        input.focus();
      }
    });
  }

  // ═══ UTILITIES ═══

  function fetchJSON(url, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) return;
      if (xhr.status === 200) {
        try {
          cb(null, JSON.parse(xhr.responseText));
        } catch (e) {
          cb(e, null);
        }
      } else {
        cb(new Error('HTTP ' + xhr.status), null);
      }
    };
    xhr.send();
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function extractDomain(url) {
    if (!url) return '';
    try {
      var a = document.createElement('a');
      a.href = url;
      return a.hostname.replace(/^www\./, '');
    } catch (e) {
      return '';
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    var d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    return d.toISOString().split('T')[0];
  }

  function showError(msg) {
    showView('results');
    resultsDiv.innerHTML = '<div class="error">' + escapeHtml(msg) + '</div>';
    statsDiv.textContent = '';
    paginationDiv.classList.add('hide');
  }

})();
