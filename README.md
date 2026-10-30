# SMS2Clip

**iPhone SMS → ntfy → Windows verification-code clipboard**

[中文说明](README.zh-CN.md)

> **Attribution:** This is an unofficial secondary development built on [ntfy](https://github.com/binwiederhier/ntfy). It also uses an iPhone Shortcut adapted from the original created and shared by **谢週五**. See [Credits and attribution](CREDITS.md).

SMS2Clip is a small Windows desktop app that receives SMS forwarded from an iPhone through [ntfy](https://ntfy.sh/) and puts the verification code into the Windows clipboard.

Automatic code copying is enabled by default: the app copies the **full SMS** first, then the **verification code** after a short delay. You can turn this off in the app; the notification still provides a **Copy** button for the detected code.

![SMS2Clip English UI](docs/screenshot-en.png)

## Features

- Desktop GUI — no command line required.
- Background tray icon on the Windows notification area.
- Right-click tray menu: **Open manager**, **Start listening**, **Stop listening**, **Exit**.
- Closing the window hides it to the tray instead of stopping the listener.
- Opening SMS2Clip automatically starts listening when no listener is running.
- Clicking the EXE again brings the existing manager to the front instead of opening a second window.
- Three startup modes: manual, manager at login, or a headless background service at login.
- Connection details are hidden by default and only shown after clicking **Show connection settings**.
- Chinese / English UI switch in the top-right corner.
- ntfy JSON-stream subscription with automatic reconnect and message de-duplication.
- Optional automatic verification-code copying, with a full-SMS fallback.
- Windows clipboard history friendly: full SMS first, verification code last.
- Full-SMS Windows toast notifications with a copy-code action.
- Persistent history of every received ntfy message, including messages without a code.
- Extraction for exact 4- or 6-digit codes, full-width digits, spaced/hyphenated codes, and Google-style codes such as `G-123456` or `G-123-456`.
- Public `ntfy.sh`, self-hosted ntfy, Bearer token, and Basic Auth support.
- Single-file Windows executable built with PyInstaller.

![Test and log tab](docs/screenshot-tools.png)

## Quick-add iPhone Shortcut

A public iCloud Shortcut is available here:

https://www.icloud.com/shortcuts/2e72a660dec84fd9b8c7abd92d42043f

The app also has an **iPhone Shortcut** button in the top-right corner. It opens a QR code dialog that you can scan with the iPhone Camera.

![QR code for the iPhone Shortcut](docs/screenshot-shortcut.png)

Import steps:

1. Scan the QR code with the iPhone Camera, or open the link in Safari.
2. Tap **Add Shortcut** / **添加快捷指令**.
3. Keep the server as `https://ntfy.sh` (or enter your self-hosted server).
4. Paste the **Topic** copied from SMS2Clip.
5. Finish adding the shortcut. A new automation named **When I receive a message containing “【”** appears under **Shortcuts → Automation**. It is **off by default**, so turn on its switch manually to enable it.
6. If you only want verification-code SMS, edit the automation condition to `验证码` or `校验码`.

The Shortcut posts JSON to ntfy. It is a project-specific adaptation of the public ntfy notification Shortcut originally created by **谢週五**; see [Credits and attribution](CREDITS.md). If you import it twice, delete the duplicate automation.

## Quick start

### 1. Get the executable

Build it locally:

```powershell
cd D:\CodePlayground\Python\SMS2Clip
.\build.ps1
```

The output is:

```text
D:\CodePlayground\Python\SMS2Clip\SMS2Clip.exe
```

You can upload that file as a GitHub Release asset. The executable is intentionally ignored by Git so the repository does not carry a large binary.

### 2. Start the app

Double-click `SMS2Clip.exe`.

On first launch, the app generates a random ntfy topic. Click **Show connection settings** to reveal the **Publish URL** needed by the iPhone Shortcut.

Opening SMS2Clip automatically starts listening. The status changes to **Listening**, and a tray icon appears in the Windows notification area. If the listener is already running, the app reuses it instead of starting a duplicate.

### 3. Configure the iPhone Shortcut

1. Open **Shortcuts** → **Automation** → `+`.
2. Choose the **Message** trigger.
3. Set the condition to **Message contains** `verification code` (or a local keyword such as `验证码` / `校验码`), and choose **Run Immediately**.
4. Add **Get Text from Input** to turn the SMS into plain text.
5. Add **Get Contents of URL**:
   - URL: the **Publish URL** shown in the app
   - Method: `POST`
   - Request Body: `Text`, using the SMS text
   - Header: `Content-Type` = `text/plain; charset=utf-8`
6. Save the automation.

The app also includes a built-in **Help** dialog with the same steps.

### 4. Send a test SMS

In the app, click **Send test SMS**.

The app publishes:

```text
验证码为 482913，5分钟内有效。
```

A few seconds later:

- the clipboard becomes `482913`;
- `Win+V` should show the code and the full SMS.

## Clipboard behavior

**Auto-copy verification code** is enabled by default. On each incoming SMS:

1. The **full SMS** is copied first.
2. After a short delay, the **verification code** is copied.

The default delay is `350 ms`. You can change it under **Advanced** if your clipboard manager needs more time.

When **Auto-copy verification code** is disabled, only the full SMS is copied. The notification still includes a **Copy** button for the detected code, so you can choose when to copy it.

Changing this option while the listener is running restarts the listener automatically so the new behavior takes effect immediately.

For the full-SMS entry to remain in history, enable:

**Windows Settings → System → Clipboard → Clipboard history**

If you do not want verification codes synchronized to other devices, disable cross-device clipboard sync.

## Windows notifications

Every incoming message uses the same notification layout:

- title: **SMS received**
- body: the complete SMS
- button: **Copy** when a verification code was found

The **Copy** button copies the detected verification code to the clipboard. It does not replace the full-SMS notification. If no code is found, the notification is shown without a button.

The auto-copy setting is stored in `config.json` as `auto_copy_code` (`true` or `false`).

## Message history

The **History** tab stores every received ntfy message, whether or not a verification code was found.

- Click any record to view the complete message.
- When a code was detected, use **Copy verification code** below the message.
- The latest 200 records are kept in `%APPDATA%\SMS2Clip\history.json` and persist across restarts.
- Use **Clear history** to delete stored messages.

![Message history](docs/screenshot-history.png)

History is stored locally as plain text. Clear it when using a shared Windows account or when messages may contain sensitive information.

## Verification-code extraction

The extractor accepts exact standalone codes such as:

```text
1234
123456
G-123456
G-123-456
验证码：123456
校验码：12-34
```

It rejects a code embedded inside a longer number:

```text
1234567     → no match
G-1234-567  → no match
```

It also avoids common false positives such as phone numbers, dates, amounts, tracking numbers, and order IDs.

Try the extraction logic without starting the listener:

```powershell
python -m SMS2Clip --extract "Your Google verification code is G-123-456."
```

## Tray and startup modes

Use **Startup** in the app to choose one of three modes:

- **Do not auto-start**: nothing starts at sign-in.
- **Run in tray after sign-in**: show a tray icon and automatically begin listening; double-click the icon to open the manager.
- **Run silently after sign-in**: start only the listener, with no manager window or tray icon. Open `SMS2Clip.exe` whenever you need to manage it.

Selecting **Run silently after sign-in** asks for confirmation first. After confirming, the current manager closes while the listener keeps running. If the listener is not already running, it is started first. Open `SMS2Clip.exe` whenever you need to manage it again.

The startup entry is stored in the current user's Windows `Run` registry key.

> **Why not a service in `services.msc`?** Traditional Windows services run in Session 0 and cannot access the signed-in user's clipboard or desktop toast notifications. SMS2Clip therefore uses a per-user, interactive background process, which preserves clipboard and notification behavior without starting the manager UI.

## Language switch

Use the button in the top-right corner:

- `English` switches from Chinese to English.
- `中文` switches from English to Chinese.

The selected language is saved in the user configuration file under `%APPDATA%\SMS2Clip`. Switching language also restarts a running listener so notifications use the new language.

## Configuration

When running the packaged `SMS2Clip.exe`, settings are stored in:

```text
%APPDATA%\SMS2Clip\config.json
```

`history.json`, `state.json`, and `logs\sms2clip.log` are stored in the same user directory. This works even if the exe is placed in a read-only folder such as `Program Files`.

For source runs, `config.json` stays in the project root. On first frozen run, an existing config next to the exe is copied automatically to `%APPDATA%\SMS2Clip`.

When editing hidden connection settings, use **Save connection settings**. If the listener is running, saving restarts it automatically to apply the new server or topic.

The PowerShell helper scripts are intended for source/development runs. When using `SMS2Clip.exe`, use the in-app **Startup** selector; it stores the chosen mode with the per-user config path.

The configuration file looks like this:

```json
{
  "server": "https://ntfy.sh",
  "topic": "replace-with-a-long-random-topic",
  "token": "",
  "username": "",
  "password": "",
  "since": "",
  "clipboard_gap_ms": 350,
  "state_file": "state.json",
  "log_file": "logs/sms2clip.log",
  "reconnect_min_seconds": 1,
  "reconnect_max_seconds": 60,
  "language": "en",
  "auto_copy_code": true
}
```

Useful fields:

| Field | Meaning |
| --- | --- |
| `server` | `https://ntfy.sh` or your self-hosted ntfy server |
| `topic` | Random topic shared by the iPhone Shortcut and the app |
| `token` | Bearer token for a protected ntfy topic |
| `username` / `password` | Basic Auth alternative to a token |
| `since` | Leave empty for live messages only; a message ID is used automatically after the first message |
| `clipboard_gap_ms` | Delay between copying the full SMS and the code |
| `language` | `en` or `zh-CN` |
| `auto_copy_code` | Automatically copy the detected verification code (`true` or `false`) |

## Build from source

Requirements:

- Windows 10/11
- Python 3.10+
- `pystray`, Pillow, qrcode, windows-toasts, and pywin32 for the tray, QR code, notifications, and Windows notification identity
- PyInstaller for packaging

Install dependencies:

```powershell
python -m pip install -e .
python -m pip install pyinstaller
```

Run the GUI from source:

```powershell
python -m SMS2Clip.gui
```

Build the executable:

```powershell
.\build.ps1
```

The build script:

- installs PyInstaller and runtime dependencies;
- bundles the icon and assets;
- produces `dist\SMS2Clip.exe`;
- copies the final executable to `SMS2Clip.exe` in the project root.

## Development

Run tests:

```powershell
python -m unittest discover -s tests -v
```

Lint and format:

```powershell
ruff check SMS2Clip tests
ruff format --check SMS2Clip tests
```

The test suite covers extraction rules, clipboard ordering, ntfy parsing, publishing, state persistence, service lifecycle, toast action callbacks, i18n, and GUI smoke behavior.

## CLI mode

The desktop app is the primary interface, but the CLI remains available for debugging and advanced use:

```powershell
python -m SMS2Clip --config .\config.json --check
python -m SMS2Clip --config .\config.json --send "验证码为 482913，5分钟内有效。" --title "SMS"
python -m SMS2Clip --config .\config.json --service
```

## Security notes

- A public ntfy topic is effectively a password. Use a long random topic.
- SMS contents and verification codes transit the ntfy server. For sensitive use, self-host ntfy and enable authentication.
- The log records only message IDs and whether a code was found; it does not log SMS content.
- Clipboard history may be synchronized by Windows. Disable cross-device sync if you do not want codes on other devices.

## Credits and attribution

- [ntfy](https://github.com/binwiederhier/ntfy): This project is an unofficial secondary development built on ntfy's open-source publish/subscribe capabilities. It is not affiliated with or endorsed by the ntfy project or its maintainers.
- **谢週五**: The bundled iPhone Shortcut is adapted and further developed from a public ntfy notification Shortcut originally created by 谢週五. The adapted version is tailored to this project's server/topic configuration and verification-code workflow.

Full attribution: [CREDITS.md](CREDITS.md). If any attribution is inaccurate or incomplete, please open an issue so it can be corrected.

## Project layout

```text
SMS2Clip/
  entry.py          Single-exe dispatcher: GUI or service
  gui.py            Tkinter desktop UI and tray integration
  i18n.py           Chinese/English translations
  app.py            Message → clipboard business logic
  clipboard.py      Windows clipboard writer
  extractor.py      Verification-code extraction
  ntfy_client.py    ntfy publish/subscribe
  service.py        Background reconnect loop
  history.py        Persistent received-message history
  single_instance.py Single manager-instance guard
  state.py          Last message ID persistence
  startup.py        Per-user startup mode registry
  notifications.py  Windows toast notifications and action buttons
  runtime.py        Child process and PID helpers
  paths.py          Per-user config, state, and migration paths
tests/              Unit and GUI smoke tests
assets/             App icon and tray image
docs/               Sanitized screenshots
build.ps1           Build the single-file executable
config.example.json Configuration template
```
