from itertools import combinations, islice
import json
import pandas as pd
from Cards import deck_to_cards
from GameLoop import GameLoop
from EvaluateDecks import evaluate_decks
from Elo import update_elo

import Constants

from DeckBuilding import *
from Stats import *

def load_data(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        data = json.load(file)

    # read strixhaven cards from json
    cards = pd.DataFrame(data["data"]["cards"])
    cards = cards.drop_duplicates(subset="name", keep="first")


    columns_to_drop = [
        "artist", "artistIds", "availability", "borderColor",
        "edhrecRank", "edhrecSaltiness", "finishes", "foreignData", "frameEffects",
        "frameVersion", "language", "layout", "printings", "purchaseUrls",
        "securityStamp", "setCode", "skuIds", "sourceProducts", "flavorText", "isStorySpotlight",
        "relatedCards", "watermark", "isReprint", "isFullArt", "isTextless",
        "promoTypes", "isPromo", "rulings", "rarity", "variations", "uuid", "number",
        "identifiers", "legalities", "leadershipSkills", "manaValue",
    ]

    existing_columns_to_drop = [col for col in columns_to_drop if col in cards.columns]
    cards = cards.drop(columns=existing_columns_to_drop)
    return cards



def play_games(deck_records, max_turns, best_of, k=32):
    for i, j in combinations(range(len(deck_records)), 2):
        rec_a, rec_b = deck_records[i], deck_records[j]
        games_played = 0
        while games_played < best_of:
            gameLoop = GameLoop(rec_a.cards, rec_b.cards, verbose=False)
            winner = gameLoop.run(max_turns=max_turns)
            if winner is not None:
                score_a = 1.0 if winner == 0 else 0.0
                rec_a.elo, rec_b.elo = update_elo(rec_a.elo, rec_b.elo, score_a, k=k)
            games_played += 1
    return deck_records


def evaluate_vs_benchmarks(deck_records, benchmarks, max_turns, games_per_matchup=5):
    results = {}
    for rec in deck_records:
        wins = 0
        total = 0
        for bench in benchmarks:
            for _ in range(games_per_matchup):
                gameLoop = GameLoop(rec.cards, bench.cards, verbose=False)
                winner = gameLoop.run(max_turns=max_turns)
                if winner is not None:
                    total += 1
                    if winner == 0:
                        wins += 1
        results[rec.id] = wins / total if total else 0.0
    return results



if __name__ == "__main__":
    generation_stats = []

    print("Loading cards...")

    set_codes = [
        "SOS"
    ]

    set_dataframes = []
    for code in set_codes:
        filepath = rf"E:\Python\mtg\Set_json\{code}.json"
        set_df = load_data(filepath)
        set_df["setCode"] = code  # tag origin before merging, in case you want it later
        set_dataframes.append(set_df)

    Constants.TOTAL_CARDPOOL = pd.concat(set_dataframes, ignore_index=True)
    Constants.TOTAL_CARDPOOL = Constants.TOTAL_CARDPOOL.drop_duplicates(subset="name", keep="first")

    print(f"Loaded {len(Constants.TOTAL_CARDPOOL)} unique cards across {len(set_codes)} sets.")

    num_decks = 30
    num_generations = 20
    num_benchmarks = 4

    deck_records = [DeckRecord(construct_deck(Constants.TOTAL_CARDPOOL, 31, 44)) for _ in range(num_decks)]

    benchmark_decks = [DeckRecord(construct_deck(Constants.TOTAL_CARDPOOL, 31, 44)) for _ in range(num_benchmarks)]
    for bench in benchmark_decks:
        bench.cards = deck_to_cards(bench.deck_df)

    for gen in range(num_generations):
        for rec in deck_records:
            rec.cards = deck_to_cards(rec.deck_df)

        play_games(deck_records, 25, 5)  #play against decks in current generation, update overall elo score

        bench_results = evaluate_vs_benchmarks(deck_records, benchmark_decks, max_turns=25)

        ranked = sorted(deck_records, key=lambda r: r.elo, reverse=True)
        print(f"Generation {gen + 1} Elo:\n" +
              "\n".join(f"deck {r.id}: {r.elo:.1f} | vs benchmarks: {bench_results[r.id]:.2%}" for r in ranked))

        generation_stats = update_generation_stats(generation_stats, deck_records, bench_results, gen)

        deck_records = evaluate_decks(deck_records, 0.5, 0.25)

    generate_plot_overall(generation_stats)
    
    
    

    

    


