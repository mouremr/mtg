from typing import Optional
from copy import deepcopy
import random
from GameState import PlayerState, GameState
from Cards import Card


class GameLoop:
    def __init__(self, deck1: list[Card], deck2: list[Card], verbose: bool = True):
        self.verbose = verbose

        d1 = deepcopy(deck1)
        d2 = deepcopy(deck2)
        random.shuffle(d1)
        random.shuffle(d2)

        p1 = PlayerState(name="Player 1", library=d1)
        p2 = PlayerState(name="Player 2", library=d2)

        self.state = GameState(players=[p1, p2])
        for p in self.state.players:
            self._draw_n(p, 7)
    
    
    def log(self, msg: str):
        if self.verbose:
            print(msg)

# ── card movement ──

    def _draw(self, player: PlayerState) -> bool:
        """Draw one card. Returns False if library is empty (player loses)."""
        if not player.library:
            self.log(f"  {player.name} has no cards to draw!")
            self.state.gameover = True
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
            self.log(f"{card.name} dies")


# ── mana management ──

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







# ── turn phases ──

    def _untap_phase(self):
        ap = self.state.active_player
        op = self.state.opponent
        for card in ap.battlefield:
            card.tapped = False
            card.summoning_sick = False 
        for card in op.battlefield: #clear summoning sickness for opponents cards so they can block(technically not right but easiest)
            card.summoning_sick = False
        ap.lands_played_this_turn = 0
        self.log(f"\n{'='*50}")
        self.log(f"Turn {self.state.turn} - {ap.name}  (Life: {ap.life} | Hand: {len(ap.hand)} | Board: {len(ap.battlefield)})")

    def _draw_phase(self):
        ap = self.state.active_player
        # first player skips draw on turn 1
        if self.state.turn == 1 and self.state.active_player_idx == 0:
            return
        self._draw(ap)

    def _main_phase(self, phase_name: str = "Main 1"):
        """tap all lands, then cast whatever player can afford."""
        ap = self.state.active_player
        

        # play land if possible
        if ap.lands_played_this_turn == 0:
            lands_in_hand = [c for c in ap.hand if c.is_land]
            if lands_in_hand:
                land = lands_in_hand[0]
                self._put_on_battlefield(ap, land)
                ap.lands_played_this_turn += 1
                self.log(f" {ap.name} plays {land.name}")
        
        # tap all lands for mana
        self._tap_lands_for_mana(ap)

        self.log(f"  [{phase_name}] Mana: {ap.mana_pool}  Hand: {[c.name for c in ap.hand]}")

        # Cast spells greedily, cheapest first
        castable = sorted(
            [c for c in ap.hand if c.is_spell and self._can_afford(ap, c)],
            key=lambda c: c.cmc
        )
        for card in castable:
            if self._can_afford(ap, card):
                self._pay_mana(ap, card)
                self.log(f"{ap.name} casts {card}")
                if card.is_creature:
                    self._put_on_battlefield(ap, card)
                else:
                    # Non-creature spells: simple removal plan
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

        # look for "deals X damage" on a card
        import re
        dmg_match = re.search(r'deals?\s+(\d+)\s+damage', text)
        if dmg_match and opponent:
            dmg = int(dmg_match.group(1))
            # check for targeting creature or face
            enemy_creatures = opponent.creatures()
            if enemy_creatures and 'target creature' in text:
                target = random.choice(enemy_creatures)
                target.damage += dmg
                self.log(f"     {card.name} deals {dmg} damage to {target.name}")
                self._check_creature_deaths(opponent)
            else:
                opponent.life -= dmg
                self.log(f"     {card.name} deals {dmg} damage to {opponent.name} (life: {opponent.life})")

        player.graveyard.append(card)
    
    def _combat_phase(self):
        ap = self.state.active_player
        opp = self.state.opponent
        attackers = ap.untapped_creatures()

        if not attackers:
            return

        self.log(f"    {ap.name} attacks with: {[c.name for c in attackers]}")

        for c in attackers:
            c.tapped = True

        # each untapped creature blocks one attacker
        blockers = opp.untapped_creatures()
        blocks: dict[Card, Optional[Card]] = {a: None for a in attackers}

        blocker_pool = list(blockers)
        for attacker in attackers:
            if blocker_pool:
                blocker = blocker_pool.pop(0)
                blocks[attacker] = blocker
                blocker.tapped = True
                self.log(f"     {blocker.name} blocks {attacker.name}")

        # combat damage
        for attacker, blocker in blocks.items():
            if blocker is None:
                opp.life -= attacker.power
                self.log(f"     {attacker.name} deals {attacker.power} damage to {opp.name} (life: {opp.life})")
            else:
                attacker.damage += blocker.power
                blocker.damage += attacker.power
                self.log(f"     {attacker.name} ({attacker.power}/{attacker.toughness}) vs "
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
                self.log(f"\n{self.state.players[1-i].name} wins! ({p.name} reached {p.life} life)")
                self.state.gameover = True
                self.state.winner = 1 - i
                return
            
    def _end_phase(self):
        ap = self.state.active_player
        # Discard to hand size 7
        while len(ap.hand) > 7:
            discarded = ap.hand.pop()
            ap.graveyard.append(discarded)
            self.log(f"   {ap.name} discards {discarded.name}")
        # Reset creature damage
        for c in ap.battlefield:
            c.damage = 0

    def _next_turn(self):
        self.state.active_player_idx = 1 - self.state.active_player_idx
        if self.state.active_player_idx == 0:
            self.state.turn += 1

# main game loop

    def run(self, max_turns: int = 50) -> Optional[int]:
        """
        Run a full game. Returns the winner's player index (0 or 1),
        or None for a draw/timeout.
        """
        while not self.state.gameover:
            if self.state.turn > max_turns:
                self.log(f"\nTurn limit reached — draw!")
                return None

            self._untap_phase()
            if self.state.gameover:
                break

            self._draw_phase()
            if self.state.gameover:
                break

            self._main_phase("Main 1")
            self._check_win_conditions()
            if self.state.gameover:
                break

            self._combat_phase()
            self._check_win_conditions()
            if self.state.gameover:
                break

            self._main_phase("Main 2")
            self._check_win_conditions()
            if self.state.gameover:
                break

            self._end_phase()
            self._next_turn()

        return self.state.winner
