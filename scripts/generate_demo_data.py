from pathlib import Path
import csv,random
root=Path(__file__).resolve().parents[1]; out=root/"data"/"demo_telemetry.csv"; out.parent.mkdir(exist_ok=True); r=random.Random(26249); rows=[]
for a in range(1,13):
 for c in range(1,61):
  d=(c/60)**1.6; rows.append({"aircraft_id":f"AF-{a:03d}","cycle":c,"component":"ENGINE","egt_c":round(650+90*d+r.uniform(-6,6),2),"vibration_g":round(.12+.55*d+r.uniform(-.02,.02),3),"oil_pressure_kpa":round(410-55*d+r.uniform(-4,4),2)})
with out.open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print(out)