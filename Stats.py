import pandas as pd
import matplotlib.pyplot as plt

def generate_plot_overall(generation_stats):
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


def update_generation_stats(generation_stats, win_rates, i):
    generation_stats.append({
        "generation": i,
        "top_win_rate": max(win_rates.values()),
        "avg_win_rate": sum(win_rates.values()) / len(win_rates),
        "winner": max(win_rates, key=win_rates.get)
    })
    return generation_stats


