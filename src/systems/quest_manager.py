"""Quest state tracking, completion, failure, and reward distribution."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.player import PlayerCharacter

from src.models.quest import (
    Quest, FetchQuest, EscortQuest, DeliveryQuest, DialogueQuest,
    CombatQuest, MultiStepQuest,
)
from src.registry import registry


class QuestManager:
    """Centralizes quest lifecycle: offer, accept, progress, complete, fail."""

    def __init__(self, quests: dict[str, Quest], events: dict | None = None):
        self.quests = quests
        self.events = events or {}

    # ------------------------------------------------------------------
    # Startup checks
    # ------------------------------------------------------------------

    def check_kill_quests_already_cleared(self, player: PlayerCharacter):
        """Complete combat quests whose target event was already resolved."""
        for qid, quest in self.quests.items():
            if quest.type != "combat" or quest.status != "not_started":
                continue
            target_eid = getattr(quest, "target_event_id", "")
            if target_eid:
                event = self.events.get(target_eid)
                if event and getattr(event, "resolved", False):
                    quest.status = "completed"
                    # Directly add to completed since quest was never active
                    if qid not in player.completed_quests:
                        player.completed_quests.append(qid)

    # ------------------------------------------------------------------
    # Offering quests (NPC interaction)
    # ------------------------------------------------------------------

    def try_offer_quest(self, npc, player: PlayerCharacter) -> Quest | None:
        """If the NPC has an unoffered quest whose prereqs are met, activate it.

        Returns the newly-activated quest or None.
        """
        quest_id = getattr(npc, "quest_id", None)
        if not quest_id or quest_id not in self.quests:
            return None
        quest = self.quests[quest_id]
        if quest.status != "not_started":
            return None
        prereq = quest.prerequisite_quest_id
        if prereq and not player.has_completed(prereq):
            return None

        quest.status = "active"
        player.accept_quest(quest.id)

        # Activate first sub-quest for multi-step
        if quest.type == "multi_step":
            first_sub = quest.get_current_sub_quest_id()
            if first_sub and first_sub in self.quests:
                sub = self.quests[first_sub]
                if sub.status == "not_started":
                    sub.status = "active"
                    player.accept_quest(sub.id)

        # Check if kill-quest target already cleared
        if quest.type == "combat":
            target_eid = getattr(quest, "target_event_id", "")
            event = self.events.get(target_eid)
            if event and getattr(event, "resolved", False):
                self.complete_quest(quest, player)

        return quest

    # ------------------------------------------------------------------
    # Turn-in checks (talking to NPC)
    # ------------------------------------------------------------------

    def check_turn_in(self, npc, player: PlayerCharacter) -> Quest | None:
        """Check if any active quest can be completed by talking to *npc*.

        Returns the completed quest, or None.
        """
        for qid, quest in list(self.quests.items()):
            if quest.status != "active" or qid not in player.active_quests:
                continue

            if quest.type == "fetch" and quest.giver_npc_id == npc.id:
                if self._check_fetch_items(quest, player):
                    self._remove_fetch_items(quest, player)
                    self.complete_quest(quest, player)
                    return quest

            elif quest.type == "delivery" and getattr(quest, "target_npc_id", None) == npc.id:
                delivery_item = registry.get_item(getattr(quest, "delivery_item_id", 0))
                if delivery_item and delivery_item.name in player.inventory:
                    player.remove_from_inventory(delivery_item.name)
                    self.complete_quest(quest, player)
                    return quest

        return None

    # ------------------------------------------------------------------
    # Completion on event resolution (combat)
    # ------------------------------------------------------------------

    def on_event_resolved(self, event_id: str, player: PlayerCharacter) -> Quest | None:
        """Called when a combat event is resolved. Completes matching combat quests."""
        for qid, quest in self.quests.items():
            if (quest.type == "combat"
                    and getattr(quest, "target_event_id", "") == event_id
                    and quest.status == "active"):
                self.complete_quest(quest, player)
                return quest
        return None

    # ------------------------------------------------------------------
    # Escort zone check
    # ------------------------------------------------------------------

    def check_escort_zone(self, player: PlayerCharacter) -> Quest | None:
        """Check if any active escort quest target zone has been reached."""
        from src.models.items import EscortItem
        for item_name, item in list(player.inventory.items()):
            if isinstance(item, EscortItem):
                tx, ty = item.target_zone
                if abs(player.x - tx) <= 2 and abs(player.y - ty) <= 2:
                    player.remove_from_inventory(item_name)
                    for qid, quest in self.quests.items():
                        if (quest.type == "escort"
                                and getattr(quest, "escort_npc_id", None) == item.npc_id
                                and quest.status == "active"):
                            self.complete_quest(quest, player)
                            return quest
        return None

    # ------------------------------------------------------------------
    # Quest completion
    # ------------------------------------------------------------------

    def complete_quest(self, quest: Quest, player: PlayerCharacter) -> str:
        """Mark quest completed, grant rewards, advance multi-step parents.

        Returns a human-readable reward message.
        """
        quest.status = "completed"
        player.complete_quest(quest.id)
        msg = f"Quest completed: {quest.title}!"

        if quest.reward:
            if quest.reward.item_id:
                reward_item = registry.get_item(quest.reward.item_id)
                if reward_item:
                    player.add_to_inventory(reward_item.clone())
            money = getattr(quest.reward, "money", 0)
            if money > 0:
                player.add_money(money)
                msg += f" +{money} gold!"
            if quest.reward.story_info:
                msg += f" {quest.reward.story_info}"

        self._advance_multi_step(quest.id, player)
        return msg

    # ------------------------------------------------------------------
    # Quest failure
    # ------------------------------------------------------------------

    def fail_quest(self, quest: Quest, player: PlayerCharacter) -> str:
        """Fail a quest and apply penalties. Returns message."""
        quest.status = "failed"
        player.fail_quest(quest.id)
        penalty_msg = quest.apply_failure_penalty(player)
        msg = f"Quest failed: {quest.title}!"
        if penalty_msg:
            msg += f" ({penalty_msg})"
        return msg

    def check_room_quest_failures(self, player: PlayerCharacter, current_room: int) -> list[str]:
        """Fail quests that are room-local and player has moved past them.

        Room-local quests: fetch/dialogue quests with room_id set, where
        the player has moved to a room beyond that quest's room.
        Returns list of failure messages.
        """
        messages = []
        for qid, quest in list(self.quests.items()):
            if quest.status != "active" or qid not in player.active_quests:
                continue
            if not quest.room_id:
                continue
            # room_id is a string like "room_1"; extract number
            try:
                quest_room = int(quest.room_id.split("_")[-1])
            except (ValueError, IndexError):
                continue
            if current_room > quest_room:
                messages.append(self.fail_quest(quest, player))
        return messages

    # ------------------------------------------------------------------
    # Multi-step advancement
    # ------------------------------------------------------------------

    def _advance_multi_step(self, completed_quest_id: str, player: PlayerCharacter) -> str | None:
        """If completing a sub-quest advances a multi-step parent, do so.

        Returns a progress message or None.
        """
        for qid, quest in self.quests.items():
            if quest.type != "multi_step" or quest.status != "active":
                continue
            current_sub = quest.get_current_sub_quest_id()
            if current_sub == completed_quest_id:
                all_done = quest.advance_step()
                if all_done:
                    self.complete_quest(quest, player)
                    return None
                else:
                    next_sub = quest.get_current_sub_quest_id()
                    if next_sub and next_sub in self.quests:
                        next_q = self.quests[next_sub]
                        if next_q.status == "not_started":
                            next_q.status = "active"
                            player.accept_quest(next_q.id)
                    return (f"Quest progress: {quest.title} "
                            f"— step {quest.current_step}/{len(quest.sub_quest_ids)}")
        return None

    # ------------------------------------------------------------------
    # Quest log
    # ------------------------------------------------------------------

    def get_quest_log(self) -> dict:
        """Return quests organized by status for the quest log view."""
        active: list[dict] = []
        completed: list[dict] = []
        failed: list[dict] = []

        for qid, quest in self.quests.items():
            # Skip sub-quests of multi-step (they appear as progress on the parent)
            is_sub = False
            for other in self.quests.values():
                if other.type == "multi_step" and qid in getattr(other, "sub_quest_ids", []):
                    is_sub = True
                    break
            if is_sub and quest.status != "active":
                continue

            entry = {
                "id": qid,
                "title": quest.title,
                "description": quest.description,
                "type": quest.type,
                "is_story_quest": getattr(quest, "is_story_quest", False),
            }
            if quest.type == "multi_step":
                entry["current_step"] = getattr(quest, "current_step", 0)
                entry["total_steps"] = len(getattr(quest, "sub_quest_ids", []))
                # Include current sub-quest description as objective
                current_sub_id = quest.get_current_sub_quest_id()
                if current_sub_id and current_sub_id in self.quests:
                    entry["current_objective"] = self.quests[current_sub_id].description

            if quest.status == "active":
                active.append(entry)
            elif quest.status == "completed":
                completed.append(entry)
            elif quest.status == "failed":
                failed.append(entry)

        return {"active": active, "completed": completed, "failed": failed}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_fetch_items(quest, player: PlayerCharacter) -> bool:
        for req in getattr(quest, "target_items", []):
            item_id = req["item_id"]
            count = req.get("count", 1)
            item_obj = registry.get_item(item_id)
            if item_obj and item_obj.name in player.inventory:
                if player.inventory[item_obj.name].quantity >= count:
                    continue
            return False
        return True

    @staticmethod
    def _remove_fetch_items(quest, player: PlayerCharacter):
        for req in getattr(quest, "target_items", []):
            item_obj = registry.get_item(req["item_id"])
            if item_obj:
                for _ in range(req.get("count", 1)):
                    player.remove_from_inventory(item_obj.name)
