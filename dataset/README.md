# FAIR1M Sample Acquisition Notes

SAT-Edge-Agent uses a 100-image sample acquired from the third-party FAIR1M satellite-imagery mirror on Kaggle:

https://www.kaggle.com/datasets/ollypowell/fair1m-satellite-imagery-for-object-detection

The Kaggle data card was checked on 2026-08-04. It describes the mirror as derived from FAIR1M and lists `Attribution-NonCommercial-ShareAlike 3.0 IGO (CC BY-NC-SA 3.0 IGO)`.

The project does not redistribute the image files or the complete internal metadata bundle. Users must obtain the data from the original FAIR1M/Kaggle source and comply with the terms shown there.

## Public Verification Files

| File | Purpose |
|---|---|
| `sample_100_mix_manifest.csv` | The 100 selected filenames and source split, with internal source paths removed. |
| `sample_100_mix_sha256.csv` | SHA-256 checksum for each selected image. |
| `DATA_LICENSE.md` | Separation between the repository software license and third-party data terms. |

## Expected Local Layout

```text
dataset/
  sample_100_mix_manifest.csv
  sample_100_mix_sha256.csv
  sample_100_mix/
    train__t_10144.jpg
    train__t_10175.jpg
    ...
```

The `sample_100_mix/` image directory is ignored by Git.

## Reproduce the Local Sample

1. Download the FAIR1M Kaggle mirror or obtain FAIR1M through an authorized source.
2. Select and rename the files according to `sample_100_mix_manifest.csv`.
3. Place them under `dataset/sample_100_mix/`.
4. Verify each image against `sample_100_mix_sha256.csv`.
5. Run the HIL orchestration or downlink-payload scripts described in `REPRODUCIBILITY.md`.

Example checksum verification in PowerShell:

```powershell
$expected = Import-Csv dataset/sample_100_mix_sha256.csv
$expected | ForEach-Object {
  $path = Join-Path dataset/sample_100_mix $_.file_name
  $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
  [pscustomobject]@{ file_name = $_.file_name; match = ($actual -eq $_.sha256) }
}
```

## Geographic Metadata Boundary

The HIL service propagates geographic fields associated with the FAIR1M-style sample metadata. It does not implement a new sensor-model or map-registration algorithm. The public artifact package includes a redacted output example, but the complete internal metadata bundle is not redistributed because it contains third-party-derived fields outside the software-release boundary.
