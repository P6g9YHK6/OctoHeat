import octoprint.plugin
import flask
import logging
import threading
import time

from octoprint_octoheat import const
from octoprint_octoheat.controller import HeaterController

logger = logging.getLogger(__name__)


class OctoHeatPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SimpleApiPlugin,
):

    def __init__(self):
        self._controller = None
        self._poll_thread = None
        self._poll_running = False

    def get_settings_defaults(self):
        return {
            const.SETTING_HA_URL: "http://homeassistant:8123",
            const.SETTING_HA_TOKEN: "",
            const.SETTING_HA_TEMP_SENSOR: "",
            const.SETTING_HA_HEATER_SWITCH: "",
            const.SETTING_TRIGGER: "bed_set",
            const.SETTING_OFF_CONDITION: "bed_unset",
            const.SETTING_TEMP_MODE: "direct",
            const.SETTING_TARGET_TEMP: 45,
            const.SETTING_OFFSET_VALUE: 10,
            const.SETTING_OFFSET_PERCENT: 15,
            const.SETTING_OFFSET_TYPE: "raw",
            const.SETTING_HYSTERESIS: 2,
            const.SETTING_UPDATE_INTERVAL: 30,
            const.SETTING_TEMP_TIMEOUT: 120,
            const.SETTING_HEATER_MODE: const.HEATER_MODE_AUTO,
            const.SETTING_THERMAL_RUNAWAY_TEMP: 80,
            const.SETTING_THERMAL_RUNAWAY_ENABLED: True,
            const.SETTING_THERMAL_RUNAWAY_TRIGGERED: False,
        }

    def on_after_startup(self):
        self._controller = HeaterController(self._settings)
        self._controller.set_printer(self._printer)
        self._start_polling()

    def on_shutdown(self):
        self._stop_polling()
        if self._controller:
            self._controller.turn_off_heater()

    def on_startup(self, host, port):
        pass

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_events=True),
            dict(type="settings", name="OctoHeat"),
        ]

    def get_template_vars(self):
        return {
            "plugin_version": __plugin_version__,
        }

    def get_assets(self):
        return {
            "js": ["js/octoheat.js"],
            "css": ["css/octoheat.css"],
        }

    def get_api_commands(self):
        return {
            "getStatus": [],
            "testHaConnection": [],
            "cycleHeaterMode": [],
            "setHeaterMode": ["mode"],
        }

    def on_api_command(self, command, data):
        if command == "getStatus":
            status = self._controller.get_status() if self._controller else {}
            return flask.jsonify(status)
        elif command == "testHaConnection":
            from octoprint_octoheat.ha_client import HomeAssistantClient
            ha_url = self._settings.get([const.SETTING_HA_URL])
            ha_token = self._settings.get([const.SETTING_HA_TOKEN])
            if not ha_url or not ha_token:
                return flask.jsonify({"success": False, "error": "HA URL or token not set"})
            client = HomeAssistantClient(ha_url, ha_token)
            success = client.test_connection()
            return flask.jsonify({"success": success})
        elif command == "cycleHeaterMode":
            result = self._controller.cycle_heater_mode() if self._controller else {}
            return flask.jsonify(result)
        elif command == "setHeaterMode":
            mode = data.get("mode") if data else None
            if not mode:
                return flask.jsonify({"error": "mode is required"})
            result = self._controller.set_heater_mode(mode) if self._controller else {}
            return flask.jsonify(result)

    def _start_polling(self):
        if self._poll_running:
            return
        self._poll_running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _stop_polling(self):
        self._poll_running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=5)
            self._poll_thread = None

    def _poll_loop(self):
        while self._poll_running:
            try:
                if self._controller:
                    status = self._controller.run_control_cycle()
                    self._send_status_message(status)
            except Exception as e:
                logger.error(f"Control cycle error: {e}")

            interval = self._settings.get([const.SETTING_UPDATE_INTERVAL]) or 30
            time.sleep(interval)

    def _send_status_message(self, status):
        self._plugin_manager.send_plugin_message(self._identifier, status)

    def on_printer_state_changed(self, state, data):
        pass

    def check_and_control(self):
        if self._controller:
            status = self._controller.run_control_cycle()
            self._send_status_message(status)

    def get_update_information(self):
        return {
            "octoheat": {
                "displayName": "OctoHeat",
                "displayVersion": __plugin_version__,
                "type": "github_release",
                "user": "P6g9YHK6",
                "repo": "OctoHeat",
                "current": __plugin_version__,
                "pip": "https://github.com/P6g9YHK6/OctoHeat/archive/{target_version}.zip",
            }
        }


__plugin_implementation__ = OctoHeatPlugin()

__plugin_name__ = "OctoHeat"
__plugin_version__ = "1.1.0"
__plugin_description__ = "Control a heater via Home Assistant based on temperature sensor readings"
__plugin_author__ = "P6g9YHK6"
__plugin_url__ = "https://github.com/P6g9YHK6/OctoHeat"
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7"
__plugin_privacypolicy__ = "https://github.com/P6g9YHK6/OctoHeat/blob/main/PRIVACY.md"