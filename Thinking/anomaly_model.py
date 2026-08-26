import datetime
import numpy as np
from sklearn.ensemble import IsolationForest
from logger import get_logger

log = get_logger("thinking")

def get_active_hours(dt1, dt2):
    start = min(dt1, dt2)
    end = max(dt1, dt2)
    
    active_minutes = 0
    current = start
    while current < end:
        if 7 <= current.hour < 23:
            active_minutes += 5
        current += datetime.timedelta(minutes=5)
        
    return active_minutes / 60.0

def predict_anomaly(historical_datetimes, current_datetime, hours_since_last_seen):
    if not historical_datetimes:
        return False

    first_seen = min(historical_datetimes)
    days_of_data = (current_datetime - first_seen).total_seconds() / (3600 * 24)
    
    if days_of_data < 3.0:
        log.info(f"Only {days_of_data:.1f} days of data available. Fallback rules will apply.")
        return False
        
    X_train = []
    sorted_history = sorted(historical_datetimes)
    
    for i in range(1, len(sorted_history)):
        dt = sorted_history[i]
        prev_dt = sorted_history[i-1]
        
        hour_of_day = dt.hour + dt.minute / 60.0
        active_gap = get_active_hours(prev_dt, dt)
        
        if active_gap > 0.1:
            X_train.append([hour_of_day, active_gap])
            
    if len(X_train) < 10:
        log.info("Not enough distinct historical gaps to train ML model.")
        return False
        
    X_train = np.array(X_train)
    
    model = IsolationForest(contamination="auto", random_state=42)
    model.fit(X_train)
    
    current_hour_of_day = current_datetime.hour + current_datetime.minute / 60.0
    prev_dt = current_datetime - datetime.timedelta(hours=hours_since_last_seen)
    current_active_gap = get_active_hours(prev_dt, current_datetime)
    
    X_test = np.array([[current_hour_of_day, current_active_gap]])
    
    prediction = model.predict(X_test)[0]
    
    mean_gap = np.mean(X_train[:, 1])
    std_gap = np.std(X_train[:, 1])
    
    if prediction == -1:
        if current_active_gap <= mean_gap + std_gap:
            log.info(f"ML flagged anomaly, but gap ({current_active_gap:.1f}h) is <= normal range (mean {mean_gap:.1f}h). Overriding to NORMAL.")
            return False
            
        log.warning(f"ML Anomaly detected! Current Hour: {current_hour_of_day:.1f}, Active Hours missing: {current_active_gap:.1f}")
        return True
        
    log.info(f"ML prediction: NORMAL. Current Hour: {current_hour_of_day:.1f}, Active Hours missing: {current_active_gap:.1f}")
    return False
