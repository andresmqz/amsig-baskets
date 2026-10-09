# Amsig Basket: Rules and Methodology

Basket selected: October 1, 2026
Rules published: the date of the first commit of this file
Author: Andrés Márquez, Amsig Labs

This is a paper model portfolio kept as a research record. It is not investment advice, it is not a recommendation to buy or sell any asset, and nobody should copy it. Its purpose is to test a set of long-term views in public, with fixed rules, so the result can be judged honestly whichever way it goes.

## What it is

A long-term crypto index built from conviction rather than market cap. The core is established infrastructure; the rest is a deliberate tilt toward institutional adoption, tokenization and on-chain credit, with a few newer players that have earned a place. It is published in two official versions: one without Bitcoin, which is the real test of the thesis, and one with Bitcoin as an eleventh asset.

## The assets and why each one is here

**ETH (Ethereum).** I have held this view for years: every serious path in this industry leads back to Ethereum. It is the standard for settlement, DeFi and tokenization, and no L2 or new L1 has made a real dent in its usage or its ecosystem.

**LINK (Chainlink).** It has quietly run underneath most of the industry for years, and no newer oracle has taken meaningful share from it. Quiet, but it works.

**BNB (BNB).** Binance is the most powerful company in the industry and it keeps winning. BNB is a bet that this continues.

**ONDO (Ondo).** Tokenization is the biggest use case traditional finance is taking from crypto, and Ondo is at the front of it.

**SYRUP (Maple).** Institutional on-chain credit. Maple connects institutional borrowers with lenders through on-chain lending pools, bringing real credit underwriting to a market that DeFi has long served with crypto collateral alone. (Maple's token migrated from MPL to SYRUP; the basket tracks SYRUP.)

**HYPE (Hyperliquid).** Novel and efficient when it launched, and it changed what people expect from an on-chain venue. It is now a major venue for on-chain derivatives trading.

**CC (Canton Coin).** The leader in private, compliance-aligned blockchain infrastructure for institutions. Retail rarely talks about it because it isn't built for retail, and Wall Street is adopting it anyway.

**AAVE (Aave).** The largest DeFi protocol there has ever been. A survivor that keeps adapting; measured by its deposits and loans, it would rank among the larger banks in the United States.

**XMR (Monero).** After Bitcoin, the coin most aligned with the original ethos of the industry, and still doing what blockchains were first imagined for: private peer-to-peer transactions.

**ENA (Ethena).** Synthetic dollars and crypto-native yield. I expected it to fail and it held up through real stress instead, and it is connected to several other assets in this basket.

**BTC (Bitcoin).** Included only in the "with BTC" version. It is the benchmark for everything else.

## Official versions

| Version | Assets | Weighting | Rebalancing |
|---|---|---|---|
| Amsig Basket (ex-BTC) | the 10 assets above, without BTC | equal, 10% each at launch | none, buy and hold |
| Amsig Basket + BTC | all 11 | equal, about 9.1% each at launch | none, buy and hold |

Both are compared against BTC alone, and also shown next to ETH alone.

Buy and hold means the weights are set once and then drift with prices, so winners grow into a bigger share of the basket. Nothing is trimmed or topped up.

## Lab versions

The lab versions use the same assets with different weighting rules (monthly rebalancing, capped market-cap weights, conviction weights). They exist to learn how much the weighting choice matters. They are exploratory, they are always labelled as such, and none of them replaces the official versions after the fact. Picking whichever lab version did best and promoting it would defeat the point of the record.

## Data

Prices are daily USD snapshots from CoinGecko at 00:00 UTC. The index starts at 100. If an asset is missing a price for a day, the last known price is carried forward and the gap is reported.

## Backtest and live record

Everything before the publication date is a backtest. The assets were chosen in October 2026, knowing how the year had gone so far, so that part of the chart is hypothetical and is shown as such. Everything from the publication date onward is the live record, and that is the part that counts.

If any asset has no price history back to January 1, 2026, the backtest for that version starts on the first day every asset has a price, and this is stated on the chart.

## Changes

The price history is never edited. Every change to the basket is logged below with a date and a one-line reason.

An asset is removed if any of these happen: it loses its price source for seven consecutive days, the protocol behind it suffers an exploit or insolvency that breaks its core product, or the reason it was included no longer holds. The last one is a judgment call, so it is logged with the reasoning. A removed asset is sold at its last available price and the proceeds are held as cash at 0% until the next review. They are not moved into whatever has been performing well.

New assets are only considered at scheduled reviews in January and July, and every addition is logged with its reason.

## Change log

| Date | Change | Reason |
|---|---|---|
| 2026-10-01 | Basket selected | Initial selection |
