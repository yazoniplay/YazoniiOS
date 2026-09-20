import os, re, time, urllib.robotparser
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup

UA="YazoniiOSBot/1.0 (+public-web-intelligence)"
TIMEOUT=int(os.getenv("CRAWL_TIMEOUT_SECONDS","12"))
MAX_BYTES=int(os.getenv("CRAWL_MAX_BYTES","1500000"))
MAX_PAGES=int(os.getenv("MAX_CRAWL_PAGES","12"))
HONOR_ROBOTS=os.getenv("HONOR_ROBOTS","true").lower()!="false"

def normalize(url):
    p=urlparse(url if url.startswith(("http://","https://")) else "https://"+url)
    scheme=p.scheme.lower()
    host=p.netloc.lower().split("@")[-1]
    path=p.path or "/"
    if path!="/": path=path.rstrip("/")
    return f"{scheme}://{host}{path}"

def crawl(start_url):
    start=normalize(start_url)
    base=urlparse(start)
    domain=base.netloc.lower().split("@")[-1]
    session=requests.Session()
    session.headers.update({"User-Agent":UA,"Accept":"text/html,application/xhtml+xml"})
    rp=urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(f"{base.scheme}://{domain}/robots.txt"); rp.read()
    except Exception:
        rp=None

    q=deque([start]); queued={start}; pages=[]
    while q and len(pages)<MAX_PAGES:
        url=q.popleft()
        if HONOR_ROBOTS and rp and not rp.can_fetch(UA,url):
            continue
        try:
            r=session.get(url,timeout=TIMEOUT,allow_redirects=True,stream=True)
            if r.status_code>=400: continue
            ctype=r.headers.get("content-type","").lower()
            if "text/html" not in ctype: continue
            chunks=[]; size=0
            for chunk in r.iter_content(16384):
                if not chunk: continue
                size += len(chunk)
                if size>MAX_BYTES: break
                chunks.append(chunk)
            raw=b"".join(chunks).decode(r.encoding or "utf-8","ignore")
            final=normalize(r.url)
            soup=BeautifulSoup(raw,"html.parser")
            for tag in soup(["script","style","noscript","svg"]): tag.decompose()
            text=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
            title=(soup.title.get_text(" ",strip=True) if soup.title else "")[:240]
            meta=soup.find("meta",attrs={"name":re.compile("^description$",re.I)})
            description=(meta.get("content","") if meta else "")[:500]
            links=[]
            for a in soup.find_all("a",href=True):
                href=normalize(urljoin(final,a["href"]))
                hp=urlparse(href)
                if hp.scheme in ("http","https") and hp.netloc.lower().split("@")[-1]==domain:
                    if href not in queued and len(queued)<MAX_PAGES*5:
                        queued.add(href); q.append(href)
                    links.append(href)
            pages.append({
                "url":final,"title":title,"description":description,
                "text":text[:18000],"html":raw[:MAX_BYTES],
                "links":list(dict.fromkeys(links))[:100],
                "headers":dict(r.headers),
            })
        except requests.RequestException:
            continue
        time.sleep(0.08)
    return pages
