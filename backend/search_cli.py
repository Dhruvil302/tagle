import sqlite3, sys
DB="data/tagle.sqlite"
q=" ".join(sys.argv[1:]).strip().lower()
if not q: raise SystemExit("Usage: python tagle/search_cli.py <keywords>")

terms=q.split()
where=" AND ".join(["(lower(caption) LIKE ? OR lower(tags) LIKE ?)"]*len(terms))
params=[]
for t in terms: params.extend([f"%{t}%",f"%{t}%"])

con=sqlite3.connect(DB); cur=con.cursor()
cur.execute(f"SELECT file_path,date_taken,caption,tags FROM photos WHERE {where} LIMIT 50",params)
for i,(p,d,c,t) in enumerate(cur.fetchall(),1):
    print(f"{i:02d}. {p}\n    date:{d}\n    caption:{c}\n    tags:{t}\n")
con.close()