from collections.abc import Mapping
from enum import Enum
import json
import logging
from threading import RLock
import time
import urllib.request

_LOGGER = logging.getLogger(__name__)


class ScalerModes(Enum):
    """Enum for setting the scaler mode."""

    BYPASS = 0
    SCALE_4K_1080P = 1
    AUTO = 3


class OutputCECCommands(Enum):
    """Enum for sending output a CEC command."""

    POWER_ON = 0
    POWER_OFF = 1
    VOLUME_MUTE = 2
    VOLUME_DOWN = 3
    VOLUME_UP = 4
    SOURCE = 5


class InputCECCommands(Enum):
    """Enum for sending input a CEC command."""

    POWER_ON = 1
    POWER_OFF = 2
    UP = 3
    LEFT = 4
    ENTER = 5
    RIGHT = 6
    MENU = 7
    DOWN = 8
    BACK = 9
    PREV = 10
    PLAY = 11
    NEXT = 12
    REWIND = 13
    PAUSE = 14
    FAST_FORWARD = 15
    STOP = 16
    VOLUME_MUTE = 17
    VOLUME_DOWN = 18
    VOLUME_UP = 19


class EDIDModes(Enum):
    """Enum for setting the EDID."""

    # 1080P,Stereo Audio 2.0
    EDID_1080P_STEREO_AUDIO_2_0 = 1
    # 1080P,Dolby/DTS 5.1
    EDID_1080P_DOLBY_DTS_5_1 = 2
    # 1080P,HD Audio 7.1
    EDID_1080P_HD_AUDIO_7_1 = 3
    # 1080I,Stereo Audio 2.0
    EDID_1080I_STEREO_AUDIO_2_0 = 4
    # 1080I,Dolby/DTS 5.1
    EDID_1080I_DOLBY_DTS_5_1 = 5
    # 1080I,HD Audio 7.1
    EDID_1080I_HD_AUDIO_7_1 = 6
    # 3D,Stereo Audio 2.0
    EDID_3D_STEREO_AUDIO_2_0 = 7
    # 3D,Dolby/DTS 5.1
    EDID_3D_DOLBY_DTS_5_1 = 8
    # 3D,HD Audio 7.1
    EDID_3D_HD_AUDIO_7_1 = 9
    # 4K2K30_444,Stereo Audio 2.0
    EDID_4K2K30_444_STEREO_AUDIO_2_0 = 10
    # 4K2K30_444,Dolby/DTS 5.1
    EDID_4K2K30_444_DOLBY_DTS_5_1 = 11
    # 4K2K30_444,HD Audio 7.1
    EDID_4K2K30_444_HD_AUDIO_7_1 = 12
    # 4K2K60_420,Stereo Audio 2.0
    EDID_4K2K60_420_STEREO_AUDIO_2_0 = 13
    # 4K2K60_420,Dolby/DTS 5.1
    EDID_4K2K60_420_DOLBY_DTS_5_1 = 14
    # 4K2K60_420,HD Audio 7.1
    EDID_4K2K60_420_HD_AUDIO_7_1 = 15
    # 4K2K60_444,Stereo Audio 2.0
    EDID_4K2K60_444_STEREO_AUDIO_2_0 = 16
    # 4K2K60_444,Dolby/DTS 5.1
    EDID_4K2K60_444_DOLBY_DTS_5_1 = 17
    # 4K2K60_444,HD Audio 7.1
    EDID_4K2K60_444_HD_AUDIO_7_1 = 18
    # 4K2K60_444,Stereo Audio 2.0 HDR
    EDID_4K2K60_444_STEREO_AUDIO_2_0_HDR = 19
    # 4K2K60_444,Dolby/DTS 5.1 HDR
    EDID_4K2K60_444_DOLBY_DTS_5_1_HDR = 20
    # 4K2K60_444,HD Audio 7.1 HDR
    EDID_4K2K60_444_HD_AUDIO_7_1_HDR = 21
    # User Define1
    EDID_USER_DEFINE_1 = 22
    # User Define2
    EDID_USER_DEFINE_2 = 23
    # COPY_FROM_OUT_1
    EDID_COPY_FROM_OUT_1 = 24
    # COPY_FROM_OUT_2
    EDID_COPY_FROM_OUT_2 = 25
    # COPY_FROM_OUT_3
    EDID_COPY_FROM_OUT_3 = 26
    # COPY_FROM_OUT_4
    EDID_COPY_FROM_OUT_4 = 27
    # COPY_FROM_OUT_5
    EDID_COPY_FROM_OUT_5 = 28
    # COPY_FROM_OUT_6
    EDID_COPY_FROM_OUT_6 = 29
    # COPY_FROM_OUT_7
    EDID_COPY_FROM_OUT_7 = 30
    # COPY_FROM_OUT_8
    EDID_COPY_FROM_OUT_8 = 31
    ### Model HDP-MXB88H150 ###
    # COPY_FROM_HDBT_OUT_1
    EDID_COPY_FROM_HDBT_OUT_1 = 32
    # COPY_FROM_HDBT_OUT_2
    EDID_COPY_FROM_HDBT_OUT_2 = 33
    # COPY_FROM_HDBT_OUT_3
    EDID_COPY_FROM_HDBT_OUT_3 = 34
    # COPY_FROM_HDBT_OUT_4
    EDID_COPY_FROM_HDBT_OUT_4 = 35
    # COPY_FROM_HDBT_OUT_5
    EDID_COPY_FROM_HDBT_OUT_5 = 36
    # COPY_FROM_HDBT_OUT_6
    EDID_COPY_FROM_HDBT_OUT_6 = 37
    # COPY_FROM_HDBT_OUT_7
    EDID_COPY_FROM_HDBT_OUT_7 = 38
    # COPY_FROM_HDBT_OUT_8
    EDID_COPY_FROM_HDBT_OUT_8 = 39


