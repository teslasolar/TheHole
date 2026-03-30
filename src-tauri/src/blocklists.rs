use std::collections::HashSet;
use std::path::Path;
use url::Url;

/// A set of domains to block (ads, trackers, malware).
pub struct BlockList {
    domains: HashSet<String>,
}

impl BlockList {
    /// Create an empty blocklist.
    pub fn new() -> Self {
        Self {
            domains: HashSet::new(),
        }
    }

    /// Load the bundled default blocklist shipped with the app.
    pub fn load_default() -> Self {
        let raw = include_str!("../blocklists/hole_blacklist.txt");
        Self::parse_list(raw)
    }

    /// Load a blocklist from a file path (EasyList-style, domain blocks only).
    pub fn load_from_file(path: &Path) -> Result<Self, String> {
        let raw = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
        Ok(Self::parse_list(&raw))
    }

    /// Parse an EasyList-format list.  We only support simple domain lines:
    ///   - Lines starting with `||` and ending with `^` → domain block
    ///   - Bare domain lines (no special chars) → domain block
    ///   - Lines starting with `!` or `[` → comments / metadata, skipped
    fn parse_list(raw: &str) -> Self {
        let mut domains = HashSet::new();
        for line in raw.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('!') || line.starts_with('[') {
                continue;
            }
            // EasyList domain format: ||example.com^
            if let Some(rest) = line.strip_prefix("||") {
                if let Some(domain) = rest.strip_suffix('^') {
                    let domain = domain.to_lowercase();
                    if !domain.is_empty() {
                        domains.insert(domain);
                    }
                    continue;
                }
            }
            // Plain domain line (one domain per line)
            if !line.contains('/') && !line.contains('*') && !line.contains('#') {
                let domain = line.to_lowercase();
                if domain.contains('.') {
                    domains.insert(domain);
                }
            }
        }
        Self { domains }
    }

    /// Check whether a URL's host is on the blocklist.
    /// Also checks parent domains (e.g. sub.tracker.com matches tracker.com).
    pub fn is_blocked(&self, raw_url: &str) -> bool {
        let host = if let Ok(parsed) = Url::parse(raw_url) {
            parsed.host_str().unwrap_or("").to_lowercase()
        } else {
            // Might be a bare domain
            raw_url.to_lowercase()
        };

        if host.is_empty() {
            return false;
        }

        // Check the full host, then progressively strip subdomains
        let parts: Vec<&str> = host.split('.').collect();
        for i in 0..parts.len().saturating_sub(1) {
            let candidate = parts[i..].join(".");
            if self.domains.contains(&candidate) {
                return true;
            }
        }
        false
    }

    /// Number of domains in the list.
    pub fn len(&self) -> usize {
        self.domains.len()
    }

    pub fn is_empty(&self) -> bool {
        self.domains.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_load_default_has_entries() {
        let bl = BlockList::load_default();
        assert!(bl.len() > 50, "bundled list should have 50+ domains");
        assert!(!bl.is_empty());
    }

    #[test]
    fn test_known_domains_blocked() {
        let bl = BlockList::load_default();
        assert!(bl.is_blocked("https://doubleclick.net/ad.js"));
        assert!(bl.is_blocked("https://sub.google-analytics.com/collect"));
    }

    #[test]
    fn test_easylist_format_parsed() {
        let bl = BlockList::parse_list("||tracker.example.com^\n||ads.test.org^\n");
        assert_eq!(bl.len(), 2);
        assert!(bl.is_blocked("https://tracker.example.com/pixel"));
        assert!(bl.is_blocked("https://ads.test.org/banner"));
    }

    #[test]
    fn test_plain_domain_parsed() {
        let bl = BlockList::parse_list("badsite.com\nevil.org\n");
        assert_eq!(bl.len(), 2);
        assert!(bl.is_blocked("https://badsite.com/page"));
    }

    #[test]
    fn test_comments_skipped() {
        let bl = BlockList::parse_list("! this is a comment\n[Adblock Plus]\n||real.com^\n");
        assert_eq!(bl.len(), 1);
        assert!(bl.is_blocked("https://real.com/x"));
    }

    #[test]
    fn test_subdomain_match() {
        let bl = BlockList::parse_list("||tracker.com^\n");
        assert!(bl.is_blocked("https://sub.tracker.com/path"));
        assert!(bl.is_blocked("https://deep.sub.tracker.com/path"));
    }

    #[test]
    fn test_not_blocked() {
        let bl = BlockList::load_default();
        assert!(!bl.is_blocked("https://example.com"));
        assert!(!bl.is_blocked("https://rust-lang.org"));
    }
}
