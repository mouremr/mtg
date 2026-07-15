import matplotlib.pyplot as plt

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