# Life-Scheduler

A Trello-based personal productivity system that automatically manages recurring tasks and daily routines using timer cards and Butler automation.

## Overview

Life-Scheduler is a Python-based automation tool that integrates with Trello to create a sophisticated personal task management system. It combines recurring "timer" tasks with daily routine automation to help you maintain consistent habits and workflows.

### Key Features

- **Automated Timer Recovery**: Recovers archived timer cards only when they're actually due
- **Smart Scheduling**: Automatically reschedules recurring tasks based on configurable cadences
- **Daily Routine Automation**: Creates daily habit cards automatically via Trello Butler
- **Timezone Support**: Handles timezone conversions properly for global usage
- **Duplicate Prevention**: Cleans up legacy task duplicates automatically

## How It Works

### Timer System
The core concept revolves around "timer" cards that represent recurring tasks:

1. **Timer Cards**: Tasks labeled with `timer` and a cadence label (e.g., `every-2-days`)
2. **Due Date Management**: Cards are automatically archived when completed and recovered when due
3. **Smart Recovery**: Only overdue cards are brought back from archive
4. **Automatic Rescheduling**: When recovered, cards get new due dates based on their cadence

### Daily Routine Automation
Using Trello Butler, the system automatically creates daily habit cards like:
- Breakfast
- Wash Teeth (Morning/Night)
- Lunch
- Work blocks
- Exercise
- Shower

## Installation

### Prerequisites

- Python 3.9+
- A Trello account with API access
- Trello Butler Power-Up enabled on your board

### Required Python Packages

```bash
pip install requests pyyaml
```

### Environment Setup

1. **Get Trello API Credentials**:
   - Go to https://trello.com/app-key
   - Copy your API Key
   - Generate a token with read/write permissions

2. **Set Environment Variables**:
   ```bash
   export TRELLO_API_KEY="your_api_key_here"
   export TRELLO_API_TOKEN="your_token_here"
   export TRELLO_BOARD_ID="your_board_id"  # Optional if using LIST_ID
   export TRELLO_LIST_ID="your_list_id"    # Optional if using BOARD_ID
   ```

3. **Create Configuration File** (`config.yml`):
   ```yaml
   timezone: "Europe/Bucharest"
   list_name: "Daily Log"
   
   labels:
     timer: "timer"
   
   cadences:
     every-2-days:
       days: 2
     every-3-days:
       days: 3
     every-4-days:
       days: 4
   
   defaults:
     timer_hour: "03:00"
   ```

## Configuration

### config.yml Structure

| Setting | Description | Default |
|---------|-------------|---------|
| `timezone` | Your local timezone | `"Europe/Bucharest"` |
| `list_name` | Name of your main task list | `"Daily Log"` |
| `labels.timer` | Label name for timer cards | `"timer"` |
| `cadences` | Recurring intervals for tasks | See example |
| `defaults.timer_hour` | Time when timer cards become due | `"03:00"` |

### Cadence Configuration

Define how often different types of tasks repeat:

```yaml
cadences:
  every-2-days:
    days: 2
  every-3-days:
    days: 3
  every-4-days:
    days: 4
  weekly:
    days: 7
  bi-weekly:
    days: 14
```

## Usage

### Running the Timer Script

```bash
python trello-timers.py
```

### Verbose Mode (for debugging)

```bash
VERBOSE=1 python trello-timers.py
```

### Setting Up Butler Automation

In Trello Butler, create this daily automation rule:

```
every day at 2:00 am, 
archive all the cards in list "Daily Log", 
archive all the cards in list "DONE", 
create a new card with title "Breakfast" in list "Daily Log" and add the dark purple "daily" label, 
create a new card with title "Wash Teeth Morning" in list "Daily Log" and add the dark purple "daily" label, 
create a new card with title "lunch" in list "Daily Log" and add the dark purple "daily" label, 
create a new card with title "C&Algos - 1hr" in list "Daily Log" and add the dark purple "daily" label, 
create a new card with title "Shower" in list "Daily Log" and add the dark purple "daily" label, 
and create a new card with title "Wash Teeth Night" in list "Daily Log" and add the dark purple "daily" label
```

### Creating Timer Cards

1. Create a card with your task name
2. Add the `timer` label
3. Add a cadence label (e.g., `every-2-days`)
4. Set an initial due date
5. When you complete the task, archive the card

The system will automatically bring it back when it's due again.

## Trello Board Setup

### Required Lists
- **Daily Log**: Main working list for current tasks
- **DONE**: Completed tasks (optional, for Butler cleanup)

### Required Labels
- **timer**: Purple label for recurring timer tasks
- **daily**: Dark purple label for daily habit cards
- **every-2-days**: Cadence label for 2-day intervals
- **every-3-days**: Cadence label for 3-day intervals
- **every-4-days**: Cadence label for 4-day intervals

### Recommended Workflow

1. **Morning**: Check Daily Log for today's tasks
2. **Throughout Day**: Complete tasks and archive when done
3. **Evening**: Timer cards stay archived until due
4. **Automatic**: Butler creates fresh daily cards at 2 AM
5. **Automatic**: Timer script recovers overdue recurring tasks

## Advanced Features

### Custom Timer Hours
Set when timer cards become "due" by adjusting `timer_hour` in config:

```yaml
defaults:
  timer_hour: "06:00"  # Cards become due at 6 AM
```

### Timezone Handling
The system properly handles timezone conversions. Set your local timezone:

```yaml
timezone: "America/New_York"  # or any valid timezone
```

### Duplicate Cleanup
The script automatically removes duplicate cards ending with "– 1h" or "- 1h" that aren't proper timer cards.

## Scheduling

### Cron Setup
Run the timer script automatically with cron:

```bash
# Add to your crontab (crontab -e)
*/15 * * * * cd /path/to/life-scheduler && python trello-timers.py >/dev/null 2>&1
```

This runs every 15 minutes to check for overdue timer cards.

## Troubleshooting

### Common Issues

1. **"Missing Trello creds" Error**
   - Ensure `TRELLO_API_KEY` and `TRELLO_API_TOKEN` are set
   - Check that your token has read/write permissions

2. **"List not found" Error**
   - Verify `TRELLO_BOARD_ID` points to correct board
   - Ensure the list name in config matches your Trello list exactly

3. **Timer Cards Not Recovering**
   - Run with `VERBOSE=1` to see debug output
   - Check that cards have both `timer` and cadence labels
   - Verify due dates are actually in the past

4. **Timezone Issues**
   - Ensure your timezone string is valid (use `pytz.all_timezones` to check)
   - Remember that due dates are stored in UTC in Trello

### Debug Mode

Run with verbose logging to see exactly what's happening:

```bash
VERBOSE=1 python trello-timers.py
```

This shows:
- Current time and timezone
- Cards being processed
- Due date comparisons
- Why cards are skipped or recovered

## Output

The script provides clear status output:

```
Timers OK — recovered:2, dueReset:2, bumped:2, skipped:1, cleanedClones:0
```

- **recovered**: Timer cards brought back from archive
- **dueReset**: Cards that got new due dates
- **bumped**: Cards moved to active list
- **skipped**: Cards not yet due
- **cleanedClones**: Duplicate cards removed

## Integration Tips

### With Other Tools
- **Calendar Sync**: Use Trello's calendar Power-Up to see due dates
- **Mobile Access**: Use Trello mobile app for on-the-go task completion
- **Notifications**: Enable Trello notifications for due date reminders

### Workflow Optimization
- **Time Blocking**: Create timer cards for focused work sessions
- **Habit Tracking**: Use daily cards for habit formation
- **Project Management**: Combine with regular Trello cards for larger projects

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.
