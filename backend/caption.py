import sqlite3, time
from PIL import Image
from tqdm import tqdm
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

DB = "data/tagle.sqlite"
MODEL = "Salesforce/blip-image-captioning-large"

device = "cuda" if torch.cuda.is_available() else "cpu"
processor = BlipProcessor.from_pretrained(MODEL)
model = BlipForConditionalGeneration.from_pretrained(MODEL).to(device)

def uncaptions(limit=200):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT id,file_path,gps_lat,gps_lon FROM photos LIMIT ?",(limit,))
    rows = cur.fetchall(); con.close()
    return rows

def save(pid,cap):
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.execute("UPDATE photos SET caption=? WHERE id=?",(cap,pid))
    con.commit(); con.close()

def make_caption(p,lat,lon):
    img=Image.open(p).convert("RGB")
    prompt="Photo is of"
    inputs=processor(images=img, text=prompt ,return_tensors="pt").to(device)
    out=model.generate(**inputs,max_new_tokens=100)
    return processor.decode(out[0],skip_special_tokens=True)

def run():
    for pid,p,plat,plon in tqdm(uncaptions(100),desc="Captioning"):
        try: save(pid,make_caption(p,plat,plon))
        except Exception as e: print("skip",p,e); time.sleep(0.1)

if __name__=="__main__":
    run(); print("✅ Captions generated")