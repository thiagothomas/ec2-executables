import json

def alert(message):
    return json.dumps({"send_notification": True, "message": message})


def calculate_news2(
    resp_rate,
    hypercapnic_failure,
    o2_sat,
    o2_supplement,
    temperature,
    systolic_bp,
    pulse_rate,
    consciousness,
):
    score = 0

    score += calculate_resp_rate_score(resp_rate)
    score += calculate_o2_sat_score(o2_sat, hypercapnic_failure, o2_supplement)
    score += calculate_temperature_score(temperature)
    score += calculate_systolic_bp_score(systolic_bp)
    score += calculate_pulse_rate_score(pulse_rate)
    score += calculate_consciousness_score(consciousness)

    return score


def get_score(value, ranges):
    return next(
        (points for (low, high), points in ranges.items() if low <= value <= high), 0
    )


def calculate_resp_rate_score(resp_rate):
    resp_rate_ranges = {
        (0, 8): 3,
        (9, 11): 1,
        (12, 20): 0,
        (21, 24): 2,
        (25, float("inf")): 3,
    }
    return get_score(resp_rate, resp_rate_ranges)


def calculate_o2_sat_score(o2_sat, hypercapnic_failure, o2_supplement):
    score = 0
    o2_sat_ranges = (
        {(0, 83): 3, (84, 85): 2, (86, 87): 1, (88, 92): 0, (93, float("inf")): 0}
        if hypercapnic_failure
        else {(0, 91): 3, (92, 93): 2, (94, 95): 1, (96, float("inf")): 0}
    )

    score += get_score(o2_sat, o2_sat_ranges)

    # Supplemental O₂ adjustment
    if o2_supplement:
        score += 2
        if hypercapnic_failure:
            o2_supplement_ranges = {(93, 94): 1, (95, 96): 2, (97, float("inf")): 3}
            score += get_score(o2_sat, o2_supplement_ranges)

    return score


def calculate_temperature_score(temperature):
    temp_ranges = {
        (0, 35.0): 3,
        (35.1, 36.0): 1,
        (36.1, 38.0): 0,
        (38.1, 39.0): 1,
        (39.1, float("inf")): 2,
    }
    return get_score(temperature, temp_ranges)


def calculate_systolic_bp_score(systolic_bp):
    bp_ranges = {
        (0, 90): 3,
        (91, 100): 2,
        (101, 110): 1,
        (111, 219): 0,
        (220, float("inf")): 3,
    }
    return get_score(systolic_bp, bp_ranges)


def calculate_pulse_rate_score(pulse_rate):
    pulse_rate_ranges = {
        (0, 40): 3,
        (41, 50): 1,
        (51, 90): 0,
        (91, 110): 1,
        (111, 130): 2,
        (131, float("inf")): 3,
    }
    return get_score(pulse_rate, pulse_rate_ranges)


def calculate_consciousness_score(consciousness):
    return 3 if consciousness != "Alert" else 0


def handle(req):
    vital_sign = json.loads(req)

    score = calculate_news2(
        vital_sign["resp_rate"],
        vital_sign["hypercapnic_failure"],
        vital_sign["o2_sat"],
        vital_sign["o2_supplement"],
        vital_sign["temperature"],
        vital_sign["systolic_bp"],
        vital_sign["pulse_rate"],
        vital_sign["consciousness"],
    )

    return alert(f"NEWS2 score: {score}")
