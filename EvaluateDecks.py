import random
import pandas as pd

import Constants
from DeckBuilding import construct_manabase, DeckRecord
from Constants import BASIC_NAMES


def evaluate_decks(deck_records, percent_keep, percent_mutate):
    total = len(deck_records)
    ranked = sorted(deck_records, key=lambda r: r.elo, reverse=True)

    elitism_count = min(2, len(ranked))
    elites = ranked[:elitism_count]

    amount_to_keep = int(total * percent_keep) - elitism_count
    amount_to_mutate = int(total * percent_mutate)

    if amount_to_keep > len(ranked) - elitism_count:
        shortfall = amount_to_keep - (len(ranked) - elitism_count)
        amount_to_keep = len(ranked) - elitism_count
        amount_to_mutate += shortfall

    amount_to_crossover = total - amount_to_keep - amount_to_mutate - elitism_count

    kept = ranked[elitism_count:elitism_count + amount_to_keep]
    mutated = mutate_decks(ranked, amount_to_mutate)
    crossover = crossover_decks(ranked, amount_to_crossover, tournament_size=3)

    new_records = list(elites) + list(kept) + mutated + crossover

    assert len(new_records) == total, (
        f"Population size drifted: expected {total}, got {len(new_records)} "
        f"(keep={len(kept)}, mutate={len(mutated)}, crossover={len(crossover)})"
    )
    return new_records


def mutate_decks(ranked_records, num_decks, num_swaps=2, color_mutation_rate=0.10):
    mutated = []
    top_records = ranked_records[:num_decks]

    if len(top_records) < num_decks:
        remaining = [r for r in ranked_records if r not in top_records]
        random.shuffle(remaining)
        top_records += remaining[:num_decks - len(top_records)]

    for parent in top_records:
        df = parent.deck_df.copy()
        
        # Determine current color identity
        colors = set(df['colorIdentity'].explode().dropna().unique().tolist())
        current_color_count = len(colors)

        # Dynamic mutation rate: high for mono-color, scaling down to near-zero for 4+ colors
        # 1 color -> 25% chance | 2 colors -> 10% chance | 3 colors -> 2% chance | 4+ colors -> 0%
        if current_color_count == 1:
            dynamic_color_rate = 0.25
        elif current_color_count == 2:
            dynamic_color_rate = 0.10
        elif current_color_count == 3:
            dynamic_color_rate = 0.02
        else:
            dynamic_color_rate = 0.00
        
        # Apply the scaled splash chance
        if random.random() < dynamic_color_rate:
            all_colors = {'W', 'U', 'B', 'R', 'G'}
            available_to_add = list(all_colors - colors)
            if available_to_add:
                new_color = random.choice(available_to_add)
                colors.add(new_color)

        for _ in range(num_swaps):
            nonbasics = df[~df['name'].isin(BASIC_NAMES)]
            if nonbasics.empty:
                break

            drop_idx = df.sample(1).index
            dropped_card = df.loc[drop_idx]
            df = df.drop(drop_idx)

            target_cmc = dropped_card['faceManaValue'].values[0] if 'faceManaValue' in dropped_card else 3

            # Candidates must match our (potentially expanded) color set
            candidates = Constants.TOTAL_CARDPOOL[
                ~Constants.TOTAL_CARDPOOL['name'].isin(BASIC_NAMES) &
                Constants.TOTAL_CARDPOOL['colorIdentity'].apply(
                    lambda card_colors: all(c in colors for c in card_colors)
                )
            ].copy()

            candidates['cmc_diff'] = abs(candidates['faceManaValue'] - target_cmc)
            candidates = candidates.sort_values('cmc_diff').head(20)

            if candidates.empty:
                candidates = Constants.TOTAL_CARDPOOL[~Constants.TOTAL_CARDPOOL['name'].isin(BASIC_NAMES)]

            while True:
                candidate = candidates.sample(1)
                name = candidate['name'].values[0]
                if (df['name'] == name).sum() < 4:
                    df = pd.concat([df, candidate], ignore_index=True)
                    break

        df = df[~df['name'].isin(BASIC_NAMES)].reset_index(drop=True)
        df = construct_manabase(df)

        mutated.append(DeckRecord(df, elo=parent.elo))

    return mutated


def crossover_decks(ranked_records, amount_to_crossover, tournament_size):
    """picks candidate decks to crossover"""
    children = []

    for _ in range(amount_to_crossover):
        parents = []
        for _ in range(2):
            tournament = random.sample(ranked_records, tournament_size)
            best = max(tournament, key=lambda r: r.elo)
            parents.append(best)

        if parents[0].deck_df.equals(parents[1].deck_df):
            children.append(mutate_decks(ranked_records, 1)[0])
        else:
            child_df = breed_decks(parents[0].deck_df, parents[1].deck_df)
            child_elo = (parents[0].elo + parents[1].elo) / 2
            children.append(DeckRecord(child_df, elo=child_elo))

    return children

def breed_decks(parent1, parent2, num_cards=36):
    new_deck = pd.DataFrame(columns=parent1.columns)
    
    p1_nonbasics = parent1[~parent1['name'].isin(BASIC_NAMES)]
    p2_nonbasics = parent2[~parent2['name'].isin(BASIC_NAMES)]
    
    # 1. Start with cards they have in common (the "consensus" core)
    common_names = set(p1_nonbasics['name']).intersection(set(p2_nonbasics['name']))
    
    for card_name in common_names:
        count1 = (p1_nonbasics['name'] == card_name).sum()
        count2 = (p2_nonbasics['name'] == card_name).sum()
        num_to_add = min(count1, count2, 4)
        
        card_row = p1_nonbasics[p1_nonbasics['name'] == card_name].iloc[0]
        rows_to_add = pd.DataFrame([card_row] * num_to_add)
        new_deck = pd.concat([new_deck, rows_to_add], ignore_index=True)
        
    # skew remaining cards towards one parent to keep archetypes intact
    dominant_parent = p1_nonbasics if random.random() < 0.5 else p2_nonbasics
    secondary_parent = p2_nonbasics if dominant_parent is p1_nonbasics else p1_nonbasics
    
    parent_pool = pd.concat([dominant_parent, secondary_parent], ignore_index=True)
    parent_pool = parent_pool[~parent_pool['name'].isin(common_names)]

    remaining_slots = num_cards - len(new_deck)
    
    for _ in range(remaining_slots):
        # Prefer the parents' un-shared cards
        if not parent_pool.empty:
            candidate = parent_pool.sample(1)
            name = candidate['name'].values[0]
            
            if (new_deck['name'] == name).sum() < 4:
                new_deck = pd.concat([new_deck, candidate], ignore_index=True)
                parent_pool = parent_pool.drop(candidate.index[0]).reset_index(drop=True)
                continue

        # Fallback to general database if parent pool is exhausted or invalid
        source = Constants.TOTAL_CARDPOOL[~Constants.TOTAL_CARDPOOL['name'].isin(BASIC_NAMES)]
        while True:
            candidate = source.sample(1)
            name = candidate['name'].values[0]
            if (new_deck['name'] == name).sum() < 4:
                new_deck = pd.concat([new_deck, candidate], ignore_index=True)
                break
    
    new_deck = construct_manabase(new_deck)
    return new_deck