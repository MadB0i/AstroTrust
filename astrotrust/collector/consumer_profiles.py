"""Fixed fictional research inputs. Never accept participant or custom birth values."""

from __future__ import annotations

from types import MappingProxyType
from typing import Literal, get_args

from astrotrust.benchmark.models import Record
from astrotrust.benchmark.prompts import digest
from astrotrust.validation.files import canonical_json

PROFILE_VERSION = "consumer-profile-1.0"
SYNTHETIC_LABEL = "FICTIONAL / SYNTHETIC RESEARCH INPUT — NOT PARTICIPANT DATA"
ProfileID = Literal["consumer-profile-001", "not_used"]
ProfileField = Literal["date_of_birth", "birth_time", "birthplace", "timezone", "gender"]
PROFILE_FIELDS = get_args(ProfileField)


class SyntheticProfile(Record):
    profile_id: Literal["consumer-profile-001"]
    profile_version: Literal["consumer-profile-1.0"]
    research_input_label: Literal["FICTIONAL / SYNTHETIC RESEARCH INPUT — NOT PARTICIPANT DATA"]
    date_of_birth: Literal["1998-02-12"]
    birth_time: Literal["10:30"]
    birthplace: Literal["Guwahati, Assam, India"]
    timezone: Literal["Asia/Kolkata"]
    gender: Literal["male"]
    gender_use: Literal["only_when_service_requires_gender"]


PROFILES = MappingProxyType(
    {
        "consumer-profile-001": SyntheticProfile(
            profile_id="consumer-profile-001",
            profile_version=PROFILE_VERSION,
            research_input_label=SYNTHETIC_LABEL,
            date_of_birth="1998-02-12",
            birth_time="10:30",
            birthplace="Guwahati, Assam, India",
            timezone="Asia/Kolkata",
            gender="male",
            gender_use="only_when_service_requires_gender",
        )
    }
)


def profile_digest(profile: SyntheticProfile) -> str:
    """Hash the existing canonical_json UTF-8 encoding, including its framing LF."""
    return digest(canonical_json(profile))
