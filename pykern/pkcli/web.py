"""mirror a website as a static site

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdc, pkdlog, pkdp
import re
import urllib.parse


#: script src patterns to remove (analytics, beacons)
_ANALYTICS_SRC_RE = re.compile(
    r"google-analytics\.com|googletagmanager\.com|gtag\.js|hotjar\.com|clarity\.ms|amplitude\.com",
    re.IGNORECASE,
)

#: inline script content patterns to remove
_ANALYTICS_INLINE_RE = re.compile(
    r"GoogleAnalyticsObject|gtag\s*\(|_gaq\s*\.|hotjar|clarity\(",
    re.IGNORECASE,
)


def mirror(url, output_dir):
    """Mirror `url` as a static site in `output_dir`

    Fetches pages starting from `url`, follows internal links within
    the same URL prefix, rewrites URLs to relative, and strips analytics.
    Contact pages are skipped.

    Args:
        url (str): starting URL to mirror
        output_dir (str): local directory for output files
    """
    import pykern.pkio

    _Mirror(url, pykern.pkio.py_path(output_dir)).run()


class _Mirror:
    def __init__(self, start_url, output_dir):
        p = urllib.parse.urlparse(start_url)
        self._scheme_host = f"{p.scheme}://{p.netloc}"
        self._base_path = p.path.rstrip("/")
        self._base_url = self._scheme_host + self._base_path
        self._output_dir = output_dir
        self._visited = set()
        self._queue = [self._base_url + "/"]

    def run(self):
        import pykern.pkio
        import requests

        pykern.pkio.mkdir_parent(self._output_dir)
        s = requests.Session()
        while self._queue:
            u = self._queue.pop(0)
            if u in self._visited:
                continue
            self._visited.add(u)
            self._fetch(s, u)

    def _fetch(self, session, url):
        import pykern.pkio

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
        import bs4

        s = bs4.BeautifulSoup(html, "html.parser")
        self._strip_analytics(s)
        self._rewrite_links(url, s)
        out_path.write(str(s))

    def _strip_analytics(self, soup):
        for t in soup.find_all("script"):
            s = t.get("src", "")
            if s and _ANALYTICS_SRC_RE.search(s):
                t.decompose()
                continue
            if t.string and _ANALYTICS_INLINE_RE.search(t.string):
                t.decompose()
        for t in soup.find_all("noscript"):
            for f in t.find_all("iframe"):
                if _ANALYTICS_SRC_RE.search(f.get("src", "")):
                    t.decompose()
                    break

    def _rewrite_links(self, current_url, soup):
        for tag, attr in (
            ("a", "href"),
            ("link", "href"),
            ("script", "src"),
            ("img", "src"),
            ("source", "src"),
        ):
            for el in soup.find_all(tag):
                v = el.get(attr)
                if not v:
                    continue
                a = self._to_absolute(current_url, v)
                if a is None or not self._is_internal(a):
                    continue
                if self._is_contact(a):
                    continue
                if a not in self._visited:
                    self._queue.append(a)
                el[attr] = self._to_relative(current_url, a)

    def _is_contact(self, url):
        return "/contact" in urllib.parse.urlparse(url).path.lower()

    def _is_internal(self, url):
        return url.startswith(self._base_url)

    def _to_absolute(self, base, href):
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            return None
        return urllib.parse.urljoin(base, href)

    def _to_relative(self, from_url, to_url):
        import os

        f = self._url_to_path(from_url)
        t = self._url_to_path(to_url)
        return os.path.relpath(str(t), str(f.dirpath()))

    def _url_to_path(self, url):
        p = urllib.parse.urlparse(url).path
        if p.startswith(self._base_path):
            p = p[len(self._base_path) :]
        p = p.lstrip("/")
        if not p or p.endswith("/"):
            p = p + "index.html"
        elif "." not in p.rsplit("/", 1)[-1]:
            p = p + "/index.html"
        return self._output_dir.join(p)
