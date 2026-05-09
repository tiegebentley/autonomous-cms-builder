"""
SEO Auditor Agent — runs after the applicator merges the CMS.

Crawls every .html file in the project root (skipping node_modules, dist,
build, cms-generated, .cms-backups, venv) and emits two outputs:

  1. A list of FINDINGS, each tagged severity (critical/high/medium/low)
     and category (title, meta, headings, alt, canonical, og, twitter, schema).
  2. A list of AUTO_FIXES that were mechanically applied — only safe edits
     that don't require content judgment:
       - Inject a <link rel="canonical"> when missing (uses file path → URL)
       - Add empty alt="" on <img> tags missing the attribute (Marcus already
         knows real alt text is content judgment — empty is the WAI-ARIA-blessed
         fallback for purely decorative images and is *less harmful* than no
         alt attr at all, which forces screen readers to read the filename)
       - Add og:title / og:description fallbacks copied from existing <title>
         and <meta name="description"> when those exist but the OG tags don't
       - Add twitter:card="summary_large_image" when OG tags exist but Twitter
         tags don't
     Anything content-judgment (rewriting a bad title, generating meta
     descriptions from scratch, choosing real alt text) goes in the report.

Writes SEO_REPORT.md to the project root.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseAgent


SKIP_DIRS = {
    "node_modules", "dist", "build", ".git", "venv", "__pycache__",
    "cms-generated", ".cms-backups", ".kirby-backups", ".next",
    "cache", "kirby-cms", "kirby-cms-generated",
}

# Severity → numeric weight for the score
SEVERITY_WEIGHT = {"critical": 10, "high": 5, "medium": 2, "low": 1}


class SeoAuditorAgent(BaseAgent):
    def __init__(
        self,
        project_path: str,
        project_name: str,
        auto_apply: bool = False,
        base_url: str | None = None,
    ):
        super().__init__(project_path, project_name)
        self.auto_apply = auto_apply
        # Used only to construct canonical URLs. If unknown, canonical fix is skipped.
        self.base_url = base_url
        self.project_root = Path(project_path)

    async def execute(self) -> dict[str, Any]:
        results: dict[str, Any] = {
            "audit_status": "pending",
            "auto_apply": self.auto_apply,
            "files_scanned": 0,
            "score": 100,
            "findings": [],          # all issues
            "auto_fixes_applied": [], # subset that was mechanically fixed
            "report_path": None,
            "errors": [],
        }

        html_files = self._find_html_files()
        results["files_scanned"] = len(html_files)

        if not html_files:
            results["audit_status"] = "skipped"
            results["errors"].append("No .html files found in project root")
            return results

        all_findings: list[dict[str, Any]] = []
        all_fixes: list[dict[str, Any]] = []

        for html_file in html_files:
            try:
                content = html_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                results["errors"].append(f"{html_file.name}: read failed ({e})")
                continue

            soup = BeautifulSoup(content, "lxml")
            file_findings = self._audit_file(html_file, soup)
            all_findings.extend(file_findings)

            if self.auto_apply:
                fixed_soup, fixes = self._apply_safe_fixes(html_file, soup, file_findings)
                if fixes:
                    html_file.write_text(str(fixed_soup), encoding="utf-8")
                    all_fixes.extend(fixes)

        results["findings"] = all_findings
        results["auto_fixes_applied"] = all_fixes
        results["score"] = self._compute_score(all_findings)

        report_path = self._write_report(results)
        results["report_path"] = str(report_path)

        results["audit_status"] = "completed"
        return results

    # ---- discovery ----

    def _find_html_files(self) -> list[Path]:
        files = []
        for p in self.project_root.rglob("*.html"):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            files.append(p)
        return sorted(files)

    # ---- per-file audit ----

    def _audit_file(self, path: Path, soup: BeautifulSoup) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        rel = str(path.relative_to(self.project_root))

        def add(category: str, severity: str, issue: str, autofix: str | None = None):
            findings.append({
                "file": rel,
                "category": category,
                "severity": severity,
                "issue": issue,
                "autofix": autofix,  # name of fix that *could* apply, or None
            })

        # --- title ---
        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else ""
        if not title:
            add("title", "critical", "Missing <title> tag", None)
        elif not title_text:
            add("title", "critical", "Empty <title> tag", None)
        elif len(title_text) < 10:
            add("title", "high", f"Title too short ({len(title_text)} chars, recommend 30-60)", None)
        elif len(title_text) > 60:
            add("title", "medium", f"Title too long ({len(title_text)} chars, recommend 30-60)", None)

        # --- meta description ---
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_text = (meta_desc.get("content") or "").strip() if meta_desc else ""
        if not meta_desc:
            add("meta", "high", "Missing meta description", None)
        elif not desc_text:
            add("meta", "high", "Empty meta description", None)
        elif len(desc_text) < 50:
            add("meta", "medium", f"Meta description too short ({len(desc_text)} chars, recommend 120-160)", None)
        elif len(desc_text) > 160:
            add("meta", "low", f"Meta description too long ({len(desc_text)} chars, recommend 120-160)", None)

        # --- headings ---
        h1s = soup.find_all("h1")
        if len(h1s) == 0:
            add("headings", "high", "No <h1> tag on page", None)
        elif len(h1s) > 1:
            add("headings", "medium", f"Multiple <h1> tags ({len(h1s)}); use exactly one", None)

        # --- images ---
        for img in soup.find_all("img"):
            if not img.has_attr("alt"):
                src = img.get("src", "(no src)")
                add("alt", "high", f"<img> missing alt attribute (src={src})", "add_empty_alt")

        # --- canonical ---
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if not canonical:
            add("canonical", "medium", "Missing canonical <link>", "add_canonical" if self.base_url else None)

        # --- Open Graph ---
        og_title = soup.find("meta", attrs={"property": "og:title"})
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if not og_title:
            fix = "add_og_title" if title_text else None
            add("og", "medium", "Missing og:title", fix)
        if not og_desc:
            fix = "add_og_description" if desc_text else None
            add("og", "medium", "Missing og:description", fix)

        # --- Twitter Card ---
        twitter = soup.find("meta", attrs={"name": "twitter:card"})
        if not twitter and og_title:
            add("twitter", "low", "Missing twitter:card (og:* present)", "add_twitter_card")
        elif not twitter:
            add("twitter", "low", "Missing twitter:card", None)

        # --- structured data ---
        ld_json = soup.find_all("script", attrs={"type": "application/ld+json"})
        if not ld_json:
            add("schema", "low", "No JSON-LD structured data on page", None)

        # --- viewport (mobile) ---
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if not viewport:
            add("technical", "high", "Missing viewport meta tag (mobile rendering)", None)

        # --- charset ---
        charset = soup.find("meta", attrs={"charset": True})
        if not charset:
            add("technical", "low", "Missing <meta charset>", None)

        return findings

    # ---- safe auto-fixes ----

    def _apply_safe_fixes(
        self,
        path: Path,
        soup: BeautifulSoup,
        findings: list[dict[str, Any]],
    ) -> tuple[BeautifulSoup, list[dict[str, Any]]]:
        """Apply only the fixes that don't require content judgment."""
        applied: list[dict[str, Any]] = []
        rel = str(path.relative_to(self.project_root))

        head = soup.find("head")
        if not head:
            # Without a <head> nothing meaningful is fixable. Bail.
            return soup, applied

        title_text = ""
        title_tag = soup.find("title")
        if title_tag:
            title_text = title_tag.get_text(strip=True)

        desc_text = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            desc_text = (meta_desc.get("content") or "").strip()

        for f in findings:
            fix_name = f.get("autofix")
            if not fix_name:
                continue

            if fix_name == "add_empty_alt":
                src_match = re.search(r"src=(.+)$", f["issue"])
                src = src_match.group(1).rstrip(")") if src_match else None
                if src:
                    img = soup.find("img", attrs={"src": src})
                    if img and not img.has_attr("alt"):
                        img["alt"] = ""
                        applied.append({"file": rel, "fix": fix_name, "detail": f"img src={src}"})

            elif fix_name == "add_canonical" and self.base_url:
                if not soup.find("link", attrs={"rel": "canonical"}):
                    canonical_url = urljoin(self.base_url.rstrip("/") + "/", rel)
                    new_tag = soup.new_tag("link", rel="canonical", href=canonical_url)
                    head.append(new_tag)
                    applied.append({"file": rel, "fix": fix_name, "detail": canonical_url})

            elif fix_name == "add_og_title" and title_text:
                if not soup.find("meta", attrs={"property": "og:title"}):
                    new_tag = soup.new_tag("meta")
                    new_tag.attrs["property"] = "og:title"
                    new_tag.attrs["content"] = title_text
                    head.append(new_tag)
                    applied.append({"file": rel, "fix": fix_name, "detail": title_text[:60]})

            elif fix_name == "add_og_description" and desc_text:
                if not soup.find("meta", attrs={"property": "og:description"}):
                    new_tag = soup.new_tag("meta")
                    new_tag.attrs["property"] = "og:description"
                    new_tag.attrs["content"] = desc_text
                    head.append(new_tag)
                    applied.append({"file": rel, "fix": fix_name, "detail": desc_text[:60]})

            elif fix_name == "add_twitter_card":
                if not soup.find("meta", attrs={"name": "twitter:card"}):
                    new_tag = soup.new_tag("meta")
                    new_tag.attrs["name"] = "twitter:card"
                    new_tag.attrs["content"] = "summary_large_image"
                    head.append(new_tag)
                    applied.append({"file": rel, "fix": fix_name, "detail": "summary_large_image"})

        return soup, applied

    # ---- scoring ----

    def _compute_score(self, findings: list[dict[str, Any]]) -> int:
        """Start at 100, deduct *average* severity-weighted issues per file, floor at 0.

        Per-finding deduction without normalization makes any site with >20 pages
        bottom out at 0 instantly. Normalize to per-file so a 24-page site and a
        2-page site with the same per-page issue density score the same.
        """
        if not findings:
            return 100
        files_affected = len({f["file"] for f in findings})
        if files_affected == 0:
            return 100
        deduction = sum(SEVERITY_WEIGHT.get(f["severity"], 0) for f in findings) / files_affected
        return max(0, round(100 - deduction))

    # ---- report ----

    def _write_report(self, results: dict[str, Any]) -> Path:
        report_path = self.project_root / "SEO_REPORT.md"
        findings = results["findings"]
        fixes = results["auto_fixes_applied"]
        score = results["score"]

        # Group findings by severity
        by_sev: dict[str, list[dict[str, Any]]] = {"critical": [], "high": [], "medium": [], "low": []}
        for f in findings:
            by_sev.setdefault(f["severity"], []).append(f)

        lines = []
        lines.append(f"# SEO Audit Report — {self.project_name}")
        lines.append("")
        lines.append(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by SeoAuditorAgent_")
        lines.append("")
        lines.append(f"**Score:** {score}/100")
        lines.append(f"**Files scanned:** {results['files_scanned']}")
        lines.append(f"**Findings:** {len(findings)} ({len(by_sev['critical'])} critical, "
                     f"{len(by_sev['high'])} high, {len(by_sev['medium'])} medium, {len(by_sev['low'])} low)")
        lines.append(f"**Auto-fixes applied:** {len(fixes)}")
        lines.append("")

        # Auto-fixes section
        if fixes:
            lines.append("## ✅ Auto-fixes Applied")
            lines.append("")
            lines.append("These mechanical fixes were applied directly to your files. "
                         "Backups of the original CMS-merged state live in `.cms-backups/`.")
            lines.append("")
            for fix in fixes:
                lines.append(f"- `{fix['file']}` — **{fix['fix']}**: {fix['detail']}")
            lines.append("")
        elif self.auto_apply:
            lines.append("## ✅ Auto-fixes Applied")
            lines.append("")
            lines.append("_No safe auto-fixes available for this project's findings._")
            lines.append("")
        else:
            lines.append("## ℹ️ Auto-fixes Skipped")
            lines.append("")
            lines.append("_auto_apply was off for this run. Re-run with `auto_apply=true` to apply mechanical fixes._")
            lines.append("")

        # Findings by severity
        lines.append("## 🔍 Findings (by severity)")
        lines.append("")
        for sev in ("critical", "high", "medium", "low"):
            items = by_sev[sev]
            if not items:
                continue
            lines.append(f"### {sev.title()} ({len(items)})")
            lines.append("")
            for item in items:
                tag = f"[{item['category']}]"
                lines.append(f"- `{item['file']}` {tag} {item['issue']}")
            lines.append("")

        if not findings:
            lines.append("_No issues found. Score: 100/100._")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("**Next steps:** Review high-severity issues first. Most low-severity items "
                     "(missing JSON-LD, short meta descriptions) require content judgment and were "
                     "intentionally not auto-fixed.")
        lines.append("")

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path
