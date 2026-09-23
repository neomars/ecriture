import { invoke } from "@tauri-apps/api/core";
import { openUrl } from "@tauri-apps/plugin-opener";

// @ts-ignore
window.__TAURI__ = { core: { invoke } };

// The webview doesn't open `target="_blank"` links by itself: send external
// web links (update download, release notes, about/donation links) to the
// user's default browser instead.
document.addEventListener("click", (event) => {
  const link = (event.target as Element | null)?.closest?.("a[href]");
  if (!(link instanceof HTMLAnchorElement)) return;
  if (!/^https?:\/\//i.test(link.href) || link.target !== "_blank") return;
  event.preventDefault();
  openUrl(link.href).catch((e) => console.error("Failed to open link:", e));
});
