from __future__ import annotations

import pytest

from fairy.core.services.preflight_profiles import ProfileNotFoundError, get_registry


def test_profiles_registry_lists_geo_and_generic():
    reg = get_registry()
    items = reg.list()
    ids = {i["id"] for i in items}

    # Don't require equality (future profiles will be added)
    assert {"geo", "generic"}.issubset(ids)


def test_profiles_registry_unknown_profile_raises():
    reg = get_registry()
    with pytest.raises(ProfileNotFoundError):
        reg.get("does_not_exist")
