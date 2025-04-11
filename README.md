# dune-certik integrated to create how3 base model /rahul lath


# Centralized Protocol Processor

This module provides a unified approach to processing protocol data and calculating scores, with protocol-specific customizations applied from a central configuration.

## Overview

Instead of creating individual files for each protocol's score calculations, this centralized approach uses a JSON configuration file to define protocol-specific adjustments and parameters. This makes the system:

1. **Scalable** - Add new protocols by simply updating the configuration file
2. **Maintainable** - Protocol-specific logic is in one place rather than scattered across files
3. **Transparent** - All adjustments are documented in the configuration file
4. **Consistent** - Core calculation logic is reused across protocols

## Key Components

### 1. Configuration File (`protocol_config.json`)

The configuration file defines:

- Protocol metadata (name, symbol, category, description)
- Protocol-specific query IDs for Dune Analytics
- Adjustments to be applied to the data (e.g., revenue mapping, weights)
- Default settings for protocols that don't have specific configurations

Example:
```json
{
  "protocols": {
    "chainlink": {
      "name": "Chainlink",
      "symbol": "LINK",
      "category": "Oracle",
      "description": "Decentralized oracle network connecting smart contracts to real-world data",
      "queries": {
        "eqs": {
          "query_id": "4953227",
          "adjustments": {
            "revenue_mapping": {
              "ocr": "fm",
              "comment": "OCR doesn't generate fees directly, attributing to FM (Price Feeds)"
            },
            "weights": {
              "stability": 0.7,
              "diversification": 0.3
            }
          }
        }
      }
    }
  }
}
```

### 2. Centralized Processor (`centralized_processor.py`)

The processor:

- Loads the configuration file
- Applies protocol-specific adjustments to the data
- Calculates scores using the configured parameters
- Generates comprehensive reports

### 3. Calculation Logic (`improved_eqs_calculator.py`)

The underlying calculation logic remains consistent, but can be customized through the configuration:

- Stability score: Based on month-over-month revenue volatility
- Diversification score: Based on distribution of revenue sources
- Magnitude score: Based on total revenue amount
- Combined EQS score: Weighted combination adjusted by magnitude

### 4. Runner Script (`run_centralized_scoring.py`)

A command-line tool to run the scoring process for any protocol.

## Usage

### Adding a New Protocol

1. Add an entry to the `protocols` section of `protocol_config.json`:

```json
"uniswap": {
  "name": "Uniswap",
  "symbol": "UNI",
  "category": "DEX",
  "description": "...",
  "queries": {
    "eqs": {
      "query_id": "4953227",
      "adjustments": {
        "weights": {
          "stability": 0.7,
          "diversification": 0.3
        }
      }
    }
  }
}
```

2. Run the scoring for the new protocol:

```
python run_centralized_scoring.py uniswap
```

### Protocol-Specific Adjustments

#### Revenue Mapping

Used to reallocate revenue from one source to another:

```json
"revenue_mapping": {
  "source_from": "source_to"
}
```

This adds the revenue from `source_from` to `source_to` and sets `source_from` to zero.

#### Custom Weights

Adjust the weights used for combining component scores:

```json
"weights": {
  "stability": 0.7,
  "diversification": 0.3
}
```

#### Reference Values

Set reference values for normalization:

```json
"reference_revenue": 5000000
```

## Output

The system produces:

1. JSON report files (in `scores/{protocol}_report.json`)
2. CSV files with adjusted data (in `scores/{protocol}_adjusted_data.csv`)
3. Console output with summary information

## Example: Chainlink EQS Calculation

For Chainlink, the configuration specifies:

1. OCR revenue should be attributed to FM (Price Feeds)
2. Stability should have 70% weight, diversification 30%

Before adjustments:
- Original revenue distribution: fm (39.90%), ocr (57.18%), others (~2.9%)
- EQS Score: 80.29

After adjustments:
- Adjusted revenue distribution: fm (97.08%), ocr (0.00%), others (~2.9%)
- EQS Score: 90.22

The improvement in EQS reflects that Chainlink's revenue is more sustainable when properly attributed to its primary revenue-generating services.
