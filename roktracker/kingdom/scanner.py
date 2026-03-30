import datetime
import logging
from roktracker.kingdom.pandas_handler import PandasHandler
from roktracker.utils.output_formats import OutputFormats
import roktracker.utils.rok_ui_positions as rok_ui
import shutil
import time
import tkinter
import numpy as np

from dummy_root import get_app_root
from pathlib import Path
from roktracker.utils.adb import *
from roktracker.utils.general import *
from roktracker.utils.ocr import *
from roktracker.utils.ch_matcher import CHLevelMatcher
from roktracker.kingdom.types.additional_data import AdditionalData
from roktracker.kingdom.types.governor_data import GovernorData
from tesserocr import PyTessBaseAPI, PSM, OEM  # type: ignore (tesserocr has no type defs)
from typing import Callable, List
from PIL import Image

from roktracker.utils.types.full_config import FormatsConfig, FullConfig
from roktracker.utils.types.scan_preset import ScanItems, ScanOptions, ScanPreset

logger = logging.getLogger(__name__)


def default_gov_callback(gov: GovernorData, extra: AdditionalData) -> None:
    pass


def default_state_callback(msg: str) -> None:
    pass


def default_ask_continue(msg: str) -> bool:
    return False


def default_output_handler(msg: str) -> None:
    console.log(msg)
    pass


def scan_preset_to_scan_options(preset: ScanPreset) -> ScanOptions:
    return ScanOptions(
        id=ScanItems.ID in preset.selections,
        name=ScanItems.NAME in preset.selections,
        power=ScanItems.POWER in preset.selections,
        killpoints=ScanItems.KILLPOINTS in preset.selections,
        alliance=ScanItems.ALLIANCE in preset.selections,
        t1_kills=ScanItems.T1_KILLS in preset.selections,
        t2_kills=ScanItems.T2_KILLS in preset.selections,
        t3_kills=ScanItems.T3_KILLS in preset.selections,
        t4_kills=ScanItems.T4_KILLS in preset.selections,
        t5_kills=ScanItems.T5_KILLS in preset.selections,
        ranged=ScanItems.RANGED in preset.selections,
        deaths=ScanItems.DEATHS in preset.selections,
        assistance=ScanItems.ASSISTANCE in preset.selections,
        gathered=ScanItems.GATHERED in preset.selections,
        helps=ScanItems.HELPS in preset.selections,
    )


