from itertools import combinations
import json
import pandas as pd
from Cards import deck_to_cards
from GameLoop import GameLoop


BASIC_NAMES = ['Forest', 'Swamp', 'Plains', 'Mountain', 'Island']

BASIC_MAP = {'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Mountain', 'G': 'Forest'}



def load_data(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        data = json.load(file)

    # read strixhaven cards from json
    cards = pd.DataFrame(data["data"]["cards"])
    cards = cards.drop_duplicates(subset="name", keep="first")


    cards = cards.drop(columns=["artist", 'artist', 'artistIds', 'availability', 'borderColor', 
                                        'edhrecRank', 'edhrecSaltiness', 'finishes', 'foreignData', 'frameEffects', 
                                        'frameVersion', 'language', 'layout', 'printings', 'purchaseUrls', 
                                        'securityStamp', 'setCode', 'skuIds', 'sourceProducts', 'flavorText', 'isStorySpotlight', 
                                        'relatedCards', 'watermark', 'isReprint', 'isFullArt', 'isTextless', 
                                        'promoTypes', 'isPromo', 'rulings', 'rarity', 'variations', 'uuid', 'number', 'identifiers', 'legalities', 'leadershipSkills', 'manaValue'])
    return cards




def construct_deck(cards):
    basic_names = ['Forest', 'Swamp', 'Plains', 'Mountain', 'Island']

    #pick random non-basic land cards from the input dataframe
    deck = pd.DataFrame(columns=cards.columns)
    
    while len(deck) < 38:
        random_row = cards[~cards['name'].isin(basic_names)].sample()  # exclude basics here
        card_name = random_row['name'].values[0]
        
        if (deck['name'] == card_name).sum() < 4:
            deck = pd.concat([deck, random_row], ignore_index=True)
            
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
            basic_row = cards[cards['name'] == basic_name]
            for i in range(count):
                deck = pd.concat([deck, basic_row], ignore_index=True)

    return deck




def play_games(n, cards, max_turns):
    decks = []
    winners = {}
    for i in range(n):
        deck_df = construct_deck(cards)
        deck = deck_to_cards(deck_df)
        decks.append(deck)
    for i in list(combinations(range(n), 2)):
        deck1 = decks[i[0]]
        deck2 = decks[i[1]]
        gameLoop = GameLoop(deck1, deck2, verbose=True)
        winner = gameLoop.run(max_turns=max_turns)
        
        winnerIndex = i[winner]

        key = "deck " + str(winnerIndex)
        winners[key] = winners.get(key, 0) + 1
    return winners




if __name__ == "__main__":
    print("Loading cards...")
    sos_cards = load_data(r"E:\Python\mtg\SOS.json")
    winners = play_games(10, sos_cards, 25)
    print(winners)

    
    # deck1_df = construct_deck(sos_cards)
    # deck2_df = construct_deck(sos_cards)

    # deck1 = deck_to_cards(deck1_df)
    # deck2 = deck_to_cards(deck2_df)




    # print("\n--- Starting Game ---\n")
    # gameLoop = GameLoop(deck1, deck2, verbose=True)
    # winner = gameLoop.run(max_turns=25)

    # if winner is not None:
    #     print(f"\nResult: Player {winner + 1} wins!")
    # else:
    #     print("\nResult: Draw / Timeout")


