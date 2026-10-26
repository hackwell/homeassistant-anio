"""Little load for SD cards: static attributes stay out of the database."""

from __future__ import annotations

import pytest

from custom_components.anio.binary_sensor import (
    AnioGeofenceSensor,
    AnioSchoolWaySensor,
    AnioSilenceActiveSensor,
)
from custom_components.anio.sensor import AnioNextAlarmSensor
from custom_components.anio.switch import (
    AnioSchoolWayTimeSwitch,
    AnioSilenceTimeEntrySwitch,
    AnioSilenceTimeSwitch,
)


@pytest.mark.parametrize(
    ("entity_class", "attributes"),
    [
        (AnioSchoolWaySensor, {"periods"}),
        (AnioSilenceActiveSensor, {"periods"}),
        (AnioGeofenceSensor, {"latitude", "longitude", "radius_meters", "active_from"}),
        (AnioSilenceTimeSwitch, {"periods", "silence_time_count"}),
        (AnioSchoolWayTimeSwitch, {"start", "end", "days"}),
        (AnioSilenceTimeEntrySwitch, {"start", "end", "days"}),
        (AnioNextAlarmSensor, {"alarm_count", "enabled_count", "next_alarm_days"}),
    ],
)
def test_static_attributes_are_not_recorded(
    entity_class: type, attributes: set[str]
) -> None:
    """Test settings-like attributes are excluded from the recorder."""
    assert attributes <= entity_class._unrecorded_attributes
