#!/usr/bin/env python3
"""
Hot Reload Development Server for AstraDesk

This script provides hot-reload functionality for rapid development iteration,
automatically restarting services when code changes are detected.
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Set
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class ChangeHandler(FileSystemEventHandler):
    """File system change handler for hot reload"""

    def __init__(self, callback):
        self.callback = callback
        self.last_reload = time.time()
        self.cooldown = 1.0  # Minimum seconds between reloads

    def on_modified(self, event):
        if event.is_directory:
            return

        # Check file extension
        if event.src_path.endswith(('.py', '.yaml', '.yml', '.json')):
            current_time = time.time()
            if current_time - self.last_reload > self.cooldown:
                logger.info(f"File changed: {event.src_path}")
                self.last_reload = current_time
                self.callback()


class HotReloadServer:
    """
    Hot reload development server

    Monitors file changes and automatically restarts the application
    """

    def __init__(
        self,
        command: List[str],
        watch_paths: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None
    ):
        self.command = command
        self.watch_paths = watch_paths or [
            "services/api-gateway/src",
            "mcp/src",
            "packages",
            "core"
        ]
        self.ignore_patterns = ignore_patterns or [
            "__pycache__",
            ".git",
            "*.pyc",
            "*.pyo",
            ".pytest_cache"
        ]
        self.process: Optional[subprocess.Popen] = None
        self.observer: Optional[Observer] = None
        self.running = False

    async def start(self):
        """Start the hot reload server"""
        logger.info("Starting hot reload server...")
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Start file watcher
        self._start_watcher()

        # Start initial process
        await self._restart_process()

        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await self.stop()

    async def stop(self):
        """Stop the hot reload server"""
        logger.info("Stopping hot reload server...")
        self.running = False

        if self.observer:
            self.observer.stop()
            self.observer.join()

        if self.process:
            await self._stop_process()

    def _start_watcher(self):
        """Start file system watcher"""
        self.observer = Observer()

        for watch_path in self.watch_paths:
            if os.path.exists(watch_path):
                handler = ChangeHandler(self._on_file_change)
                self.observer.schedule(handler, watch_path, recursive=True)
                logger.info(f"Watching path: {watch_path}")

        self.observer.start()

    def _on_file_change(self):
        """Handle file change event"""
        logger.info("Detected file changes, restarting...")
        asyncio.create_task(self._restart_process())

    async def _restart_process(self):
        """Restart the application process"""
        # Stop current process
        if self.process:
            await self._stop_process()

        # Start new process
        try:
            logger.info(f"Starting process: {' '.join(self.command)}")
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Start output monitoring
            asyncio.create_task(self._monitor_output())

        except Exception as e:
            logger.error(f"Failed to start process: {e}")

    async def _stop_process(self):
        """Stop the current process"""
        if self.process:
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(
                        asyncio.create_subprocess_shell(
                            f"kill -TERM {self.process.pid}",
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        ),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Process didn't terminate gracefully, killing...")
                    self.process.kill()

                await asyncio.create_subprocess_shell(
                    f"wait {self.process.pid}",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )

            except Exception as e:
                logger.error(f"Error stopping process: {e}")
            finally:
                self.process = None

    async def _monitor_output(self):
        """Monitor process output"""
        if not self.process or not self.process.stdout:
            return

        try:
            while self.running and self.process:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self.process.stdout.readline
                )
                if line:
                    print(line.rstrip())
                elif self.process.poll() is not None:
                    break
        except Exception as e:
            logger.error(f"Error monitoring output: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False


async def run_hot_reload(
    command: List[str],
    watch_paths: Optional[List[str]] = None
):
    """Run hot reload for the given command"""
    server = HotReloadServer(command, watch_paths)
    await server.start()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Hot Reload Development Server")
    parser.add_argument(
        "command",
        nargs="+",
        help="Command to run (e.g., python -m uvicorn app:app --reload)"
    )
    parser.add_argument(
        "--watch",
        action="append",
        help="Paths to watch for changes (can be specified multiple times)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run hot reload
    try:
        asyncio.run(run_hot_reload(args.command, args.watch))
    except KeyboardInterrupt:
        logger.info("Hot reload stopped by user")
    except Exception as e:
        logger.error(f"Hot reload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()