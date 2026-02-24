# SURGE Integration Reference

## What is SURGE?

SURGE is a multi-chain Internet Capital Markets (ICM) launchpad built across BNB Chain, Base, and Solana. It connects startups and investors through tokenized startup financing with automated bonding curves.

**Key concepts:**
- **Bonding Curves** — Automated pricing for token secondary markets from day one
- **Multi-chain** — Supports Base, Solana, BNB Chain
- **Due Diligence Tracks** — Direct launch (proven teams) or acceleration track (early-stage)
- **Graduation** — Tokens can graduate to DEXes like PancakeSwap, Uniswap

## Token Launch Parameters

When preparing a launch via SURGE:

| Parameter | Description | Example |
|-----------|-------------|---------|
| name | Token name | "ProjectAlpha Token" |
| symbol | Token ticker (2-10 chars) | "PALPHA" |
| totalSupply | Total token supply | "1000000" |
| bondingCurve | Curve type | "linear", "exponential", "sigmoid" |
| initialPriceUsd | Starting price in USD | "0.001" |
| chain | Target blockchain | "base", "solana", "bnb" |
| description | Token/project description | "AI-powered..." |

## Bonding Curve Types

- **Linear** — Price increases proportionally with supply sold. Best for stable, predictable growth.
- **Exponential** — Price accelerates as supply decreases. Best for high-demand, viral projects.
- **Sigmoid** — S-curve pricing: slow start, rapid middle, plateau. Best for balanced launches.

## SURGE API Endpoints

Base URL: `https://api.surge.xyz`

- `POST /v1/tokens/launch` — Deploy a new token
- `GET /v1/tokens/{id}/status` — Check token status
- `GET /v1/tokens` — List all tokens
- `GET /v1/tokens/{id}/price` — Current price info

## Alternative: OpenClaw Skills

If the SURGE API is unavailable, use these OpenClaw skills:
- **Clanker skill** — Deploy ERC20 tokens on Base via Clanker SDK
- **BankrBot skills** — Token swaps, liquidity, yield farming
- **CryptoWallet skill** — Manage wallets on EVM + Solana
