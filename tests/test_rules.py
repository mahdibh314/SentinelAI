"""Unit tests for SentinelAI access rules."""

import pytest
from sentinelai.rules import check_access

def test_unknown_user():
    granted, reason = check_access(None, "zone_interdite")
    assert not granted
    assert "inconnu" in reason.lower()

def test_inactive_user():
    user = {"code_id": "test_id", "name": "Inactive User", "grp": "Technique", "level": 3, "zone": "zone_interdite", "active": 0}
    granted, reason = check_access(user, "zone_interdite")
    assert not granted
    assert "inactif" in reason.lower()

def test_open_zone():
    user = {"code_id": "user_demo", "name": "Alice", "grp": "Technique", "level": 1, "zone": "zone_libre", "active": 1}
    granted, reason = check_access(user, "zone_libre")
    assert granted

def test_restricted_zone_denied():
    user = {"code_id": "user_demo", "name": "Alice", "grp": "Technique", "level": 1, "zone": "zone_libre", "active": 1}
    granted, reason = check_access(user, "zone_interdite")
    assert not granted
    assert "insuffisants" in reason.lower()

def test_restricted_zone_allowed_admin():
    user = {"code_id": "user_admin", "name": "Bob", "grp": "Direction", "level": 3, "zone": "zone_interdite", "active": 1}
    granted, reason = check_access(user, "zone_interdite")
    assert granted
