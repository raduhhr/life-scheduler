#!/usr/bin/env python3
import os, sys, csv, time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import yaml

API = "https://api.trello.com/1"

KEY   = os.environ["TRELLO_KEY"]
TOKEN = os.environ["TRELLO_TOKEN"]
BOARD_ID = os.environ.get("TRELLO_BOARD_ID")     # either this...
LIST_ID  = os.environ.get("TRELLO_LIST_ID")      # ...or this
CFG_PATH = os.environ.get("CONFIG_PATH", "config.yml")

with open(CFG_PATH, "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

TZ = ZoneInfo(CFG.get("timezone", "Europe/Bucharest"))

def trello(method, path, **kwargs):
    params = kwargs.pop("params", {})
    params.update({"key": KEY, "token": TOKEN})
    url = f"{API}{path}"
    r = requests.request(method, url, params=params, **kwargs)
    if r.status_code == 429:
        time.sleep(1.0)
        r = requests.request(method, url, params=params, **kwargs)
    r.raise_for_status()
    if r.headers.get("Content-Type","").startswith("application/json"):
        return r.json()
    return r.text

def find_list_id():
    if LIST_ID:
        return LIST_ID
    if not BOARD_ID:
        raise SystemExit("Provide TRELLO_LIST_ID or TRELLO_BOARD_ID env var.")
    lists = trello("GET", f"/boards/{BOARD_ID}/lists")
    for lst in lists:
        if lst["name"] == CFG.get("list_name","Daily Log"):
            return lst["id"]
    raise SystemExit("List not found by name on BOARD_ID.")

def board_label_maps(board_id):
    labels = trello("GET", f"/boards/{board_id}/labels")
    id_to_name = {lbl["id"]: (lbl.get("name") or "").lower() for lbl in labels}
    name_to_id = {(lbl.get("name") or "").lower(): lbl["id"] for lbl in labels}
    return id_to_name, name_to_id

def list_cards(list_id):
    return trello("GET", f"/lists/{list_id}/cards",
                  params={"fields":"name,idLabels,due,closed"})

def create_card(list_id, name):
    return trello("POST", "/cards", params={"idList": list_id, "name": name})

def update_card_due(card_id, due_iso):
    return trello("PUT", f"/cards/{card_id}", params={"due": due_iso})

def parse_due_utc(due):
    if not due: return None
    base = due.replace("Z","").split(".")[0]
    return datetime.fromisoformat(base).replace(tzinfo=ZoneInfo("UTC"))

def next_due_utc(cadence_days: int, hour: str) -> str:
    hh, mm = [int(x) for x in hour.split(":")]
    target_local = (datetime.now(TZ).date() + timedelta(days=cadence_days))
    dt_local = datetime(target_local.year, target_local.month, target_local.day, hh, mm, tzinfo=TZ)
    return dt_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def ensure_metrics_csv(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_local","task_name","cadence_label","category","list_id","card_id_spawned"])

def append_metric(path, task_name, cadence_label, category, list_id, card_id):
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            datetime.now(TZ).isoformat(timespec="seconds"),
            task_name,
            cadence_label,
            category,
            list_id,
            card_id
        ])

def main():
    list_id = find_list_id()
    lst = trello("GET", f"/lists/{list_id}")
    board_id = lst["idBoard"]
    id_to_name, _ = board_label_maps(board_id)

    cards = list_cards(list_id)
    active_names = {c["name"] for c in cards if not c.get("closed")}

    timer_label = CFG["labels"]["timer"].lower()

    # Cadences structure: {label: {"days": int, "category": str}}
    cadences_cfg = CFG.get("cadences", {})
    # Normalize keys to lowercase
    cadences = {k.lower(): {"days": int(v["days"]), "category": v.get("category","uncategorized")}
                for k,v in cadences_cfg.items()}

    suffix = CFG.get("defaults",{}).get("daily_spawn_suffix"," – 1h")
    timer_hour = CFG.get("defaults",{}).get("timer_hour","03:00")

    metrics_cfg = CFG.get("metrics", {"enable": True, "csv_path": "metrics/blocks.csv"})
    metrics_on = metrics_cfg.get("enable", True)
    metrics_path = metrics_cfg.get("csv_path", "metrics/blocks.csv")
    if metrics_on:
        ensure_metrics_csv(metrics_path)

    for c in cards:
        label_names = [id_to_name.get(lid,"") for lid in c.get("idLabels",[])]
        lname_set = {n.lower() for n in label_names}
        if timer_label not in lname_set:
            continue

        cadence_label = None
        cadence_days = None
        category = "uncategorized"
        for lname in lname_set:
            if lname in cadences:
                cadence_label = lname
                cadence_days = cadences[lname]["days"]
                category = cadences[lname]["category"]
                break
        if not cadence_days:
            continue

        due_utc = parse_due_utc(c.get("due"))
        now_utc = datetime.now(ZoneInfo("UTC"))
        if not due_utc or now_utc < due_utc:
            continue  # not due yet

        work_name = f"{c['name']}{suffix}"
        if work_name not in active_names:
            spawned = create_card(list_id, work_name)
            active_names.add(work_name)
            if metrics_on:
                append_metric(metrics_path, work_name, cadence_label, category, list_id, spawned["id"])

        new_due = next_due_utc(cadence_days, timer_hour)
        update_card_due(c["id"], new_due)

    print("Timers processed OK")

if __name__ == "__main__":
    main()
