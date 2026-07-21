import matplotlib.pyplot as plt
from Constants import BASIC_NAMES
from DeckBuilding import DeckRecord
import pandas as pd

def update_generation_stats(generation_stats, deck_records, bench_results, i):
    elos = [r.elo for r in deck_records]
    best = max(deck_records, key=lambda r: r.elo)
    bench_rates = list(bench_results.values())

    generation_stats.append({
        "generation": i,
        "top_elo": best.elo,
        "avg_elo": sum(elos) / len(elos),
        "winner_id": best.id,
        "top_benchmark_winrate": bench_results[best.id],
        "avg_benchmark_winrate": sum(bench_rates) / len(bench_rates),
    })
    return generation_stats

def generate_plot_overall(generation_stats):
    generations = [s["generation"] for s in generation_stats]

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(8, 8))

    ax1.plot(generations, [s["top_elo"] for s in generation_stats], label="Top Elo")
    ax1.plot(generations, [s["avg_elo"] for s in generation_stats], label="Avg Elo")
    ax1.set_ylabel("Elo Rating")
    ax1.set_title("Within-Population Elo (selection signal -- expected to drift up)")
    ax1.legend()

    ax2.plot(generations, [s["top_benchmark_winrate"] for s in generation_stats], label="Top Deck vs Benchmarks")
    ax2.plot(generations, [s["avg_benchmark_winrate"] for s in generation_stats], label="Population Avg vs Benchmarks")
    ax2.set_xlabel("Generation")
    ax2.set_ylabel("Win Rate vs Frozen Benchmarks")
    ax2.set_title("Real Improvement Signal (fixed yardstick)")
    ax2.legend()

    plt.tight_layout()
    plt.show()

def update_winner_stats(generation_stats, best: DeckRecord, gen: int):
    def find_cmc():
        cmc_column = 'convertedManaCost'
        
        if not nonlands.empty and cmc_column in nonlands.columns:
            avg_cmc = nonlands[cmc_column].mean()
        else:
            avg_cmc = 0.0
            
        # print(f"Deck {best.id} Average Non-Land CMC: {avg_cmc:.2f}")
        return avg_cmc
    
    def color_dist():
        distribution = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0, 'C': 0}
        
        if 'colorIdentity' in nonlands.columns:
            counts = nonlands['colorIdentity'].explode().value_counts(dropna=False)
            
            for color, count in counts.items():
                if pd.isna(color):
                    distribution['C'] = int(count)
                elif color in distribution:
                    distribution[color] = int(count)
        return distribution
        

    
    def avg_win_turn():
        win_turns = best.match_history.get("win_turns", [])
    
        if not win_turns:
            # Returns 0 or None if the deck never won a single match
            return 0.0
            
        avg = sum(win_turns) / len(win_turns)
        return round(avg, 2)
    

    nonlands = best.deck_df[~best.deck_df['name'].isin(BASIC_NAMES)]
    lands = best.deck_df[best.deck_df['name'].isin(BASIC_NAMES)]
    
    stats = {
        "generation": gen, # FIX: Added to track history across x-axis
        "avg_cmc": round(find_cmc(), 2), 
        "num_lands": len(lands),
        "num_nonlands": len(nonlands),
        "color_dist": color_dist(),
        "avg_win_turn": avg_win_turn()
    }
    
    return stats

def generate_plot_winner(winner_stats: list):
    """Generates four distinct historical trend plots tracking the evolution

    of winning deck archetypes over generations.
    """
    if not winner_stats:
        print("No winner stats recorded to plot.")
        return

    # 1. Extract primary independent x-axis array
    generations = [s["generation"] for s in winner_stats]

    # 2. Set up a comprehensive 2x2 grid layout
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, sharex=True, figsize=(12, 10))

    # --- Plot 1: Mana Cost Curve Evolution ---
    ax1.plot(generations, [s["avg_cmc"] for s in winner_stats], color='purple', marker='o', label="Avg CMC")
    ax1.set_ylabel("Mana Value")
    ax1.set_title("Average Card CMC (Spells Only)")
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()

    # --- Plot 2: Land Density Balance ---
    ax2.plot(generations, [s["num_lands"] for s in winner_stats], color='forestgreen', marker='s', label="Lands")
    ax2.plot(generations, [s["num_nonlands"] for s in winner_stats], color='crimson', marker='^', label="Spells")
    ax2.set_ylabel("Card Count")
    ax2.set_title("Deck Composition (Lands vs. Spells)")
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend()

    # --- Plot 3: Speed & Win Clocks ---
    ax3.plot(generations, [s["avg_win_turn"] for s in winner_stats], color='darkorange', marker='d', label="Avg Win Turn")
    ax3.set_xlabel("Generation")
    ax3.set_ylabel("Turn Count")
    ax3.set_title("Average Game-Winning Turn Speed")
    ax3.grid(True, linestyle='--', alpha=0.6)
    ax3.legend()

    # --- Plot 4: Unpacked Color Identity Distribution ---
    # Define exact official hex color codes matching MTG branding themes
    mtg_colors = {
        'W': {'label': 'White', 'color': '#F8E7B9'},
        'U': {'label': 'Blue',  'color': '#0E68AB'},
        'B': {'label': 'Black', 'color': '#A69F9D'},
        'R': {'label': 'Red',   'color': '#D32F2F'},
        'G': {'label': 'Green', 'color': '#2E7D32'},
        'C': {'label': 'Colorless', 'color': '#757575'}
    }

    # Extract historical pip sequences safely color-by-color
    for key, styles in mtg_colors.items():
        pip_counts = [s["color_dist"].get(key, 0) for s in winner_stats]
        ax4.plot(generations, pip_counts, color=styles['color'], linewidth=2.5, label=styles['label'])

    ax4.set_xlabel("Generation")
    ax4.set_ylabel("Number of Non-Land Pips")
    ax4.set_title("Color Identity Composition Trends")
    ax4.grid(True, linestyle='--', alpha=0.6)
    ax4.legend(loc="upper right")

    plt.tight_layout()
    plt.show()