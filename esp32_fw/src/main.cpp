#include <Arduino.h>
#include <WiFi.h>
#include <micro_ros_platformio.h>

#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <std_msgs/msg/int8.h>
#include <std_msgs/msg/string.h>

#include "config.h"

// Entités ROS 2
rcl_node_t node;
rclc_support_t support;
rcl_allocator_t allocator;
rclc_executor_t executor;

rcl_subscription_t led_sub;
rcl_subscription_t buzzer_sub;
rcl_publisher_t status_pub;

std_msgs__msg__Int8 led_msg;
std_msgs__msg__Int8 buzzer_msg;
std_msgs__msg__String status_msg;

// États internes
int led_state = 0;       // 0=off, 1=verte, 2=rouge
int buzzer_state = 0;    // 0=off, 1=alarme bips, 2=bip court
unsigned long last_agent_msg_time = 0;
unsigned long buzzer_start_time = 0;
unsigned long last_heartbeat_time = 0;
unsigned long buzzer_step_time = 0;
bool buzzer_toggle = false;

char status_buffer[64];

void apply_leds() {
    if (led_state == 1) {
        digitalWrite(PIN_GREEN, HIGH);
        digitalWrite(PIN_RED, LOW);
    } else if (led_state == 2) {
        digitalWrite(PIN_GREEN, LOW);
        digitalWrite(PIN_RED, HIGH);
    } else {
        digitalWrite(PIN_GREEN, LOW);
        digitalWrite(PIN_RED, LOW);
    }
}

void apply_buzzer(bool on) {
    if (BUZZER_IS_ACTIVE) {
        digitalWrite(PIN_BUZZER, on ? HIGH : LOW);
    } else {
        if (on) {
            tone(PIN_BUZZER, 2000);
        } else {
            noTone(PIN_BUZZER);
        }
    }
}

void led_callback(const void *msgin) {
    const std_msgs__msg__Int8 *msg = (const std_msgs__msg__Int8 *)msgin;
    led_state = msg->data;
    apply_leds();
    last_agent_msg_time = millis();
}

void buzzer_callback(const void *msgin) {
    const std_msgs__msg__Int8 *msg = (const std_msgs__msg__Int8 *)msgin;
    buzzer_state = msg->data;
    buzzer_start_time = millis();
    buzzer_step_time = millis();
    buzzer_toggle = false;
    if (buzzer_state == 0) {
        apply_buzzer(false);
    } else if (buzzer_state == 2) {
        apply_buzzer(true);
    }
    last_agent_msg_time = millis();
}

void setup() {
    // 1. Initialisation matérielle
    pinMode(PIN_GREEN, OUTPUT);
    pinMode(PIN_RED, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    apply_leds();
    apply_buzzer(false);

    // 2. Point d'accès Wi-Fi
    WiFi.mode(WIFI_AP);
    WiFi.softAP(WIFI_AP_SSID, WIFI_AP_PASS);

    // 3. micro-ROS transport série
    set_microros_serial_transports(Serial);
    delay(2000);

    allocator = rcl_get_default_allocator();

    // Initialisation support
    rclc_support_init(&support, 0, NULL, &allocator);

    // Création du nœud esp32_node
    rclc_node_init_default(&node, "esp32_node", "", &support);

    // Souscription /esp32/led_cmd
    rclc_subscription_init_default(
        &led_sub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int8),
        "/esp32/led_cmd"
    );

    // Souscription /esp32/buzzer_cmd
    rclc_subscription_init_default(
        &buzzer_sub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int8),
        "/esp32/buzzer_cmd"
    );

    // Publication /esp32/status
    rclc_publisher_init_default(
        &status_pub,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
        "/esp32/status"
    );

    // Initialisation exécuteur (2 abonnements)
    rclc_executor_init(&executor, &support.context, 2, &allocator);
    rclc_executor_add_subscription(&executor, &led_sub, &led_msg, &led_callback, ON_NEW_DATA);
    rclc_executor_add_subscription(&executor, &buzzer_sub, &buzzer_msg, &buzzer_callback, ON_NEW_DATA);

    status_msg.data.data = status_buffer;
    status_msg.data.capacity = sizeof(status_buffer);
    status_msg.data.size = 0;

    last_agent_msg_time = millis();
}

void loop() {
    rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
    unsigned long now = millis();

    // Gestion du buzzer
    if (buzzer_state == 1) { // alarme : bips répétés 150ms
        if (now - buzzer_step_time >= 150) {
            buzzer_step_time = now;
            buzzer_toggle = !buzzer_toggle;
            apply_buzzer(buzzer_toggle);
        }
    } else if (buzzer_state == 2) { // bip court : 150ms
        if (now - buzzer_start_time >= 150) {
            buzzer_state = 0;
            apply_buzzer(false);
        }
    }

    // Sécurité 1 : extinction buzzer après 10s max
    if (buzzer_state != 0 && (now - buzzer_start_time > 10000)) {
        buzzer_state = 0;
        apply_buzzer(false);
    }

    // Sécurité 2 : extinction totale si pas de message agent depuis 15s
    if (now - last_agent_msg_time > 15000 && last_agent_msg_time > 0) {
        led_state = 0;
        buzzer_state = 0;
        apply_leds();
        apply_buzzer(false);
    }

    // Heartbeat 1 Hz sur /esp32/status
    if (now - last_heartbeat_time >= 1000) {
        last_heartbeat_time = now;
        snprintf(status_buffer, sizeof(status_buffer), "{\"status\":\"ok\",\"uptime\":%lu}", now / 1000);
        status_msg.data.size = strlen(status_buffer);
        rcl_publish(&status_pub, &status_msg, NULL);
    }
}
