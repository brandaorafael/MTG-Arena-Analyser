"""
Type definitions for MTG Arena Log Parser
"""

from typing import TypedDict, List


class CardInfo(TypedDict):
    """Structure of card information from the card database"""
    name: str
    expansion: str
    collector_number: str
    types: List[str]


class InstanceLocation(TypedDict):
    """Structure tracking a card instance's location"""
    grpId: int
    zone: int
    owner: int
    visibility: str
