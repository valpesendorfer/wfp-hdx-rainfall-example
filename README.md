## WFP rainfall datasets on the Humanitarian Data Exchange (HDX)

In July 2025, the UN World Food Programme (WFP) released an update to their [rainfall datasets on HDX](https://data.humdata.org/dataset/?dataseries_name=WFP+-+Rainfall+Indicators+at+Subnational+Level) adding [CHIRPS-GEFS](https://chc.ucsb.edu/data/chirps-gefs) short term forecasts, and coverage at administrative level 1, increasing to full subnational coverage for each country.

This repository contains a simple example on how to programmatically access this data, and create a simple analysis with visualizations, which combines the [rainfall dataset for Yemen](https://data.humdata.org/dataset/yem-rainfall-subnational) with the [subnational boundary files of Yemen](https://data.humdata.org/dataset/cod-ab-yem), also available on HDX. To get more info about the rainfall dataset or the country boundaries, please refer to the datasets' description on HDX.

To see a static version of this dashboard, please visit the [GitHub pages site of this repo](https://valpesendorfer.github.io/wfp-hdx-rainfall-example/).

## Features

- Interactive Marimo notebook for exploring WFP rainfall data
- Direct access to HDX datasets using the [HDX Python API](https://hdx-python-api.readthedocs.io/en/latest/)
- Visualization of 3-month rainfall anomalies at subnational level
- Interactive maps and charts using Altair and GeoPandas
- Efficient data loading with [DuckDB](https://duckdb.org/), [DuckDB spatial](https://duckdb.org/docs/stable/core_extensions/spatial/overview.html) and [GDAL virtual file systems](https://gdal.org/en/stable/user/virtual_file_systems.html)

## Requirements

- Python 3.13+
- Dependencies managed with `uv` (see `pyproject.toml`)
. To install `uv`., sIf you need to install `uv`, follow [this guide](https://docs.astral.sh/uv/getting-started/installation/).
## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/valpesendorfer/wfp-hdx-rainfall-example.git
   cd hdx
   ```

2. Install dependencies using `uv`:
   ```bash
   uv sync
   ```

## Usage

Run the interactive Marimo notebook:

```bash
uv run marimo run app.py
```

Or edit the notebook:

```bash
uv run marimo edit app.py
```

The notebook will open in your browser and guide you through:
- Accessing WFP rainfall datasets from HDX
- Loading subnational boundary data for Yemen
- Creating interactive visualizations of rainfall anomalies
- Exploring temporal trends in rainfall data

## What the notebook covers

The example focuses on Yemen's rainfall data and demonstrates:

1. **Data Access**: How to programmatically access HDX datasets
2. **Data Processing**: Using DuckDB for efficient data manipulation
3. **Geospatial Analysis**: Combining rainfall data with administrative boundaries
4. **Interactive Visualization**: Creating maps and time series charts
5. **Deep Dive Analysis**: Exploring specific governorates and districts

The analysis examines 3-month rainfall anomalies, comparing current values against long-term averages (1989-2018) to identify areas with below or above normal rainfall patterns.

