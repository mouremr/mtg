from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, auto
from Cards import Card


class Phase(Enum):
    UNTAP = auto()
    UPKEEP = auto()
    DRAW = auto()
    MAIN1 = auto()
    COMBAT = auto()
    MAIN2 = auto()
    END = auto()

@dataclass
class PlayerState:
    name: str
    library: list[Card]
    hand: list[Card] = field(default_factory=list)
    battlefield: list[Card] = field(default_factory=list)
    graveyard: list[Card] = field(default_factory=list)
    life: int = 20
    lands_played_this_turn: int = 0
    
    mana_pool: dict = field(default_factory=lambda: {
        'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0, 'C': 0
    })

    def available_mana(self) -> int:
        return sum(self.mana_pool.values())

    def untapped_lands(self) -> list[Card]:
        return [c for c in self.battlefield if c.is_land and not c.tapped]

    def untapped_creatures(self) -> list[Card]:
        return [c for c in self.battlefield
                if c.is_creature and not c.tapped and not c.summoning_sick]

    def creatures(self) -> list[Card]:
        return [c for c in self.battlefield if c.is_creature]

    def total_tappable_mana(self) -> int:
        """How much mana this player can produce by tapping all lands."""
        return len([c for c in self.battlefield if c.is_land and not c.tapped])

@dataclass
class GameState:
    players: list[PlayerState]
    turn: int = 1
    active_player_idx: int = 0
    phase: Phase = Phase.UNTAP
    gameover: bool = False
    winner: Optional[int] = None  # player index

    @property
    def active_player(self):
        return self.players[self.active_player_idx]

    @property
    def opponent(self):
        return self.players[1 - self.active_player_idx]