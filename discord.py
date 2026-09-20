import os,requests
def send_report(p):
 webhook=os.getenv("DISCORD_WEBHOOK_URL")
 if not webhook:return False
 score=int(p.get("opportunity_score",0));confidence=int(p.get("confidence",0));color=0x65D39B if score>=75 else 0xFFB84D if score>=50 else 0x6F7785
 fields=[{"name":"Opportunity","value":f"**{score}/100**","inline":True},{"name":"Confidence","value":f"**{confidence}/100**","inline":True},{"name":"Category","value":str(p.get("category","unknown"))[:100],"inline":True},{"name":"Summary","value":str(p.get("summary","No summary"))[:1024]}]
 if p.get("pain_points"):fields.append({"name":"Signals","value":"\n".join("• "+x for x in p["pain_points"])[:1024]})
 if p.get("opportunities"):fields.append({"name":"Opportunities","value":"\n".join("• "+x for x in p["opportunities"])[:1024]})
 fields.append({"name":"Recommended action","value":str(p.get("recommended_action",""))[:1024]})
 payload={"username":"YazoniiOS","embeds":[{"title":str(p.get("name") or p.get("domain") or "Prospect")[:256],"url":p.get("url"),"description":"Automated public-web prospect intelligence.","color":color,"fields":fields,"footer":{"text":"YazoniiOS · public-web intelligence"}}]}
 r=requests.post(webhook,json=payload,timeout=15);r.raise_for_status();return True