#ifndef SENTINEL_CONFIG_H
#define SENTINEL_CONFIG_H

// Broches matérielles ESP32-S3
const int PIN_GREEN  = 6;
const int PIN_RED    = 15;
const int PIN_BUZZER = 18;

// Type de buzzer : true pour buzzer actif (HIGH=bip), false pour passif (PWM)
const bool BUZZER_IS_ACTIVE = true;

// Configuration Point d'Accès Wi-Fi
#ifndef WIFI_AP_SSID
#define WIFI_AP_SSID "SentinelAI"
#endif

#if __has_include("secrets.h")
#include "secrets.h"
#endif
#ifndef WIFI_AP_PASS
#define WIFI_AP_PASS "changeme"
#endif

#endif // SENTINEL_CONFIG_H