class HDMIMatrixAPI:
    """HDMI Matrix API abstration."""

    def __init__(self) -> None:
        """Initialize the API."""
        self._lock = RLock()
        self._cache: Mapping[str, (int, str)] = {}

    def _hdmi_matrix_cmd(self, host, cmd, use_cache=False):
        cmd["language"] = 0
        cache_key = cmd["comhead"]

        if use_cache:
            cached = self._cache.get(cache_key, None)
            if cached:
                (ts, data) = cached
                if time.time() - ts < 5:
                    _LOGGER.debug(f"Cache Hit: '{cache_key}'")
                    return json.loads(data)
                del self._cache[cache_key]

            _LOGGER.debug(f"Cache miss: '{cache_key}'")

        for _ in range(5):
            req = urllib.request.Request(
                f"http://{host}/cgi-bin/instr",
                data=json.dumps(cmd).encode("utf-8"),
                headers={"Accept": "application/json"},
                method="POST",
            )
            try:
                resp_data = None
                with urllib.request.urlopen(req, timeout=5) as r:
                    if r.getcode() == 200:
                        resp_data = json.load(r)
                        if self._validate_comhead_response(cmd["comhead"], resp_data):
                            self._cache[cache_key] = (
                                time.time(),
                                json.dumps(resp_data),
                            )
                            return resp_data

                        _LOGGER.error(
                            f"Invalid data from device for cmd: '{cmd}': '{resp_data}'"
                        )
                        resp_data = None
            except Exception as e:
                _LOGGER.error(f"Error connecting to the HDMI Matrix: {e}")

            time.sleep(1)

        return None

    def _validate_comhead_response(self, comhead, resp):
        valid = resp is not None and "comhead" in resp and resp["comhead"] == comhead
        if not resp:
            return False
        if comhead == "get video status":
            for field in ["allsource", "allinputname", "alloutputname"]:
                valid &= field in resp
        elif comhead == "get system status":
            for field in ["power", "baudrate", "beep", "lock", "mode", "version"]:
                valid &= field in resp
        elif comhead == "get output status":
            for field in [
                "allsource",
                "allscaler",
                "allhdcp",
                "allout",
                "allconnect",
                "allarc",
                "name",
            ]:
                valid &= field in resp
        elif comhead == "get input status":
            for field in ["edid", "inactive", "inname", "power"]:
                valid &= field in resp

        return valid

    def get_system_status(self, host):
        """Gets the system status"""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host, {"comhead": "get system status"}, use_cache=True
            )

    def get_video_status(self, host):
        """Get the video status."""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host, {"comhead": "get video status"}, use_cache=True
            )

    def get_output_status(self, host):
        """Get the output status."""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host, {"comhead": "get output status"}, use_cache=True
            )

    def get_input_status(self, host):
        """Get the input status."""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host, {"comhead": "get input status"}, use_cache=True
            )

    def video_switch(self, host, input_id, output_id):
        """Switch video source."""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host,
                {"comhead": "video switch", "source": [input_id, output_id]},
                use_cache=False,
            )

    def tx_stream(self, host, output_id, on_state):
        """Tx Stream switch."""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host,
                {"comhead": "tx stream", "out": [output_id, int(on_state)]},
                use_cache=False,
            )

    def set_arc(self, host, output_id, on_state):
        """Set ARC on output."""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host,
                {"comhead": "set arc", "arc": [output_id, int(on_state)]},
                use_cache=False,
            )

    def video_scaler(self, host, output_id, scaler_mode: ScalerModes):
        """Set video scaler."""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host,
                {"comhead": "video scaler", "scaler": [output_id, scaler_mode.value]},
                use_cache=False,
            )

    def set_input_edid(self, host, input_id, edid_mode: EDIDModes):
        """Set input EDID."""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host,
                {"comhead": "set edid", "edid": [input_id, edid_mode.value]},
                use_cache=False,
            )

    def output_cec_command(self, host, output_id, cmd: OutputCECCommands):
        """Send output a CEC command"""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host,
                {
                    "comhead": "cec command",
                    "object": 1,
                    "port": [1 if i == output_id else 0 for i in range(8)],
                    "index": cmd.value,
                },
                use_cache=False,
            )

    def input_cec_command(self, host, input_id, cmd: InputCECCommands):
        """Send output a CEC command"""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host,
                {
                    "comhead": "cec command",
                    "object": 0,
                    "port": [1 if i == input_id else 0 for i in range(8)],
                    "index": cmd.value,
                },
                use_cache=False,
            )

    def power_on(self, host):
        """Send command to power on and exit standby"""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host,
                {"comhead": "set poweronoff", "power": 1},
                use_cache=False,
            )

    def standby(self, host):
        """Send command to enter standby"""
        with self._lock:
            return self._hdmi_matrix_cmd(
                host,
                {"comhead": "set poweronoff", "power": 0},
                use_cache=False,
            )
