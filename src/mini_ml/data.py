import random


def generate_samples(count: int, seed: int) -> list[tuple[float, float, int]]:
    if count <= 0:
        raise ValueError("count must be positive")

    rng = random.Random(seed)
    samples = []

    for _ in range(count):
        x1 = rng.uniform(-1, 1)
        x2 = rng.uniform(-1, 1)
        label = int(x1 + x2 >= 0)
        samples.append((x1, x2, label))

    return samples