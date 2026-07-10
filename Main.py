from itertools import combinations, islice
import json
import pandas as pd
from Cards import deck_to_cards
from GameLoop import GameLoop
from EvaluateDecks import evaluate_decks
import matplotlib.pyplot as plt

import Constants

from DeckBuilding import *
from Stats import *

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



def play_games(n, decks, max_turns, best_of):
    winners = {}
    for i in list(combinations(range(n), 2)):
        match_winners = {}
        games_played = 0
        
        while games_played < best_of:    
            deck1 = decks[i[0]]
            deck2 = decks[i[1]]
            gameLoop = GameLoop(deck1, deck2, verbose = False)
            winner = gameLoop.run(max_turns=max_turns)
            if(winner is not None):
                winnerIndex = i[winner]
                key = "deck " + str(winnerIndex)
                match_winners[key] = match_winners.get(key, 0) + 1
            games_played += 1

        if match_winners:
            match_winner = max(match_winners, key=match_winners.get)
            winners[match_winner] = winners.get(match_winner, 0) + 1
    
    
    
    return winners



if __name__ == "__main__":
    generation_stats = []
    
    
    print("Loading cards...")
    Constants.SOS_CARDS = load_data(r"E:\Python\mtg\SOS.json")
    decks = []
    deck_dfs = []
    num_decks = 30
    num_generations = 20

    for i in range(num_decks):
        deck_df = construct_deck(Constants.SOS_CARDS, 31, 44)
        deck = deck_to_cards(deck_df)
        decks.append(deck)
        deck_dfs.append(deck_df)

    for i in range(num_generations):
        winners = play_games(len(decks), decks, 25, 5)  # use actual deck count
        sorted_winners = sorted(winners.items(), key=lambda item: item[1], reverse=True)
        print("Generation " + str(i + 1) + " Winrates:\n" + str(sorted_winners))

        total_wins = sum(winners.values())
        
        
        win_rates = {key: wins / total_wins for key, wins in winners.items()}
        generation_stats = update_generation_stats(generation_stats, win_rates, i)
        
        


        

        decks, deck_dfs = evaluate_decks(deck_dfs, winners, .5, .25)
        


    generate_plot_overall(generation_stats)
    
    
    

    

    


