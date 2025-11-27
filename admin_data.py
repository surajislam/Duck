import uuid
import json
import os

DB_FILE = "users.json"


class AdminDB:
    def __init__(self):
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, "w") as f:
                json.dump([], f)

    def load(self):
        with open(DB_FILE, "r") as f:
            return json.load(f)

    def save(self, data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def create_user(self, name):
        users = self.load()

        hash_code = uuid.uuid4().hex[:8].upper()
        user = {
            "name": name,
            "hash_code": hash_code
        }

        users.append(user)
        self.save(users)
        return user

    def get_user_by_hash(self, hash_code):
        users = self.load()
        for user in users:
            if user["hash_code"] == hash_code:
                return user
        return None


admin_db = AdminDB()