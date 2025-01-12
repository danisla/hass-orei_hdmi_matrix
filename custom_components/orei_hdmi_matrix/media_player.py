"""Platform to control OREI HDMI Matrix."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player.const import DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_STATE,
    CONF_HOST,
    CONF_NAME,
    CONF_TYPE,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import api as matrix_api
from .const import (
    ATTR_ARC,
    ATTR_CEC_CMD,
    ATTR_CONNECT,
    ATTR_HDCP,
    ATTR_INPUT_ACTIVE,
    ATTR_INPUT_EDID,
    ATTR_INPUT_NUM,
    ATTR_SCALER_MODE,
    ATTR_SOURCE,
    ATTR_STREAM,
    CONF_ALL_SOURCE,
    CONF_ARC,
    CONF_CONNECT,
    CONF_EDID,
    CONF_HDCP,
    CONF_INPUT_ACTIVE,
    CONF_OUT,
    CONF_SCALER,
    CONF_SOURCES,
    CONF_ZONES,
    DATA_HDMIMATRIX,
    SERVICE_INPUT_CEC,
    SERVICE_OUTPUT_CEC,
    SERVICE_SET_ARC,
    SERVICE_SET_INPUT_EDID,
    SERVICE_SET_SCALER,
    SERVICE_SET_TX_STREAM,
    SERVICE_SET_ZONE,
)
from .orei_hdmi_matrix import (
    EDIDModes,
    InputCECCommands,
    OutputCECCommands,
    ScalerModes,
)

_LOGGER = logging.getLogger(__name__)

SUPPORT_HDMIMATRIX = MediaPlayerEntityFeature.SELECT_SOURCE

MEDIA_PLAYER_SCHEMA = vol.Schema(
    {
        ATTR_ENTITY_ID: cv.comp_entity_ids,
    }
)

ZONE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
    }
)

SOURCE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
    }
)

SERVICE_SET_ZONE_SCHEMA = MEDIA_PLAYER_SCHEMA.extend(
    {vol.Required(ATTR_SOURCE): cv.string}
)

SERVICE_SET_SCALER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_SCALER_MODE): cv.enum(ScalerModes),
    }
)

SERVICE_SET_ARC_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_STATE): cv.boolean,
    }
)

SERVICE_SET_TX_STREAM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_STATE): cv.boolean,
    }
)

SERVICE_SET_INPUT_EDID_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_INPUT_EDID): cv.enum(EDIDModes),
    }
)

SERVICE_OUTPUT_CEC_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_CEC_CMD): cv.enum(OutputCECCommands),
    }
)

SERVICE_INPUT_CEC_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_INPUT_NUM): vol.All(vol.Coerce(int), vol.In(range(1, 9))),
        vol.Required(ATTR_CEC_CMD): cv.enum(InputCECCommands),
    }
)

PLATFORM_SCHEMA = vol.All(
    cv.has_at_least_one_key(CONF_HOST),
    PLATFORM_SCHEMA.extend(
        {
            vol.Exclusive(CONF_HOST, CONF_TYPE): cv.string,
        }
    ),
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the HDMI Matrix platform."""

    if DATA_HDMIMATRIX not in hass.data:
        hass.data[DATA_HDMIMATRIX] = {}

    data = None
    connection = None
    host = config.get(CONF_HOST)
    if host is not None:
        data = matrix_api.get_video_status(host)
        if data is not None:
            connection = host

    if data is None or connection is None:
        _LOGGER.error(f"Failed to setup platform, unable to contact host at: {host}")
        return

    sources = dict(
        zip(range(1, len(data[CONF_SOURCES]) + 1), data[CONF_SOURCES], strict=False)
    )

    devices = []
    for zone_id, name in zip(
        range(1, len(data[CONF_ZONES]) + 1), data[CONF_ZONES], strict=False
    ):
        _LOGGER.info("Adding zone %d - %s", zone_id, name)
        unique_id = f"{connection}-{zone_id}"
        device = HDMIMatrixZone(connection, sources, zone_id, name)
        hass.data[DATA_HDMIMATRIX][unique_id] = device
        devices.append(device)

    add_entities(devices, True)

    def set_source_service_handle(service):
        """Handler for setting source service."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        source = service.data.get(ATTR_SOURCE)
        if entity_ids:
            devices = [
                device
                for device in hass.data[DATA_HDMIMATRIX].values()
                if device.entity_id in entity_ids
            ]
        else:
            devices = hass.data[DATA_HDMIMATRIX].values()

        for device in devices:
            if service.service == SERVICE_SET_ZONE:
                device.select_source(source)

    def set_scaler_mode_service_handle(service):
        """Handler for setting scaler mode service."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        scaler_mode = service.data.get(ATTR_SCALER_MODE)

        if entity_ids:
            devices = [
                device
                for device in hass.data[DATA_HDMIMATRIX].values()
                if device.entity_id in entity_ids
            ]
        else:
            devices = hass.data[DATA_HDMIMATRIX].values()

        for device in devices:
            if service.service == SERVICE_SET_SCALER:
                device.set_scaler_mode(scaler_mode)

    def set_arc_service_handle(service):
        """Handler for setting ARC service."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        state = service.data.get(ATTR_STATE)

        if entity_ids:
            devices = [
                device
                for device in hass.data[DATA_HDMIMATRIX].values()
                if device.entity_id in entity_ids
            ]
        else:
            devices = hass.data[DATA_HDMIMATRIX].values()

        for device in devices:
            if service.service == SERVICE_SET_ARC:
                device.set_arc(state)

    def set_tx_stream_service_handle(service):
        """Handler for setting TX Stream service."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        state = service.data.get(ATTR_STATE)

        if entity_ids:
            devices = [
                device
                for device in hass.data[DATA_HDMIMATRIX].values()
                if device.entity_id in entity_ids
            ]
        else:
            devices = hass.data[DATA_HDMIMATRIX].values()

        for device in devices:
            if service.service == SERVICE_SET_TX_STREAM:
                device.set_tx_stream(state)

    def set_input_edid_service_handle(service):
        """Handler for setting input EDID service."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        input_edid = service.data.get(ATTR_INPUT_EDID)

        if entity_ids:
            devices = [
                device
                for device in hass.data[DATA_HDMIMATRIX].values()
                if device.entity_id in entity_ids
            ]
        else:
            devices = hass.data[DATA_HDMIMATRIX].values()

        for device in devices:
            if service.service == SERVICE_SET_INPUT_EDID:
                device.set_input_edid(input_edid)

    def output_cec_command_service_handle(service):
        """Handler for sending output CEC command."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        cmd = service.data.get(ATTR_CEC_CMD)

        if entity_ids:
            devices = [
                device
                for device in hass.data[DATA_HDMIMATRIX].values()
                if device.entity_id in entity_ids
            ]
        else:
            devices = hass.data[DATA_HDMIMATRIX].values()

        for device in devices:
            if service.service == SERVICE_OUTPUT_CEC:
                device.output_cec_command(cmd)

    def input_cec_command_service_handle(service):
        """Handler for sending input CEC command."""
        input_id = service.data.get(ATTR_INPUT_NUM) - 1
        cmd = service.data.get(ATTR_CEC_CMD)
        matrix_api.input_cec_command(host, input_id, cmd)

    hass.services.register(
        DOMAIN,
        SERVICE_SET_ZONE,
        set_source_service_handle,
        schema=SERVICE_SET_ZONE_SCHEMA,
    )

    hass.services.register(
        DOMAIN,
        SERVICE_SET_SCALER,
        set_scaler_mode_service_handle,
        schema=SERVICE_SET_SCALER_SCHEMA,
    )

    hass.services.register(
        DOMAIN,
        SERVICE_SET_ARC,
        set_arc_service_handle,
        schema=SERVICE_SET_ARC_SCHEMA,
    )

    hass.services.register(
        DOMAIN,
        SERVICE_SET_TX_STREAM,
        set_tx_stream_service_handle,
        schema=SERVICE_SET_TX_STREAM_SCHEMA,
    )

    hass.services.register(
        DOMAIN,
        SERVICE_SET_INPUT_EDID,
        set_input_edid_service_handle,
        schema=SERVICE_SET_INPUT_EDID_SCHEMA,
    )

    hass.services.register(
        DOMAIN,
        SERVICE_OUTPUT_CEC,
        output_cec_command_service_handle,
        schema=SERVICE_OUTPUT_CEC_SCHEMA,
    )

    hass.services.register(
        DOMAIN,
        SERVICE_INPUT_CEC,
        input_cec_command_service_handle,
        schema=SERVICE_INPUT_CEC_SCHEMA,
    )


