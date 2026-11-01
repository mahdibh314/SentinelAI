"""Temporisation des changements de zone (anti-clignotement)."""


class ZoneTracker:
    def __init__(self, confirm_seconds: float = 0.7):
        self.confirm_seconds = confirm_seconds
        self._state = {}  # track_id -> {"confirmed", "candidate", "since"}

    def update(self, track_id, raw_zone, now):
        """Retourne (zone_confirmée, a_changé) pour cette personne."""
        st = self._state.get(track_id)
        if st is None:  # première apparition : on prend la zone observée
            self._state[track_id] = {"confirmed": raw_zone, "candidate": raw_zone, "since": now}
            return raw_zone, True
        if raw_zone == st["confirmed"]:  # rien à changer, on annule tout candidat
            st["candidate"], st["since"] = raw_zone, now
            return st["confirmed"], False
        if raw_zone != st["candidate"]:  # nouvelle zone candidate : on démarre le chrono
            st["candidate"], st["since"] = raw_zone, now
            return st["confirmed"], False
        if now - st["since"] >= self.confirm_seconds:  # candidate stable assez longtemps
            st["confirmed"] = raw_zone
            return raw_zone, True
        return st["confirmed"], False