class KingdomScanner:
    def __init__(self, config, scan_options, port):
        self.run_id = generate_random_id(8)
        self.scan_times = []
        self.start_date = datetime.date.today()
        self.stop_scan = False

        self.config = config
        self.timings = config.scan.timings.model_dump()
        self.max_random_delay = config.scan.timings.max_random

        self.advanced_scroll = config.scan.advanced_scroll
        self.scan_options = scan_options
        self.abort = False
        self.inactive_players = 0

        # TODO: Load paths from config
        self.root_dir = get_app_root()
        self.tesseract_path = Path(self.root_dir / "deps" / "tessdata")
        self.img_path = Path(self.root_dir / "temp_images")
        self.img_path.mkdir(parents=True, exist_ok=True)
        self.scan_path = Path(self.root_dir / "scans_kingdom")
        self.scan_path.mkdir(parents=True, exist_ok=True)
        self.inactive_path = Path(
            self.root_dir / "inactives" / str(self.start_date) / str(self.run_id)
        )
        self.review_path = Path(
            self.root_dir / "manual_review" / str(self.start_date) / str(self.run_id)
        )
        self.created_review_path = False

        self.gov_callback = default_gov_callback
        self.state_callback = default_state_callback
        self.ask_continue = default_ask_continue
        self.output_handler = default_output_handler

        # City Hall verification state
        self._in_search_screen = False
        self._ch_matcher = CHLevelMatcher(
            self.root_dir / "deps" / "ch_templates" / "city_hall_numbers",
            self.tesseract_path,
        )

        self.adb_client = AdvancedAdbClient(
            str(self.root_dir / "deps" / "platform-tools" / "adb.exe"),
            port,
            config.general.emulator,
            self.root_dir / "deps" / "inputs",
        )

    def set_governor_callback(
        self, cb: Callable[[GovernorData, AdditionalData], None]
    ) -> None:
        self.gov_callback = cb

    def set_state_callback(self, cb: Callable[[str], None]):
        self.state_callback = cb

    def set_continue_handler(self, cb: Callable[[str], bool]):
        self.ask_continue = cb

    def set_output_handler(self, cb: Callable[[str], None]):
        self.output_handler = cb

    def get_remaining_time(self, remaining_govs: int) -> float:
        return (sum(self.scan_times, start=0) / len(self.scan_times)) * remaining_govs

    def save_failed(
        self, fail_type: str, gov_data: GovernorData, reconstructed: bool = False
    ):
        pre = "Unset"
        if fail_type == "kills":
            if reconstructed:
                pre = "R"
                logging.log(
                    logging.INFO,
                    f"""Kills for {gov_data.name} ({to_int_check(gov_data.id)}) reconstructed, t1 might be off by up to 4 kills.""",
                )
            else:
                pre = "F"
                logging.log(
                    logging.WARNING,
                    f"""Kills for {gov_data.name} ({to_int_check(gov_data.id)}) don't check out, manually need to look at them!""",
                )
        elif fail_type == "power":
            pre = "P"
            logging.log(
                logging.WARNING,
                f"""Power for {gov_data.name} ({to_int_check(gov_data.id)}) is higher then previous governor, manually need to look at it!""",
            )

        if not self.created_review_path:
            self.review_path.mkdir(parents=True, exist_ok=True)
            self.created_review_path = True

        shutil.copy(
            Path(self.img_path / "gov_info.png"),
            Path(self.review_path / f"""{pre}{gov_data.id}-profile.png"""),
        )
        if fail_type == "kills":
            shutil.copy(
                Path(self.img_path / "kills_tier.png"),
                Path(self.review_path / f"""{pre}{gov_data.id}-kills.png"""),
            )

    def get_gov_position(self, current_position, skips):
        # Positions for next governor to check
        Y = [285, 390, 490, 590, 605, 705, 805]

        # skips only are relevant in the first 4 governors
        if current_position + skips < 4:
            return Y[current_position + skips]
        else:
            if current_position < 998:
                return Y[4]
            elif current_position == 998:
                return Y[5]
            elif current_position == 999:
                return Y[6]
            else:
                console.log("Reached final governor on the screen. Scan complete.")
                logging.log(
                    logging.INFO, "Reached final governor on the screen. Scan complete."
                )
                return Y[6]

    def is_page_needed(self, page: int) -> bool:
        match page:
            case 1:
                return (
                    self.scan_options.id
                    or self.scan_options.name
                    or self.scan_options.power
                    or self.scan_options.killpoints
                    or self.scan_options.alliance
                )
            case 2:
                return (
                    self.scan_options.t1_kills
                    or self.scan_options.t2_kills
                    or self.scan_options.t3_kills
                    or self.scan_options.t4_kills
                    or self.scan_options.t5_kills
                    or self.scan_options.ranged
                )
            case 3:
                return (
                    self.scan_options.deaths
                    or self.scan_options.assistance
                    or self.scan_options.gathered
                    or self.scan_options.helps
                )
            case _:
                return False

    def scan_governor(
        self,
        current_player: int,
        track_inactives: bool,
    ) -> GovernorData:
        start_time = time.time()
        governor_data = GovernorData()

        self.state_callback("Opening governor")
        # Open governor
        self.adb_client.secure_adb_shell(
            f"input tap 690 "
            + str(self.get_gov_position(current_player, self.inactive_players))
        )

        wait_random_range(self.timings["gov_open"], self.max_random_delay)

        gov_info = False
        count = 0
        ui_positions = {}
        tap_positions = {}

        while not (gov_info):
            self.adb_client.secure_adb_screencap().save(
                self.img_path / "check_more_info.png"
            )

            image_check = load_cv2_img(
                self.img_path / "check_more_info.png", cv2.IMREAD_GRAYSCALE
            )

            # Checking for more info
            im_check_more_info = cropToRegion(
                image_check, rok_ui.ocr_regions["more_info"]
            )
            check_more_info = ""

            with PyTessBaseAPI(path=str(self.tesseract_path)) as api:
                api.SetVariable("tessedit_char_whitelist", "MoreInfo")
                api.SetImage(Image.fromarray(im_check_more_info))  # type: ignore (pylance is messed up)
                check_more_info = api.GetUTF8Text()

            # Probably tapped governor is inactive and needs to be skipped
            if not more_info_present(check_more_info):
                self.inactive_players += 1
                if track_inactives:
                    image_check_inactive = load_cv2_img(
                        self.img_path / "check_more_info.png", cv2.IMREAD_UNCHANGED
                    )

                    roiInactive = (
                        0,
                        self.get_gov_position(current_player, self.inactive_players - 1)
                        - 100,
                        1400,
                        200,
                    )
                    image_inactive_raw = cropToRegion(image_check_inactive, roiInactive)
                    write_cv2_img(
                        image_inactive_raw,
                        self.inactive_path / f"inactive {self.inactive_players:03}.png",
                        "png",
                    )

                if self.advanced_scroll:
                    self.adb_client.adb_send_events(
                        "Touch",
                        "kingdom_1_person_scroll.txt",
                    )
                else:
                    self.adb_client.secure_adb_shell(f"input swipe 690 605 690 540")
                self.adb_client.secure_adb_shell(
                    f"input tap 690 "
                    + str(self.get_gov_position(current_player, self.inactive_players)),
                )
                count += 1
                wait_random_range(self.timings["gov_open"], self.max_random_delay)
                if count == 10:
                    cont = self.ask_continue("Could not find user, retry?")
                    if cont:
                        count = 0
                    else:
                        break
            else:
                gov_info = True
                image_check = load_cv2_img(
                    self.img_path / "check_more_info.png", cv2.IMREAD_GRAYSCALE
                )

                # Checking for more info
                im_check_more_info = cropToRegion(
                    image_check, rok_ui.ocr_check_profile_version
                )
                check_profile_version = ""

                with PyTessBaseAPI(path=str(self.tesseract_path)) as api:
                    api.SetVariable("tessedit_char_whitelist", "Aclaim")
                    api.SetImage(Image.fromarray(im_check_more_info))  # type: ignore (pylance is messed up)
                    check_profile_version = api.GetUTF8Text()

                if "Acclaim" in check_profile_version:
                    ui_positions = rok_ui.ocr_regions
                    tap_positions = rok_ui.tap_positions
                else:
                    ui_positions = rok_ui.ocr_regions_old
                    tap_positions = rok_ui.tap_positions_old

                break

        if self.is_page_needed(1):
            self.state_callback("Scanning general page")

            # take screenshot before copying the name
            self.adb_client.secure_adb_screencap().save(self.img_path / "gov_info.png")
            image = load_cv2_img(self.img_path / "gov_info.png", cv2.IMREAD_UNCHANGED)

            if self.scan_options.name:
                # nickname copy
                copy_try = 0
                while copy_try < 3:
                    try:
                        self.adb_client.secure_adb_tap(
                            tap_positions["name_copy"]
                        )
                        wait_random_range(
                            self.timings["copy_wait"], self.max_random_delay
                        )
                        tk_clipboard = tkinter.Tk()
                        governor_data.name = tk_clipboard.clipboard_get()
                        tk_clipboard.destroy()
                        break
                    except:
                        console.log("Name copy failed, retying")
                        logging.log(logging.INFO, "Name copy failed, retying")
                        copy_try = copy_try + 1

            # 1st image data (ID, Power, Killpoints, Alliance)
            with PyTessBaseAPI(
                path=str(self.tesseract_path), psm=PSM.SINGLE_WORD, oem=OEM.LSTM_ONLY
            ) as api:
                if self.scan_options.power:
                    im_gov_power = cropToRegion(image, ui_positions["power"])
                    im_gov_power_bw = preprocessImage(im_gov_power, 3, 100, 12, True)

                    governor_data.power = ocr_number(api, im_gov_power_bw)

                if self.scan_options.killpoints:
                    im_gov_killpoints = cropToRegion(
                        image, ui_positions["killpoints"]
                    )
                    im_gov_killpoints_bw = preprocessImage(
                        im_gov_killpoints, 3, 100, 12, True
                    )

                    governor_data.killpoints = ocr_number(api, im_gov_killpoints_bw)

                api.SetPageSegMode(PSM.SINGLE_LINE)
                if self.scan_options.id:
                    im_gov_id = cropToRegion(image, ui_positions["gov_id"])
                    im_gov_id_gray = cv2.cvtColor(im_gov_id, cv2.COLOR_BGR2GRAY)
                    im_gov_id_gray = cv2.bitwise_not(im_gov_id_gray)
                    (thresh, im_gov_id_bw) = cv2.threshold(
                        im_gov_id_gray, 120, 255, cv2.THRESH_BINARY
                    )

                    governor_data.id = ocr_number(api, im_gov_id_bw)

                if self.scan_options.alliance:
                    im_alliance_tag = cropToRegion(
                        image, ui_positions["alliance_name"]
                    )
                    im_alliance_bw = preprocessImage(im_alliance_tag, 3, 50, 12, True)

                    governor_data.alliance = ocr_text(api, im_alliance_bw)

        if self.is_page_needed(2):
            # kills tier
            self.adb_client.secure_adb_tap(tap_positions["open_kills"])
            self.state_callback("Scanning kills page")
            wait_random_range(self.timings["kills_open"], self.max_random_delay)

            self.adb_client.secure_adb_screencap().save(
                self.img_path / "kills_tier.png"
            )
            image2 = load_cv2_img(
                self.img_path / "kills_tier.png", cv2.IMREAD_UNCHANGED
            )
            image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2RGB)

            with PyTessBaseAPI(
                path=str(self.tesseract_path), psm=PSM.SINGLE_WORD, oem=OEM.LSTM_ONLY
            ) as api:
                if self.scan_options.t1_kills:
                    # tier 1 Kills
                    governor_data.t1_kills = preprocess_and_ocr_number(
                        api, image2, ui_positions["t1_kills"]
                    )

                    # tier 1 KP
                    governor_data.t1_kp = preprocess_and_ocr_number(
                        api, image2, ui_positions["t1_killpoints"]
                    )

                if self.scan_options.t2_kills:
                    # tier 2 Kills
                    governor_data.t2_kills = preprocess_and_ocr_number(
                        api, image2, ui_positions["t2_kills"]
                    )

                    # tier 2 KP
                    governor_data.t2_kp = preprocess_and_ocr_number(
                        api, image2, ui_positions["t2_killpoints"]
                    )

                if self.scan_options.t3_kills:
                    # tier 3 Kills
                    governor_data.t3_kills = preprocess_and_ocr_number(
                        api, image2, ui_positions["t3_kills"]
                    )

                    # tier 3 KP
                    governor_data.t3_kp = preprocess_and_ocr_number(
                        api, image2, ui_positions["t3_killpoints"]
                    )

                if self.scan_options.t4_kills:
                    # tier 4 Kills
                    governor_data.t4_kills = preprocess_and_ocr_number(
                        api, image2, ui_positions["t4_kills"]
                    )

                    # tier 4 KP
                    governor_data.t4_kp = preprocess_and_ocr_number(
                        api, image2, ui_positions["t4_killpoints"]
                    )

                if self.scan_options.t5_kills:
                    # tier 5 Kills
                    governor_data.t5_kills = preprocess_and_ocr_number(
                        api, image2, ui_positions["t5_kills"]
                    )

                    # tier 5 KP
                    governor_data.t5_kp = preprocess_and_ocr_number(
                        api, image2, ui_positions["t5_killpoints"]
                    )

                if self.scan_options.ranged:
                    # ranged points
                    governor_data.ranged_points = preprocess_and_ocr_number(
                        api, image2, ui_positions["ranged_points"]
                    )

        if self.is_page_needed(3):
            # More info tab
            self.adb_client.secure_adb_tap(tap_positions["more_info"])
            self.state_callback("Scanning more info page")
            wait_random_range(self.timings["info_open"], self.max_random_delay)
            self.adb_client.secure_adb_screencap().save(self.img_path / "more_info.png")
            image3 = load_cv2_img(self.img_path / "more_info.png", cv2.IMREAD_UNCHANGED)

            with PyTessBaseAPI(
                path=str(self.tesseract_path), psm=PSM.SINGLE_WORD, oem=OEM.LSTM_ONLY
            ) as api:
                if self.scan_options.deaths:
                    governor_data.dead = preprocess_and_ocr_number(
                        api, image3, ui_positions["deads"], True
                    )

                if self.scan_options.assistance:
                    governor_data.rss_assistance = preprocess_and_ocr_number(
                        api, image3, ui_positions["rss_assisted"], True
                    )

                if self.scan_options.gathered:
                    governor_data.rss_gathered = preprocess_and_ocr_number(
                        api, image3, ui_positions["rss_gathered"], True
                    )

                if self.scan_options.helps:
                    governor_data.helps = preprocess_and_ocr_number(
                        api, image3, ui_positions["alliance_helps"], True
                    )

        # Just to check the progress, printing in cmd the result for each governor
        governor_data.flag_unknown()

        self.state_callback("Closing governor")
        if self.is_page_needed(3):
            self.adb_client.secure_adb_tap(
                tap_positions["close_info"]
            )  # close more info
            wait_random_range(self.timings["info_close"], self.max_random_delay)
        self.adb_client.secure_adb_tap(
            tap_positions["close_gov"]
        )  # close governor info
        wait_random_range(self.timings["gov_close"], self.max_random_delay)

        end_time = time.time()

        self.output_handler("Time needed for governor: " + str((end_time - start_time)))
        self.scan_times.append(end_time - start_time)

        return governor_data

    # ------------------------------------------------------------------
    # City Hall verification methods
    # ------------------------------------------------------------------

    def get_governors_needing_ch(
        self, data_list: list, min_power: int = 25_000_000
    ) -> List[GovernorData]:
        """Identify governors that need in-game CH verification.

        - Governors with power >= min_power are auto-assigned CH 25.
        - Returns governors with 0 < power < min_power and city_hall_level == 0.
        """
        needing_check = []
        for entry in data_list:
            gov_power = entry.get("Power", 0)
            gov_id = entry.get("ID", 0)
            current_ch = entry.get("City Hall Level", 0)

            if gov_power <= 0 or gov_id <= 0:
                continue

            if current_ch > 0:
                # Already set (e.g., from a resumed scan)
                continue

            if gov_power >= min_power:
                # Auto-assign CH 25 for high-power governors
                entry["City Hall Level"] = 25
            else:
                # Create a minimal GovernorData for the check
                gov = GovernorData(id=gov_id, power=gov_power)
                needing_check.append(gov)

        return needing_check

    def _navigate_to_search_screen(self, tap_positions: dict) -> None:
        """Navigate from the ranking list to the governor search screen."""
        if self._in_search_screen:
            return

        self.state_callback("Navigating to search screen")
        # Close any open panels
        self.adb_client.secure_adb_tap(tap_positions["back_button"])
        time.sleep(0.5)
        self.adb_client.secure_adb_tap(tap_positions["back_button"])
        time.sleep(0.5)

        # Open settings / search
        self.adb_client.secure_adb_tap(tap_positions["settings"])
        time.sleep(1.0)
        self.adb_client.secure_adb_tap(tap_positions["search_gov_button"])
        time.sleep(1.0)

        self._in_search_screen = True
        self._first_search = True  # Track first search to skip field clearing

    def check_city_hall_level(
        self, governor_id: str, tap_positions: dict
    ) -> int:
        """Look up a governor by ID and read their City Hall level.

        Uses template matching as the primary method with Tesseract OCR fallback.
        Returns the CH level (1-25) or 0 if identification fails.
        """
        # Navigate to search screen if not already there
        self._navigate_to_search_screen(tap_positions)

        # Clear previous ID (skip on first entry)
        if not self._first_search:
            # Tap the input field first
            self.adb_client.secure_adb_tap(tap_positions["id_input_field"])
            time.sleep(0.3)
            # Send DEL keys to clear the field
            for _ in range(15):
                self.adb_client.secure_adb_shell("input keyevent KEYCODE_DEL")
        else:
            # Tap input field on first search
            self.adb_client.secure_adb_tap(tap_positions["id_input_field"])
            time.sleep(0.3)
            self._first_search = False

        # Input governor ID
        self.adb_client.secure_adb_shell(f"input text {governor_id}")
        time.sleep(0.3)

        # Double-tap search button
        self.adb_client.secure_adb_tap(tap_positions["search_button"])
        time.sleep(0.3)
        self.adb_client.secure_adb_tap(tap_positions["search_button"])

        # Retry loop with exponential backoff
        backoff_times = [1.0, 1.5, 2.25]
        ch_level = 0

        for attempt, wait_time in enumerate(backoff_times):
            time.sleep(wait_time)

            # Take screenshot and crop the CH level region (with padding)
            screenshot = self.adb_client.secure_adb_screencap()
            screenshot_cv2 = pil_to_cv2(screenshot)
            crop = cropToRegion(screenshot_cv2, rok_ui.ch_level_region_padded)

            # Try to identify CH level
            ch_level = self._ch_matcher.identify(crop)

            if 1 <= ch_level <= 25:
                logger.info(
                    f"CH level for governor {governor_id}: {ch_level} "
                    f"(attempt {attempt + 1})"
                )
                return ch_level

            logger.debug(
                f"CH identification attempt {attempt + 1} failed for governor {governor_id}"
            )

        # All attempts failed — save debug image
        try:
            debug_path = self.img_path / f"ch_level_region_{governor_id}.png"
            write_cv2_img(crop, debug_path, "png")
            logger.warning(
                f"Failed to identify CH level for governor {governor_id}. "
                f"Debug image saved to {debug_path}"
            )
        except Exception as e:
            logger.warning(f"Failed to save debug image: {e}")

        return 0

    def _run_ch_verification_pass(
        self, data_handler: PandasHandler, tap_positions: dict
    ) -> None:
        """Second pass: verify City Hall levels for governors that need it."""
        if not self.config.scan.check_cityhall:
            return
        if self.stop_scan:
            return

        self.state_callback("Starting CH verification")
        self.output_handler("Starting City Hall level verification pass...")

        min_power = self.config.scan.ch_auto_assign_power
        governors_needing_ch = self.get_governors_needing_ch(
            data_handler.data_list, min_power
        )

        if not governors_needing_ch:
            self.output_handler("No governors need CH verification.")
            return

        self.output_handler(
            f"Verifying CH level for {len(governors_needing_ch)} governors..."
        )

        for i, gov in enumerate(governors_needing_ch):
            if self.stop_scan:
                self.output_handler("CH verification stopped.")
                break

            self.state_callback(
                f"Verifying CH: {i + 1}/{len(governors_needing_ch)}"
            )

            ch_level = self.check_city_hall_level(
                str(gov.id), tap_positions
            )

            if ch_level > 0:
                gov.city_hall_level = ch_level
                data_handler.update_governor(gov)
                data_handler.save()  # Incremental save for crash recovery

            # Emit progress callback
            self.gov_callback(
                gov,
                AdditionalData(
                    current_governor=i + 1,
                    target_governor=len(governors_needing_ch),
                    skipped_governors=0,
                    power_ok="Not Checked",
                    kills_ok="Not Checked",
                    reconstruction_success="Not Checked",
                    remaining_sec=0,
                    ch_verification_mode=True,
                    ch_current_governor=i + 1,
                    ch_total_governors=len(governors_needing_ch),
                ),
            )

        # Clean up: exit search screen
        if self._in_search_screen:
            self.adb_client.secure_adb_tap(tap_positions["back_button"])
            time.sleep(0.5)
            self.adb_client.secure_adb_tap(tap_positions["back_button"])
            self._in_search_screen = False

        data_handler.save()
        self.output_handler("CH verification pass complete.")

    def start_scan(
        self,
        kingdom: str,
        amount: int,
        resume: bool,
        track_inactives: bool,
        validate_kills: bool,
        reconstruct_fails: bool,
        validate_power: bool,
        power_threshold: int,
        formats: OutputFormats,
    ):
        self.state_callback("Initializing")
        self.adb_client.start_adb()
        if track_inactives:
            self.inactive_path.mkdir(parents=True, exist_ok=True)

        ######Excel Formatting
        # Resume Scan options. Refine the loop
        j = 0
        if resume:
            j = 4
            amount = amount + j

        if resume:
            file_name_prefix = "NEXT"
        else:
            file_name_prefix = "TOP"

        filename = f"{file_name_prefix}{amount - j}-{self.start_date}-{kingdom}-[{self.run_id}]"
        data_handler = PandasHandler(self.scan_path, filename, formats)

        # The loop in TOP XXX Governors in kingdom - It works both for power and killpoints Rankings
        # MUST have the tab opened to the 1st governor(Power or Killpoints)

        last_two = False
        next_gov_to_scan = -1
        last_gov_power = -1

        for i in range(j, amount):
            if self.stop_scan:
                self.output_handler("Scan Terminated! Saving the current progress...")
                break

            next_gov_to_scan = max(next_gov_to_scan + 1, i)
            gov_data = self.scan_governor(
                next_gov_to_scan,
                track_inactives,
            )

            # Check for duplicate governor
            if data_handler.is_duplicate(to_int_check(gov_data.id)):
                roi = (196, 698, 52, 27)
                self.adb_client.secure_adb_screencap().save(
                    self.img_path / "currentState.png"
                )
                image = load_cv2_img(
                    self.img_path / "currentState.png", cv2.IMREAD_UNCHANGED
                )

                im_ranking = cropToRegion(image, roi)
                im_ranking_bw = preprocessImage(im_ranking, 3, 90, 12, True)

                ranking = ""

                with PyTessBaseAPI(
                    path=str(self.tesseract_path),
                    psm=PSM.SINGLE_WORD,
                    oem=OEM.LSTM_ONLY,
                ) as api:
                    api.SetImage(Image.fromarray(im_ranking_bw))  # type: ignore (pylance is messed up)
                    ranking = api.GetUTF8Text()
                    ranking = re.sub("[^0-9]", "", ranking)

                if ranking == "" or to_int_check(ranking) != 999:
                    self.output_handler(
                        f"Duplicate governor detected, but current rank is {ranking}, trying a second time."
                    )
                    logging.log(
                        logging.INFO,
                        f"Duplicate governor detected, but current rank is {ranking}, trying a second time.",
                    )

                    # repeat scan with next governor
                    gov_data = self.scan_governor(next_gov_to_scan, track_inactives)
                else:
                    if not last_two:
                        last_two = True
                        next_gov_to_scan = 998
                        self.output_handler(
                            "Duplicate governor detected, switching to scanning of last two governors."
                        )
                        logging.log(
                            logging.INFO,
                            "Duplicate governor detected, switching to scanning of last two governors.",
                        )

                        # repeat scan with next governor
                        gov_data = self.scan_governor(next_gov_to_scan, track_inactives)
                    else:
                        self.output_handler(
                            "Reached final governor on the screen. Scan complete."
                        )
                        logging.log(
                            logging.INFO,
                            "Reached final governor on the screen. Scan complete.",
                        )
                        self.state_callback("Scan finished")
                        return

            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M:%S")

            kills_ok = "Not Checked"
            reconstruction_success = "Not Checked"
            if validate_kills:
                kills_ok = gov_data.validate_kills()
                if not kills_ok and reconstruct_fails:
                    reconstruction_success = gov_data.reconstruct_kills()

                    if reconstruction_success:
                        self.save_failed("kills", gov_data, True)
                    else:
                        self.save_failed("kills", gov_data, False)

            power_ok = "Not Checked"
            if validate_power:
                # TODO: Respect threshold here
                gov_power = to_int_check(gov_data.power)
                if gov_power == 0:
                    gov_power = -1

                power_ok = (gov_power != -1) and (
                    (last_gov_power == -1)
                    or (to_int_check(gov_data.power) < last_gov_power)
                )

                if power_ok:
                    last_gov_power = gov_power
                else:
                    self.save_failed("power", gov_data)

            # Write results in excel file
            data_handler.write_governor(gov_data)
            data_handler.save()

            additional_info = AdditionalData(
                current_governor=i + 1,
                target_governor=amount,
                skipped_governors=self.inactive_players,
                power_ok=str(power_ok),
                kills_ok=str(kills_ok),
                reconstruction_success=str(reconstruction_success),
                remaining_sec=self.get_remaining_time(amount - i),
            )

            self.gov_callback(gov_data, additional_info)

        data_handler.save()
        self.output_handler("Reached the target amount of people. Scan complete.")
        logging.log(logging.INFO, "Reached the target amount of people. Scan complete.")

        # --- City Hall verification second pass ---
        self._run_ch_verification_pass(data_handler, rok_ui.tap_positions)

        self.adb_client.kill_adb()  # make sure to clean up adb server
        self.state_callback("Scan finished")
        return

    def end_scan(self):
        self.stop_scan = True