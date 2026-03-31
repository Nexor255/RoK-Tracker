"""
RokTracker Sidecar Process
Reads JSON commands from stdin, writes JSON events to stdout.
Used by Tauri to communicate with the Python scanner logic.
"""
import json
import logging
import sys
import os
import threading
from threading import Event, Thread
from typing import List

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dummy_root
from pydantic import TypeAdapter

from roktracker.alliance.scanner import AllianceScanner
from roktracker.honor.scanner import HonorScanner
from roktracker.kingdom.types.additional_data import AdditionalData
from roktracker.kingdom.types.governor_data import GovernorData
from roktracker.seed.scanner import SeedScanner
from roktracker.utils.types.batch_scanner.batch_type import BatchStatus, BatchType
from roktracker.utils.types.batch_scanner.governor_data import GovernorData as BatchData
from roktracker.utils.types.batch_scanner.additional_data import (
    AdditionalData as BatchAdditionalData,
)
from roktracker.kingdom.scanner import KingdomScanner, scan_preset_to_scan_options
from roktracker.utils.exception_handling import ConsoleExceptionHander
from roktracker.utils.file_manager import (
    load_config,
    save_config,
    load_kingdom_presets,
    save_kingdom_presets,
)
from roktracker.utils.types.full_config import FullConfig
from roktracker.utils.types.scan_preset import ScanPreset

