$(function() {
    function OctoHeatViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.loginStateViewModel = parameters[1];
        self.connectionTestResult = ko.observable("");

        self.heater_indicator = $("#heater_indicator");
        self.heater_icon = $("#heater_icon");
        self.heater_warning = $("#heater_warning");

        self.chamberTemp = ko.observable(null);
        self.targetTemp = ko.observable(null);
        self.heaterOn = ko.observable(null);
        self.heaterMode = ko.observable("auto");
        self.thermalRunawayTriggered = ko.observable(false);
        self.haConfigured = ko.observable(false);

        self.testHaConnection = function() {
            self.connectionTestResult("Testing...");
            OctoPrint.simpleApiCommand("octoheat", "testHaConnection")
                .done(function(response) {
                    if (response.success) {
                        self.connectionTestResult("Connected!");
                    } else {
                        self.connectionTestResult("Failed: " + (response.error || "Unknown error"));
                    }
                })
                .fail(function() {
                    self.connectionTestResult("Request failed");
                });
        };

        self._updateIcon = function() {
            var mode = self.heaterMode();
            var runaway = self.thermalRunawayTriggered();
            var isOn = self.heaterOn();
            var chamberTemp = self.chamberTemp();
            var targetTemp = self.targetTemp();
            var tempReached = chamberTemp !== null && targetTemp !== null && chamberTemp >= targetTemp;

            self.heater_indicator.removeClass("auto-heating auto-waiting auto-off on off runaway");
            self.heater_warning.hide();

            if (runaway) {
                self.heater_indicator.addClass("runaway");
                self.heater_warning.show();
            } else if (mode === "manual_on") {
                self.heater_indicator.addClass("on");
            } else if (mode === "manual_off") {
                self.heater_indicator.addClass("off");
            } else {
                if (isOn) {
                    self.heater_indicator.addClass("auto-heating");
                } else if (tempReached) {
                    self.heater_indicator.addClass("auto-waiting");
                } else {
                    self.heater_indicator.addClass("auto-off");
                }
            }
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "octoheat") return;

            if (data.chamber_temp !== undefined) {
                self.chamberTemp(data.chamber_temp);
            }
            if (data.target_temp !== undefined) {
                self.targetTemp(data.target_temp);
            }
            if (data.heater_on !== undefined) {
                self.heaterOn(data.heater_on);
            }
            if (data.heater_mode !== undefined) {
                self.heaterMode(data.heater_mode);
                self._updateIcon();
            }
            if (data.thermal_runaway_triggered !== undefined) {
                self.thermalRunawayTriggered(data.thermal_runaway_triggered);
                self._updateIcon();
            }
            if (data.ha_configured !== undefined) {
                self.haConfigured(data.ha_configured);
            }

            self._updateIcon();
        };

        self.requestStatus = function() {
            OctoPrint.simpleApiCommand("octoheat", "getStatus")
                .done(function(response) {
                    self.chamberTemp(response.chamber_temp);
                    self.targetTemp(response.target_temp);
                    self.heaterOn(response.heater_on);
                    self.heaterMode(response.heater_mode || "auto");
                    self.thermalRunawayTriggered(response.thermal_runaway_triggered || false);
                    self.haConfigured(response.ha_configured);
                    self._updateIcon();
                });
        };

        self.onStartup = function() {
            self._updateIcon();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: OctoHeatViewModel,
        dependencies: ["settingsViewModel", "loginStateViewModel"],
        elements: ["#settings_plugin_octoheat", "#heater_indicator"]
    });
});