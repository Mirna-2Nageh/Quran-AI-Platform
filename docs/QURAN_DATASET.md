# Quran Dataset Setup

## Overview

The recitation backend uses a local Quran text dataset to validate
the expected text for a selected surah and ayah range.

The dataset is not committed to this repository.

## Source

- API: https://api.alquran.cloud/v1/quran/ar.uthmani
- Edition: `quran-uthmani-quran-academy`
- Surahs: 114
- Ayahs: 6,236

Local dataset path: `backend/data/quran/uthmani.json`

## Initial Setup

Run from the repository root:

    python scripts/setup_quran_dataset.py

An internet connection is required for the initial download.
The script validates the dataset and checks its pinned SHA-256.
It refuses to overwrite an existing file.

## Verify an Existing Dataset

    python scripts/setup_quran_dataset.py --verify-only

Expected output: `Quran dataset verification: PASSED`

## Run Tests

    PYTHONPATH=backend python -m pytest backend/tests -q

## Important Limitations

- The pinned checksum verifies snapshot consistency, not independent
  Quranic text accuracy.
- Independent verification against an authoritative Quran text
  remains required before production release.
- Source licensing and redistribution permissions require review.
- The upstream API may change; mismatched downloads are rejected.
- Deployment environments must provision the dataset before
  enabling recitation analysis.
