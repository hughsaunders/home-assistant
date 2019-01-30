"""
Support for controlling an Atlona Juno 451 HDMI switch.

"""
import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA, SUPPORT_SELECT_SOURCE, SUPPORT_TURN_OFF, SUPPORT_TURN_ON,
    MediaPlayerDevice)
from homeassistant.const import (
    CONF_HOST, CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_PORT, STATE_OFF, STATE_ON)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['pyatlonajuno==0.1.2']

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 23

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_NAME, default="atlonajuno"): cv.string,
})


SUPPORT_AtlonaJuno = SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Atlona Juno platform."""
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    name = config.get(CONF_NAME)

    if 'atlonajuno' not in hass.data:
        hass.data['atlonajuno'] = {}
    hass_data = hass.data['atlonajuno']

    device_label = "{}:{}".format(host, port)
    if device_label in hass_data:
        return

    device = AtlonaJunoDevice(username, password, host, port, name)
    hass_data[device_label] = device
    add_entities([device], True)


def format_input_source(input_source_name, input_source_number):
    """Format input source for display in UI."""
    return "{} {}".format(input_source_name, input_source_number)


class AtlonaJunoDevice(MediaPlayerDevice):
    """Representation of a AtlonaJuno device."""

    def __init__(self, username, password, host, port, name):
        """Iinitialize the AtlonaJuno device."""
        self._username = username
        self._password = password
        self._host = host
        self._port = port
        self._name = name
        self._pwstate = STATE_OFF
        self._current_source = None
        self._source_list = [1,2,3,4]
        self.juno = self.create_juno()

    def create_juno(self):
        """Create Juno451 Instance."""
        from pyatlonajuno.lib import Juno451
        return Juno451(self._username, self._password, self._host, self._port)

    def update(self):
        """Get the latest state from the device."""
        pwstate = self.juno.getPowerState()
        if pwstate == 'off':
            self._pwstate = STATE_OFF
        else:
            self._pwstate = STATE_ON
        self._current_source = self.juno.getSource()

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._pwstate

    @property
    def source(self):
        """Return current input source."""
        return self._current_source
    
    @property
    def source_list(self):
        """Return all available input sources."""
        return self._source_list

    @property
    def supported_features(self):
        """Return supported features."""
        return SUPPORT_AtlonaJuno

    def turn_off(self):
        """Turn hdmi switch off."""
        self.juno.setPowerState("off")

    def turn_on(self):
        """Turn hdmi switch on."""
        self.juno.setPowerState("on")

    def select_source(self, source):
        """Set the input source."""
        self.juno.setSource(source)
