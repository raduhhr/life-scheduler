```markdown
# Life-Scheduler

Life-Scheduler is a Trello-based automation system that combines **Butler rules** and a **Python script (run via GitHub Actions)** to keep your daily routine and recurring tasks self-managing.

---

## Overview

- **Ritual cards (Butler)**  
  Every night, Butler archives yesterday’s tasks and clones two ritual templates into your **Daily Log**:  
  - 🌅 **Morning Ritual** – start-of-day checklist (e.g., breakfast, planning, quick cleaning)  
  - 🌙 **Evening Ritual** – end-of-day checklist (e.g., dinner, shower, review day, plan tomorrow)  

- **Recurring blocks (Life-Scheduler script)**  
  The Python script checks your Trello board for archived cards labeled with `timer` and a cadence label (e.g., `Daily`, `every-3-days`, `weekly`).  
  - If a card’s due date has passed, it is **unarchived**, moved to **Daily Log**, and assigned a new due date.  
  - If it’s not due yet, it stays archived.  
  - Optional metrics are logged to CSV for tracking.

**Result:** Each day your **Daily Log** contains:
- A **Morning Ritual** card to start the day,  
- The **recurring blocks** that are actually due,  
- An **Evening Ritual** card to close the day.  

---

## How It Works

```

00:00–02:00   Butler night routine
├─ Archives yesterday’s lists
└─ Copies ritual templates:
• Morning Ritual
• Evening Ritual

On schedule   GitHub Actions → trello-timers.py
├─ Scans archived cards
├─ Finds cards labeled:  timer  +  <cadence>
├─ If overdue → unarchive, move to Daily Log, reset due
└─ Logs optional metrics

````

---

## Installation

### Prerequisites
- Python 3.9+
- A Trello account with API access
- Trello Butler Power-Up enabled

### Python packages
```bash
pip install requests pyyaml
````

### Environment setup

1. **Get Trello API credentials**

   * Go to [https://trello.com/app-key](https://trello.com/app-key)
   * Copy your API key and generate a token

2. **Set environment variables**

   ```bash
   export TRELLO_API_KEY="your_api_key_here"
   export TRELLO_API_TOKEN="your_token_here"
   export TRELLO_BOARD_ID="your_board_id"  # or TRELLO_LIST_ID
   ```

3. **Create config.yml**

   ```yaml
   timezone: "Europe/Bucharest"
   list_name: "Daily Log"
   labels:
     timer: "timer"

   cadences:
     Daily:        { days: 1 }
     every-3-days: { days: 3 }
     weekly:       { days: 7 }

   defaults:
     timer_hour: "03:00"

   metrics:
     enable: true
     csv_path: "metrics/blocks.csv"
   ```

---

## Configuration

| Setting               | Description                           | Default              |
| --------------------- | ------------------------------------- | -------------------- |
| `timezone`            | Your local timezone                   | `"Europe/Bucharest"` |
| `list_name`           | Trello list where due cards are moved | `"Daily Log"`        |
| `labels.timer`        | Label name for timer cards            | `"timer"`            |
| `cadences`            | Recurrence intervals (days)           | Custom               |
| `defaults.timer_hour` | Time new due dates are set            | `"03:00"`            |
| `metrics`             | Enable CSV logging                    | `false`              |

Cadence example:

```yaml
cadences:
  every-2-days: { days: 2 }
  every-3-days: { days: 3 }
  weekly:       { days: 7 }
  monthly:      { days: 30 }
```

---

## Usage

Run manually:

```bash
python trello-timers.py
```

Debug mode:

```bash
VERBOSE=1 python trello-timers.py
```

---

## GitHub Actions setup

`.github/workflows/trello-timers.yml`:

```yaml
name: life-scheduler
on:
  schedule:
    - cron: "*/15 * * * *"
  workflow_dispatch: {}

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python trello-timers.py
        env:
          TRELLO_API_KEY:   ${{ secrets.TRELLO_API_KEY }}
          TRELLO_API_TOKEN: ${{ secrets.TRELLO_API_TOKEN }}
          TRELLO_BOARD_ID:  ${{ secrets.TRELLO_BOARD_ID }}
          CONFIG_PATH:      config.yml
          VERBOSE:          "0"
```

---

## Trello Setup

### Lists

* **Daily Log** – where active tasks appear
* **DONE** – optional cleanup list

### Labels

* `timer` – all recurring cards
* Cadence labels – must match `cadences` in config (`Daily`, `every-3-days`, …)

### Ritual cards

Butler clones two templates daily:

* **Morning Ritual** (checklist)
* **Evening Ritual** (checklist)

### Timer cards

1. Create card (e.g., `Job Hunting`).
2. Add labels: `timer` + `every-3-days`.
3. Set initial due date.
4. Archive when completed — script revives when due.

---

## Troubleshooting

* **Missing creds** → Check API key/token are set in secrets.
* **List not found** → Ensure `list_name` matches exactly.
* **Cards not reviving** → Must have `timer` + cadence label + past due date.
* **Timezone issues** → Trello stores UTC, script converts with your config.

Debug logs with:

```bash
VERBOSE=1 python trello-timers.py
```

---

