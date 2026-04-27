"""mirror a website as a static site

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdc, pkdlog, pkdp
import os
import bs4
import re
import pykern.pkio
import requests
import urllib.parse

#: built-in tag rules applied to every mirror (analytics, beacons, WP infrastructure)
_DEFAULT_TAG_RULES = {
    # Google Analytics / Tag Manager
    r"script.*src=.*google-analytics\.com": "delete",
    r"script.*src=.*googletagmanager\.com": "delete",
    r"script.*src=.*gtag\.js": "delete",
    r"script.*GoogleAnalyticsObject": "delete",
    r"script.*gtag\s*\(": "delete",
    r"script.*_gaq\s*\.": "delete",
    # Other analytics/beacons
    r"script.*src=.*hotjar\.com": "delete",
    r"script.*hotjar": "delete",
    r"script.*src=.*clarity\.ms": "delete",
    r"script.*clarity\(": "delete",
    r"script.*src=.*amplitude\.com": "delete",
    # GTM noscript fallback
    r"noscript.*googletagmanager": "delete",
    # WordPress infrastructure links
    r"link.*type=application/json\+oembed": "delete",
    r"link.*type=text/xml\+oembed": "delete",
    r"link.*type=application/rsd\+xml": "delete",
    r"link.*https://api\.w\.org/": "delete",
    r"link.*rel=EditURI": "delete",
}


def mirror(url, output_dir, rules_file=None):
    """Mirror `url` as a static site in `output_dir`

    Fetches pages starting from `url`, follows internal links within
    the same URL prefix, rewrites URLs to relative, and strips analytics.
    Contact pages are replaced with mailto links.

    Args:
        url (str): starting URL to mirror
        output_dir (str): local directory for output files
        rules_file (str): optional path to a YAML rules file
    """
    return _Mirror(
        url, pykern.pkio.py_path(output_dir), _load_rules(url, rules_file)
    ).run()


def _load_rules(url, rules_file):
    import ruamel.yaml

    h = urllib.parse.urlparse(url).netloc
    u = {}
    if rules_file:
        u = ruamel.yaml.YAML().load(pykern.pkio.py_path(rules_file).read()) or {}
    r = dict(tag=[], uri={})
    for pat, act in _DEFAULT_TAG_RULES.items():
        m = re.match(r"^(\w+)", pat)
        r["tag"].append(
            (m.group(1) if m else None, re.compile(pat, re.IGNORECASE | re.DOTALL), act)
        )
    for s in (u.get("default") or {}, u.get(h) or {}):
        for pat, act in (s.get("tag") or {}).items():
            m = re.match(r"^(\w+)", pat)
            r["tag"].append(
                (
                    m.group(1) if m else None,
                    re.compile(pat, re.IGNORECASE | re.DOTALL),
                    act,
                )
            )
        for path, act in (s.get("uri") or {}).items():
            r["uri"][path] = act
    return r


class _Mirror:
    def __init__(self, start_url, output_dir, rules):
        p = urllib.parse.urlparse(start_url)
        self._scheme_host = f"{p.scheme}://{p.netloc}"
        self._base_path = p.path.rstrip("/")
        self._base_url = self._scheme_host + self._base_path
        self._output_dir = output_dir
        self._visited = set()
        self._queue = [self._base_url + "/"]
        s = re.sub(r"^www\.", "", p.netloc)
        self._contact_mailto = f"mailto:info@{s}"
        self._tag_rules = rules["tag"]
        self._uri_rules = rules["uri"]

    def run(self):
        pykern.pkio.mkdir_parent(self._output_dir)
        s = requests.Session()
        s.headers["User-Agent"] = (
            "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
        )
        while self._queue:
            u = self._queue.pop(0)
            if u in self._visited:
                continue
            self._visited.add(u)
            self._fetch(s, u)
        return f"wrote {len(self._visited)} pages to {self._output_dir}"

    def _fetch(self, session, url):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            pkdlog("fetch error url={} err={}", url, e)
            return
        p = self._url_to_path(url)
        pykern.pkio.mkdir_parent(p.dirpath())
        if "text/html" in r.headers.get("content-type", ""):
            self._save_html(url, r.text, p)
        else:
            p.write_binary(r.content)

    def _save_html(self, url, html, out_path):
        s = bs4.BeautifulSoup(html, "html.parser")
        self._apply_tag_rules(s)
        self._rewrite_links(url, s)
        out_path.write(str(s))

    def _apply_tag_rules(self, soup):
        for tag_name, pattern, action in self._tag_rules:
            for t in soup.find_all(tag_name or True):
                if pattern.search(str(t)):
                    if action == "delete":
                        t.decompose()

    def _rewrite_links(self, current_url, soup):
        for tag, attr, follow_only in (
            ("a", "href", True),
            ("link", "href", False),
            ("script", "src", False),
            ("img", "src", False),
            ("source", "src", False),
        ):
            for e in soup.find_all(tag):
                v = e.get(attr)
                if not v:
                    continue
                a = self._to_absolute(current_url, v)
                if a is None:
                    continue
                fetchable = self._is_internal(a) or (
                    not follow_only and self._is_same_host(a)
                )
                if not fetchable:
                    continue
                act = self._uri_action(a)
                if act == "keep":
                    continue
                if act and act.startswith("mailto:"):
                    if tag == "a":
                        e[attr] = act
                    continue
                p = urllib.parse.urlparse(a)
                a = p.scheme + "://" + p.netloc + p.path
                if a not in self._visited:
                    self._queue.append(a)
                e[attr] = self._to_relative(current_url, a)

    def _is_internal(self, url):
        return url.startswith(self._base_url)

    def _is_same_host(self, url):
        return (
            urllib.parse.urlparse(url).netloc
            == urllib.parse.urlparse(self._base_url).netloc
        )

    def _to_absolute(self, base, href):
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            return None
        return urllib.parse.urljoin(base, href)

    def _to_relative(self, from_url, to_url):
        return os.path.relpath(
            str(self._url_to_path(to_url)),
            str(self._url_to_path(from_url).dirpath()),
        )

    def _uri_action(self, url):
        p = urllib.parse.urlparse(url)
        pq = p.path + ("?" + p.query if p.query else "")
        for k in (pq, p.path):
            if k in self._uri_rules:
                return self._uri_rules[k]
        if "/contact" in p.path.lower():
            return self._contact_mailto
        return None

    def _url_to_path(self, url):
        p = urllib.parse.urlparse(url).path
        if p.startswith(self._base_path):
            p = p[len(self._base_path) :]
        p = p.lstrip("/")
        if not p or p.endswith("/"):
            p = p + "index.html"
        elif "." not in p.rsplit("/", 1)[-1]:
            p = p + "/index.html"
        r = self._output_dir.join(p)
        if not str(r).startswith(str(self._output_dir)):
            raise ValueError(f"path traversal detected url={url} resolved={r}")
        return r
