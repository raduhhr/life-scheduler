#!/usr/bin/env python3
import os, sys, time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import yaml

API = "https://api.trello.com/1"

# --- Secrets ---
KEY   = (os.environ.get("TRELLO_API_KEY")  or os.environ.get("TRELLO_KEY")  or "").strip()
TOKEN = (os.environ.get("TRELLO_API_TOKEN") or os.environ.get("TRELLO_TOKEN") or "").strip()
if not KEY or not TOKEN:
    print("Missing Trello creds: set TRELLO_API_KEY/TRELLO_API_TOKEN (or TRELLO_KEY/TRELLO_TOKEN).", file=sys.stderr)
    sys.exit(1)

# --- Wiring ---
BOARD_ID = os.environ.get("TRELLO_BOARD_ID")
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
    r = requests.request(method, f"{API}{path}", params=params, **kwargs)
    if r.status_code == 429:
        time.sleep(1.0)
        r = requests.request(method, f"{API}{path}", params=params, **kwargs)
    r.raise_for_status()
    if r.headers.get("Content-Type","").startswith("application/json"):
        return r.json()
    return r.text

def find_list_id():
    if LIST_ID: return LIST_ID
    if not BOARD_ID: raise SystemExit("Provide TRELLO_LIST_ID or TRELLO_BOARD_ID env var.")
    for lst in trello("GET", f"/boards/{BOARD_ID}/lists"):
        if lst["name"] == CFG.get("list_name","Daily Log"):
            return lst["id"]
    raise SystemExit("List not found by name on BOARD_ID.")

def board_label_maps(board_id):
    labels = trello("GET", f"/boards/{board_id}/labels")
    id_to_name = {lbl["id"]: (lbl.get("name") or "").lower() for lbl in labels}
    return id_to_name

def board_cards(board_id, filter_mode="closed"):
    return trello("GET", f"/boards/{board_id}/cards",
                  params={"fields":"name,idLabels,due,closed,idList,dueComplete",
                          "filter": filter_mode})

def list_cards(list_id):
    return trello("GET", f"/lists/{list_id}/cards",
                  params={"fields":"name,idLabels,due,closed,idList,dueComplete","filter":"open"})

def parse_due_utc(due):
    if not due: return None
    base = due.replace("Z","").split(".")[0]
    return datetime.fromisoformat(base).replace(tzinfo=ZoneInfo("UTC"))

def next_due_utc(days: int, hour: str) -> str:
    hh, mm = [int(x) for x in hour.split(":")]
    d = (datetime.now(TZ).date() + timedelta(days=days))
    dt_local = datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ)
    return dt_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def set_card_closed(card_id, closed: bool):
    trello("PUT", f"/cards/{card_id}", params={"closed": str(closed).lower()})

def move_card_to_list(card_id, list_id):
    trello("PUT", f"/cards/{card_id}", params={"idList": list_id})

def set_due_complete(card_id, completed: bool):
    trello("PUT", f"/cards/{card_id}", params={"dueComplete": str(completed).lower()})

def set_due_and_uncomplete(card_id, due_iso):
    # critical: set due and dueComplete=false IN THE SAME REQUEST
    trello("PUT", f"/cards/{card_id}", params={"due": due_iso, "dueComplete": "false"})

def is_card_overdue(due_utc, now_utc):
    """Check if a card is actually overdue (past its due date)"""
    if not due_utc:
        return False
    return now_utc >= due_utc

def main():
    list_id = find_list_id()
    lst = trello("GET", f"/lists/{list_id}")
    board_id = lst["idBoard"]
    id_to_name = board_label_maps(board_id)

    timer_label = CFG["labels"]["timer"].lower()
    cadences = {k.lower(): int(v["days"]) for k,v in CFG.get("cadences", {}).items()}
    timer_hour = CFG.get("defaults", {}).get("timer_hour","03:00")

    recovered = bumped = reset_due = cleaned = skipped = 0
    now_utc = datetime.now(ZoneInfo("UTC"))

    # 1) recover only overdue archived timer cards
    for c in board_cards(board_id, filter_mode="closed"):
        labels = [id_to_name.get(lid,"").lower() for lid in c.get("idLabels",[])]
        if timer_label not in labels:
            continue
        
        cadence_days = next((cadences[l] for l in labels if l in cadences), None)
        if not cadence_days:
            continue

        due_utc = parse_due_utc(c.get("due"))
        
        # Only recover if the card is actually overdue
        if not is_card_overdue(due_utc, now_utc):
            log(f"SKIP (not due yet) → '{c['name']}' due: {due_utc}")
            skipped += 1
            continue

        log(f"UNARCHIVE (overdue) → '{c['name']}' was due: {due_utc}")
        set_card_closed(c["id"], False)
        move_card_to_list(c["id"], list_id)
        recovered += 1

        # set new due AND mark incomplete atomically
        new_due = next_due_utc(cadence_days, timer_hour)
        set_due_and_uncomplete(c["id"], new_due)
        bumped += 1
        reset_due += 1
        log(f"bumped + dueComplete=false → '{c['name']}' → {new_due}")

    # 2) safety: archive legacy clones like "… – 1h" / "... - 1h" that are not timer cards
    suffixes = ("– 1h", "- 1h")
    for c in list_cards(list_id):
        if any(c["name"].strip().endswith(s) for s in suffixes):
            labels = [id_to_name.get(lid,"").lower() for lid in c.get("idLabels",[])]
            if timer_label not in labels:
                set_card_closed(c["id"], True)
                cleaned += 1
                log(f"cleanup clone → '{c['name']}'")

    print(f"Timers OK — recovered:{recovered}, dueReset:{reset_due}, bumped:{bumped}, skipped:{skipped}, cleanedClones:{cleaned}")

if __name__ == "__main__":
    main()
