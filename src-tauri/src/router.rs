use url::Url;

/// Actions the router can dispatch based on address bar input.
#[derive(Debug, Clone, serde::Serialize)]
#[serde(tag = "type", content = "payload")]
pub enum RouterAction {
    HoleSearch(String),
    HoleHome,
    HoleSettings,
    Navigate(String),
    SourceShortcut { source: String, query: String },
    GoogleFallback(String),
}

/// Source-shortcut prefixes recognised in the address bar.
const SOURCE_SHORTCUTS: &[(&str, &str, &str)] = &[
    (":gh", "github", "https://github.com/search?q="),
    (":arxiv", "arxiv", "https://arxiv.org/search/?query="),
    (":hn", "hackernews", "https://hn.algolia.com/?q="),
    (":so", "stackoverflow", "https://stackoverflow.com/search?q="),
];

/// Returns `true` when `input` looks like a navigable URL (not a search query).
fn looks_like_url(input: &str) -> bool {
    if input.starts_with("http://") || input.starts_with("https://") {
        return true;
    }
    // bare domain heuristic: contains a dot, no spaces, at least 2-char TLD
    if !input.contains(' ') && !input.starts_with(':') && !input.starts_with('!') {
        if let Some(dot_pos) = input.find('.') {
            let after_dot = &input[dot_pos + 1..];
            // grab the TLD part (up to next / or end)
            let tld_part = after_dot.split('/').next().unwrap_or("");
            if tld_part.len() >= 2 && tld_part.chars().all(|c| c.is_ascii_alphanumeric()) {
                return true;
            }
        }
    }
    false
}

/// Parse raw address-bar input into a `RouterAction`.
pub fn parse_input(input: &str) -> RouterAction {
    let input = input.trim();

    if input.is_empty() || input == "hole://home" {
        return RouterAction::HoleHome;
    }

    if input == "hole://settings" {
        return RouterAction::HoleSettings;
    }

    // Google fallback with "!" prefix
    if let Some(query) = input.strip_prefix('!') {
        let query = query.trim();
        if query.is_empty() {
            return RouterAction::HoleHome;
        }
        return RouterAction::GoogleFallback(query.to_string());
    }

    // Source shortcuts ":gh query", ":arxiv query", etc.
    for &(prefix, source, _base_url) in SOURCE_SHORTCUTS {
        if input.starts_with(prefix) {
            let rest = input[prefix.len()..].trim();
            if rest.is_empty() {
                return RouterAction::HoleSearch(source.to_string());
            }
            return RouterAction::SourceShortcut {
                source: source.to_string(),
                query: rest.to_string(),
            };
        }
    }

    // Direct URL navigation
    if looks_like_url(input) {
        let url = if input.starts_with("http://") || input.starts_with("https://") {
            input.to_string()
        } else {
            format!("https://{}", input)
        };
        // Validate with the url crate
        if Url::parse(&url).is_ok() {
            return RouterAction::Navigate(url);
        }
    }

    // hole:// internal URLs
    if input.starts_with("hole://") {
        return RouterAction::Navigate(input.to_string());
    }

    // Default: treat as THE HOLE search
    RouterAction::HoleSearch(input.to_string())
}

/// Build the full redirect URL for a source shortcut.
pub fn build_shortcut_url(source: &str, query: &str) -> Option<String> {
    for &(_prefix, src_name, base_url) in SOURCE_SHORTCUTS {
        if src_name == source {
            let encoded_query: String =
                url::form_urlencoded::byte_serialize(query.as_bytes()).collect();
            return Some(format!("{}{}", base_url, encoded_query));
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_plain_text_is_search() {
        match parse_input("rust programming") {
            RouterAction::HoleSearch(q) => assert_eq!(q, "rust programming"),
            other => panic!("expected HoleSearch, got {:?}", other),
        }
    }

    #[test]
    fn test_empty_is_home() {
        assert!(matches!(parse_input(""), RouterAction::HoleHome));
        assert!(matches!(parse_input("   "), RouterAction::HoleHome));
        assert!(matches!(parse_input("hole://home"), RouterAction::HoleHome));
    }

    #[test]
    fn test_https_url_navigate() {
        match parse_input("https://example.com") {
            RouterAction::Navigate(u) => assert_eq!(u, "https://example.com"),
            other => panic!("expected Navigate, got {:?}", other),
        }
    }

    #[test]
    fn test_bare_domain_navigate() {
        match parse_input("example.com") {
            RouterAction::Navigate(u) => assert_eq!(u, "https://example.com"),
            other => panic!("expected Navigate, got {:?}", other),
        }
    }

    #[test]
    fn test_gh_shortcut() {
        match parse_input(":gh tauri") {
            RouterAction::SourceShortcut { source, query } => {
                assert_eq!(source, "github");
                assert_eq!(query, "tauri");
            }
            other => panic!("expected SourceShortcut, got {:?}", other),
        }
    }

    #[test]
    fn test_arxiv_shortcut() {
        match parse_input(":arxiv transformers") {
            RouterAction::SourceShortcut { source, query } => {
                assert_eq!(source, "arxiv");
                assert_eq!(query, "transformers");
            }
            other => panic!("expected SourceShortcut, got {:?}", other),
        }
    }

    #[test]
    fn test_google_fallback() {
        match parse_input("! something") {
            RouterAction::GoogleFallback(q) => assert_eq!(q, "something"),
            other => panic!("expected GoogleFallback, got {:?}", other),
        }
    }

    #[test]
    fn test_bang_empty_is_home() {
        assert!(matches!(parse_input("!"), RouterAction::HoleHome));
        assert!(matches!(parse_input("!  "), RouterAction::HoleHome));
    }

    #[test]
    fn test_settings_url() {
        assert!(matches!(parse_input("hole://settings"), RouterAction::HoleSettings));
    }

    #[test]
    fn test_build_shortcut_url_github() {
        let url = build_shortcut_url("github", "hello world").unwrap();
        assert!(url.starts_with("https://github.com/search?q="));
        assert!(url.contains("hello"));
    }

    #[test]
    fn test_build_shortcut_url_unknown() {
        assert!(build_shortcut_url("unknown_source", "q").is_none());
    }
}
