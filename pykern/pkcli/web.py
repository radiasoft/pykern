"""mirror a website as a static site

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import os
import bs4
import re
import pykern.pkio
import requests
import urllib.parse

_VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

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
    # Yoast SEO structured data
    r"script.*yoast-schema-graph": "delete",
    # WordPress infrastructure links
    r"link.*/feed/": "delete",
    r"link.*wp-json/oembed": "delete",
    r"link.*https://api\.w\.org/": "delete",
    r"link.*xmlrpc\.php": "delete",
    r"link.*wp-json/wp/": "delete",
}


_SIREPO_PATH_REWRITES = {"/cloudmc": "/openmc"}

_SIREPO_PROXY_HOSTS = frozenset(("www.sirepo.com", "beta2.sirepo.com"))


def sirepo_wp_mirror(url, output_dir, rules_file=None, contact_mailto=None):
    """Mirror `url` as a static site in `output_dir`

    Fetches pages starting from `url`, follows internal links within
    the same URL prefix, rewrites URLs to relative, and strips analytics.
    If `contact_mailto` is supplied, contact pages are replaced with that
    mailto link.

    Args:
        url (str): starting URL to mirror
        output_dir (str): local directory for output files
        rules_file (str): optional path to a YAML rules file
        contact_mailto (str): mailto link to substitute for contact pages, e.g. ``mailto:info@example.com``
    """
    return _Mirror(
        url,
        pykern.pkio.py_path(output_dir),
        _load_rules(rules_file),
        contact_mailto,
        _SIREPO_PROXY_HOSTS,
        _SIREPO_PATH_REWRITES,
    ).run()


def _load_rules(rules_file):
    import pykern.pkyaml

    def add_tag(p, a):
        if a != "delete":
            raise AssertionError(f"invalid tag rule action={a} pattern={p}")
        m = re.match(r"^(\w+)", p)
        r.tag.append(
            (m.group(1) if m else None, re.compile(p, re.IGNORECASE | re.DOTALL))
        )

    u = PKDict()
    if rules_file:
        u = pykern.pkyaml.load_file(rules_file).get("rules") or PKDict()
    r = PKDict(tag=[], uri=PKDict(), hosts=set())
    for p, a in _DEFAULT_TAG_RULES.items():
        add_tag(p, a)
    for p, a in (u.get("tag") or PKDict()).items():
        add_tag(p, a)
    for p, a in (u.get("uri") or PKDict()).items():
        r.uri[p] = a
    for h in u.get("hosts") or []:
        r.hosts.add(h)
    return r


class _Mirror:
    def __init__(
        self,
        start_url,
        output_dir,
        rules,
        contact_mailto,
        proxy_hosts,
        path_rewrites=None,
    ):
        p = urllib.parse.urlparse(start_url)
        self._scheme_host = f"{p.scheme}://{p.netloc}"
        self._base_path = p.path.rstrip("/")
        self._base_url = self._scheme_host + self._base_path
        self._contact_mailto = contact_mailto
        self._output_dir = output_dir
        self._path_rewrites = path_rewrites or {}
        self._proxy_hosts = proxy_hosts
        self._visited = set()
        self._queue = [self._base_url + "/"]
        self._tag_rules = rules.tag
        self._uri_rules = rules.uri
        self._asset_hosts = rules.hosts | {p.netloc} | proxy_hosts

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

    def _apply_tag_rules(self, soup):
        def tag_str(t):
            r = [t.name]
            for k, v in (t.attrs or {}).items():
                r.append(f'{k}="{" ".join(v) if isinstance(v, list) else v}"')
            if t.name not in _VOID_ELEMENTS and (c := t.decode_contents()):
                r.append(c)
            return " ".join(r)

        for n, p in self._tag_rules:
            for t in soup.find_all(n or True):
                if p.search(tag_str(t)):
                    t.decompose()

    def _fetch(self, session, url):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            pkdlog("fetch error url={} err={}", url, e)
            raise
        p = self._url_to_path(url)
        pykern.pkio.mkdir_parent(p.dirpath())
        if "text/html" in r.headers.get("content-type", ""):
            if not self._is_internal(url):
                return
            self._save_html(url, r.text, p)
        elif "text/css" in r.headers.get("content-type", ""):
            p.write(self._rewrite_css(url, r.text))
        else:
            p.write_binary(r.content)

    def _is_internal(self, url):
        return url.startswith(self._base_url)

    def _is_same_host(self, url):
        return urllib.parse.urlparse(url).netloc in self._asset_hosts

    def _rewrite_css(self, css_url, text):
        def _sub(m):
            q = m.group(1)
            a = urllib.parse.urljoin(css_url, m.group(2))
            if not self._is_same_host(a):
                return m.group(0)
            if a not in self._visited:
                self._queue.append(a)
            return f"url({q}{self._to_relative(a)}{q})"

        return re.sub(r"url\(\s*(['\"]?)([^'\")\s]+)['\"]?\s*\)", _sub, text)

    def _rewrite_proxy_content(self, soup):
        if not self._proxy_hosts:
            return
        _p = re.compile(
            r"https?://("
            + "|".join(re.escape(h) for h in self._proxy_hosts)
            + r")(/[^\s\"'<>)]*)"
        )

        def _sub(m):
            path, q = (m.group(2).split("?", 1) + [""])[:2]
            u = self._scheme_host + path
            if u not in self._visited:
                self._queue.append(u)
            return self._to_relative(u) + ("?" + q if q else "")

        for el in soup.find_all("meta"):
            if v := el.get("content", ""):
                el["content"] = _p.sub(_sub, v)
        for el in soup.find_all(style=True):
            el["style"] = _p.sub(_sub, el["style"])
        for el in soup.find_all("script"):
            if el.string:
                el.string = _p.sub(_sub, el.string)

    def _rewrite_links(self, current_url, soup):
        def _apply_proxy_rewrite(element, attr, href):
            p = urllib.parse.urlparse(self._to_absolute(current_url, href))
            if p.netloc not in self._proxy_hosts:
                return
            for o, n in self._path_rewrites.items():
                if p.path.startswith(o):
                    element[attr] = urllib.parse.urlunparse(
                        p._replace(path=n + p.path[len(o) :])
                    )
                    return

        def _fetchable(uri, is_a):
            if not uri or not (rv := self._to_absolute(current_url, uri)):
                return None
            if self._is_internal(rv) or (not is_a and self._is_same_host(rv)):
                return rv
            return None

        def _find_all(tag, attr, is_a):
            for e in soup.find_all(tag):
                if not (u := _fetchable(e.get(attr), is_a)):
                    if is_a and (r := e.get(attr)):
                        _apply_proxy_rewrite(e, attr, r)
                    continue
                if _url_ok(u, e, attr, is_a):
                    continue
                _url_fix(urllib.parse.urlparse(u), e, attr)

        def _url_fix(parsed, element, attr):
            q = ("?" + parsed.query) if parsed.query else ""
            if parsed.netloc in self._proxy_hosts:
                u = self._scheme_host + parsed.path
            else:
                u = parsed.scheme + "://" + parsed.netloc + parsed.path
            if u not in self._visited:
                self._queue.append(u)
            element[attr] = self._to_relative(u) + q

        def _url_ok(url, element, attr, is_a):
            if not (c := self._uri_action(url)):
                return False
            if c == "keep":
                return True
            if c.startswith("mailto:"):
                if not is_a:
                    raise ValueError(f"mailto rule on non-<a> tag url={url} value={c}")
                element[attr] = c
                return True
            raise AssertionError(
                f"invalid rule value={c} for url={url}; must be keep, delete, or mailto:"
            )

        for n, a in (
            ("a", "href"),
            ("link", "href"),
            ("script", "src"),
            ("img", "src"),
            ("source", "src"),
        ):
            _find_all(n, a, n == "a")

    def _save_html(self, url, html, out_path):
        s = bs4.BeautifulSoup(html, "html.parser")
        self._apply_tag_rules(s)
        self._rewrite_links(url, s)
        self._rewrite_proxy_content(s)
        out_path.write("\n".join(l.rstrip() for l in str(s).splitlines()) + "\n")

    def _to_absolute(self, base, href):
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            return None
        return urllib.parse.urljoin(base, href)

    def _to_relative(self, to_url):
        prefix = "/" + self._output_dir.basename + "/"
        if to_url == self._base_url + "/":
            return "/"
        p = os.path.relpath(str(self._url_to_path(to_url)), str(self._output_dir))
        if p.endswith("/index.html"):
            p = p[: -len("index.html")]
        elif p == "index.html":
            p = ""
        assert not any(c in (".", "..") for c in p.split("/")), f"url={to_url} path={p}"
        return prefix + p

    def _uri_action(self, url):
        p = urllib.parse.urlparse(url)
        pq = p.path + ("?" + p.query if p.query else "")
        for k in (pq, p.path):
            if k in self._uri_rules:
                return self._uri_rules[k]
        if self._contact_mailto and "/contact" in p.path.lower():
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
