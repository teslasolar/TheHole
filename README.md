# THE HOLE -- search for things people built

A practitioner-first search engine and browser. No ads. No tracking. No slop.

THE HOLE indexes primary sources -- arXiv, GitHub, Hacker News, Stack Overflow,
PubMed, practitioner blogs, Lobsters, and IETF RFCs -- and ranks them with a
transparent, open-source algorithm that rewards real work over SEO.

**BLOOM** is the browser edition: a Tauri-based desktop browser where the search
engine is not a feature but the foundation. Every page is analyzed by the slop
shield. Affiliate links are dimmed. Source tiers are shown. Reader mode strips
pages to clean text. The address bar is the search bar.

## Quick start

### Run the search frontend locally

```bash
cd frontend
python3 -m http.server 8000
# Open http://localhost:8000
```

The frontend works with sample data out of the box. To build the full index:

```bash
pip install -r requirements.txt
python scripts/build_index.py
```

### Build the BLOOM browser

Requires [Rust](https://rustup.rs/) and the Tauri CLI.

```bash
cargo install tauri-cli --version "^2" --locked

# Linux: install system dependencies first
sudo apt-get install libwebkit2gtk-4.1-dev libappindicator3-dev \
  librsvg2-dev patchelf libssl-dev libgtk-3-dev libsoup-3.0-dev \
  libjavascriptcoregtk-4.1-dev

# Build
cargo tauri build
```

For development with hot reload:

```bash
cargo tauri dev
```

## Architecture

```
TheHole/
  frontend/          Search engine web frontend (standalone)
    index.html       Home page and results view
    search.js        Lunr.js client-side search
    lunr.min.js      Lunr.js library
    index/           Built search index (generated)
    sample_data/     Sample documents for development

  src/               BLOOM browser frontend
    index.html       Browser home page (hole://home)
    search.js        Search with Tauri IPC integration
    shield-inject.js Slop shield content script
    reader.css       Reader mode stylesheet
    settings.html    Settings page (hole://settings)

  src-tauri/         Tauri backend (Rust)
    src/
      router.rs      Address bar input parsing
    Cargo.toml       Rust dependencies
    build.rs         Tauri build script

  spiders/           Web crawlers for each source
  filters/           Slop detection (affiliate links, content quality)
  rankers/           Ranking algorithm
  scripts/           Index building and maintenance
  data/              Raw crawled data
  tests/             Test suite

  Cargo.toml         Workspace root
```

### How search works

1. **Crawl**: Spiders fetch documents from each source (arXiv, GitHub, etc.)
2. **Filter**: The slop filter scores each document for quality signals --
   affiliate links, keyword stuffing, listicle patterns, LLM-generated content
3. **Rank**: Documents are scored by a composite algorithm weighing source tier,
   practitioner signals, recency, and content quality
4. **Index**: Lunr.js builds a client-side search index from the scored documents
5. **Search**: The frontend searches the index entirely in the browser -- no
   server required

### How the slop shield works (BLOOM)

When you visit any page in BLOOM:

1. The page HTML is sent to the Tauri backend via IPC
2. The backend runs slop analysis (affiliate detection, quality scoring)
3. Results are injected into the page via shadow DOM:
   - Score < -50: red warning banner at top
   - Score < -30: subtle badge in corner
   - Affiliate links: dimmed to 30% opacity with [affiliate] label
   - Known domains: source tier badge (T1/T2/T3)

### Address bar routing

The address bar handles all input types:

- Plain text: THE HOLE search
- URLs (with or without https://): direct navigation
- `hole://home`: home page
- `hole://settings`: settings page
- `:gh query`: GitHub search
- `:arxiv query`: arXiv search
- `:hn query`: Hacker News search
- `:so query`: Stack Overflow search
- `! query`: Google fallback

## Contributing

THE HOLE is open source. Contributions welcome.

1. Fork the repository
2. Create a branch for your change
3. Make your changes
4. Run the test suite: `python -m pytest tests/`
5. Submit a pull request

Areas where help is needed:

- **Spiders**: New source crawlers (e.g., Semantic Scholar, crates.io, PyPI)
- **Filters**: Better slop detection heuristics
- **Rankers**: Ranking algorithm improvements (with justification)
- **Browser**: Tauri backend features (bookmarks, history, tab management)
- **Frontend**: Accessibility improvements, keyboard navigation

Please read [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md) before contributing to
understand the project's values and design decisions.

## License

MIT
