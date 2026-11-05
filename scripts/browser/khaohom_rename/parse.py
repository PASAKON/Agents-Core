import re, json, sys
K="C:/mooniex/khaohom-ep01b/POST-KIT.md"
t=open(K,encoding="utf-8").read()
title=re.search(r"## TITLE.*?\n(.+)\n",t).group(1).strip()
desc=re.search(r"## DESCRIPTION\n(.*?)\n## TAGS",t,re.S).group(1).strip()
tags=[x.strip() for x in re.search(r"## TAGS.*?\n(.+)\n",t).group(1).split(",")]
tr={}
for m in re.finditer(r"### (\S+) \([^\n]*\)\nTITLE: ([^\n]+)\nDESCRIPTION:\n(.*?)(?=\n### |\Z)",t,re.S):
    tr[m.group(1)]={"title":m.group(2).strip(),"description":m.group(3).strip()}
json.dump({"title":title,"description":desc,"tags":tags,"tr":tr},open(sys.argv[1],"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print(title,len(title),len(desc),len(tags),{k:(len(v["title"]),len(v["description"])) for k,v in tr.items()})
