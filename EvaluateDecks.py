from itertools import islice
import random

import pandas as pd

import Constants

from DeckBuilding import construct_manabase

from Constants import BASIC_NAMES


def evaluate_decks(deck_dfs, winners, percent_to_keep, percent_to_mutate, percent_to_crossover):
    #deck_dfs = 
    
    amount_to_keep = (int)(len(deck_dfs) * percent_to_keep)
    winners = dict(sorted(winners.items(), key=lambda item: item[1], reverse=True))
    kept_winners = dict(islice(winners.items(), amount_to_keep))

    amount_to_mutate = (int)(len(deck_dfs) * percent_to_mutate)
    mutated = mutate_decks(deck_dfs, amount_to_mutate)
    

    amount_to_crossover = (int)(len(deck_dfs) * percent_to_crossover)
    crossover = crossover_decks(deck_dfs, winners, amount_to_crossover, 3)

    kept_indices = [int(key.split(" ")[1]) for key in kept_winners.keys()]
    kept_deck_dfs = {key: deck_dfs[idx] for key, idx in zip(kept_winners.keys(), kept_indices)}
    
    return pd.concat(
        list(kept_deck_dfs.values()) + list(mutated.values()) + list(crossover.values()),
        ignore_index=True
    )


def mutate_decks(deck_dfs, num_decks, num_swaps=2):
    mutated_decks = {}
    
    #this might just be taking random decks and mutating, not sure if thats the plan
    decks_to_mutate = deck_dfs[:num_decks]

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
            while True:
                candidate = Constants.SOS_CARDS[~Constants.SOS_CARDS['name'].isin(BASIC_NAMES)].sample()
                name = candidate['name'].values[0]
                if (df['name'] == name).sum() < 4:
                    df = pd.concat([df, candidate], ignore_index=True)
                    break
        
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

        if parents[0].equals(parents[1]):
            continue

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
            candidate = SOS_CARDS[~SOS_CARDS['name'].isin(BASIC_NAMES)].sample()
        else:
            candidate = available.sample(1)
        
        name = candidate['name'].values[0]
        if (new_deck['name'] == name).sum() < 4:
            new_deck = pd.concat([new_deck, candidate], ignore_index=True)

    #Add basic adding logic
    new_deck = construct_manabase(new_deck)
    return new_deck
    
