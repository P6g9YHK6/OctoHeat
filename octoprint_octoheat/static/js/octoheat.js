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
        self.heaterTitle = ko.observable("OctoHeat: click to cycle mode");

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
            var configured = self.haConfigured();
            var mode = self.heaterMode();
            var runaway = self.thermalRunawayTriggered();
            var isOn = self.heaterOn();
            var chamberTemp = self.chamberTemp();
            var targetTemp = self.targetTemp();
            var tempReached = chamberTemp !== null && targetTemp !== null && chamberTemp >= targetTemp;

            self.heater_indicator.removeClass("auto-heating auto-waiting auto-off on off runaway not-configured");
            self.heater_warning.hide();

            if (!configured) {
                self.heater_indicator.addClass("not-configured");
                self.heater_icon.html("\uD83D\uDD27");
                self.heaterTitle("OctoHeat: not configured \u2014 click to open settings");
                self.heater_indicator.off("click").on("click", function() {
                    OctoPrint.settings.show();
                    setTimeout(function() {
                        var el = $("#settings_plugin_octoheat");
                        if (el.length) el[0].scrollIntoView({ behavior: "smooth" });
                    }, 300);
                });
                return;
            }

            self.heater_indicator.off("click").on("click", function() {
                OctoPrint.simpleApiCommand("octoheat", "cycleHeaterMode");
            });
            self.heater_icon.html("\uD83D\uDCA4");

            if (runaway) {
                self.heater_indicator.addClass("runaway");
                self.heater_warning.show();
                self.heaterTitle("OctoHeat: THERMAL RUNAWAY - click to cycle mode");
            } else if (mode === "manual_on") {
                self.heater_indicator.addClass("on");
                self.heaterTitle("OctoHeat: manual ON - click to cycle mode");
            } else if (mode === "manual_off") {
                self.heater_indicator.addClass("off");
                self.heaterTitle("OctoHeat: manual OFF - click to cycle mode");
            } else {
                if (isOn) {
                    self.heater_indicator.addClass("auto-heating");
                    self.heaterTitle("OctoHeat: auto HEATING - click to cycle mode");
                } else if (tempReached) {
                    self.heater_indicator.addClass("auto-waiting");
                    self.heaterTitle("OctoHeat: auto idle (target reached) - click to cycle mode");
                } else {
                    self.heater_indicator.addClass("auto-off");
                    self.heaterTitle("OctoHeat: auto OFF - click to cycle mode");
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