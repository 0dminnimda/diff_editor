# Configuration settings V1
DATABASE_HOST = "localhost"
DEBUG_MODE = False

def connect_to_db():
    print(f"Connecting to {DATABASE_HOST}...")
    # Placeholder for connection logic
    if DEBUG_MODE:
        print("Debug mode is active.")
    return True

def utility_function():
    return "This function will be removed."

if __name__ == "__main__":
    connect_to_db()