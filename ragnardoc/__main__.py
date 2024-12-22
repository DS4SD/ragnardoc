#!/usr/bin/env python
"""
RAGNARDoc is a tool that runs natively on a developer workstation to
automatically ingest local documents into a variety of RAG applications. It can
operate as a CLI for direct ingestion or as a service for background ingestion
and synchronization (Coming soon!)
"""

# Standard
import argparse

# First Party
import alog

# Local
from . import config
from .core import RagnardocCore


log = alog.use_channel("MAIN")

def main():
    parser = argparse.ArgumentParser(description=__doc__)

    # Logging
    parser.add_argument("--log-level", "-l", default=config.log_level, help="Default log channel level")
    parser.add_argument("--log-filters", "-lf", default=config.log_filters, help="Per-channel log filters")
    parser.add_argument("--log-json", "-lj", action="store_true", default=config.log_json, help="Log output as JSON")
    parser.add_argument("--log-thread-id", "-lt", action="store_true", default=config.log_thread_id, help="Include the thread ID in log header")

    # Operation mode
    parser.add_argument("--mode", "-m", default=config.mode, choices=["cli", "service"], help="Mode of operation for the tool")

    # Parse and configure logging
    args = parser.parse_args()
    alog.configure(
        default_level=args.log_level,
        filters=args.log_filters,
        formatter="json" if args.log_json else "pretty",
        thread_id=args.log_thread_id,
    )
    log.info("RAGNARDoc is starting up in [%s] mode", args.mode)

    # Construct the core instance
    instance = RagnardocCore(config)

    # If operating as a CLI, run a single time
    if args.mode == "cli":
        with alog.ContextTimer(log.info, "Finished CLI ingestion in: "):
            instance.ingest()
    elif args.mode == "service":
        raise NotImplementedError("Service mode is not currently supported. Coming soon!")
    else:
        raise RuntimeError(f"Unknown mode: {args.mode}")

if __name__ == "__main__":
    main()
