# Private validation outputs

This directory is reserved for future external-validation exports. Use one new
private run subfolder per approved external CSV. A reviewed run may contain
validation metadata, random-forest and RBF-SVC predictions, model-disagreement
flags, applicability results, and optional comparisons with laboratory labels.
Keep real predictions, applicability flags, observed labels, laboratory
identifiers, and derived tables private until data-use permissions,
model/version provenance, descriptor compatibility, threshold/applicability
approvals, and scientific review are complete.

Only reviewed aggregate outputs may be shared. Do not commit molecule-level results or confidential laboratory data. The directory is intentionally retained with `.gitkeep` so the future output location is visible without containing results.