class HDMIMatrixZone(MediaPlayerEntity):
    """Representation of a HDMI matrix zone."""

    def __init__(self, host, sources, zone_id, zone_name):
        """Initialize new zone."""
        self._host = host
        self._source_id = STATE_UNKNOWN
        # dict source_id -> source name
        self._source_id_name = sources
        # dict source name -> source_id
        self._source_name_id = {v: k for k, v in sources.items()}
        # ordered list of all source names
        self._source_names = sorted(
            self._source_name_id.keys(), key=lambda v: self._source_name_id[v]
        )
        self._zone_id = zone_id
        self._name = f"OREI HDMI Matrix - {zone_name}"
        self._state = None
        self._source = None
        self._attributes = {
            CONF_HOST: self._host,
            ATTR_SCALER_MODE: STATE_UNKNOWN,
            ATTR_STREAM: STATE_UNKNOWN,
            ATTR_ARC: STATE_UNKNOWN,
            ATTR_CONNECT: STATE_UNKNOWN,
            ATTR_HDCP: STATE_UNKNOWN,
            ATTR_INPUT_EDID: STATE_UNKNOWN,
            ATTR_INPUT_ACTIVE: STATE_UNKNOWN,
        }

    def update(self):
        """Retrieve latest state."""
        video_status = matrix_api.get_video_status(self._host)
        if video_status is None:
            self._state = STATE_UNKNOWN
            return
        self._source_id = video_status[CONF_ALL_SOURCE][self._zone_id - 1]

        output_status = matrix_api.get_output_status(self._host)
        if output_status is None:
            self._state = STATE_UNKNOWN
            return

        input_status = matrix_api.get_input_status(self._host)
        if input_status is None:
            self._state = STATE_UNKNOWN
            return

        # The last zone_id is for "All Outputs" and does not have output status.
        if self._zone_id < 9:
            self._attributes[ATTR_SCALER_MODE] = ScalerModes(
                output_status[CONF_SCALER][self._zone_id - 1]
            ).name
            self._attributes[ATTR_STREAM] = (
                STATE_ON
                if output_status[CONF_OUT][self._zone_id - 1] == 1
                else STATE_OFF
            )
            self._attributes[ATTR_ARC] = (
                STATE_ON
                if output_status[CONF_ARC][self._zone_id - 1] == 1
                else STATE_OFF
            )
            self._attributes[ATTR_CONNECT] = (
                STATE_ON
                if output_status[CONF_CONNECT][self._zone_id - 1] == 1
                else STATE_OFF
            )
            self._attributes[ATTR_HDCP] = (
                STATE_ON
                if output_status[CONF_HDCP][self._zone_id - 1] == 1
                else STATE_OFF
            )
            self._attributes[ATTR_INPUT_EDID] = EDIDModes(
                input_status[CONF_EDID][self._source_id - 1] + 1
            ).name

            self._attributes[ATTR_INPUT_ACTIVE] = (
                STATE_ON
                if input_status[CONF_INPUT_ACTIVE][self._source_id - 1]
                else STATE_OFF
            )

        idx = self._source_id
        self._state = STATE_ON
        if idx in self._source_id_name:
            self._source = self._source_id_name[idx]
        else:
            self._source = None
        self._attr_extra_state_attributes = self._attributes

    @property
    def name(self):
        """Return the name of the zone."""
        return self._name

    @property
    def state(self):
        """Return the state of the zone."""
        return self._state

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_HDMIMATRIX

    @property
    def media_title(self):
        """Return the current source as media title."""
        return self._source

    @property
    def source(self):
        """Return the current input source of the device."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_names

    def select_source(self, source):
        """Set input source."""
        if source not in self._source_name_id:
            return
        idx = self._source_name_id[source]
        _LOGGER.info("Setting zone %d source to %s", self._zone_id, idx)

        matrix_api.video_switch(self._host, idx, self._zone_id)

    def set_scaler_mode(self, scaler_mode: ScalerModes):
        """Set scaler mode."""
        _LOGGER.info(
            f"Setting scaler mode for zone {self._zone_id} to value {scaler_mode.value}"
        )
        matrix_api.video_scaler(self._host, self._zone_id, scaler_mode.value)

    def set_arc(self, on_state):
        """Set ARC state"""
        _LOGGER.info(f"Setting ARC for zone {self._zone_id} to value {on_state}")
        matrix_api.set_arc(self._host, self._zone_id, on_state)

    def set_tx_stream(self, on_state):
        """Set output stream."""
        _LOGGER.info(f"Setting TX stream for zone {self._zone_id} to value {on_state}")
        matrix_api.tx_stream(self._host, self._zone_id, on_state)

    def set_input_edid(self, input_edid: EDIDModes):
        """Set EDID of selected source."""
        _LOGGER.info(f"Setting EDID of input {self._source_id} to {input_edid.name}")
        matrix_api.set_input_edid(self._host, self._source_id, input_edid)

    def output_cec_command(self, cmd: OutputCECCommands):
        """Send output CEC command."""
        _LOGGER.info(
            f"Sending output id {self._name}={self._zone_id} CEC command: {cmd.name}={cmd.value}"
        )
        matrix_api.output_cec_command(self._host, (self._zone_id - 1), cmd)
