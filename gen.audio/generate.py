import os
import sys
import time
import subprocess
import signal
import shlex
import shutil


SCRIPTS = [
    "1.character.py",
    "2.story.py",
    "3.transcribe.py",
    "4.quality.py",
    "5.timeline.py",
    "6.timing.py",
    "7.sfx.py",
    "8.combine.py",
]

SCRIPTS_DIR = "scripts"

NEEDS_COMFYUI = {"2.story.py", "7.sfx.py"}
NEEDS_LMSTUDIO = {"5.timeline.py", "6.timing.py"}

# Log maintenance
MAX_LOG_LINES = 1236

# Centralized non-interactive defaults (only change this file)
SCRIPT_ARGS = {
    "1.character.py": ["--auto-gender", "m", "--auto-confirm", "y", "--change-settings", "n"],
    # "7.sfx.py": ["--auto-confirm", "y"],  # sfx script auto-confirms by default; passing is harmless
}


def resolve_comfyui_dir(base_dir: str) -> str:
    candidate = os.path.abspath(os.path.join(base_dir, "..", "ComfyUI"))
    if os.path.exists(os.path.join(candidate, "main.py")):
        return candidate
    alt = os.environ.get("COMFYUI_DIR")
    if alt and os.path.exists(os.path.join(alt, "main.py")):
        return alt
    return candidate


def start_comfyui(working_dir: str, log_handle) -> subprocess.Popen:
    comfy_dir = resolve_comfyui_dir(working_dir)
    main_py = os.path.join(comfy_dir, "main.py")

    log_handle.write(f"Starting ComfyUI backend using Windows cmd style...\n")
    log_handle.flush()

    if not os.path.exists(main_py):
        log_handle.write(f"ERROR: ComfyUI main.py not found at: {main_py}\n")
        log_handle.flush()
        return None

    creation_flags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

    if os.name == "nt":
        # Launch directly with cwd set to ComfyUI dir
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=comfy_dir,
            stdout=log_handle,
            stderr=log_handle,
            text=True,
            creationflags=creation_flags,
            env=env,
        )
    else:
        # Non-Windows fallback
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=comfy_dir,
            stdout=log_handle,
            stderr=log_handle,
            text=True,
            creationflags=creation_flags,
        )

    return proc


def stop_comfyui(proc: subprocess.Popen, log_handle) -> None:
    if proc is None:
        return
    log_handle.write("Stopping ComfyUI backend...\n")
    log_handle.flush()

    try:
        # Use a normal terminate to avoid CTRL_BREAK abort messages on Windows
        proc.terminate()

        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
            proc.wait(timeout=5)
    except Exception as ex:
        log_handle.write(f"WARNING: Failed to stop ComfyUI cleanly: {ex}\n")
        log_handle.flush()


