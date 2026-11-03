def format_data(data):
    # Function to format data received from the Muse headset
    return [round(d, 2) for d in data]

def log_message(message):
    # Function to log messages to the console or a file
    print(message)

def validate_data(data):
    # Function to validate the data received from the Muse headset
    return isinstance(data, (list, tuple)) and all(isinstance(d, (int, float)) for d in data)