import numpy as np
import pandas as pd

from src.external_cr8_extension import frozen_five_splits


def test_frozen_cr8_selection_splits_have_no_group_leakage() -> None:
    frame = pd.read_csv("data/official/train_RDKitFixed.csv")
    splits = frozen_five_splits(frame)
    assert len(splits) == 5
    covered = np.concatenate([validation for _, validation in splits])
    assert sorted(covered.tolist()) == list(range(len(frame)))
    for train_idx, validation_idx in splits:
        assert not (
            set(frame.iloc[train_idx].BUTINA_CLUSTER_ID)
            & set(frame.iloc[validation_idx].BUTINA_CLUSTER_ID)
        )
