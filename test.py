import json
import random
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from copy import deepcopy

# ─────────────────────────────────────────────
#  DATA LOADING & DECK CONSTRUCTION (your code)
# ─────────────────────────────────────────────

DROP_COLS = [
    'artist', 'artistIds', 'availability', 'borderColor',
    'edhrecRank', 'edhrecSaltiness', 'finishes', 'foreignData', 'frameEffects',
    'frameVersion', 'language', 'layout', 'printings', 'purchaseUrls',
    'securityStamp', 'setCode', 'skuIds', 'sourceProducts', 'flavorText',
    'isStorySpotlight', 'relatedCards', 'watermark', 'isReprint', 'isFullArt',
    'isTextless', 'promoTypes', 'isPromo', 'rulings', 'rarity', 'variations',
    'uuid', 'number', 'identifiers', 'legalities', 'leadershipSkills', 'manaValue'
]

BASIC_NAMES = ['Forest', 'Swamp', 'Plains', 'Mountain', 'Island']

BASIC_MAP = {'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Mountain', 'G': 'Forest'}

COLOR_MANA_MAP = {'W': 'W', 'U': 'U', 'B': 'B', 'R': 'R', 'G': 'G'}


def load_cards(json_path: str) -> pd.DataFrame:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cards = pd.DataFrame(data["data"]["cards"])
    cards = cards.drop_duplicates(subset="name", keep="first")
    drop = [c for c in DROP_COLS if c in cards.columns]
    cards = cards.drop(columns=drop)
    return cards


def construct_deck(cards: pd.DataFrame) -> pd.DataFrame:
    deck = pd.DataFrame(columns=cards.columns)

    while len(deck) < 38:
        row = cards[~cards['name'].isin(BASIC_NAMES)].sample()
        name = row['name'].values[0]
        if (deck['name'] == name).sum() < 4:
            deck = pd.concat([deck, row], ignore_index=True)

    # Weighted basic land fill
    rows = []
    for colors in deck['colors']:
        if len(colors) > 0:
            w = 1 / len(colors)
            for c in colors:
                rows.append({'color': c, 'weight': w})

    color_weights = pd.DataFrame(rows).groupby('color')['weight'].sum()
    basics_needed = 60 - len(deck)
    color_weights = color_weights / color_weights.sum()
    basic_counts = (color_weights * basics_needed).round().astype(int)
    diff = basics_needed - basic_counts.sum()
    if diff != 0:
        basic_counts.iloc[0] += diff

    for color, count in basic_counts.items():
        if color in BASIC_MAP and count > 0:
            basic_row = cards[cards['name'] == BASIC_MAP[color]]
            for _ in range(count):
                deck = pd.concat([deck, basic_row], ignore_index=True)

    return deck.reset_index(drop=True)


# ─────────────────────────────────────────────
#  CARD MODEL
# ─────────────────────────────────────────────

def parse_mana_cost(cost_str) -> dict:
    """Parse '{2}{R}{G}' → {'generic': 2, 'R': 1, 'G': 1}"""
    if not isinstance(cost_str, str):
        return {'generic': 0}
    mana = {'generic': 0}
    import re
    for token in re.findall(r'\{([^}]+)\}', cost_str):
        if token.isdigit():
            mana['generic'] += int(token)
        elif token in COLOR_MANA_MAP:
            mana[token] = mana.get(token, 0) + 1
        # X, hybrid, phyrexian etc. ignored for now
    return mana


def total_cmc(mana: dict) -> int:
    return sum(mana.values())


@dataclass
class Card:
    name: str
    types: list        # e.g. ['Creature'], ['Instant'], ['Land']
    subtypes: list
    colors: list
    mana_cost: dict    # parsed
    cmc: int
    power: Optional[int]
    toughness: Optional[int]
    oracle_text: str

    # Runtime state (battlefield only)
    tapped: bool = False
    damage: int = 0
    summoning_sick: bool = True  # can't attack first turn it enters

    @property
    def is_land(self):
        return 'Land' in self.types

    @property
    def is_creature(self):
        return 'Creature' in self.types

    @property
    def is_spell(self):
        return not self.is_land

    @property
    def is_alive(self):
        return self.toughness is not None and self.toughness > self.damage

    def produces_mana(self) -> list:
        """Heuristic: basic lands produce their color; others inferred from colors."""
        basic_produces = {
            'Plains': ['W'], 'Island': ['U'], 'Swamp': ['B'],
            'Mountain': ['R'], 'Forest': ['G']
        }
        if self.name in basic_produces:
            return basic_produces[self.name]
        if self.is_land and self.colors:
            return self.colors
        if self.is_land:
            return ['C']  # colorless fallback
        return []

    def __repr__(self):
        if self.is_creature:
            return f"{self.name} [{self.power}/{self.toughness}]"
        return f"{self.name} ({''.join(self.colors) or 'C'})"


