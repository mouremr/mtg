def update_elo(rating_a, rating_b, score_a, k=32):
    """score_a: 1.0 if A won, 0.0 if B won"""
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    new_a = rating_a + k * (score_a - expected_a)
    new_b = rating_b + k * ((1 - score_a) - (1 - expected_a))
    return new_a, new_b