# Life-Scheduler

Life-Scheduler is a Trello-based automation that combines **Butler rules** and a **Python script (ran via GitHub Actions)** to keep daily rituals and recurring “block” tasks self-managing.

---

## Overview

- **Ritual cards (Butler)**
  - Every night Butler archives yesterday’s tasks and clones two templates into **Daily Log**:
    - 🌅 **Morning Ritual** – start-of-day checklist (e.g., breakfast, plan, quick cleaning)
    - 🌙 **Evening Ritual** – end-of-day checklist (e.g., dinner, shower, review & plan)

- **Recurring blocks (Life-Scheduler script)**
  - The script scans archived cards labeled `timer` **and** a cadence label (e.g., `Daily`, `every-3-days`, `weekly`).
  - If a card is **overdue**, it is **unarchived**, moved to **Daily Log**, and assigned the **next due** based on the cadence (at `defaults.timer_hour`).
  - Optional metrics are written to CSV.

**Result:** Each day your **Daily Log** shows Morning Ritual → the **blocks actually due today** → Evening Ritual.

---

## How It Works

```
00:00–02:00   Butler night routine
 ├─ Archive yesterday’s lists (e.g., "Daily Log", "DONE")
 └─ Copy ritual templates → "Morning Ritual", "Evening Ritual"

On schedule   GitHub Actions → trello-timers.py
 ├─ Scan archived cards
 ├─ Find cards labeled:  timer  +  <cadence>
 ├─ If overdue → unarchive, move to "Daily Log", set next due (HH:MM)
 └─ (Optional) append metrics to CSV
```

---

## Repo Layout

```
.github/workflows/   # GitHub Actions workflow(s)
metrics/             # CSV metrics output (optional)
config.yml           # labels, cadences, timezone, metrics
requirements.txt     # Python deps: requests, PyYAML
trello-timers.py     # the automation script
```

---

## Installation

### Prerequisites
- Python 3.9+
- Trello account with API access
- Trello **Butler** Power-Up enabled on your board

### Install deps
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Setup

1) **Get Trello API credentials**
   - https://trello.com/app-key → copy **API key**
   - Generate a **token** with read/write

2) **Set environment variables** (locally or as GitHub Actions secrets)
```bash
export TRELLO_API_KEY="your_api_key"
export TRELLO_API_TOKEN="your_token"
# Either provide the board (script finds list by name)…
export TRELLO_BOARD_ID="your_board_id"
# …or pass the list directly instead:
# export TRELLO_LIST_ID="your_list_id"
```

3) **Create `config.yml`**
```yaml
timezone: "Europe/Bucharest"
list_name: "Daily Log"

labels:
  timer: "timer"

cadences:
  Daily:         { days: 1 }
  every-3-days:  { days: 3 }
  weekly:        { days: 7 }
  monthly:       { days: 30 }

defaults:
  timer_hour: "03:00"

metrics:
  enable: true
  csv_path: "metrics/blocks.csv"
```

---

## Configuration

| Key                   | Description                                        | Default              |
|-----------------------|----------------------------------------------------|----------------------|
| `timezone`            | Local timezone (due calc & metrics timestamps)     | `"Europe/Bucharest"` |
| `list_name`           | Target list where revived cards are placed         | `"Daily Log"`        |
| `labels.timer`        | Label name that marks a card as a timer            | `"timer"`            |
| `cadences`            | Map of cadence label → `{ days: N }`               | —                    |
| `defaults.timer_hour` | Time of day to set **next** due date               | `"03:00"`            |
| `metrics.enable`      | Append events to CSV                               | `false`              |
| `metrics.csv_path`    | Relative path to CSV                               | `"metrics/blocks.csv"` |

> **Note:** Cadence **label text in Trello must match** the keys under `cadences` (e.g., `Daily`, `every-3-days`).

---

## Usage

Run manually:
```bash
python trello-timers.py
```

Verbose/debug:
```bash
VERBOSE=1 python trello-timers.py
```

**What you’ll see in verbose mode:** current UTC time, which archived cards were found, due comparisons, revived vs. skipped, and cleanup actions.

---

## GitHub Actions

Create `.github/workflows/life-scheduler.yml`:

```yaml
name: life-scheduler
on:
  schedule:
    - cron: "*/15 * * * *"   # run every 15 minutes
  workflow_dispatch: {}

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Life-Scheduler
        env:
          TRELLO_API_KEY:   ${{ secrets.TRELLO_API_KEY }}
          TRELLO_API_TOKEN: ${{ secrets.TRELLO_API_TOKEN }}
          TRELLO_BOARD_ID:  ${{ secrets.TRELLO_BOARD_ID }}  # or TRELLO_LIST_ID
          CONFIG_PATH:      config.yml
          VERBOSE:          "0"
        run: python trello-timers.py
```

Add the following **repo secrets**: `TRELLO_API_KEY`, `TRELLO_API_TOKEN`, and either `TRELLO_BOARD_ID` or `TRELLO_LIST_ID`.

---

## Trello Setup

### Lists
- **Daily Log** — where revived tasks appear
- **DONE** — optional (for Butler nightly archiving)

### Labels
- `timer` — add to all recurring cards
- One cadence label per interval — must match `config.yml` keys (e.g., `Daily`, `every-3-days`, `weekly`)

### Ritual Cards (Butler)
Keep ritual cards **without** the `timer` label. Create two **template** cards with checklists:
- **Morning Ritual**
- **Evening Ritual**

Example Butler rule:
```
every day at 2:00 am,
archive all the cards in list "Daily Log",
archive all the cards in list "DONE",
copy the card "Morning Ritual (TEMPLATE)" to the top of list "Daily Log",
copy the card "Evening Ritual (TEMPLATE)" to the bottom of list "Daily Log"
```

### Timer Cards (the “blocks”)
1) Create a card (e.g., `Web C#`, `VTB alert 1h`, `Wash hair`).  
2) Add labels: `timer` + cadence (e.g., `Daily`, `every-3-days`).  
3) Set an **initial due date**.  
4) When completed, **archive** it. The script revives it **only when due**, moves it to **Daily Log**, and sets the **next due** at `timer_hour`.

---

## Troubleshooting

- **“Missing Trello creds”** → Ensure API key/token are set (local env or Actions secrets).
- **“List not found”** → If using `TRELLO_BOARD_ID`, make sure `list_name` in config matches exactly.
- **Card never returns** → It must have `timer` + a matching cadence label **and** a past due date.
- **Timezone quirks** → Trello stores due dates in UTC; the script converts using `timezone`.

Verbose logs:
```bash
VERBOSE=1 python trello-timers.py
```

---

## License

MIT
