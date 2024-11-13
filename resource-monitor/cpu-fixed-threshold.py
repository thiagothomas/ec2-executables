import psutil
import requests
import schedule
import threading
import time
from flask import Flask, jsonify

system_threshold = "NONE"

system_metrics = {}
smoothed_metrics = {"cpu": 0, "memory": 0, "bandwidth": 0}
thresholds = {"cpu": {"upper": 85, "lower": 60}, "memory": {"upper": 85, "lower": 60}}
observation = 0

app = Flask(__name__)


def calculate_smoothed_metric(prev_value, current_value, observation):
    if observation == 0:
        return current_value
    else:
        return (prev_value / 2) + (current_value / 2)


def check_thresholds():
    global system_threshold, smoothed_metrics, thresholds

    # Initialize threshold state as NONE
    upper_breach = False
    lower_breach = False

    # Check CPU thresholds
    if smoothed_metrics["cpu"] > thresholds["cpu"]["upper"]:
        upper_breach = True
    elif smoothed_metrics["cpu"] > thresholds["cpu"]["lower"]:
        lower_breach = True

    # Check Memory thresholds
    if smoothed_metrics["memory"] > thresholds["memory"]["upper"]:
        upper_breach = True
    elif smoothed_metrics["memory"] > thresholds["memory"]["lower"]:
        lower_breach = True

    if upper_breach:
        system_threshold = "UPPER"
    elif lower_breach:
        system_threshold = "LOWER"
    else:
        system_threshold = "NONE"


def update_system_metrics():
    global system_metrics, smoothed_metrics, observation

    while True:
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        net_io = psutil.net_io_counters()
        bandwidth_usage = net_io.bytes_sent + net_io.bytes_recv

        # Apply exponential smoothing to each metric
        smoothed_metrics["cpu"] = calculate_smoothed_metric(
            smoothed_metrics["cpu"], cpu_usage, observation
        )
        smoothed_metrics["memory"] = calculate_smoothed_metric(
            smoothed_metrics["memory"], memory_usage, observation
        )
        smoothed_metrics["bandwidth"] = calculate_smoothed_metric(
            smoothed_metrics["bandwidth"], bandwidth_usage, observation
        )
        observation += 1

        # Check if any resource exceeds the upper or lower threshold
        check_thresholds()

        system_metrics = {
            "cpuUsage": smoothed_metrics["cpu"],
            "memoryUsage": smoothed_metrics["memory"],
            "latency": smoothed_metrics["bandwidth"],
        }

        time.sleep(1.5)


def post_metrics():
    global system_metrics

    metrics = system_metrics

    url = "http://localhost:8082/resource-info"
    payload = {"metrics": metrics, "threshold": system_threshold}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        print(f"Failed to send metrics: {e}")


def start_scheduler():
    schedule.every(3).seconds.do(post_metrics)

    while True:
        schedule.run_pending()
        time.sleep(1)


@app.route("/node-metrics", methods=["GET"])
def get_node_metrics():
    global system_metrics
    global system_threshold

    metrics = system_metrics
    threshold = system_threshold

    payload = {"metrics": metrics, "threshold": threshold}

    return jsonify(payload)


if __name__ == "__main__":
    metric_thread = threading.Thread(target=update_system_metrics, daemon=True)
    metric_thread.start()

    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    # Start the Flask server to listen for incoming requests
    app.run(host="0.0.0.0", port=5050)
