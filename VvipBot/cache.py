import time


class UserCache:
    TTL = 300

    def __init__(self):
        self._store: dict = {}

    def get(self, user_id: int):
        entry = self._store.get(user_id)
        if entry and time.monotonic() - entry[1] < self.TTL:
            return entry[0]
        return None

    def set(self, user_id: int, user_obj):
        self._store[user_id] = (user_obj, time.monotonic())

    def invalidate(self, user_id: int):
        self._store.pop(user_id, None)

    def clear(self):
        self._store.clear()


_user_cache = UserCache()