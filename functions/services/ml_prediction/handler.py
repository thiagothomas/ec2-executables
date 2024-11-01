import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import json


def notify(message, notify=True):
    return json.dumps({"notify": notify, "message": message})


def generate_synthetic_data(num_samples=1000):
    # Generate random SpO2 values between 80 and 100
    spo2_values = np.random.uniform(80, 100, num_samples)

    # Generate random heartbeat values between 40 and 200
    heartbeat_values = np.random.uniform(40, 200, num_samples)

    labels = np.zeros(num_samples)

    for i in range(num_samples):
        if spo2_values[i] < 90 or heartbeat_values[i] > 100 or heartbeat_values[i] < 60:
            labels[i] = 1  # Problem detected
        else:
            labels[i] = 0  # No problem

    data = pd.DataFrame(
        {"SpO2": spo2_values, "Heartbeat": heartbeat_values, "Heart_Problem": labels}
    )

    return data


synthetic_data = generate_synthetic_data(2000)

X_train = synthetic_data[["SpO2", "Heartbeat"]].values
y_train = synthetic_data["Heart_Problem"].values

model = RandomForestClassifier(n_estimators=150, random_state=42)
model.fit(X_train, y_train)


def handle(req):
    vital_sign = json.loads(req)

    new_data = np.array([vital_sign["o2_sat"], vital_sign["pulse_rate"]]).reshape(1, -1)
    prediction = model.predict(new_data)

    if prediction[0] == 1:
        print("Heart problem risk detected.")
        return notify("Heart problem risk detected.", notify=True)
    else:
        print("No immediate heart problem risk.")
        return notify("No immediate heart problem risk.", notify=False)
