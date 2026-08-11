import datetime

def write_conversation(entry):
    datestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    with open(f"journals/{datestamp}_conversations.log", "a") as file:
        file.write(f"{timestamp} - {entry}\n")


def get_conversations():
    datestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        with open(f"journals{datestamp}_conversations.log", "r") as file:
            entries = file.readlines()
        return entries
    except FileNotFoundError:
        return "No conversations yet - this is the first interaction."
