import re, sqlite3
import nltk
nltk.download("stopwords",quiet=True)
STOP=set(nltk.corpus.stopwords.words("english"))

DB="data/tagle.sqlite"

def extract(text,max_tags=10):
    words=re.findall(r"[A-Za-z0-9'-]{3,}",text.lower())
    uniq=[]
    for w in words:
        w=w.strip("-'")
        if w in STOP or w.isdigit(): continue
        if w not in uniq: uniq.append(w)
    return ",".join(uniq[:max_tags])

def run():
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.execute("SELECT id,caption FROM photos WHERE (tags IS NULL OR tags='') AND caption!=''")
    rows=cur.fetchall()
    for pid,cap in rows:
        tags=extract(cap)
        cur.execute("UPDATE photos SET tags=? WHERE id=?",(tags,pid))
    con.commit(); con.close(); print("✅ Tags extracted")

if __name__=="__main__": run()