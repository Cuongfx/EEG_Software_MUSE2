class MuseData:
    def __init__(self):
        self.data = []

    def add_data(self, new_data):
        self.data.append(new_data)

    def process_data(self):
        # Implement data processing logic here
        pass

    def get_data(self):
        return self.data

    def clear_data(self):
        self.data.clear()