"""
RokTracker Sidecar Process
Reads JSON commands from stdin, writes JSON events to stdout.
Used by Tauri to communicate with the Python scanner logic.
"""
import datetime
import json
import logging
import sys
import os
import threading
from threading import Event, Thread
from typing import List
import warnings

# Suppress SyntaxWarnings from third-party libraries (e.g. dtmilano invalid escape sequences)
warnings.filterwarnings("ignore", category=SyntaxWarning)

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


class _DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that converts datetime objects to ISO 8601 strings."""

    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        return super().default(obj)


def emit_event(event: str, data=None):
    """Write a single JSON line to stdout."""
    msg = {"event": event}
    if data is not None:
        msg["data"] = data
    with _write_lock:
        try:
            sys.stdout.write(json.dumps(msg, cls=_DateTimeEncoder) + "\n")
            sys.stdout.flush()
        except OSError as e:
            # Handle broken pipes
            if e.errno in (22, 9, 32):
                logger.warning("stdout pipe broken, exiting sidecar.")
                # Use os._exit() to kill all threads immediately since IPC is dead
                os._exit(0)
            else:
                raise


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
                "gov": gov_data.model_dump(),
                "extra": extra_data.model_dump(),
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
        emit_event(
            "batch_update",
            {
                "gov": TypeAdapter(list[BatchData]).dump_python(batch_data, mode="python"),
                "extra": extra_data.model_dump(),
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
    emit_event("config_loaded", config.model_dump())


@command("LoadScanPresets")
def cmd_load_presets(args):
    presets = load_kingdom_presets()
    emit_event("presets_loaded", TypeAdapter(list[ScanPreset]).dump_python(presets, mode="python"))


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
    preset_data = args.get("preset")
    if preset_data is None:
        # Fallback: use a "Full" preset with all scan selections
        logger.info("No preset provided, using default Full preset")
        preset_data = {
            "name": "Full",
            "selections": [
                "ID", "Name", "Power", "Killpoints", "Alliance",
                "T1 Kills", "T2 Kills", "T3 Kills", "T4 Kills", "T5 Kills",
                "Ranged", "Deaths", "Assistance", "Gathered", "Helps",
            ],
        }
    Thread(
        target=_start_kingdom_scanner,
        args=(json.dumps(args["config"]), json.dumps(preset_data)),
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
# Scan History commands
# ---------------------------------------------------------------------------
from roktracker.utils.scan_history import (
    list_all_scans,
    delete_scan_file,
    get_scan_folder,
    get_scan_detail,
    compare_scans,
)


@command("ListScanHistory")
def cmd_list_scan_history(args):
    history = list_all_scans()
    emit_event("scan_history_list", history)


@command("GetScanDetail")
def cmd_get_scan_detail(args):
    path = args["path"]
    page = args.get("page", 1)
    page_size = args.get("page_size", 50)
    detail = get_scan_detail(path, page=page, page_size=page_size)
    emit_event("scan_detail", detail)


@command("CompareScanFiles")
def cmd_compare_scans(args):
    path_a = args["path_a"]
    path_b = args["path_b"]
    result = compare_scans(path_a, path_b)
    emit_event("scan_compare_result", result)


@command("DeleteScanFile")
def cmd_delete_scan_file(args):
    path = args["path"]
    success = delete_scan_file(path)
    if success:
        emit_event("scan_file_deleted", path)
    else:
        emit_event("error", f"Failed to delete scan file: {path}")


@command("GetScanFolder")
def cmd_get_scan_folder(args):
    scan_type = args["scan_type"]
    folder = get_scan_folder(scan_type)
    if folder:
        emit_event("scan_folder_path", folder)
    else:
        emit_event("error", f"Unknown scan type: {scan_type}")


from roktracker.utils.adb_detector import detect_emulators

@command("DetectEmulators")
def cmd_detect_emulators(args):
    emulators = detect_emulators()
    emit_event("emulators_detected", emulators)

# ---------------------------------------------------------------------------
# Main loop — read JSON commands from stdin line by line
# ---------------------------------------------------------------------------
def main():
    # Log startup diagnostics for debugging production issues
    app_root = dummy_root.get_app_root()
    logger.info("Sidecar started, waiting for commands on stdin")
    logger.info(f"  app_root   = {app_root}")
    logger.info(f"  config.json exists = {(app_root / 'config.json').exists()}")
    logger.info(f"  python     = {sys.executable}")
    logger.info(f"  version    = {sys.version}")
    logger.info(f"  cwd        = {os.getcwd()}")

    emit_event("ready")

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
    try:
        main()
    except Exception as e:
        # Last-resort handler: log to file AND stderr so the Rust reader picks it up
        logger.critical(f"Sidecar crashed: {e}", exc_info=True)
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)

