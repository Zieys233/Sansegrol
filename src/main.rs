use std::process::{Command, Stdio};
use std::io::{self, Write, Read};
use std::env;
use std::path::Path;
use std::thread;


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
    let sansegrol_path = match env::var("Sansegrol") {
        Ok(s) if !s.trim().is_empty() => s,
        _ => {
            eprintln!("Error: 'Sansegrol' environment variable is not set or is empty.");
            std::process::exit(1);
        }
    };

    // If Sansegrol points to an existing directory, run the embedded Python
    // executable and the `src/sansegrol/main.py` script inside it.
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
        // Run python executable with the script path as argument.
        let script_arg = script.to_str().unwrap_or_else(|| {
            eprintln!("Script path is not valid UTF-8");
            std::process::exit(1);
        });
        let exit_code = run_process(&py_exe, &[script_arg])?;
        std::process::exit(exit_code);
    } else {
        eprintln!("Error: 'Sansegrol' environment variable does not point to a valid directory.");
        std::process::exit(-1);
    }
}