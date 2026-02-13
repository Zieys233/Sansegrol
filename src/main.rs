use std::process::{Command, Stdio};
use std::io::{self, Write, Read};
use std::env;
use std::path::Path;
use std::thread;


fn get_sansegrol_from_args() -> Option<String> {
    /*
        Parses command-line arguments to find `--env` and returns its value.
        If `--env` is followed by an argument (and it does not start with `-`), that argument is used as the value.
        If `--env` appears alone, the current working directory is used as the value.
        If `--env` is not found, returns `None`.
        If getting the current working directory fails or the path contains invalid UTF-8, the program exits immediately.
     */

    let args: Vec<String> = env::args().collect();
    let mut i = 0;
    let mut result = None;

    while i < args.len() {
        if args[i] == "--env" {
            // Check if next argument exists and is not another option (starts with '-')
            if i + 1 < args.len() && !args[i + 1].starts_with('-') {
                // Has argument, use it directly
                result = Some(args[i + 1].clone());
                i += 2;
            } else {
                // No argument, use current working directory
                match env::current_dir() {
                    Ok(cwd) => {
                        if let Some(path_str) = cwd.to_str() {
                            result = Some(path_str.to_string());
                        } else {
                            eprintln!("Error: current directory contains invalid UTF-8, cannot use as Sansegrol path.");
                            std::process::exit(1);
                        }
                    }
                    Err(e) => {
                        eprintln!("Error: failed to get current working directory: {}", e);
                        std::process::exit(1);
                    }
                }
                i += 1;
            }
        } else {
            i += 1;
        }
    }
    result
}

fn run_process(cmd_path: &Path, args: &[&str]) -> io::Result<i32> {
    let mut command_builder = Command::new(cmd_path);
    command_builder.args(args);

    // If we are invoking Python, force Python to emit UTF-8 output to avoid
    // encoding issues on Windows consoles.
    if let Some(file_name) = cmd_path.file_name().and_then(|s| s.to_str()) {
        if file_name.to_lowercase().contains("python") {
            command_builder.env("PYTHONIOENCODING", "utf-8");
            command_builder.env("PYTHONUTF8", "1");
        }
    }

    let mut child = command_builder
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    let mut stdout = child.stdout.take().expect("Failed to capture stdout");
    let mut stderr = child.stderr.take().expect("Failed to capture stderr");

    let stdout_handle = thread::spawn(move || {
        let mut buf = [0u8; 1024];
        loop {
            match stdout.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => {
                    if cfg!(windows) {
                        let s = String::from_utf8_lossy(&buf[..n]);
                        print!("{}", s);
                    } else {
                        let _ = io::stdout().write_all(&buf[..n]);
                    }
                    let _ = io::stdout().flush();
                }
                Err(_) => break,
            }
        }
    });

    let stderr_handle = thread::spawn(move || {
        let mut buf = [0u8; 1024];
        loop {
            match stderr.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => {
                    if cfg!(windows) {
                        let s = String::from_utf8_lossy(&buf[..n]);
                        eprint!("{}", s);
                    } else {
                        let _ = io::stderr().write_all(&buf[..n]);
                    }
                    let _ = io::stderr().flush();
                }
                Err(_) => break,
            }
        }
    });

    let status = child.wait()?;
    let _ = stdout_handle.join();
    let _ = stderr_handle.join();

    Ok(status.code().unwrap_or(1))
}

fn main() -> io::Result<()> {
    // First try to get Sansegrol path from command-line arguments
    let sansegrol_path = if let Some(path_from_args) = get_sansegrol_from_args() {
        if path_from_args.trim().is_empty() {
            eprintln!("Error: --env argument provided an empty string, cannot use as Sansegrol path.");
            std::process::exit(1);
        }
        path_from_args
    } else {
        // If no --env, read from environment variable
        match env::var("Sansegrol") {
            Ok(s) if !s.trim().is_empty() => s,
            _ => {
                eprintln!("Error: 'Sansegrol' environment variable is not set or is empty, and no --env argument provided.");
                std::process::exit(1);
            }
        }
    };

    // Set the environment variable so child processes can inherit it
    env::set_var("Sansegrol", &sansegrol_path);

    // Subsequent logic unchanged: use sansegrol_path to locate Python interpreter and script
    let p = Path::new(&sansegrol_path);

    if p.exists() && p.is_dir() {
        let py_exe = p.join("python-3.8.9-embed-amd64").join(if cfg!(windows) { "python.exe" } else { "python3" });
        let script = p.join("src").join("sansegrol").join("main.py");

        if !py_exe.exists() {
            eprintln!("Python executable not found at {}", py_exe.display());
            std::process::exit(1);
        }
        if !script.exists() {
            eprintln!("Script not found at {}", script.display());
            std::process::exit(1);
        }

        println!("Executing: {} {}", py_exe.display(), script.display());
        let script_arg = script.to_str().unwrap_or_else(|| {
            eprintln!("Script path is not valid UTF-8");
            std::process::exit(1);
        });
        let exit_code = run_process(&py_exe, &[script_arg])?;
        std::process::exit(exit_code);
    } else {
        eprintln!("Error: 'Sansegrol' environment variable does not point to a valid directory: {}", sansegrol_path);
        std::process::exit(-1);
    }
}