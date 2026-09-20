import os
import requests

class DiscoveryError(Exception):
    pass

def discover(queries, count=20):
    key=os.getenv("BRAVE_SEARCH_API_KEY")
    if not key:
        raise DiscoveryError("BRAVE_SEARCH_API_KEY is not configured")
    found=[]
    seen=set()
    headers={"Accept":"application/json","X-Subscription-Token":key}
    for query in queries:
        r=requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q":query,"count":min(int(count),20),"safesearch":"strict"},
            headers=headers,timeout=15)
        r.raise_for_status()
        data=r.json()
        for item in data.get("web",{}).get("results",[]):
            url=item.get("url")
            if not url or not url.startswith(("http://","https://")): continue
            host=url.split("://",1)[1].split("/",1)[0].lower().split(":",1)[0]
            if host.startswith("www."): host=host[4:]
            if host in seen: continue
            seen.add(host)
            found.append({"url":url,"domain":host,"title":item.get("title",""),"description":item.get("description",""),"query":query})
    return found
