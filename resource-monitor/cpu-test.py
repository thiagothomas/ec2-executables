import psutil
import requests
import schedule
import threading
import time
from flask import Flask, jsonify

system_threshold = "NONE"

system_metrics = {}
smoothed_metrics = {"cpu": 0, "memory": 0, "bandwidth": 0}
thresholds = {"cpu": {"upper": 100, "lower": 40}, "memory": {"upper": 100, "lower": 60}}
prev_load = {"cpu": 0, "memory": 0, "bandwidth": 0}

observation = 0

app = Flask(__name__)


def reset_thresholds():
    global thresholds

    thresholds = {
        "cpu": {"upper": 100, "lower": 40},
        "memory": {"upper": 100, "lower": 60},
    }


def calculate_smoothed_metric(prev_value, current_value, observation):
    if observation == 0:
        return current_value
    else:
        return (prev_value / 2) + (current_value / 2)


def adapt_thresholds(resource, current_load):
    global thresholds, prev_load

    delta_load = current_load - prev_load[resource]
    print(f"Delta Load: {delta_load} for {resource}")
    if delta_load > 0:
        # Load increasing, adjust upper threshold
        thresholds[resource]["upper"] = max(
            thresholds[resource]["upper"] - delta_load, 0
        )
    elif delta_load < 0:
        # Load decreasing, adjust lower threshold
        thresholds[resource]["lower"] = min(
            thresholds[resource]["lower"] + abs(delta_load), 100
        )
    
    # if the lower threshold is greater than the upper threshold and the system threhsold is none, reset the lower thresholds
    if thresholds[resource]["lower"] > thresholds[resource]["upper"] and system_threshold == "NONE":
        reset_thresholds()

    # Update previous load
    prev_load[resource] = current_load


def check_thresholds():
    global system_threshold, smoothed_metrics, thresholds

    if system_threshold == "UPPER":
        # Check if the load has decreased below the upper threshold
        if (
            smoothed_metrics["cpu"] < thresholds["cpu"]["lower"]
            and smoothed_metrics["memory"] < thresholds["memory"]["lower"]
        ):
            reset_thresholds()
            system_threshold = "LOWER"
        else:
            return

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
    global system_metrics, smoothed_metrics, observation, prev_load
     # initialize previous load
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent
    net_io = psutil.net_io_counters()
    bandwidth_usage = net_io.bytes_sent + net_io.bytes_recv
    if (observation == 0):
        prev_load = {"cpu": cpu_usage, "memory": memory_usage, "bandwidth": bandwidth_usage}
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
        print(f"CPU_USAGE: {cpu_usage}, CPU_SMOOTHED: {smoothed_metrics['cpu']}")
    
        smoothed_metrics["bandwidth"] = calculate_smoothed_metric(
            smoothed_metrics["bandwidth"], bandwidth_usage, observation
        )
        observation += 1

        # Adapt thresholds for each metric
        adapt_thresholds("cpu", smoothed_metrics["cpu"])
        adapt_thresholds("memory", smoothed_metrics["memory"])

        # Check if any resource exceeds the upper or lower threshold
        check_thresholds()

        system_metrics = {
            "cpuUsage": smoothed_metrics["cpu"],
            "memoryUsage": smoothed_metrics["memory"],
            "latency": smoothed_metrics["bandwidth"],
        }

        print(
            f"System Metrics: {system_metrics}, Thresholds: {thresholds}, System Threshold: {system_threshold}"
        )

        time.sleep(15)


def post_metrics():
    global system_metrics

    metrics = system_metrics

    url = "http://localhost:8081/resource-info"
    payload = {"metrics": metrics, "threshold": system_threshold}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        print(f"Successfully sent metrics: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send metrics: {e}")


def start_scheduler():
    schedule.every(30).seconds.do(post_metrics)

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
    
