from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass
from threading import Lock
from typing import Any


class CoordinationGroupID(str):
    """Identity of a group of coordinating users."""


@dataclass
class CoordinationMessage:
    """Message exchanged between members of the specified coordination group in order to coordinate."""

    group_id: CoordinationGroupID | None
    subject: str
    content: Any


class CoordinationSubscriber(ABC):
    """Base class for subscribers wishing to receive CoordinationEvent messages from other members of their coordination group."""

    def receive_coordination_message(self, msg: CoordinationMessage) -> None:
        raise NotImplementedError()


class CoordinationGroup:
    lock: Lock
    subscribers: set[CoordinationSubscriber]
    messages: list[CoordinationMessage]
    shared_sets: dict[str, set[Any]]

    def __init__(self):
        self.lock = Lock()
        self.subscribers = set()
        self.messages = []
        self.shared_sets = {}


class Coordinator:
    """Entity that handles pubsub messages for identified coordination groups."""

    _groups: dict[CoordinationGroupID, CoordinationGroup]

    def __init__(self, coordination_groups: Sequence[CoordinationGroupID]):
        """coordination_groups must identify all coordination groups that will be used."""
        self._groups = {g: CoordinationGroup() for g in coordination_groups}

    def publish(
        self, group_id: CoordinationGroupID, subject: str, content: Any
    ) -> None:
        """group_id must be among the coordination_groups identified when Coordinator was instantiated."""
        msg = CoordinationMessage(
            group_id=group_id,
            subject=subject,
            content=content,
        )
        group = self._groups[group_id]
        with group.lock:
            for subscriber in group.subscribers:
                subscriber.receive_coordination_message(msg)
            group.messages.append(msg)

    def subscribe(
        self, subscriber: CoordinationSubscriber, group_id: CoordinationGroupID
    ) -> None:
        group = self._groups[group_id]
        with group.lock:
            group.subscribers.add(subscriber)
            for msg in group.messages:
                subscriber.receive_coordination_message(msg)

    def shared_set(self, group_id: CoordinationGroupID, name: str) -> set[Any]:
        """Retrieve the named set shared by all members of a coordination group, creating it if needed.

        Unlike messages, a shared set does not grow with the number of members.  It is not locked, so only
        modify it from the event loop.
        """
        group = self._groups[group_id]
        with group.lock:
            return group.shared_sets.setdefault(name, set())
