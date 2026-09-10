import json
import pandas as pd

def leads_to_json(leads):
    return json.dumps(leads, ensure_ascii=False, indent=2).encode("utf-8")

def leads_to_csv(leads):
    df = pd.DataFrame(leads)
    return df.to_csv(index=False).encode("utf-8-sig")
