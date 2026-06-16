#!/usr/bin/env python3
"""
RAG Inbox Watcher
Watches /Users/rohith/RAG/inbox for new files and automatically
sends them to the n8n webhook for ingestion into the RAG system.
After uploading, the file is deleted from the inbox folder.
"""

import time
import os
import threading
import json
import httpx
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

INBOX_PATH = os.getenv("INBOX_PATH", "/Users/rohith/RAG/inbox")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/ingest-document")
PROCESS_LOCK = threading.Lock()


class IngestHandler(FileSystemEventHandler):
    """Handles file creation events in the inbox folder."""

    def _should_process(self, path: str, is_directory: bool) -> bool:
        return not is_directory and not path.endswith(".DS_Store")

    def process_file(self, filepath: str) -> None:
        """Upload a file to n8n and delete it from inbox."""
        with PROCESS_LOCK:
            if not os.path.exists(filepath):
                return

            # Wait for the file to finish copying
            time.sleep(2)

            print(f"\n[+] Detected: {os.path.basename(filepath)}")
            print("    Sending to n8n RAG pipeline...")

            response = ""
            parsed_response = None
            try:
                with open(filepath, "rb") as file_handle:
                    with httpx.Client(timeout=600.0) as client:
                        result = client.post(
                            N8N_WEBHOOK_URL,
                            files={"data": (os.path.basename(filepath), file_handle)},
                        )
                response = result.text.strip()
                parsed_response = result.json() if response else None
            except json.JSONDecodeError:
                parsed_response = None
            except Exception as exc:
                response = f"Watcher upload failed: {exc}"

            success = bool(parsed_response and parsed_response.get("status") == "success")

            if '"code":404' in response:
                print("    ⚠️  n8n workflow not active! Turn ON the toggle in n8n.")
            elif success:
                print("    ✅ Successfully uploaded to RAG system!")
            else:
                print(f"    n8n response: {response}")

            if success:
                try:
                    os.remove(filepath)
                    print("    🗑️  Cleaned up from inbox.")
                except OSError as e:
                    print(f"    Could not delete file: {e}")
            else:
                print("    Keeping file in inbox for retry.")

            print("    Waiting for next file...\n")

    def on_created(self, event) -> None:  # type: ignore[override]
        if self._should_process(event.src_path, event.is_directory):
            threading.Thread(
                target=self.process_file, args=(event.src_path,), daemon=True
            ).start()

    def on_moved(self, event) -> None:  # type: ignore[override]
        if self._should_process(event.dest_path, event.is_directory):
            threading.Thread(
                target=self.process_file, args=(event.dest_path,), daemon=True
            ).start()


def process_existing_files(handler: IngestHandler) -> None:
    """Process any files already sitting in inbox on startup."""
    existing = [
        f for f in os.listdir(INBOX_PATH)
        if not f.endswith(".DS_Store") and os.path.isfile(os.path.join(INBOX_PATH, f))
    ]
    if existing:
        print(f"Found {len(existing)} existing file(s) — processing now...\n")
        for filename in existing:
            filepath = os.path.join(INBOX_PATH, filename)
            handler.process_file(filepath)
    else:
        print("Inbox is empty — ready to receive files.\n")


def main() -> None:
    os.makedirs(INBOX_PATH, exist_ok=True)

    print("=" * 50)
    print("  RAG INBOX WATCHER — RUNNING")
    print(f"  Drop files into:  {INBOX_PATH}")
    print(f"  Sending to:       {N8N_WEBHOOK_URL}")
    print("=" * 50 + "\n")

    handler = IngestHandler()
    process_existing_files(handler)

    observer = PollingObserver(timeout=1.0)
    observer.schedule(handler, INBOX_PATH, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
