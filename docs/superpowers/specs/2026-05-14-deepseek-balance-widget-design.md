# DeepSeek Balance Desktop Widget — Design Spec

## Overview

A floating desktop widget (Windows) that displays DeepSeek API account balance in real time. Micro-panel style (user selected option D), built with Python + PySide6.

## Data Source

- **Endpoint**: `GET https://api.deepseek.com/user/balance`
- **Auth**: `Authorization: Bearer <API_KEY>`
- **Response**: `{ is_available, balance_infos: [{ currency, total_balance, granted_balance, topped_up_balance }] }`
- **Refresh**: QTimer every 5 minutes

## Architecture

```
[PySide6 GUI] ──→ [requests HTTP] ──→ [DeepSeek API]
     ↑                    │
     └── QTimer (5min) ───┘
```

- Single process, no backend server
- API key stored in Windows Credential Manager (keyring) or fallback to local config file
- PyInstaller for single .exe distribution (~30MB)

## UI Components

1. **Main panel** — frameless, always-on-top, draggable floating window
   - Total balance (large number, green when available, red when low)
   - Granted balance vs topped-up balance breakdown
   - Last refresh timestamp
   - Status indicator (OK / error)

2. **System tray** — icon + menu
   - Show/Hide panel
   - Refresh now
   - Settings (API key, refresh interval)
   - Quit

3. **Settings dialog** — first-run API key input, optional refresh interval customization

## Error Handling

- API failure → panel shows error state (greyed out) with message
- Network timeout (10s) → retry on next interval
- Invalid API key → prompt to re-enter

## Key Dependencies

- PySide6 — GUI framework
- requests — HTTP client
- keyring — secure credential storage (optional fallback)
- PyInstaller — packaging

## Scope

Single-user desktop tool. No multi-account, no cloud sync, no historical charts in v1.
