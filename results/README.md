# Campaign results

`results/campaigns/` is the sole retained result history. Every directory is a
completed campaign with configuration, environment, predictions, metrics, and
cryptographic manifests.

All completed campaigns are retained, including the corrected 712/181 run, the
70/20/10 run, the original final nested structure-aware run, and its clean-path
reexecution. Loose exploratory `results/runs` and paper-oriented integrated
bundles are intentionally excluded.

`FINAL_REEXECUTION_EQUIVALENCE.md` records the exact comparison between the two
final nested campaigns.

Do not combine metrics across protocols or edit files inside a completed
campaign.
