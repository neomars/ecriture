//! Update-check logic: compares the running version against a fetched
//! GitHub release. Ports `main.py::check_updates`.
//!
//! The actual HTTP call is behind the [`ReleaseFetcher`] trait so the
//! comparison/selection logic can be tested without a network round trip;
//! [`GithubFetcher`] is the real implementation used by the app.

use serde::{Deserialize, Serialize};
use std::time::Duration;

/// The running app version, taken from this crate's `Cargo.toml` so it
/// only has to be bumped in one place per release.
pub const CURRENT_VERSION: &str = env!("CARGO_PKG_VERSION");
pub const GITHUB_REPO: &str = "neomars/ecriture";

#[derive(Debug, Clone, Deserialize)]
pub struct ReleaseAsset {
    pub name: String,
    pub browser_download_url: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct GithubRelease {
    pub tag_name: String,
    pub html_url: String,
    #[serde(default)]
    pub body: String,
    #[serde(default)]
    pub assets: Vec<ReleaseAsset>,
}

pub trait ReleaseFetcher {
    fn latest_release(&self, repo: &str) -> Result<GithubRelease, String>;
}

/// Fetches the latest published (non-draft, non-prerelease) release from
/// the GitHub REST API. Blocking, with a short timeout so an offline
/// machine just reports "no update" quickly.
pub struct GithubFetcher {
    /// API root, overridable for tests.
    pub api_base: String,
}

impl Default for GithubFetcher {
    fn default() -> Self {
        Self { api_base: "https://api.github.com".into() }
    }
}

impl ReleaseFetcher for GithubFetcher {
    fn latest_release(&self, repo: &str) -> Result<GithubRelease, String> {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(10))
            // GitHub's API rejects requests without a User-Agent.
            .user_agent(concat!("Ecriture/", env!("CARGO_PKG_VERSION")))
            .build()
            .map_err(|e| e.to_string())?;
        let response = client
            .get(format!("{}/repos/{repo}/releases/latest", self.api_base))
            .header("Accept", "application/vnd.github+json")
            .send()
            .map_err(|e| e.to_string())?;
        if !response.status().is_success() {
            return Err(format!("HTTP {}", response.status().as_u16()));
        }
        let body = response.text().map_err(|e| e.to_string())?;
        serde_json::from_str(&body).map_err(|e| e.to_string())
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct UpdateStatus {
    /// False when the release couldn't be fetched (offline, GitHub down...),
    /// so the UI doesn't claim the app is up to date without knowing.
    pub checked: bool,
    pub update_available: bool,
    pub current_version: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub latest_version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub download_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub release_notes: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub release_page: Option<String>,
}

impl UpdateStatus {
    fn none(checked: bool) -> Self {
        Self {
            checked,
            update_available: false,
            current_version: CURRENT_VERSION.to_string(),
            latest_version: None,
            download_url: None,
            release_notes: None,
            release_page: None,
        }
    }
}

/// Checks for an update using `fetcher`, never propagating a network
/// failure as an error - like the Python route, any fetch problem just
/// means "no update available" (logged by the caller if desired).
pub fn check_for_update(fetcher: &impl ReleaseFetcher, os_keyword: &str) -> UpdateStatus {
    let Ok(release) = fetcher.latest_release(GITHUB_REPO) else {
        return UpdateStatus::none(false);
    };

    let latest_tag = release.tag_name.trim_start_matches('v').to_string();

    match compare_versions(&latest_tag, CURRENT_VERSION) {
        Some(std::cmp::Ordering::Greater) => {
            let mut download_url = release.html_url.clone();
            for asset in &release.assets {
                if asset.name.to_lowercase().contains(os_keyword) {
                    download_url = asset.browser_download_url.clone();
                    break;
                }
            }
            UpdateStatus {
                checked: true,
                update_available: true,
                current_version: CURRENT_VERSION.to_string(),
                latest_version: Some(latest_tag),
                download_url: Some(download_url),
                release_notes: Some(release.body),
                release_page: Some(release.html_url),
            }
        }
        _ => UpdateStatus::none(true),
    }
}

/// Returns the part of a release asset's file name that identifies this
/// OS's installer, as published by the release workflow
/// (`ecriture_<version>_x64-setup.exe`, `..._aarch64.dmg`,
/// `..._amd64.deb`).
pub fn os_keyword() -> &'static str {
    if cfg!(target_os = "windows") {
        "-setup.exe"
    } else if cfg!(target_os = "macos") {
        ".dmg"
    } else {
        ".deb"
    }
}

/// Minimal `major.minor.patch` comparison (missing components default to
/// 0), which is all `packaging.version.parse` needs to do for the plain
/// `X.Y.Z` tags this project uses.
fn compare_versions(a: &str, b: &str) -> Option<std::cmp::Ordering> {
    let parse = |s: &str| -> Vec<u64> {
        s.split(['.', '-', '+'])
            .map(|part| part.parse::<u64>().unwrap_or(0))
            .collect()
    };
    let (va, vb) = (parse(a), parse(b));
    let len = va.len().max(vb.len());
    for i in 0..len {
        let x = va.get(i).copied().unwrap_or(0);
        let y = vb.get(i).copied().unwrap_or(0);
        match x.cmp(&y) {
            std::cmp::Ordering::Equal => continue,
            other => return Some(other),
        }
    }
    Some(std::cmp::Ordering::Equal)
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockFetcher(Result<GithubRelease, String>);
    impl ReleaseFetcher for MockFetcher {
        fn latest_release(&self, _repo: &str) -> Result<GithubRelease, String> {
            self.0.clone()
        }
    }

    fn release(tag: &str, assets: Vec<ReleaseAsset>) -> GithubRelease {
        GithubRelease {
            tag_name: tag.to_string(),
            html_url: "https://example.com/release".into(),
            body: "notes".into(),
            assets,
        }
    }

    #[test]
    fn compare_versions_orders_correctly() {
        assert_eq!(compare_versions("1.2.0", "1.10.0"), Some(std::cmp::Ordering::Less));
        assert_eq!(compare_versions("2.0.0", "1.9.9"), Some(std::cmp::Ordering::Greater));
        assert_eq!(compare_versions("1.0.0", "1.0.0"), Some(std::cmp::Ordering::Equal));
        assert_eq!(compare_versions("1.0", "1.0.0"), Some(std::cmp::Ordering::Equal));
    }

    #[test]
    fn newer_release_reports_update_available() {
        let fetcher = MockFetcher(Ok(release("v2.1.0", vec![])));
        let status = check_for_update(&fetcher, "linux");
        assert!(status.update_available);
        assert_eq!(status.latest_version.as_deref(), Some("2.1.0"));
        assert_eq!(status.download_url.as_deref(), Some("https://example.com/release"));
    }

    #[test]
    fn matching_os_asset_is_preferred_over_the_release_page() {
        let fetcher = MockFetcher(Ok(release(
            "v2.1.0",
            vec![
                ReleaseAsset { name: "ecriture_2.1.0_x64-setup.exe".into(), browser_download_url: "win".into() },
                ReleaseAsset { name: "ecriture_2.1.0_aarch64.dmg".into(), browser_download_url: "mac".into() },
                ReleaseAsset { name: "ecriture_2.1.0_amd64.deb".into(), browser_download_url: "lin".into() },
            ],
        )));
        assert_eq!(check_for_update(&fetcher, ".deb").download_url.as_deref(), Some("lin"));
        assert_eq!(check_for_update(&fetcher, ".dmg").download_url.as_deref(), Some("mac"));
        assert_eq!(check_for_update(&fetcher, "-setup.exe").download_url.as_deref(), Some("win"));
    }

    /// Serves one HTTP response on loopback and returns its base URL.
    fn serve_once(status_line: &'static str, body: &'static str) -> String {
        use std::io::{BufRead, BufReader, Write};
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        std::thread::spawn(move || {
            if let Ok((mut stream, _)) = listener.accept() {
                let mut reader = BufReader::new(stream.try_clone().unwrap());
                let mut line = String::new();
                loop {
                    line.clear();
                    if reader.read_line(&mut line).unwrap_or(0) == 0 || line == "\r\n" {
                        break;
                    }
                }
                let resp = format!(
                    "{status_line}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
                    body.len()
                );
                let _ = stream.write_all(resp.as_bytes());
            }
        });
        format!("http://{addr}")
    }

    #[test]
    fn github_fetcher_parses_the_latest_release() {
        let body = r#"{"tag_name":"v2.1.0","html_url":"https://github.com/neomars/ecriture/releases/tag/v2.1.0",
            "body":"notes","draft":false,
            "assets":[{"name":"ecriture_2.1.0_amd64.deb","browser_download_url":"https://example.com/deb","size":1}]}"#;
        let fetcher = GithubFetcher { api_base: serve_once("HTTP/1.1 200 OK", body) };
        let release = fetcher.latest_release(GITHUB_REPO).unwrap();
        assert_eq!(release.tag_name, "v2.1.0");
        assert_eq!(release.assets[0].name, "ecriture_2.1.0_amd64.deb");
    }

    #[test]
    fn github_fetcher_reports_http_and_network_errors() {
        let fetcher = GithubFetcher { api_base: serve_once("HTTP/1.1 404 Not Found", "") };
        assert_eq!(fetcher.latest_release(GITHUB_REPO).unwrap_err(), "HTTP 404");

        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        drop(listener);
        let fetcher = GithubFetcher { api_base: format!("http://{addr}") };
        assert!(fetcher.latest_release(GITHUB_REPO).is_err());
    }

    #[test]
    fn same_or_older_release_reports_no_update() {
        let fetcher = MockFetcher(Ok(release(&format!("v{CURRENT_VERSION}"), vec![])));
        let status = check_for_update(&fetcher, "linux");
        assert!(status.checked);
        assert!(!status.update_available);

        let fetcher_old = MockFetcher(Ok(release("v1.3.0", vec![])));
        assert!(!check_for_update(&fetcher_old, "linux").update_available);
    }

    #[test]
    fn fetch_failure_is_treated_as_no_update_available() {
        let fetcher = MockFetcher(Err("network down".into()));
        let status = check_for_update(&fetcher, "linux");
        assert!(!status.update_available);
        assert!(!status.checked);
        assert_eq!(status.current_version, CURRENT_VERSION);
    }
}
