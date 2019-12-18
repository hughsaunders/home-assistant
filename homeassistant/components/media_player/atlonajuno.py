import datetime
import logging
import time
import os

import voluptuous as vol

from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOURCE, SUPPORT_TURN_OFF, SUPPORT_TURN_ON)
from homeassistant.components.media_player import (
    MediaPlayerDevice, PLATFORM_SCHEMA)
#from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_URL, CONF_NAME, STATE_OFF, STATE_ON)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['pyatlonajuno==0.1.2']

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_URL): cv.string,
    vol.Optional(CONF_NAME, default="atlonajuno"): cv.string,
})


SUPPORT_AtlonaJuno = SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Atlona Juno platform."""
    url = config.get(CONF_URL)
    name = config.get(CONF_NAME)

    if 'atlonajuno' not in hass.data:
        hass.data['atlonajuno'] = {}
    hass_data = hass.data['atlonajuno']

    if url in hass_data:
        return

    device = AtlonaJunoDevice(url, name, hass)
    hass_data[url] = device
    add_entities([device], True)


def format_input_source(input_source_name, input_source_number):
    """Format input source for display in UI."""
    return "{} {}".format(input_source_name, input_source_number)


class AtlonaJunoDevice(MediaPlayerDevice):
    """Representation of a AtlonaJuno device."""

    def __init__(self, url, name, hass):
        """Iinitialize the AtlonaJuno device."""
        self._url = url
        self._name = name
        self._hass = hass
        self._pwstate = STATE_OFF
        self._current_source = None
        self._source_list = [1,2,3,4]
        self._signal_detected = False
        self._signal_detected_raw = False
        self.signal_state_change_ts = datetime.datetime.now() - datetime.timedelta(minutes=2)
        self.juno = self.create_juno()
        self._signal_loss_count = 0

    def create_juno(self):
        """Create Juno451 Instance."""
        from pyatlonajuno.lib import Juno451
        return Juno451(self._url)

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return dict(
            signal_detected=self._signal_detected_raw
        )

    def update(self):
        """Get the latest state from the device."""
        pwstate = self.juno.getPowerState()
        if pwstate == 'off':
            self._pwstate = STATE_OFF
        else:
            self._pwstate = STATE_ON

            # The events fired here are mostly obsolete, as signal_detected
            # is now exposed as an entity attribute.

            # When power is on, we can detect if the currently selected
            # input is supplying a signal. A HASS event is fired
            # when signal is gained/lost so that automations can react
            # to sources being switched on/off. Signal loss events
            # are fired after consecutive loss readings to prevent
            # false events during source mode swithces.

            signal_detected = self.juno.getSignalDetected()
            self._signal_detected_raw = signal_detected

            # Reset signal lost count if signal is detected
            # 3 consecutive no signal readings are required to trigger
            # projector off, this prevents the projector being killed
            # during mode switching.
            if signal_detected == True:
                self._signal_loss_count = 0

            time_since_last_state_change = datetime.datetime.now() - self.signal_state_change_ts
            recently_switched = time_since_last_state_change < datetime.timedelta(minutes=1)

            if signal_detected != self._signal_detected:
                # new state is different to previous state
                # signal gained/lost

                if signal_detected == True:
                    # signal gained --> switch on immediately
                    self._signal_detected = True
                    self._hass.bus.fire('atlona_juno_signal_detected', {})
                else:
                    if not recently_switched:
                        # signal lost --> wait for 3 consecutive samples
                        # before firing event
                        self._signal_loss_count += 1
                        if self._signal_loss_count >= 3:
                            self._signal_detected = False
                            self._hass.bus.fire('atlona_juno_signal_lost', {})


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
