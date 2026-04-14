"""Follower lifecycle — join, dialogue, quest failure, farewell."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.player import PlayerCharacter

from src.models.follower import Follower


class FollowerManager:
    """Manages followers: add/remove, dialogue, room-progression failures."""

    def __init__(self, player: PlayerCharacter, npcs: list, quests: dict):
        self.player = player
        self.npcs = npcs
        self.quests = quests

    # ------------------------------------------------------------------
    # Adding followers (escort quest accepted)
    # ------------------------------------------------------------------

    def start_escort(self, quest, npc) -> str | None:
        """Create a Follower from an escort quest NPC, add to player.

        Returns a status message, or None on failure.
        """
        escort_npc_id = getattr(quest, "escort_npc_id", None)
        if not escort_npc_id:
            return None

        npc_to_escort = None
        for n in self.npcs:
            if n.id == escort_npc_id:
                npc_to_escort = n
                break
        if not npc_to_escort:
            return None

        follower = Follower(
            npc_id=escort_npc_id,
            name=npc_to_escort.name or f"NPC_{escort_npc_id}",
            quest_id=quest.id,
            joined_in_room=1,
            destination_room=getattr(quest, "destination_room", 1),
            personality=getattr(npc_to_escort, "personality", ""),
            farewell_text="Thank you for escorting me. Farewell!",
            dialogue_hints=[
                "I think we need to keep moving...",
                "Be careful, I've heard rumors of danger ahead.",
                "I appreciate your help, adventurer.",
            ],
        )

        if not self.player.add_follower(follower):
            return "You already have the maximum number of followers!"

        self.npcs.remove(npc_to_escort)

        # Add escort item so the zone-check works
        from src.models.items import EscortItem, ItemStats

        escort_item = EscortItem(
            category="escort",
            name=f"{npc_to_escort.name} (escort)",
            desc=f"Escorting {npc_to_escort.name} to safety.",
            item_stats=ItemStats(),
            npc_id=escort_npc_id,
            target_zone=tuple(getattr(quest, "target_zone", [0, 0])),
        )
        self.player.add_to_inventory(escort_item)
        return f"{follower.name} is now following you!"

    # ------------------------------------------------------------------
    # Removing followers
    # ------------------------------------------------------------------

    def remove_follower_for_quest(self, quest_id: str) -> str | None:
        """Remove the follower tied to *quest_id*. Returns farewell or None."""
        follower = self.player.get_follower_by_quest(quest_id)
        if not follower:
            return None
        farewell = follower.farewell_text
        self.player.remove_follower(follower.npc_id)
        return f"{follower.name}: {farewell}"

    # ------------------------------------------------------------------
    # Dialogue
    # ------------------------------------------------------------------

    def talk_to_follower(self, index: int = 0, story_context: str = "") -> str:
        """Get dialogue from the follower at *index*.

        If *story_context* is provided, the follower may react to it.
        """
        if not self.player.followers:
            return "No followers to talk to."
        if index >= len(self.player.followers):
            return "No followers to talk to."

        follower = self.player.followers[index]
        hint = follower.get_hint()

        if story_context:
            return f"{follower.name}: {hint} (Regarding recent events: {story_context})"
        return f"{follower.name}: {hint}"

    # ------------------------------------------------------------------
    # Room progression checks
    # ------------------------------------------------------------------

    def check_room_progression(self, current_room: int) -> list[str]:
        """Check if any followers should leave because player passed their destination.

        Returns list of farewell messages. Also fails the associated quest.
        """
        messages = []
        for follower in list(self.player.followers):
            if follower.should_leave(current_room):
                farewell = f"{follower.name}: {follower.farewell_text} (left the party)"
                self.player.remove_follower(follower.npc_id)

                # Fail the associated quest
                if follower.quest_id and follower.quest_id in self.quests:
                    quest = self.quests[follower.quest_id]
                    if quest.status == "active":
                        quest.status = "failed"
                        self.player.fail_quest(quest.id)
                        penalty_msg = quest.apply_failure_penalty(self.player)
                        farewell += f" Quest failed: {quest.title}!"
                        if penalty_msg:
                            farewell += f" ({penalty_msg})"

                messages.append(farewell)
        return messages

    # ------------------------------------------------------------------
    # Info for UI
    # ------------------------------------------------------------------

    def get_follower_info(self) -> list[dict]:
        """Return follower data for the player menu followers tab."""
        info = []
        for f in self.player.followers:
            quest_summary = ""
            if f.quest_id and f.quest_id in self.quests:
                quest_summary = self.quests[f.quest_id].title
            info.append(
                {
                    "name": f.name,
                    "personality": f.personality,
                    "quest_summary": quest_summary,
                    "destination_room": f.destination_room,
                    "hints": f.dialogue_hints,
                }
            )
        return info