def row_to_card(row: pd.Series) -> Card:
    def safe_list(val):
        if isinstance(val, list):
            return val
        return []

    def safe_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    return Card(
        name=row.get('name', 'Unknown'),
        types=safe_list(row.get('types')),
        subtypes=safe_list(row.get('subtypes')),
        colors=safe_list(row.get('colors')),
        mana_cost=parse_mana_cost(row.get('manaCost')),
        cmc=total_cmc(parse_mana_cost(row.get('manaCost'))),
        power=safe_int(row.get('power')),
        toughness=safe_int(row.get('toughness')),
        oracle_text=row.get('text', '') or '',
    )


def deck_to_cards(deck_df: pd.DataFrame) -> list[Card]:
    return [row_to_card(row) for _, row in deck_df.iterrows()]


# ─────────────────────────────────────────────
#  GAME STATE
# ─────────────────────────────────────────────

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
    game_over: bool = False
    winner: Optional[int] = None  # player index

    @property
    def active_player(self) -> PlayerState:
        return self.players[self.active_player_idx]

    @property
    def opponent(self) -> PlayerState:
        return self.players[1 - self.active_player_idx]


# ─────────────────────────────────────────────
#  GAME ENGINE
# ─────────────────────────────────────────────

class GameEngine:
    def __init__(self, deck1: list[Card], deck2: list[Card], verbose: bool = True):
        self.verbose = verbose

        d1 = deepcopy(deck1)
        d2 = deepcopy(deck2)
        random.shuffle(d1)
        random.shuffle(d2)

        p1 = PlayerState(name="Player 1", library=d1)
        p2 = PlayerState(name="Player 2", library=d2)

        self.state = GameState(players=[p1, p2])

        # Draw opening hands
        for p in self.state.players:
            self._draw_n(p, 7)

    def log(self, msg: str):
        if self.verbose:
            print(msg)

    # ── card movement ──

    def _draw(self, player: PlayerState) -> bool:
        """Draw one card. Returns False if library is empty (player loses)."""
        if not player.library:
            self.log(f"  {player.name} has no cards to draw — loses!")
            self.state.game_over = True
            self.state.winner = 1 - self.state.players.index(player)
            return False
        card = player.library.pop(0)
        player.hand.append(card)
        return True

    def _draw_n(self, player: PlayerState, n: int):
        for _ in range(n):
            if not self._draw(player):
                break

    def _put_on_battlefield(self, player: PlayerState, card: Card):
        player.hand.remove(card)
        card.tapped = False
        card.damage = 0
        card.summoning_sick = True
        player.battlefield.append(card)

    def _destroy(self, player: PlayerState, card: Card):
        if card in player.battlefield:
            player.battlefield.remove(card)
            player.graveyard.append(card)
            self.log(f"    ☠  {card.name} dies")

    # ── mana ──

    def _tap_lands_for_mana(self, player: PlayerState):
        """Tap all untapped lands, filling mana pool."""
        for land in player.untapped_lands():
            land.tapped = True
            for color in land.produces_mana():
                player.mana_pool[color] = player.mana_pool.get(color, 0) + 1

    def _can_afford(self, player: PlayerState, card: Card) -> bool:
        """Check if player can pay card's mana cost from current pool."""
        pool = dict(player.mana_pool)
        # Pay colored costs first
        for color in ['W', 'U', 'B', 'R', 'G']:
            needed = card.mana_cost.get(color, 0)
            if pool.get(color, 0) < needed:
                return False
            pool[color] -= needed
        # Pay generic with whatever's left
        total_left = sum(pool.values())
        return total_left >= card.mana_cost.get('generic', 0)

    def _pay_mana(self, player: PlayerState, card: Card):
        """Deduct card cost from mana pool (assumes _can_afford already checked)."""
        for color in ['W', 'U', 'B', 'R', 'G']:
            needed = card.mana_cost.get(color, 0)
            player.mana_pool[color] -= needed
        generic = card.mana_cost.get('generic', 0)
        for color in ['C', 'W', 'U', 'B', 'R', 'G']:
            while generic > 0 and player.mana_pool.get(color, 0) > 0:
                player.mana_pool[color] -= 1
                generic -= 1

    def _empty_mana_pool(self, player: PlayerState):
        player.mana_pool = {c: 0 for c in player.mana_pool}

    # ── phases ──

    def _untap_phase(self):
        ap = self.state.active_player
        for card in ap.battlefield:
            card.tapped = False
            card.summoning_sick = False  # clears after surviving a full turn
        ap.lands_played_this_turn = 0
        self.log(f"\n{'='*50}")
        self.log(f"Turn {self.state.turn} — {ap.name}  (Life: {ap.life} | Hand: {len(ap.hand)} | Board: {len(ap.battlefield)})")

    def _draw_phase(self):
        ap = self.state.active_player
        # First player skips draw on turn 1
        if self.state.turn == 1 and self.state.active_player_idx == 0:
            return
        self._draw(ap)

    def _main_phase(self, phase_name: str = "Main 1"):
        """Simple heuristic agent: tap all lands, then cast whatever it can afford."""
        ap = self.state.active_player
        self._tap_lands_for_mana(ap)

        self.log(f"  [{phase_name}] Mana: {ap.mana_pool}  Hand: {[c.name for c in ap.hand]}")

        # Play one land if we have one and haven't played one this turn
        if ap.lands_played_this_turn == 0:
            lands_in_hand = [c for c in ap.hand if c.is_land]
            if lands_in_hand:
                land = lands_in_hand[0]
                self._put_on_battlefield(ap, land)
                ap.lands_played_this_turn += 1
                self.log(f"  🌲 {ap.name} plays {land.name}")
                # Tap the new land immediately too
                self._tap_lands_for_mana(ap)

        # Cast spells greedily (lowest CMC first)
        castable = sorted(
            [c for c in ap.hand if c.is_spell and self._can_afford(ap, c)],
            key=lambda c: c.cmc
        )
        for card in castable:
            if self._can_afford(ap, card):
                self._pay_mana(ap, card)
                self.log(f"  ✨ {ap.name} casts {card}")
                if card.is_creature:
                    self._put_on_battlefield(ap, card)
                else:
                    # Non-creature spells: basic damage/removal heuristic
                    self._resolve_noncreature(ap, card)

        self._empty_mana_pool(ap)

    def _resolve_noncreature(self, player: PlayerState, card: Card):
        """
        Very simplified non-creature resolution.
        Checks oracle text for 'damage' keywords to deal face damage,
        otherwise sends card to graveyard.
        """
        text = card.oracle_text.lower()
        opponent = self.state.opponent

        # Crude damage detection: look for "deals X damage"
        import re
        dmg_match = re.search(r'deals?\s+(\d+)\s+damage', text)
        if dmg_match and opponent:
            dmg = int(dmg_match.group(1))
            # Try to target a creature, else go face
            enemy_creatures = opponent.creatures()
            if enemy_creatures and 'target creature' in text:
                target = random.choice(enemy_creatures)
                target.damage += dmg
                self.log(f"    ⚡ {card.name} deals {dmg} damage to {target.name}")
                self._check_creature_deaths(opponent)
            else:
                opponent.life -= dmg
                self.log(f"    ⚡ {card.name} deals {dmg} damage to {opponent.name} (life: {opponent.life})")

        player.graveyard.append(card)

    def _combat_phase(self):
        ap = self.state.active_player
        opp = self.state.opponent
        attackers = ap.untapped_creatures()

        if not attackers:
            return

        self.log(f"  ⚔  {ap.name} attacks with: {[c.name for c in attackers]}")

        # Tap attackers
        for c in attackers:
            c.tapped = True

        # Opponent blocks: each untapped creature blocks one attacker (greedy)
        blockers = opp.untapped_creatures()
        blocks: dict[Card, Optional[Card]] = {a: None for a in attackers}

        blocker_pool = list(blockers)
        for attacker in attackers:
            if blocker_pool:
                blocker = blocker_pool.pop(0)
                blocks[attacker] = blocker
                blocker.tapped = True
                self.log(f"    🛡  {blocker.name} blocks {attacker.name}")

        # Resolve combat damage
        for attacker, blocker in blocks.items():
            if blocker is None:
                # Unblocked: deal damage to opponent
                opp.life -= attacker.power
                self.log(f"    💥 {attacker.name} deals {attacker.power} damage to {opp.name} (life: {opp.life})")
            else:
                # Blocked: creatures deal damage to each other
                attacker.damage += blocker.power
                blocker.damage += attacker.power
                self.log(f"    💢 {attacker.name} ({attacker.power}/{attacker.toughness}) vs "
                         f"{blocker.name} ({blocker.power}/{blocker.toughness})")

        self._check_creature_deaths(ap)
        self._check_creature_deaths(opp)

    def _check_creature_deaths(self, player: PlayerState):
        dead = [c for c in player.battlefield if c.is_creature and c.damage >= (c.toughness or 999)]
        for c in dead:
            self._destroy(player, c)

    def _check_win_conditions(self):
        for i, p in enumerate(self.state.players):
            if p.life <= 0:
                self.log(f"\n🏆 {self.state.players[1-i].name} wins! ({p.name} reached {p.life} life)")
                self.state.game_over = True
                self.state.winner = 1 - i
                return

    def _end_phase(self):
        ap = self.state.active_player
        # Discard to hand size 7
        while len(ap.hand) > 7:
            discarded = ap.hand.pop()
            ap.graveyard.append(discarded)
            self.log(f"  📤 {ap.name} discards {discarded.name}")
        # Reset creature damage
        for c in ap.battlefield:
            c.damage = 0

    def _next_turn(self):
        self.state.active_player_idx = 1 - self.state.active_player_idx
        if self.state.active_player_idx == 0:
            self.state.turn += 1

    # ── main game loop ──

    def run(self, max_turns: int = 50) -> Optional[int]:
        """
        Run a full game. Returns the winner's player index (0 or 1),
        or None for a draw/timeout.
        """
        while not self.state.game_over:
            if self.state.turn > max_turns:
                self.log(f"\n⏱  Turn limit reached — draw!")
                return None

            self._untap_phase()
            if self.state.game_over:
                break

            self._draw_phase()
            if self.state.game_over:
                break

            self._main_phase("Main 1")
            self._check_win_conditions()
            if self.state.game_over:
                break

            self._combat_phase()
            self._check_win_conditions()
            if self.state.game_over:
                break

            self._main_phase("Main 2")
            self._check_win_conditions()
            if self.state.game_over:
                break

            self._end_phase()
            self._next_turn()

        return self.state.winner


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    json_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Marcel\Downloads\SOS.json"

    print("Loading cards...")
    sos_cards = load_cards(json_path)

    print("Building decks...")
    deck1_df = construct_deck(sos_cards)
    deck2_df = construct_deck(sos_cards)

    deck1 = deck_to_cards(deck1_df)
    deck2 = deck_to_cards(deck2_df)

    print(f"Deck 1: {len(deck1)} cards")
    print(f"Deck 2: {len(deck2)} cards")

    print("\n--- Starting Game ---\n")
    engine = GameEngine(deck1, deck2, verbose=True)
    winner = engine.run(max_turns=50)

    if winner is not None:
        print(f"\nResult: Player {winner + 1} wins!")
    else:
        print("\nResult: Draw / Timeout")

    # ── quick simulation run (for ML later) ──
    print("\n--- Simulating 10 games silently ---")
    wins = [0, 0, 0]  # p1 wins, p2 wins, draws
    for _ in range(10):
        d1 = deck_to_cards(construct_deck(sos_cards))
        d2 = deck_to_cards(construct_deck(sos_cards))
        result = GameEngine(d1, d2, verbose=False).run(max_turns=50)
        if result is None:
            wins[2] += 1
        else:
            wins[result] += 1

    print(f"P1 wins: {wins[0]} | P2 wins: {wins[1]} | Draws: {wins[2]}")