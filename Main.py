from itertools import combinations, islice
import json
import random
import pandas as pd
from Cards import deck_to_cards
from GameLoop import GameLoop
from EvaluateDecks import evaluate_decks
import matplotlib.pyplot as plt

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
    num_decks = 25
    num_generations = 50

    for i in range(num_decks):
        deck_df = construct_deck(Constants.SOS_CARDS)
        deck = deck_to_cards(deck_df)
        decks.append(deck)
        deck_dfs.append(deck_df)

    for i in range(num_generations):
        winners = play_games(len(decks), decks, 25, 3)  # use actual deck count
        sorted_winners = sorted(winners.items(), key=lambda item: item[1], reverse=True)
        print(sorted_winners)

        total_wins = sum(winners.values())
        
        
        win_rates = {key: wins / total_wins for key, wins in winners.items()}
        generation_stats.append({
            "generation": i,
            "top_win_rate": max(win_rates.values()),
            "avg_win_rate": sum(win_rates.values()) / len(win_rates),
            "winner": max(win_rates, key=win_rates.get)
        })
        
        
        # generation_record = {"generation": i}
        # for j in range(len(decks)):
        #     key = f"deck {j}"
        #     wins = winners.get(key, 0)
        #     generation_record[key] = wins / total_wins if total_wins > 0 else 0
        
        # generation_stats.append(generation_record)

        

        decks, deck_dfs = evaluate_decks(deck_dfs, winners, .3, .4, .3)
        


    generations = [s["generation"] for s in generation_stats]
    top_rates = [s["top_win_rate"] for s in generation_stats]
    avg_rates = [s["avg_win_rate"] for s in generation_stats]

    plt.plot(generations, top_rates, label="Top Win Rate")
    plt.plot(generations, avg_rates, label="Avg Win Rate")
    plt.xlabel("Generation")
    plt.ylabel("Win Rate")
    plt.title("Deck Evolution Over Generations")
    plt.legend()
    plt.show()
    
    
    
    # stats_df = pd.DataFrame(generation_stats)
    
    # plt.figure(figsize=(12, 6))
    # for j in range(num_decks):
    #     key = f"deck {j}"
    #     plt.plot(stats_df["generation"], stats_df[key], label=key, alpha=0.7)
    
    # # plot average on top as a bold reference line
    # deck_columns = [f"deck {j}" for j in range(num_decks)]
    # stats_df["avg"] = stats_df[deck_columns].mean(axis=1)
    # plt.plot(stats_df["generation"], stats_df["avg"], label="Average", 
    #          color="black", linewidth=2, linestyle="--")
    
    # plt.xlabel("Generation")
    # plt.ylabel("Win Rate")
    # plt.title("Individual Deck Win Rates Over Generations")
    # plt.legend(loc="upper right", fontsize=7)
    # plt.show()
    

    