def maintain_log_size(log_path: str, log_handle, max_lines: int = MAX_LOG_LINES) -> None:
    """Truncate log file to 0 size once it reaches the configured line limit.

    Uses chunked binary reads to count newlines efficiently without loading the
    entire file into memory. After truncation, resets the stream position and
    writes a single note line.
    """
    try:
        # Ensure all buffered content is on disk before counting
        try:
            log_handle.flush()
        except Exception:
            pass

        line_count = 0
        with open(log_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                line_count += chunk.count(b"\n")

        if line_count >= max_lines:
            # Truncate the file in-place
            with open(log_path, "r+b") as f:
                f.seek(0)
                f.truncate(0)

            # Reset writer handle position to end-of-file (now 0)
            try:
                log_handle.seek(0, os.SEEK_END)
            except Exception:
                pass

            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            log_handle.write(f"[log] Truncated log at {ts} after {line_count} lines (limit={max_lines}).\n")
            log_handle.flush()
    except Exception as ex:
        try:
            log_handle.write(f"WARNING: Failed to maintain log size: {ex}\n")
            log_handle.flush()
        except Exception:
            pass


def run_script(script_name: str, working_dir: str, log_handle) -> int:
    start_wall = time.strftime("%Y-%m-%d %H:%M:%S")
    start_perf = time.perf_counter()
    log_handle.write(f"\n===== START {script_name} @ {start_wall} =====\n")
    log_handle.flush()

    cmd = [sys.executable, script_name] + SCRIPT_ARGS.get(os.path.basename(script_name), [])

    # Ensure Python subprocess writes UTF-8 to stdout/stderr to avoid cp1252 errors on Windows
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    result = subprocess.run(
        cmd,
        cwd=working_dir,
        stdout=log_handle,
        stderr=log_handle,
        text=True,
        env=env,
    )

    elapsed = time.perf_counter() - start_perf
    end_wall = time.strftime("%Y-%m-%d %H:%M:%S")
    log_handle.write(
        f"\n===== END {script_name} @ {end_wall} (exit={result.returncode}, took={elapsed:.2f}s) =====\n"
    )
    log_handle.flush()
    return result.returncode


def start_lmstudio(log_handle) -> bool:
    cmd_env = os.environ.get("LM_STUDIO_CMD")
    if cmd_env:
        try:
            base_cmd = shlex.split(cmd_env, posix=False)
        except Exception:
            base_cmd = [cmd_env]
    else:
        if shutil.which("lms"):
            base_cmd = ["lms"]
        else:
            if os.name == "nt":
                userprofile = os.environ.get("USERPROFILE", "")
                candidate = os.path.join(userprofile, ".lmstudio", "bin", "lms.exe")
            else:
                candidate = os.path.expanduser(os.path.join("~", ".lmstudio", "bin", "lms"))
            base_cmd = [candidate]

    args = base_cmd + ["server", "start"]

    log_handle.write("Starting LM Studio backend via lms CLI...\n")
    log_handle.write("Command: " + " ".join(args) + "\n")
    log_handle.flush()

    creation_flags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        result = subprocess.run(
            args,
            stdout=log_handle,
            stderr=log_handle,
            text=True,
            creationflags=creation_flags,
        )
        if result.returncode == 0:
            return True
        else:
            log_handle.write(f"ERROR: lms server start exited with {result.returncode}\n")
            log_handle.flush()
            return False
    except FileNotFoundError as ex:
        log_handle.write(f"ERROR: Failed to start LM Studio. Command not found: {args[0]} ({ex})\n")
        log_handle.flush()
        return False
    except Exception as ex:
        log_handle.write(f"ERROR: Failed to start LM Studio: {ex}\n")
        log_handle.flush()
        return False


def stop_lmstudio(log_handle) -> None:
    cmd_env = os.environ.get("LM_STUDIO_CMD")
    if cmd_env:
        try:
            base_cmd = shlex.split(cmd_env, posix=False)
        except Exception:
            base_cmd = [cmd_env]
    else:
        if shutil.which("lms"):
            base_cmd = ["lms"]
        else:
            if os.name == "nt":
                userprofile = os.environ.get("USERPROFILE", "")
                candidate = os.path.join(userprofile, ".lmstudio", "bin", "lms.exe")
            else:
                candidate = os.path.expanduser(os.path.join("~", ".lmstudio", "bin", "lms"))
            base_cmd = [candidate]

    args = base_cmd + ["server", "stop"]

    log_handle.write("Stopping LM Studio backend via lms CLI...\n")
    log_handle.write("Command: " + " ".join(args) + "\n")
    log_handle.flush()

    creation_flags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        subprocess.run(
            args,
            stdout=log_handle,
            stderr=log_handle,
            text=True,
            creationflags=creation_flags,
        )
    except Exception as ex:
        log_handle.write(f"WARNING: Failed to stop LM Studio cleanly: {ex}\n")
        log_handle.flush()


def main() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "log.txt")

    with open(log_path, "w", encoding="utf-8") as log:
        log.write("Workflow runner started. Python executable: " + sys.executable + "\n")
        log.write("Working directory: " + base_dir + "\n")
        log.flush()

        # Manage services across scripts: keep running across consecutive needs
        comfy_proc = None
        lmstudio_active = False

        for idx, script in enumerate(SCRIPTS):
            script_path = os.path.join(base_dir, SCRIPTS_DIR, script)
            if not os.path.exists(script_path):
                log.write(f"ERROR: Script not found: {script_path}\n")
                log.flush()
                # Stop any running services before exiting
                if comfy_proc is not None:
                    stop_comfyui(comfy_proc, log)
                if lmstudio_active:
                    stop_lmstudio(log)
                return 1

            needs_comfy = script in NEEDS_COMFYUI
            needs_lms = script in NEEDS_LMSTUDIO

            # Start services if required and not already running
            if needs_comfy and comfy_proc is None:
                comfy_proc = start_comfyui(base_dir, log)
                if comfy_proc is None:
                    log.write("ABORTING: Could not start ComfyUI backend.\n")
                    log.flush()
                    if lmstudio_active:
                        stop_lmstudio(log)
                    return 1
                log.write("Waiting 15s for ComfyUI to initialize...\n")
                log.flush()
                time.sleep(15)

            if needs_lms and not lmstudio_active:
                lms_ok = start_lmstudio(log)
                if not lms_ok:
                    if comfy_proc is not None:
                        stop_comfyui(comfy_proc, log)
                    log.write("ABORTING: Could not start LM Studio backend.\n")
                    log.flush()
                    return 1
                lmstudio_active = True
                log.write("Waiting 15s for LM Studio to initialize...\n")
                log.flush()
                time.sleep(15)

            # Keep log small before running each step
            maintain_log_size(log_path, log)

            code = run_script(script_path, base_dir, log)

            # Keep log small after each step
            maintain_log_size(log_path, log)

            # Determine if the next script still needs services
            next_needs_comfy = False
            next_needs_lms = False
            if idx + 1 < len(SCRIPTS):
                next_script = SCRIPTS[idx + 1]
                next_needs_comfy = next_script in NEEDS_COMFYUI
                next_needs_lms = next_script in NEEDS_LMSTUDIO

            # Stop services only if not needed by the next script
            if needs_comfy and not next_needs_comfy and comfy_proc is not None:
                stop_comfyui(comfy_proc, log)
                comfy_proc = None
            if needs_lms and not next_needs_lms and lmstudio_active:
                stop_lmstudio(log)
                lmstudio_active = False

            if code != 0:
                # On error, ensure services are stopped
                if comfy_proc is not None:
                    stop_comfyui(comfy_proc, log)
                    comfy_proc = None
                if lmstudio_active:
                    stop_lmstudio(log)
                    lmstudio_active = False
                log.write(f"ABORTING: {script} exited with code {code}.\n")
                log.flush()
                return code

        # After all scripts, ensure services are stopped
        if comfy_proc is not None:
            stop_comfyui(comfy_proc, log)
        if lmstudio_active:
            stop_lmstudio(log)

        log.write("\nAll scripts completed successfully.\n")
        log.flush()

    print("All scripts completed. See log.txt for details.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


