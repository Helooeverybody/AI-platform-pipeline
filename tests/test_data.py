import pytest

from mini_ml.data import generate_samples


def test_same_seed_produces_same_data():
    assert generate_samples(20, seed=42) == generate_samples(20, seed=42)


def test_samples_have_expected_shape_and_labels():
    samples = generate_samples(20, seed=42)

    assert len(samples) == 20
    assert all(len(sample) == 3 and sample[2] in (0, 1) for sample in samples)


def test_count_must_be_positive():
    with pytest.raises(ValueError):
        generate_samples(0, seed=42)