import json
import os

FILE = "failed_search.json"


class SearchLog:
    def __init__(self):
        if not os.path.exists(FILE):
            with open(FILE, "w") as f:
                json.dump([], f)

    def load(self):
        with open(FILE, "r") as f:
            return json.load(f)

    def save(self, data):
        with open(FILE, "w") as f:
            json.dump(data, f, indent=4)

    def add_searched_username(self, username, hash_code):
        data = self.load()
        data.append({"username": username, "user": hash_code})
        self.save(data)


searched_username_manager = SearchLog()
