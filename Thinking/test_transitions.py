import os
import time

# Use a separate test database for these transition tests
os.environ["THINKING_DB"] = "SharedData/test_transitions_db.sqlite3"

from db import init_db, get_db_path, update_current_status, get_current_status

def setup_fresh_db():
    db_file = get_db_path()
    if db_file.exists():
        db_file.unlink()
    init_db()

def assert_status(location, expected_status, expected_danger_sources, step_name):
    current = get_current_status(location, clear_audio=False)
    
    if not current:
        print(f"❌ {step_name}: Status not found for location '{location}'")
        return False
        
    actual_status = current["status"]
    actual_sources = current["danger_sources"]
    
    # Sort for comparison just in case
    expected_danger_sources = sorted(expected_danger_sources)
    actual_sources = sorted(actual_sources)
    
    if actual_status == expected_status and actual_sources == expected_danger_sources:
        print(f"✅ {step_name}")
        return True
    else:
        print(f"❌ {step_name}")
        print(f"   Expected: status={expected_status}, danger_sources={expected_danger_sources}")
        print(f"   Actual:   status={actual_status}, danger_sources={actual_sources}")
        return False

def test_transitions():
    location = "LivingRoom"
    setup_fresh_db()
    
    print("\n=== Scenario 1: Initial Normal State ===")
    update_current_status(location, "ok", "detection")
    assert_status(location, "ok", [], "Visual detection sets status to OK")

    print("\n=== Scenario 2: Single Source Danger ===")
    update_current_status(location, "danger", "detection")
    assert_status(location, "danger", ["detection"], "Visual detection sets status to DANGER")

    print("\n=== Scenario 3: Single Source Danger Resolves ===")
    update_current_status(location, "ok", "detection")
    assert_status(location, "ok", [], "Visual detection resolves itself to OK")

    print("\n=== Scenario 4: Multiple Sources Danger ===")
    update_current_status(location, "danger", "detection")
    assert_status(location, "danger", ["detection"], "Visual detection detects danger")
    
    update_current_status(location, "danger", "inactive_posture")
    assert_status(location, "danger", ["detection", "inactive_posture"], "Posture check also detects danger")

    print("\n=== Scenario 5: Partial Resolution of Multiple Sources ===")
    update_current_status(location, "ok", "detection")
    assert_status(location, "danger", ["inactive_posture"], "Visual detection resolves, but overall status remains DANGER due to posture")

    print("\n=== Scenario 6: Full Resolution of Multiple Sources ===")
    update_current_status(location, "ok", "inactive_posture")
    assert_status(location, "ok", [], "Posture check resolves, overall status becomes OK")

    print("\n=== Scenario 7: Voice (STT) Overrides Visual Danger ===")
    update_current_status(location, "danger", "routine_anomaly")
    assert_status(location, "danger", ["routine_anomaly"], "Routine anomaly detects danger")
    
    update_current_status(location, "danger", "detection")
    assert_status(location, "danger", ["routine_anomaly", "detection"], "Visual detection also detects danger")
    
    # Resident speaks and says "I am okay"
    update_current_status(location, "ok", "stt")
    assert_status(location, "ok", [], "Voice confirmation (STT OK) clears ALL danger sources instantly")

    print("\n=== Scenario 8: Voice (STT) Danger is Persistent ===")
    update_current_status(location, "danger", "stt")
    assert_status(location, "danger", ["stt"], "Resident calls for help (STT DANGER)")
    
    update_current_status(location, "ok", "detection")
    assert_status(location, "danger", ["stt"], "Visual detection OK cannot clear STT DANGER")
    
    update_current_status(location, "ok", "inactive_posture")
    assert_status(location, "danger", ["stt"], "Posture OK cannot clear STT DANGER")
    
    update_current_status(location, "ok", "stt")
    assert_status(location, "ok", [], "Only another Voice confirmation (STT OK) clears STT DANGER")

    print("\n=== All tests completed ===")

if __name__ == "__main__":
    test_transitions()
