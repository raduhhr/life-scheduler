#!/usr/bin/env python3
import os, sys, time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import yaml

API = "https://api.trello.com/1"

# --- Secrets (GH Actions first; local fallbacks) ---
KEY   = (os.environ.get("TRELLO_API_KEY")  or os.environ.get("TRELLO_KEY")  or "").strip()
TOKEN = (os.environ.get("TRELLO_API_TOKEN") or os.environ.get("TRELLO_TOKEN") or "").strip()
if not KEY or not TOKEN:
    print("Missing Trello creds: set TRELLO_API_KEY/TRELLO_API_TOKEN (or TRELLO_KEY/TRELLO_TOKEN).", file=sys.stderr)
    sys.exit(1)

# --- Wiring ---
BOARD_ID = os.environ.get("TRELLO_BOARD_ID")     # or set TRELLO_LIST_ID
LIST_ID  = os.environ.get("TRELLO_LIST_ID")
CFG_PATH = os.environ.get("CONFIG_PATH", "config.yml")
VERBOSE  = os.environ.get("VERBOSE", "0") == "1"

with open(CFG_PATH, "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

TZ = ZoneInfo(CFG.get("timezone", "Europe/Bucharest"))

def log(*a):
    if VERBOSE: print(*a)

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

def board_cards(board_id, filter_mode="closed"):
    # filter: 'open' | 'closed' | 'all'
    return trello("GET", f"/boards/{board_id}/cards",
        params={"fields":"name,idLabels,due,closed,idList", "filter": filter_mode})

def parse_due_utc(due):
    if not due: return None
    base = due.replace("Z","").split(".")[0]
    return datetime.fromisoformat(base).replace(tzinfo=ZoneInfo("UTC"))

def next_due_utc(days: int, hour: str) -> str:
    hh, mm = [int(x) for x in hour.split(":")]
    target_local = (datetime.now(TZ).date() + timedelta(days=days))
    dt_local = datetime(target_local.year, target_local.month, target_local.day, hh, mm, tzinfo=TZ)
    return dt_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def set_card_closed(card_id, closed: bool):
    trello("PUT", f"/cards/{card_id}", params={"closed": str(closed).lower()})

def move_card_to_list(card_id, list_id):
    trello("PUT", f"/cards/{card_id}", params={"idList": list_id})

def update_card_due(card_id, due_iso):
    trello("PUT", f"/cards/{card_id}", params={"due": due_iso})

def main():
    list_id = find_list_id()
    lst = trello("GET", f"/lists/{list_id}")
    board_id = lst["idBoard"]
    id_to_name, _ = board_label_maps(board_id)

    timer_label_name = CFG["labels"]["timer"].lower()

    # cadences from config: {label: {"days": int, "category": str}}
    cadences_cfg = CFG.get("cadences", {})
    cadences = {k.lower(): int(v["days"]) for k,v in cadences_cfg.items()}
    timer_hour = CFG.get("defaults",{}).get("timer_hour","03:00")

    archived = board_cards(board_id, filter_mode="closed")
    recovered = 0
    bumped = 0

    for c in archived:
        # must be a timer + have a cadence label
        label_names = [id_to_name.get(lid,"").lower() for lid in c.get("idLabels",[])]
        if timer_label_name not in label_names:
            continue

        cadence_days = None
        for lname in label_names:
            if lname in cadences:
                cadence_days = cadences[lname]
                break
        if not cadence_days:
            continue

        due_utc = parse_due_utc(c.get("due"))
        now_utc = datetime.now(ZoneInfo("UTC"))
        if not due_utc or now_utc < due_utc:
            log(f"skip archived '{c['name']}' (not due yet)")
            continue

        # due → bring it back for today
        log(f"UNARCHIVE → '{c['name']}' (due reached)")
        set_card_closed(c["id"], False)
        move_card_to_list(c["id"], list_id)
        recovered += 1

        # bump its due to next cycle right away
        new_due = next_due_utc(cadence_days, timer_hour)
        update_card_due(c["id"], new_due)
        bumped += 1
        log(f"bumped '{c['name']}' → next due {new_due}")

    print(f"Timers processed OK — recovered: {recovered}, bumped: {bumped}")

if __name__ == "__main__":
    main()
