from itertools import combinations, islice
import json
import random
import pandas as pd
from Cards import deck_to_cards
from GameLoop import GameLoop
from EvaluateDecks import evaluate_decks

import Constants

from DeckBuilding import *

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



def play_games(n, decks, max_turns):
    winners = {}
    for i in list(combinations(range(n), 2)):
        deck1 = decks[i[0]]
        deck2 = decks[i[1]]
        gameLoop = GameLoop(deck1, deck2, verbose=True)
        winner = gameLoop.run(max_turns=max_turns)
        if(winner is not None):
            winnerIndex = i[winner]

            key = "deck " + str(winnerIndex)
            winners[key] = winners.get(key, 0) + 1
    return winners



if __name__ == "__main__":
    print("Loading cards...")
    Constants.SOS_CARDS = load_data(r"E:\Python\mtg\SOS.json")
    decks = []
    deck_dfs = []
    num_decks = 10
    for i in range(num_decks):
        deck_df = construct_deck(Constants.SOS_CARDS)
        deck = deck_to_cards(deck_df)
        decks.append(deck)
        deck_dfs.append(deck_df)

    print(decks)
    winners = play_games(10, decks, 25)
    print(winners)

    print(evaluate_decks(deck_dfs, winners, .3, .4, .3))


