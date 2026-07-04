import pandas as pd
import re
from dataclasses import dataclass
from typing import Optional, Tuple




COLOR_MANA_MAP = {'W': 'W', 'U': 'U', 'B': 'B', 'R': 'R', 'G': 'G'}

def parse_manaCost(costString):
    #convert mana cost from cmc notation to python dict
    #only handles normal mana symbols in card text for now
    if not isinstance(costString, str):
        return {'generic': 0}
    mana = {'generic': 0}
    for token in re.findall(r'\{([^}]+)\}', costString):
        if token.isdigit():
            mana['generic'] += int(token)
        elif token in COLOR_MANA_MAP:
            mana[token] = mana.get(token, 0) + 1
    return mana

#define card object

@dataclass
class Card:
    name: str
    types: Tuple
    subtypes: Tuple
    colors: Tuple
    mana_cost: dict
    cmc: int
    power: Optional[int]
    toughness: Optional[int]
    oracle_text: str

    #Game states
    tapped: bool = False
    damage: int = 0
    summoning_sick: bool = True



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
    
    def produces_mana(self):
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

    def __hash__(self):
        # Use name as stable identifier for hashing (card names are unique in deck)
        return hash(self.name)
    
    def __repr__(self):
        # if self.is_creature:
        #     return f"{self.name} [{self.power}/{self.toughness}]"
        # return f"{self.name} ({''.join(self.colors) or 'C'})"
        parts = []
        if self.mana_cost.get('generic'):
            parts.append(f"{{{self.mana_cost['generic']}}}")
        for symbol in ('W', 'U', 'B', 'R', 'G'):
            count = self.mana_cost.get(symbol, 0)
            parts.extend([f"{{{symbol}}}"] * count)
        mana_str = ''.join(parts) if parts else '{0}'
        return f"{self.name} {mana_str}"
    
def row_to_card(row: pd.Series) -> Card:
    def safe_list(val):
        if isinstance(val, list):
            return tuple(val)
        return tuple()

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
        mana_cost=parse_manaCost(row.get('manaCost')),
        cmc=row.get('convertedManaCost'),
        power=safe_int(row.get('power')),
        toughness=safe_int(row.get('toughness')),
        oracle_text=row.get('text', '') or '',
    )

def deck_to_cards(deck_df: pd.DataFrame) -> list[Card]:
    """
    Converts a deck dataframe into a list of card objects
    """
    return [row_to_card(row) for _, row in deck_df.iterrows()]