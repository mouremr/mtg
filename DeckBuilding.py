import pandas as pd
import Constants
import random

def construct_deck(cards, min_deck_size, max_deck_size):
    basic_names = ['Forest', 'Swamp', 'Plains', 'Mountain', 'Island']
    num_colors = random.choice([1, 2, 3])
    
    all_colors = ['W', 'U', 'B', 'R', 'G']
    chosen_colors = set(random.sample(all_colors, num_colors))

    color_filter = cards['colors'].apply(
        lambda c: len(c) == 0 or all(color in chosen_colors for color in c)
    )
    card_pool = cards[color_filter & ~cards['name'].isin(basic_names)]

    deck = pd.DataFrame(columns=cards.columns)
    
    while len(deck) < random.randint(min_deck_size, max_deck_size):
        random_row = card_pool.sample()
        card_name = random_row['name'].values[0]
        
        if (deck['name'] == card_name).sum() < 4:
            deck = pd.concat([deck, random_row], ignore_index=True)

    deck = construct_manabase(deck)
    return deck
            
def construct_manabase(deck):
    # get weighted color counts
    rows = []
    for colors in deck['colors']:
        if len(colors) > 0:
            weight = 1 / len(colors)
            for color in colors:
                rows.append({'color': color, 'weight': weight})
    
    color_weights = pd.DataFrame(rows).groupby('color')['weight'].sum()

    # Add basic lands to fill remaining deck slots
    basics_needed = 60 - len(deck)
    color_weights = color_weights
    color_weights = color_weights / color_weights.sum()

    basic_map = {
        'W': 'Plains',
        'U': 'Island',
        'B': 'Swamp',
        'R': 'Mountain',
        'G': 'Forest'
    }

    basic_counts = (color_weights * basics_needed).round().astype(int)
    diff = basics_needed - basic_counts.sum()
    if diff != 0:
        basic_counts.iloc[0] += diff

    for color, count in basic_counts.items():
        if color in basic_map and count > 0:
            basic_name = basic_map[color]
            basic_row = Constants.SOS_CARDS[Constants.SOS_CARDS['name'] == basic_name] #todo: fix this line
            for i in range(count):
                deck = pd.concat([deck, basic_row], ignore_index=True)

    return deck

