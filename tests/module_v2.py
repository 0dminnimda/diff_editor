# Configuration settings V2
DATABASE_HOST = "db.production.com" # Changed host
DEBUG_MODE = False
TIMEOUT = 30 # New setting

def connect_to_db(timeout=TIMEOUT):
    print(f"Connecting to {DATABASE_HOST} with timeout {timeout}...")
    # Placeholder for connection logic
    if not DEBUG_MODE:
        print("Production mode active.")
    return True

def new_feature():
    print("Implementing new feature!")

if __name__ == "__main__":
    connect_to_db()
    new_feature()