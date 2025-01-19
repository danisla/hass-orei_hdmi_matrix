"""Platform to control OREI HDMI Matrix Device Switches"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    CONF_HOST,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)

import logging

from . import api as matrix_api

_LOGGER = logging.getLogger(__name__)


class OREIHDMIMatrixSystemSwitch(SwitchEntity):
    def __init__(self, host, name, status_field="", switch_method=None):
        self._host = host
        self._name = f"OREI HDMI Matrix - {name}"
        self._state = False
        self._status_field = status_field
        self._switch_method = switch_method

    def update(self):
        """Retrieve latest state."""
        system_status = matrix_api.get_system_status(self._host)
        if system_status is None:
            self._state = STATE_UNKNOWN
            return
        state = system_status.get(self._status_field, None)
        if state is not None:
            self._state = state == 1

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state

    def turn_on(self, **kwargs):
        self._state = True
        self._switch_method(self._host, True)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        self._state = False
        self._switch_method(self._host, False)
        self.schedule_update_ha_state()


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the OREI HDMI Matrix switch platform."""
    host = config.get(CONF_HOST)

    add_entities(
        [
            OREIHDMIMatrixSystemSwitch(host, "Power", "power", matrix_api.set_power),
            OREIHDMIMatrixSystemSwitch(
                host, "Panel Lock", "lock", matrix_api.set_panel_lock
            ),
            OREIHDMIMatrixSystemSwitch(host, "Beep", "beep", matrix_api.set_beep),
        ]
    )
