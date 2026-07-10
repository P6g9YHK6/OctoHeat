import logging
import time
from typing import Optional

from octoprint_octoheat import const
from octoprint_octoheat.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


class HeaterController:
    def __init__(self, settings):
        self._settings = settings
        self._ha_client: Optional[HomeAssistantClient] = None
        self._heater_is_on = False
        self._last_chamber_temp: Optional[float] = None
        self._last_valid_temp_time: Optional[float] = None

    def _get_ha_client(self) -> Optional[HomeAssistantClient]:
        ha_url = self._settings.get([const.SETTING_HA_URL])
        ha_token = self._settings.get([const.SETTING_HA_TOKEN])

        if not ha_url or not ha_token:
            return None

        if self._ha_client is None:
            verify = self._settings.get([const.SETTING_HA_VERIFY_SSL])
            self._ha_client = HomeAssistantClient(ha_url, ha_token, verify_ssl=verify)

        return self._ha_client

    def _get_chamber_temp(self, ha_client: HomeAssistantClient) -> Optional[float]:
        sensor_entity = self._settings.get([const.SETTING_HA_TEMP_SENSOR])
        if not sensor_entity:
            return None
        return ha_client.get_sensor_state(sensor_entity)

    def _get_bed_target_temp(self) -> Optional[float]:
        try:
            printer_data = self._printer.get_data()
            bed_data = printer_data.get("printer", {}).get("temperature", {}).get("bed", {})
            target = bed_data.get("target")
            if target is not None and target > 0:
                return float(target)
            return None
        except Exception as e:
            logger.warning(f"Could not get bed target temp: {e}")
            return None

    def _get_print_state(self) -> Optional[str]:
        try:
            job_data = self._printer.get_current_job()
            if job_data and job_data.get("state"):
                return job_data["state"].lower()
            state_data = self._printer.get_state()
            if state_data:
                return state_data.lower()
            return None
        except Exception as e:
            logger.warning(f"Could not get print state: {e}")
            return None

    def _calculate_target_temp(self, ha_client: HomeAssistantClient) -> Optional[float]:
        temp_mode = self._settings.get([const.SETTING_TEMP_MODE])

        if temp_mode == const.TEMP_MODE_DIRECT:
            return float(self._settings.get([const.SETTING_TARGET_TEMP]))

        bed_temp = self._get_bed_target_temp()
        if bed_temp is None:
            return None

        offset_type = self._settings.get([const.SETTING_OFFSET_TYPE])

        if offset_type == const.OFFSET_TYPE_RAW:
            offset = float(self._settings.get([const.SETTING_OFFSET_VALUE]))
        else:
            offset = bed_temp * (float(self._settings.get([const.SETTING_OFFSET_PERCENT])) / 100.0)

        return bed_temp + offset

    def _check_thermal_runaway(self, ha_client: HomeAssistantClient, chamber_temp: Optional[float]) -> bool:
        if not self._settings.get([const.SETTING_THERMAL_RUNAWAY_ENABLED]):
            return False

        if chamber_temp is None:
            return False

        threshold = self._settings.get([const.SETTING_THERMAL_RUNAWAY_TEMP]) or 80
        if chamber_temp >= threshold:
            logger.warning(f"Thermal runaway threshold exceeded: {chamber_temp}°C >= {threshold}°C")
            return True

        return False

    def _should_heater_be_on(self, ha_client: HomeAssistantClient) -> bool:
        trigger = self._settings.get([const.SETTING_TRIGGER])

        if trigger == const.TRIGGER_BED_SET:
            bed_target = self._get_bed_target_temp()
            return bed_target is not None and bed_target > 0

        elif trigger == const.TRIGGER_PRINT_RUNNING:
            state = self._get_print_state()
            return state in const.PRINT_ACTIVE_STATES

        elif trigger == const.TRIGGER_THERMOSTAT:
            chamber_temp = self._get_chamber_temp(ha_client)
            if chamber_temp is None:
                return False

            target_temp = self._calculate_target_temp(ha_client)
            if target_temp is None:
                return False

            hysteresis = float(self._settings.get([const.SETTING_HYSTERESIS]))
            return chamber_temp < target_temp - hysteresis

        return False

    def _should_heater_be_off(self, ha_client: HomeAssistantClient) -> bool:
        off_condition = self._settings.get([const.SETTING_OFF_CONDITION])

        if off_condition == const.OFF_CONDITION_BED_UNSET:
            bed_target = self._get_bed_target_temp()
            return bed_target is None or bed_target == 0

        elif off_condition == const.OFF_CONDITION_PRINT_IDLE:
            state = self._get_print_state()
            return state is None or state not in const.PRINT_ACTIVE_STATES

        elif off_condition == const.OFF_CONDITION_THERMOSTAT:
            chamber_temp = self._get_chamber_temp(ha_client)
            if chamber_temp is None:
                return True

            target_temp = self._calculate_target_temp(ha_client)
            if target_temp is None:
                return True

            hysteresis = float(self._settings.get([const.SETTING_HYSTERESIS]))
            return chamber_temp >= target_temp + hysteresis

        return True

    def _turn_off_heater_internal(self, ha_client: HomeAssistantClient) -> None:
        switch_entity = self._settings.get([const.SETTING_HA_HEATER_SWITCH])
        if not switch_entity:
            return
        logger.info("Turning heater OFF")
        ha_client.turn_off_switch(switch_entity)
        self._heater_is_on = False

    def _turn_on_heater_internal(self, ha_client: HomeAssistantClient) -> None:
        switch_entity = self._settings.get([const.SETTING_HA_HEATER_SWITCH])
        if not switch_entity:
            return
        logger.info("Turning heater ON")
        ha_client.turn_on_switch(switch_entity)
        self._heater_is_on = True

    def set_printer(self, printer):
        self._printer = printer

    def set_heater_mode(self, mode: str) -> dict:
        if mode not in const.HEATER_MODE_OPTIONS:
            return {"error": f"Invalid mode: {mode}"}

        ha_client = self._get_ha_client()
        if ha_client is None:
            return {"error": "HA not configured"}

        old_mode = self._settings.get([const.SETTING_HEATER_MODE]) or const.HEATER_MODE_AUTO
        self._settings.set([const.SETTING_HEATER_MODE], mode)

        if mode == const.HEATER_MODE_MANUAL_ON:
            self._turn_on_heater_internal(ha_client)
            self._settings.set([const.SETTING_THERMAL_RUNAWAY_TRIGGERED], False)
        elif mode == const.HEATER_MODE_MANUAL_OFF:
            self._turn_off_heater_internal(ha_client)
        elif mode == const.HEATER_MODE_AUTO:
            self._settings.set([const.SETTING_THERMAL_RUNAWAY_TRIGGERED], False)
            chamber_temp = self._get_chamber_temp(ha_client)
            if self._check_thermal_runaway(ha_client, chamber_temp):
                self._turn_off_heater_internal(ha_client)
                self._settings.set([const.SETTING_HEATER_MODE], const.HEATER_MODE_MANUAL_OFF)
                self._settings.set([const.SETTING_THERMAL_RUNAWAY_TRIGGERED], True)
                return {"heater_mode": const.HEATER_MODE_MANUAL_OFF, "thermal_runaway_triggered": True}

        return {"heater_mode": mode, "thermal_runaway_triggered": False}

    def cycle_heater_mode(self) -> dict:
        current = self._settings.get([const.SETTING_HEATER_MODE]) or const.HEATER_MODE_AUTO

        if current == const.HEATER_MODE_AUTO:
            return self.set_heater_mode(const.HEATER_MODE_MANUAL_ON)
        elif current == const.HEATER_MODE_MANUAL_ON:
            return self.set_heater_mode(const.HEATER_MODE_MANUAL_OFF)
        else:
            return self.set_heater_mode(const.HEATER_MODE_AUTO)

    def run_control_cycle(self) -> dict:
        ha_client = self._get_ha_client()
        if ha_client is None:
            return {
                "error": "HA not configured",
                "heater_on": None,
                "chamber_temp": None,
                "target_temp": None,
                "heater_mode": None,
                "thermal_runaway_triggered": False,
            }

        chamber_temp = self._get_chamber_temp(ha_client)
        target_temp = self._calculate_target_temp(ha_client)
        heater_mode = self._settings.get([const.SETTING_HEATER_MODE]) or const.HEATER_MODE_AUTO
        thermal_triggered = self._settings.get([const.SETTING_THERMAL_RUNAWAY_TRIGGERED]) or False

        if chamber_temp is not None:
            self._last_valid_temp_time = time.time()
        else:
            timeout = self._settings.get([const.SETTING_TEMP_TIMEOUT]) or 120
            if self._last_valid_temp_time is not None:
                elapsed = time.time() - self._last_valid_temp_time
                if elapsed > timeout:
                    logger.warning(f"Temperature unavailable for {elapsed:.0f}s, turning heater OFF")
                    if self._heater_is_on:
                        self._turn_off_heater_internal(ha_client)
                    return {
                        "error": "Temp sensor timeout",
                        "heater_on": False,
                        "chamber_temp": None,
                        "target_temp": target_temp,
                        "heater_mode": heater_mode,
                        "thermal_runaway_triggered": thermal_triggered,
                    }

        if thermal_triggered:
            if self._heater_is_on:
                self._turn_off_heater_internal(ha_client)
            return {
                "error": None,
                "heater_on": False,
                "chamber_temp": chamber_temp,
                "target_temp": target_temp,
                "heater_mode": const.HEATER_MODE_MANUAL_OFF,
                "thermal_runaway_triggered": True,
            }

        if heater_mode != const.HEATER_MODE_AUTO:
            return {
                "error": None,
                "heater_on": self._heater_is_on,
                "chamber_temp": chamber_temp,
                "target_temp": target_temp,
                "heater_mode": heater_mode,
                "thermal_runaway_triggered": False,
            }

        if self._check_thermal_runaway(ha_client, chamber_temp):
            self._turn_off_heater_internal(ha_client)
            self._settings.set([const.SETTING_HEATER_MODE], const.HEATER_MODE_MANUAL_OFF)
            self._settings.set([const.SETTING_THERMAL_RUNAWAY_TRIGGERED], True)
            return {
                "error": None,
                "heater_on": False,
                "chamber_temp": chamber_temp,
                "target_temp": target_temp,
                "heater_mode": const.HEATER_MODE_MANUAL_OFF,
                "thermal_runaway_triggered": True,
            }

        should_be_on = self._should_heater_be_on(ha_client)
        should_be_off = self._should_heater_be_off(ha_client)

        if should_be_on and not should_be_off:
            self._turn_on_heater_internal(ha_client)
        elif should_be_off:
            self._turn_off_heater_internal(ha_client)

        return {
            "error": None,
            "heater_on": self._heater_is_on,
            "chamber_temp": chamber_temp,
            "target_temp": target_temp,
            "heater_mode": heater_mode,
            "thermal_runaway_triggered": False,
        }

    def turn_off_heater(self) -> None:
        ha_client = self._get_ha_client()
        if ha_client is None:
            return
        self._turn_off_heater_internal(ha_client)

    def get_status(self) -> dict:
        ha_client = self._get_ha_client()
        chamber_temp = None
        target_temp = None

        if ha_client:
            chamber_temp = self._get_chamber_temp(ha_client)
            target_temp = self._calculate_target_temp(ha_client)

        heater_mode = self._settings.get([const.SETTING_HEATER_MODE]) or const.HEATER_MODE_AUTO
        thermal_triggered = self._settings.get([const.SETTING_THERMAL_RUNAWAY_TRIGGERED]) or False

        return {
            "heater_on": self._heater_is_on,
            "chamber_temp": chamber_temp,
            "target_temp": target_temp,
            "heater_mode": heater_mode,
            "thermal_runaway_triggered": thermal_triggered,
            "ha_configured": ha_client is not None,
        }