# ---------------------------------------------------------------------------
# Logging — redirect to file so stdout stays clean for JSON protocol
# ---------------------------------------------------------------------------
logging.basicConfig(
    filename=str(dummy_root.get_app_root() / "sidecar.log"),
    encoding="utf-8",
    format="%(asctime)s %(module)s %(levelname)s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
ex_handler = ConsoleExceptionHander(logger)
sys.excepthook = ex_handler.handle_exception
threading.excepthook = ex_handler.handle_thread_exception

# ---------------------------------------------------------------------------
# JSON-line output (thread-safe)
# ---------------------------------------------------------------------------
_write_lock = threading.Lock()


def emit_event(event: str, data=None):
    """Write a single JSON line to stdout."""
    msg = {"event": event}
    if data is not None:
        msg["data"] = data
    with _write_lock:
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Scanner state
# ---------------------------------------------------------------------------
kingdom_scanner = None
alliance_scanner = None
honor_scanner = None
seed_scanner = None

kingdom_confirm_result = False
kingdom_response = Event()

alliance_confirm_result = False
alliance_response = Event()

# ---------------------------------------------------------------------------
# Callback handler — replaces window.evaluate_js() with emit_event()
# ---------------------------------------------------------------------------


class SidecarCallbackHandler:
    # Kingdom callbacks
    def kingdom_governor_callback(
        self, gov_data: GovernorData, extra_data: AdditionalData
    ) -> None:
        emit_event(
            "kingdom_governor_update",
            {
                "gov": json.loads(gov_data.model_dump_json()),
                "extra": json.loads(extra_data.model_dump_json()),
            },
        )

    def kingdom_state_callback(self, state: str) -> None:
        emit_event("kingdom_state_update", state)

    def ask_confirm(self, message: str) -> bool:
        kingdom_response.clear()
        emit_event("kingdom_ask_confirm", message)
        kingdom_response.wait()
        return kingdom_confirm_result

    def kingdom_scan_finished(self):
        emit_event("kingdom_scan_finished")

    def set_kingdom_scan_id(self, scan_id: str):
        emit_event("kingdom_scan_id", scan_id)

    # Batch callbacks (Alliance / Honor / Seed)
    def batch_update(
        self,
        batch_data: List[BatchData],
        extra_data: BatchAdditionalData,
        batch_type: BatchType,
    ):
        batch_data_encoded = (
            TypeAdapter(list[BatchData]).dump_json(batch_data).decode()
        )
        emit_event(
            "batch_update",
            {
                "gov": json.loads(batch_data_encoded),
                "extra": json.loads(extra_data.model_dump_json()),
                "type": BatchStatus(type=batch_type).model_dump_json(),
            },
        )

    def alliance_scan_batch_callback(
        self, batch_data: List[BatchData], extra_data: BatchAdditionalData
    ):
        self.batch_update(batch_data, extra_data, BatchType.ALLIANCE)

    def honor_scan_batch_callback(
        self, batch_data: List[BatchData], extra_data: BatchAdditionalData
    ):
        self.batch_update(batch_data, extra_data, BatchType.HONOR)

    def seed_scan_batch_callback(
        self, batch_data: List[BatchData], extra_data: BatchAdditionalData
    ):
        self.batch_update(batch_data, extra_data, BatchType.SEED)

    def batch_state_update(self, msg: str, batch_type: BatchType):
        emit_event(
            "batch_state_update",
            {
                "msg": msg,
                "type": BatchStatus(type=batch_type).model_dump_json(),
            },
        )

    def alliance_state_callback(self, msg: str):
        self.batch_state_update(msg, BatchType.ALLIANCE)

    def honor_state_callback(self, msg: str):
        self.batch_state_update(msg, BatchType.HONOR)

    def seed_state_callback(self, msg: str):
        self.batch_state_update(msg, BatchType.SEED)

    def set_batch_id(self, batch_type: BatchType, scan_id: str):
        emit_event(
            "batch_scan_id",
            {
                "id": scan_id,
                "type": BatchStatus(type=batch_type).model_dump_json(),
            },
        )

    def batch_scan_finished(self, batch_type: BatchType):
        emit_event(
            "batch_scan_finished",
            BatchStatus(type=batch_type).model_dump_json(),
        )

    def alliance_scan_finished(self):
        self.batch_scan_finished(BatchType.ALLIANCE)

    def honor_scan_finished(self):
        self.batch_scan_finished(BatchType.HONOR)

    def seed_scan_finished(self):
        self.batch_scan_finished(BatchType.SEED)

    def ask_confirm_alliance(self, message: str) -> bool:
        alliance_response.clear()
        emit_event(
            "batch_ask_confirm",
            {
                "msg": message,
                "type": BatchStatus(type=BatchType.ALLIANCE).model_dump_json(),
            },
        )
        alliance_response.wait()
        return alliance_confirm_result


cb = SidecarCallbackHandler()

# ---------------------------------------------------------------------------
# Scanner start helpers (run in threads)
# ---------------------------------------------------------------------------


def _start_kingdom_scanner(full_config: str, scan_preset: str):
    global kingdom_scanner
    try:
        config = FullConfig(**json.loads(full_config))
        preset = ScanPreset(**json.loads(scan_preset))
        kingdom_scanner = KingdomScanner(
            config, scan_preset_to_scan_options(preset), config.general.adb_port
        )
        kingdom_scanner.set_governor_callback(cb.kingdom_governor_callback)
        kingdom_scanner.set_state_callback(cb.kingdom_state_callback)
        kingdom_scanner.set_continue_handler(cb.ask_confirm)

        cb.set_kingdom_scan_id(kingdom_scanner.run_id)

        kingdom_scanner.start_scan(
            config.scan.kingdom_name,
            config.scan.people_to_scan,
            config.scan.resume,
            config.scan.track_inactives,
            config.scan.validate_kills,
            config.scan.reconstruct_kills,
            config.scan.validate_power,
            config.scan.power_threshold,
            config.scan.formats,
        )
        cb.kingdom_scan_finished()
    except Exception as e:
        logger.exception("Kingdom scan error")
        emit_event("error", str(e))


def _start_alliance_scanner(full_config: str):
    global alliance_scanner
    try:
        config = FullConfig(**json.loads(full_config))
        alliance_scanner = AllianceScanner(config.general.adb_port, config)
        alliance_scanner.set_batch_callback(cb.alliance_scan_batch_callback)
        alliance_scanner.set_state_callback(cb.alliance_state_callback)
        cb.set_batch_id(BatchType.ALLIANCE, alliance_scanner.run_id)
        alliance_scanner.start_scan(
            config.scan.kingdom_name, config.scan.people_to_scan, config.scan.formats
        )
        cb.alliance_scan_finished()
    except Exception as e:
        logger.exception("Alliance scan error")
        emit_event("error", str(e))


def _start_honor_scanner(full_config: str):
    global honor_scanner
    try:
        config = FullConfig(**json.loads(full_config))
        honor_scanner = HonorScanner(config.general.adb_port, config)
        honor_scanner.set_batch_callback(cb.honor_scan_batch_callback)
        honor_scanner.set_state_callback(cb.honor_state_callback)
        cb.set_batch_id(BatchType.HONOR, honor_scanner.run_id)
        honor_scanner.start_scan(
            config.scan.kingdom_name, config.scan.people_to_scan, config.scan.formats
        )
        cb.honor_scan_finished()
    except Exception as e:
        logger.exception("Honor scan error")
        emit_event("error", str(e))


def _start_seed_scanner(full_config: str):
    global seed_scanner
    try:
        config = FullConfig(**json.loads(full_config))
        seed_scanner = SeedScanner(config.general.adb_port, config)
        seed_scanner.set_batch_callback(cb.seed_scan_batch_callback)
        seed_scanner.set_state_callback(cb.seed_state_callback)
        cb.set_batch_id(BatchType.SEED, seed_scanner.run_id)
        seed_scanner.start_scan(
            config.scan.kingdom_name, config.scan.people_to_scan, config.scan.formats
        )
        cb.seed_scan_finished()
    except Exception as e:
        logger.exception("Seed scan error")
        emit_event("error", str(e))


# ---------------------------------------------------------------------------
# Command handlers — one per stdin command
# ---------------------------------------------------------------------------
COMMANDS = {}


def command(name):
    """Decorator to register a command handler."""
    def decorator(fn):
        COMMANDS[name] = fn
        return fn
    return decorator


@command("LoadFullConfig")
def cmd_load_config(args):
    config = load_config()
    emit_event("config_loaded", json.loads(config.model_dump_json()))


@command("LoadScanPresets")
def cmd_load_presets(args):
    presets = load_kingdom_presets()
    data = TypeAdapter(list[ScanPreset]).dump_json(presets).decode()
    emit_event("presets_loaded", json.loads(data))


@command("SaveConfig")
def cmd_save_config(args):
    config = FullConfig.model_validate(args["config"])
    save_config(config)
    logger.info("Configuration saved successfully")
    emit_event("config_saved")


@command("SaveScanPresets")
def cmd_save_presets(args):
    presets = TypeAdapter(list[ScanPreset]).validate_python(args["presets"])
    save_kingdom_presets(presets)
    emit_event("presets_saved")


@command("StartKingdomScan")
def cmd_start_kingdom(args):
    Thread(
        target=_start_kingdom_scanner,
        args=(json.dumps(args["config"]), json.dumps(args["preset"])),
    ).start()


@command("StopKingdomScan")
def cmd_stop_kingdom(args):
    if kingdom_scanner:
        kingdom_scanner.end_scan()


@command("ConfirmKingdom")
def cmd_confirm_kingdom(args):
    global kingdom_confirm_result
    kingdom_confirm_result = args["confirmed"]
    kingdom_response.set()


@command("StartBatchScan")
def cmd_start_batch(args):
    batch_type = args["batch_type"]
    config_json = json.dumps(args["config"])
    match batch_type:
        case "Alliance":
            Thread(target=_start_alliance_scanner, args=(config_json,)).start()
        case "Honor":
            Thread(target=_start_honor_scanner, args=(config_json,)).start()
        case "Seed":
            Thread(target=_start_seed_scanner, args=(config_json,)).start()


@command("StopBatchScan")
def cmd_stop_batch(args):
    batch_type = args["batch_type"]
    match batch_type:
        case "Alliance":
            if alliance_scanner:
                alliance_scanner.end_scan()
        case "Honor":
            if honor_scanner:
                honor_scanner.end_scan()
        case "Seed":
            if seed_scanner:
                seed_scanner.end_scan()


@command("ConfirmBatch")
def cmd_confirm_batch(args):
    global alliance_confirm_result
    batch_type = args["batch_type"]
    confirmed = args["confirmed"]
    match batch_type:
        case "Alliance":
            alliance_confirm_result = confirmed
            alliance_response.set()


# ---------------------------------------------------------------------------
# Main loop — read JSON commands from stdin line by line
# ---------------------------------------------------------------------------
def main():
    emit_event("ready")
    logger.info("Sidecar started, waiting for commands on stdin")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {line} — {e}")
            emit_event("error", f"Invalid JSON: {e}")
            continue

        cmd = msg.get("cmd")
        args = msg.get("args", {})

        if cmd in COMMANDS:
            try:
                COMMANDS[cmd](args)
            except Exception as e:
                logger.exception(f"Error handling command {cmd}")
                emit_event("error", f"Command {cmd} failed: {e}")
        else:
            logger.warning(f"Unknown command: {cmd}")
            emit_event("error", f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
