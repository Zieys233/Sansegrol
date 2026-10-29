# Sansegrol

Sansegrol is a Windows desktop web browser. A Rust launcher starts the bundled
Python 3.8.9 application; PySide6 and Qt WebEngine provide the browser window,
and a local Flask server serves the app's HTML, CSS, and JavaScript.

## Features

- Tabbed browsing with back, forward, reload, and address-bar navigation
- Download manager
- Local welcome pages served from the `web` directory

## Requirements

- Windows 64-bit
- Rust toolchain (including Cargo)
- The bundled Python 3.8.9 runtime in `python-3.8.9-embed-amd64`
- PySide6 6.6.3.1 and Flask 3.0.3 in the bundled runtime's `Lib\site-packages`

The Python runtime is included in the repository. If its Python packages are
not installed, run this from the project root using Python 3.8:

```powershell
python -m pip install --target .\python-3.8.9-embed-amd64\Lib\site-packages "PySide6==6.6.3.1" "Flask==3.0.3"
```

## Run

From the project root, start the app in development mode with Cargo:

```powershell
cargo run -- --env .
```

To build and run the release executable:

```powershell
cargo build --release
.\target\release\sansegrol.exe --env .
```

`--env` takes the project directory. If used without a value, the launcher uses
the current working directory. Alternatively, set the `Sansegrol` environment
variable to the project directory and run the launcher without `--env`.

## Project layout

- `src\main.rs` — Rust launcher
- `src\sansegrol\` — Python application, Qt browser window, and logging
- `web\server\index.py` — Flask server
- `web\html\`, `web\css\`, `web\js\` — pages and frontend assets
- `config\sansegrol.json` — application and server settings
- `assets\icons\` — application icons

The default configuration opens the local Flask site at `http://localhost:8720`.
Browser profile data is stored in `.browser_data`, and application logs are
written to `logs`.
