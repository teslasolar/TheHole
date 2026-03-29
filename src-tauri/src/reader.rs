use regex::Regex;

/// Extracted article data for reader mode.
#[derive(Debug, Clone, serde::Serialize)]
pub struct Article {
    pub title: String,
    pub author: String,
    pub content: String,
    pub word_count: usize,
    pub reading_time: usize,
}

/// Very simple readability extraction.
///
/// Strategy:
/// 1. Extract <title> for the page title.
/// 2. Look for <meta name="author"> for the author.
/// 3. Find the first <article> or <main> block; fall back to <body>.
/// 4. Strip <script>, <style>, <nav>, <aside>, <footer>, <header> tags.
/// 5. Strip remaining HTML tags to get plain text.
/// 6. Compute word count and reading time (~230 wpm).
pub fn extract_article(html: &str) -> Article {
    let title = extract_tag_content(html, "title").unwrap_or_default();
    let author = extract_meta_author(html).unwrap_or_default();

    // Grab the best content region
    let region = extract_tag_content(html, "article")
        .or_else(|| extract_tag_content(html, "main"))
        .or_else(|| extract_tag_content(html, "body"))
        .unwrap_or_else(|| html.to_string());

    // Strip unwanted structural tags and their contents
    let cleaned = strip_tag_and_contents(&region, "script");
    let cleaned = strip_tag_and_contents(&cleaned, "style");
    let cleaned = strip_tag_and_contents(&cleaned, "nav");
    let cleaned = strip_tag_and_contents(&cleaned, "aside");
    let cleaned = strip_tag_and_contents(&cleaned, "footer");
    let cleaned = strip_tag_and_contents(&cleaned, "header");
    let cleaned = strip_tag_and_contents(&cleaned, "noscript");
    let cleaned = strip_tag_and_contents(&cleaned, "iframe");
    let cleaned = strip_tag_and_contents(&cleaned, "form");

    // Strip all remaining HTML tags
    let text = strip_all_tags(&cleaned);

    // Collapse whitespace
    let text = collapse_whitespace(&text);

    let word_count = text.split_whitespace().count();
    let reading_time = (word_count as f64 / 230.0).ceil() as usize;

    Article {
        title,
        author,
        content: text,
        word_count,
        reading_time,
    }
}

fn extract_tag_content(html: &str, tag: &str) -> Option<String> {
    let open_pattern = format!("<{}", tag);
    let close_tag = format!("</{}>", tag);
    let lower = html.to_lowercase();
    let start_pos = lower.find(&open_pattern)?;
    // Skip past the opening tag's `>`
    let after_open = html[start_pos..].find('>')?;
    let content_start = start_pos + after_open + 1;
    let end_pos = lower[content_start..].find(&close_tag)?;
    Some(html[content_start..content_start + end_pos].to_string())
}

fn extract_meta_author(html: &str) -> Option<String> {
    let re = Regex::new(r#"(?i)<meta\s+name=["']author["']\s+content=["']([^"']+)["']"#).ok()?;
    re.captures(html).map(|c| c[1].to_string())
}

fn strip_tag_and_contents(html: &str, tag: &str) -> String {
    let pattern = format!(r"(?is)<{}\b[^>]*>.*?</{}>", regex::escape(tag), regex::escape(tag));
    if let Ok(re) = Regex::new(&pattern) {
        re.replace_all(html, "").into_owned()
    } else {
        html.to_string()
    }
}

fn strip_all_tags(html: &str) -> String {
    let re = Regex::new(r"<[^>]+>").unwrap();
    let text = re.replace_all(html, " ");
    // Decode common HTML entities
    text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
}

fn collapse_whitespace(text: &str) -> String {
    let re = Regex::new(r"\s+").unwrap();
    re.replace_all(text.trim(), " ").into_owned()
}

// ── Tauri command ──

#[tauri::command]
pub fn get_reader_content(html: String) -> Article {
    extract_article(&html)
}
