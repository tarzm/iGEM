#!/usr/bin/env python3
from flask import Flask, jsonify, render_template, request
from threading import Event
from bioreactor_backend import BioreactorMonitor
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize monitor
monitor = BioreactorMonitor()
monitor.start_monitoring(interval=1.0)
shutdown_event = Event()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    data = monitor.get_current_data()
    return jsonify(data)


@app.route("/api/history", methods=["GET"])
def api_history():
    try:
        minutes = int(request.args.get("minutes", 30))
    except Exception:
        minutes = 30
    history = monitor.get_history(minutes=minutes)
    return jsonify({"minutes": minutes, "data": history})


@app.route("/api/fan", methods=["POST"])
def api_fan():
    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "").lower()
    if action == "start":
        monitor.fan_controller.start_fan()
    elif action == "stop":
        monitor.fan_controller.stop_fan()
    else:
        return jsonify({"error": "Invalid action. Use 'start' or 'stop'."}), 400
    return jsonify({"fan_running": monitor.fan_controller.fan_running})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        return jsonify({
            "fan_temp_threshold": monitor.fan_controller.temp_threshold
        })
    else:
        body = request.get_json(silent=True) or {}
        try:
            if "fan_temp_threshold" in body:
                monitor.fan_controller.temp_threshold = float(body["fan_temp_threshold"])
            return jsonify({
                "fan_temp_threshold": monitor.fan_controller.temp_threshold
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400

@app.teardown_appcontext
def shutdown_session(exception=None):
    if shutdown_event.is_set():
        try:
            monitor.stop_monitoring()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5050, debug=True)
    finally:
        shutdown_event.set()
