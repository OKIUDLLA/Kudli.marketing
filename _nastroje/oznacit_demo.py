#!/usr/bin/env python3
"""Mark a demo website as a non-binding demo and hide it from search engines.

Usage: inject_demo.py <repo_dir> [<repo_dir> ...]

Per repo:
  * every .html file gets <meta name="robots" content="noindex, nofollow">
    (an existing robots meta is replaced) and a fixed bottom notice bar
    inserted before </body>; files already marked are skipped;
  * the site gets an X-Robots-Tag header (existing _headers "/*" block,
    else existing netlify.toml "/*" block, else a new netlify.toml).
Idempotent: running it twice changes nothing.
"""
import os
import re
import sys

MARK = "<!-- kudli-demo:start -->"
ROBOTS = '<meta name="robots" content="noindex, nofollow">'
HEADER_VALUE = "noindex, nofollow"

BANNER = """<!-- kudli-demo:start -->
<div id="kudli-demo-banner" role="note" lang="cs" style="all:initial;box-sizing:border-box;display:block;position:fixed;left:0;right:0;bottom:0;z-index:2147483647;width:100%;margin:0;padding:9px 16px calc(9px + env(safe-area-inset-bottom, 0px));background:#14181c;color:#f3f4f6;font:500 13px/1.45 system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;text-align:center;border-top:1px solid rgba(255,255,255,.16);box-shadow:0 -2px 12px rgba(0,0,0,.25)">Nezávazná ukázka webu, nejde o oficiální stránky firmy. Připravil <a href="https://www.kudlimarketing.cz/" target="_blank" rel="noopener" style="all:initial;font:inherit;color:#ffffff;text-decoration:underline;cursor:pointer">Kudli.&nbsp;marketing</a>.</div>
<style>@media print{#kudli-demo-banner{display:none!important}}</style>
<script>(function(){try{var b=document.getElementById('kudli-demo-banner');if(!b)return;var d=document.body,t=0;function fit(){var h=b.offsetHeight||0,vh=window.innerHeight||0;d.style.removeProperty('padding-bottom');var base=parseFloat(getComputedStyle(d).paddingBottom)||0;d.style.setProperty('padding-bottom',(base+h)+'px','important');var els=d.getElementsByTagName('*');for(var i=0;i<els.length;i++){var el=els[i];if(el===b||b.contains(el))continue;var o=el.getAttribute('data-kudli-bottom');if(o===null){var cs=getComputedStyle(el);if(cs.position!=='fixed')continue;var r=el.getBoundingClientRect();if(!r.width||!r.height||r.top<vh*0.5||r.bottom<vh-160)continue;o=parseFloat(cs.bottom);if(isNaN(o))continue;el.setAttribute('data-kudli-bottom',String(o));}el.style.setProperty('bottom',(parseFloat(o)+h)+'px','important');}}function later(){clearTimeout(t);t=setTimeout(fit,150);}fit();window.addEventListener('load',fit);window.addEventListener('resize',later);window.addEventListener('scroll',later,{passive:true});setTimeout(fit,1200);setTimeout(fit,3500);}catch(e){}})();</script>
<!-- kudli-demo:end -->
"""

ROBOTS_RE = re.compile(r"<meta\b[^>]*\bname\s*=\s*[\"']robots[\"'][^>]*>", re.I)
HEAD_RE = re.compile(r"<head\b[^>]*>", re.I)
BODY_CLOSE_RE = re.compile(r"</body\s*>", re.I)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def mark_html(path):
    text = read(path)
    if MARK in text:
        return "already"
    nl = "\r\n" if "\r\n" in text else "\n"
    notes = []
    found = ROBOTS_RE.findall(text)
    if found:
        first = True

        def repl(_m):
            nonlocal first
            if first:
                first = False
                return ROBOTS
            return ""

        text = ROBOTS_RE.sub(repl, text)
        notes.append("robots replaced")
    else:
        m = HEAD_RE.search(text)
        if m:
            text = text[: m.end()] + nl + "    " + ROBOTS + text[m.end():]
            notes.append("robots added")
        else:
            notes.append("NO <head>, robots not added")
    banner = BANNER.replace("\n", nl)
    closes = list(BODY_CLOSE_RE.finditer(text))
    if closes:
        pos = closes[-1].start()
        text = text[:pos] + banner + text[pos:]
        notes.append("banner")
    else:
        text = text + nl + banner
        notes.append("banner appended (no </body>)")
    write(path, text)
    return ", ".join(notes)


def add_header(repo):
    hdr = os.path.join(repo, "_headers")
    toml = os.path.join(repo, "netlify.toml")
    for path in (hdr, toml):
        if os.path.exists(path) and "X-Robots-Tag" in read(path):
            return "header already present"
    if os.path.exists(hdr):
        text = read(hdr)
        nl = "\r\n" if "\r\n" in text else "\n"
        lines = text.split(nl)
        for i, line in enumerate(lines):
            if line.strip() == "/*":
                lines.insert(i + 1, "  X-Robots-Tag: " + HEADER_VALUE)
                write(hdr, nl.join(lines))
                return "_headers /* block"
    if os.path.exists(toml):
        text = read(toml)
        nl = "\r\n" if "\r\n" in text else "\n"
        lines = text.split(nl)
        for i, line in enumerate(lines):
            if re.match(r'\s*for\s*=\s*"/\*"\s*$', line):
                for j in range(i + 1, min(i + 4, len(lines))):
                    if lines[j].strip() == "[headers.values]":
                        indent = re.match(r"\s*", lines[j]).group(0) + "  "
                        lines.insert(j + 1, indent + 'X-Robots-Tag = "' + HEADER_VALUE + '"')
                        write(toml, nl.join(lines))
                        return "netlify.toml /* block"
        block = (nl + "# Ukázkový web: nezobrazovat ve vyhledávačích" + nl + "[[headers]]" + nl
                 + '  for = "/*"' + nl + "  [headers.values]" + nl
                 + '    X-Robots-Tag = "' + HEADER_VALUE + '"' + nl)
        write(toml, text.rstrip("\r\n") + nl + block)
        return "netlify.toml new block"
    write(toml, "# Ukázkový web: nezobrazovat ve vyhledávačích\n[[headers]]\n  for = \"/*\"\n"
                "  [headers.values]\n    X-Robots-Tag = \"" + HEADER_VALUE + "\"\n")
    return "netlify.toml created"


def main(repos):
    for repo in repos:
        results = []
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
            for name in sorted(files):
                if name.lower().endswith(".html"):
                    path = os.path.join(root, name)
                    results.append(os.path.relpath(path, repo) + ": " + mark_html(path))
        print("== " + os.path.basename(repo.rstrip("/")) + " | " + add_header(repo))
        for r in results:
            print("   " + r)


if __name__ == "__main__":
    main(sys.argv[1:])
