from itertools import islice
import random

import pandas as pd

import Constants

from DeckBuilding import construct_manabase

from Constants import BASIC_NAMES

from Cards import deck_to_cards


def evaluate_decks(deck_dfs, winners, percent_keep, percent_mutate, percent_crossover):
    #returns a list of the mutated and changed deck as card objects in order to be used for the next pass of games
    total = len(deck_dfs)
    winners = dict(sorted(winners.items(), key=lambda item: item[1], reverse=True))
    
    amount_to_keep = int(total * percent_keep)
    amount_to_mutate = int(total * percent_mutate)

    if amount_to_keep > len(winners):
        shortfall = amount_to_keep - len(winners)
        amount_to_keep = len(winners)
        amount_to_mutate += shortfall
    amount_to_crossover = total - amount_to_keep - amount_to_mutate

    kept_winners = dict(islice(winners.items(), amount_to_keep))
    mutated = mutate_decks(deck_dfs, winners, amount_to_mutate)
    crossover = crossover_decks(deck_dfs, winners, amount_to_crossover, 3)

    kept_indices = [int(key.split(" ")[1]) for key in kept_winners.keys()]
    kept_deck_dfs = {key: deck_dfs[idx] for key, idx in zip(kept_winners.keys(), kept_indices)}

    #convert all the new decks to a list of card objs
    new_deck_dfs = list(kept_deck_dfs.values()) + list(mutated.values()) + list(crossover.values())
    
    assert len(new_deck_dfs) == total, (
        f"Population size drifted: expected {total}, got {len(new_deck_dfs)} "
        f"(keep={len(kept_deck_dfs)}, mutate={len(mutated)}, crossover={len(crossover)})"
    )
    
    decks = [deck_to_cards(df) for df in new_deck_dfs]
    return decks, new_deck_dfs





def mutate_decks(deck_dfs, winners, num_decks, num_swaps=2):
    mutated_decks = {}
    
    
    top_indices = [int(key.split(" ")[1]) for key, _ in list(winners.items())[:num_decks]]
    
    #fall back to full decklist if not enough winners
    if len(top_indices) < num_decks:
        all_indices = set(range(len(deck_dfs)))
        remaining = list(all_indices - set(top_indices))
        random.shuffle(remaining)
        top_indices += remaining[:num_decks - len(top_indices)]
    
    decks_to_mutate = [deck_dfs[i] for i in top_indices]

    

    for i, df in enumerate(decks_to_mutate):
        df = df.copy()  # avoid mutating the original deck in place
        
        for _ in range(num_swaps):
            nonbasics = df[~df['name'].isin(BASIC_NAMES)]
            if nonbasics.empty:
                break
            
            # remove one random nonbasic card
            #maybe this should take basics too
            drop_idx = nonbasics.sample(1).index
            df = df.drop(drop_idx)
            
            # add a random replacement, respecting 4-copy limit
            #todo: add random card already in colors
            while True:
                colors = df['colorIdentity'].explode().unique().tolist()

                #exclude basices and only include cards of the same color
                candidates = Constants.SOS_CARDS[
                    ~Constants.SOS_CARDS['name'].isin(BASIC_NAMES) & 
                    Constants.SOS_CARDS['colorIdentity'].apply(lambda card_colors: all(c in colors for c in card_colors))
                ]
                if candidates.empty:
                    #if no cards match, just pick from all non-basics
                    print("falling back t random card!")
                    candidates = Constants.SOS_CARDS[~Constants.SOS_CARDS['name'].isin(BASIC_NAMES)]
                candidate = candidates.sample(1)
                #candidate = Constants.SOS_CARDS[~Constants.SOS_CARDS['name'].isin(BASIC_NAMES)].sample()


                name = candidate['name'].values[0]
                if (df['name'] == name).sum() < 4:
                    df = pd.concat([df, candidate], ignore_index=True)
                    break
        
        df = df[~df['name'].isin(BASIC_NAMES)].reset_index(drop=True)
        df = construct_manabase(df)
        mutated_decks[f"deck {i}"] = df
    
    return mutated_decks

def crossover_decks(deck_dfs, winners, amount_to_crossover, tournament_size):
    crossover_decks = {}

    for i in range(amount_to_crossover):
        parents = []

        for _ in range(2):
            tournament_indices = random.sample(range(len(deck_dfs)), tournament_size)
            best_idx = max(tournament_indices, key=lambda idx: winners.get(f"deck {idx}", 0))
            parents.append(deck_dfs[best_idx])

        # fall back to a mutation of the single parent instead
        if parents[0].equals(parents[1]):
            crossover_decks[f"deck {i}"] = mutate_decks(deck_dfs, winners, 1)[f"deck 0"]
        else:
            crossover_decks[f"deck {i}"] = breed_decks(parents[0], parents[1])

    return crossover_decks

def breed_decks(parent1, parent2):
    nonbasics1 = parent1[~parent1['name'].isin(BASIC_NAMES)]
    nonbasics2 = parent2[~parent2['name'].isin(BASIC_NAMES)]

    merged = pd.concat([nonbasics1, nonbasics2], ignore_index=True)

    new_deck = pd.DataFrame(columns=merged.columns)

    #todo: adjust the num of nonlands to be flexible later
    while len(new_deck) < 36:
        available = merged[merged['name'].apply(lambda name: (new_deck['name'] == name).sum() < 4)]
        
        if available.empty:
            # merged is exhausted, draw from sos_cards instead
            candidate = Constants.SOS_CARDS[~Constants.SOS_CARDS['name'].isin(BASIC_NAMES)].sample()
        else:
            candidate = available.sample(1)
        
        name = candidate['name'].values[0]
        if (new_deck['name'] == name).sum() < 4:
            new_deck = pd.concat([new_deck, candidate], ignore_index=True)

    #Add basic adding logic
    new_deck = construct_manabase(new_deck)
    return new_deck
    
