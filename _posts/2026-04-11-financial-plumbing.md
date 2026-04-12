---
title:  "Financial Plumbing"
category: finance
---

Financial plumbing refers to everything that happens after a trade: clearing, settlement, payment, and bookkeeping. These systems make sure that payments and financial assets trade hands atomically.

Exchanges like NASDAQ and NYSE get all the attention, because that's where the fast paced, modernized, high-frequency trading ridden price discovery action happens.

But the behind the scenes "plumbing" is just as important, and is also getting its fair share of modernization, with [T+1 settlement](https://www.dtcc.com/ust1/faqs), stablecoins, tokenization, CBDCs, etc.

![image](/assets/financial-plumbing/trading-clearing-settlement-payment.png)

Although this financial plumbing has existed for decades, the 2008 Global Financial Crisis has brought international eyes on it and realized that there was a need for standardization and international regulation.

The Bank for International Settlement (BIS) released in 2012 a 188 page document titled [Principles for Financial Market Infrastructures (PFMI)](https://www.bis.org/cpmi/publ/d101a.pdf) where it standardized the term "plumbing" as "Financial Market Infrastructure" which is now used globally by regulators and central banks. FMIs are the systems and institutions that facilitate the clearing, settlement, and recording of financial transactions. 

The five main types are:
- Payment Systems (PS) move cash
- Security Settlement Systems (SSS) move securities against cash (technical term is Delivery-versus-Payment, or DvP)
- Central Securities Depositories (CSD) record who owns the securities (always same entity as SSS in US, but different in Europe)
- Central CounterParties (CCP) stand in the middle to manage counterparty risk
- Trade Repositories (TR) give regulators a window into what's been traded

The US implementation of the PFMI framework is done by the Dodd-Frank Act (Title VIII, 2010), which uses the legal-term Financial Market Utility (FMU) instead.

![image](/assets/financial-plumbing/pfmi-5-categories.png)

CB-operated means under direct control of the Fed (Central Bank), and those include Fedwire Funds/Securities and the NSS.

Additionally, the Financial Stability Oversight Council (FSOC) can designate certain privately-owned FMUs (DFMUs) as "systemically important" (aka SIFMUs), which subjects them to heightened supervision by their primary regulator (either the Fed, SEC, or CFTC). There are currently 8 SIFMUs.

| #   | Entity                                    | PFMI Category  | Primary Regulator | Parent                               |
| --- | ----------------------------------------- | -------------- | ----------------- | ------------------------------------ |
| 1   | CHIPS (The Clearing House Payments Co.)   | Payment System | Fed               | The Clearing House (bank consortium) |
| 2   | CLS Bank International                    | Payment System | Fed               | CLS Group (bank cooperative)         |
| 3   | CME Clearing                              | CCP            | CFTC              | CME Group                            |
| 4   | ICE Clear Credit                          | CCP            | CFTC              | ICE                                  |
| 5   | OCC (Options Clearing Corporation)        | CCP            | SEC               | Exchange-owned                       |
| 6   | NSCC (National Securities Clearing Corp.) | CCP            | SEC               | DTCC                                 |
| 7   | FICC (Fixed Income Clearing Corp.)        | CCP            | SEC               | DTCC                                 |
| 8   | DTC (Depository Trust Company)            | CSD / SSS      | SEC               | DTCC                                 |


## 1. Payment Systems (PS)

Infrastructure, along with procedures and rules for the transfer of funds between participants. In other words, the pipes (or "rails") for moving money between institutions. They execute the transfer of funds, not just record it.

The system is built hierarchically, and there are 4 systems directly plugged into the Fed:
- Fedwire optimizes for certainty at any cost. One at a time, real-time, gross. Expensive in liquidity.
- NSS optimizes for private-sector efficiency. "You do the netting, we'll just post the result." Cheap, but end-of-day only, and only available to approved clearing arrangements.
- FedACH optimizes for mass-market cost. The Fed does the item processing and netting. Fractions of a penny per payment. But you wait hours or days.
- FedNow optimizes for instant + cheap. Same real-time ledger operation as Fedwire, but sized and priced for everyday payments. 24/7/365. The newest and smallest door, still ramping up.

All four ultimately do the same thing: change numbers in the master account ledger at the Fed. They just differ in how much processing the Fed does (none for NSS, per-item for FedACH), how fast (instant for Fedwire/FedNow, batch for FedACH/NSS), and who they're designed to serve (wholesale for Fedwire/NSS, retail for FedACH/FedNow).

![image](/assets/financial-plumbing/payment-rails-tree.png)

Here's another visualization of the same systems.

![image](/assets/financial-plumbing/payment-rails-2d.png)

### Top-left: Fedwire (large + instant)

Who uses it: Banks settling with each other, the Treasury, and large corporates making time-critical payments. Also heavily used by Layer 2 systems that need real-time finality for their own settlement mechanics — CHIPS sends its end-of-day residual via Fedwire, CLS settles its USD leg via Fedwire, RTP replenishes its prefunded joint account via Fedwire. These L2 systems choose Fedwire because they need instant, gross, irrevocable movement of large sums — not because Fedwire is architecturally above the other L1 systems. CHIPS could theoretically submit a net file through NSS instead; it would just be slower.

Why it exists: When you need absolute certainty that \\$500M moved right now, with finality, in central bank money. Each transaction is a single atomic operation: debit one bank's master account, credit another's, done. No netting, no batching, no waiting. The average transaction is ~\\$5.4M — this is not for paying your electric bill.

Think of it as: The express lane. One item at a time, instant, no compression. Expensive in liquidity terms (you need reserves sitting at the Fed to fund each payment) but the fastest and most certain path to the ledger.

### Top-right: NSS (large + batch)

Who uses it: Not end users or even banks directly — NSS is used by other clearing systems. Its 13 active arrangements include EPN (private ACH, ~62% of all US ACH traffic), check clearinghouses (SVPCO), and — outside the payments world — DTC/NSCC (equities) and OCC (options). These systems accumulate thousands or millions of transactions throughout the day, net them down internally, and submit a single pre-calculated file to NSS. The Fed posts the debits and credits to master accounts without knowing or caring what the underlying transactions were.

Why it exists: Efficiency. The systems that use NSS have already done all the hard work — matching, validating, netting. They don't need the Fed to process individual items (that's FedACH's job) or settle in real time (that's Fedwire's job). They just need the Fed to post a set of pre-netted positions to master accounts, ideally all at once so nobody is exposed to partial settlement. NSS does exactly that. EPN processes \\$230B/day in gross ACH, but after netting, the positions it submits to NSS are far smaller. DTC processes \\$2.5 quadrillion/year, compressed to ~\\$100B/day in net settlement through NSS.

### Bottom-right: FedACH (small + batch)
Who uses it: Almost everyone in America, whether they know it or not. Your paycheck direct deposit, your rent autopay, your Netflix subscription debit, B2B vendor payments, tax refunds, Social Security benefits — all ACH. Unlike NSS, FedACH receives and processes the individual payment instructions. It reads every item, routes it to the receiving bank, calculates the net positions itself, and posts them to master accounts.

Why it exists: Scale and cost. ACH transactions cost fractions of a penny per item because the Fed batches them — it collects files from thousands of banks, processes them at scheduled windows throughout the day, and settles the net positions. FedACH handles ~38% of US ACH volume; the other ~62% is processed by EPN (a private ACH operator run by The Clearing House) which then settles its nets through NSS. Both operate under Nacha rules. Together they moved \\$93 trillion in 2025 across 35.2 billion payments.

Think of it as: The postal service of money. Not fast, but reliable, cheap, and it reaches every bank account in America. It's also the only L1 system that actually processes the individual payment items — the other three either settle gross (Fedwire, FedNow) or just post pre-netted totals (NSS).

### Bottom-left: FedNow (small + instant)

Who uses it: Banks offering instant payment products to consumers and small businesses. The person splitting a dinner bill, the gig worker who needs earnings now, the small business paying a supplier at 11pm on a Saturday. Like Fedwire, each FedNow payment is a single atomic debit/credit to master accounts in real time. Unlike Fedwire, it's designed for small values (limit \\$10M, but typical transactions are far smaller), operates 24/7/365, and is priced for retail use.

Why it exists: Because the other three doors left a gap. Fedwire is instant but expensive, wholesale-only, and closed on weekends. FedACH is cheap but takes 1-3 days. NSS doesn't face end users at all. There was no Fed-operated system for cheap, instant, small-value payments until FedNow launched in July 2023. TCH's RTP filled this gap privately starting in 2017, but only reached banks that chose to join. FedNow leverages the Fed's existing relationship with all 10,000+ depository institutions — any bank with a master account can participate.

Think of it as: The text message of money. Same underlying operation as Fedwire (debit one master account, credit another, instantly), but built on a different, newer tech stack optimized for high-volume, low-value, always-on consumer payments. It's the newest door into the oldest room.


## 2. Central Securities Depositories (CSDs)

Providers of securities accounts, central safekeeping services and asset services. They hold the definitive record of who owns what securities (custody + registry).

| Entity                             | Operator/Owner        | Primary Regulator | Notes                                                                                                                                                   |
| ---------------------------------- | --------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DTC** (Depository Trust Company) | DTCC (industry-owned) | **SEC**           | Holds virtually all US equities and corporate/municipal bonds in book-entry form. Registered owner of most US securities is Cede & Co. (DTC's nominee). |
| **Fedwire Securities Service**     | Federal Reserve Banks | Fed               | CSD and DVP settlement for US Treasuries, agency MBS, and other government securities. The Fed's own securities depository.                             |

Note that there are only 2 CSDs in the US: Fedwire Securities for government securities and DTC for basically everything else. The entire fixed income universe — corporates, munis, money market, ABS — lives at DTC alongside equities.

## 3. Securities Settlement Systems (SSS)

Systems that enable the transfer and settlement of securities by book entry.

These handle the actual delivery-versus-payment (DvP) — making sure the securities move and the cash moves at the same time. Computer scientists can think of SSS as performing a 2-phase commit (2PC) on the cash and securities ledger to make sure they settle atomically, even though in practice it's more so done via a SAGA-like mechanism. This is the part that eliminates principal risk.

In the U.S., DTCC acts as both CSD and SSS, so the distinction feels academic. In Europe, they are actually separate because European countries are more politically and legally sovereign than US states, and each want to manage their own property rights.

[T2S](https://en.wikipedia.org/wiki/TARGET2-Securities) is a centralized settlement platform operated by the European Central Bank (ECB) that settles securities transactions for 20+ national CSDs across Europe. The CSDs (Euroclear France, Clearstream Frankfurt, Monte Titoli, etc.) maintain the ownership records, but when a trade actually settles, T2S handles the DVP mechanics — debiting/crediting securities accounts at the relevant CSD while simultaneously moving the cash leg through dedicated cash accounts (DCAs) linked to the TARGET/T2 payment system. This is architecturally analogous to if the Fed built a single settlement engine that DTC had to use, while DTC continued to maintain the ownership ledger.


## 4. Central Counterparties (CCPs)

Entities that interpose themselves between counterparties, becoming buyer to every seller and seller to every buyer.

They interpose themselves between buyer and seller (novation), net down exposures, and mutualize default risk through margin and default funds. They're the reason a bilateral web of counterparty risk becomes a hub-and-spoke model.

| Entity                                              | Operator / Owner                          | SIFMU?          | Primary Regulator | Notes                                                                                                                                                                               |
| --------------------------------------------------- | ----------------------------------------- | --------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **NSCC** (National Securities Clearing Corporation) | DTCC                                      | **Yes — SIFMU** | **SEC**           | Clears virtually all US equities and corporate bond trades. CCP and netting for ~\\$2.3T daily.                                                                                     |
| **FICC** (Fixed Income Clearing Corporation)        | DTCC                                      | **Yes — SIFMU** | **SEC**           | Clears US government securities (Treasuries) and mortgage-backed securities via two divisions: Government Securities Division (GSD) and Mortgage-Backed Securities Division (MBSD). |
| **OCC** (Options Clearing Corporation)              | Exchange-owned (Cboe, NYSE, Nasdaq, etc.) | **Yes — SIFMU** | **SEC**           | Sole CCP for US exchange-listed options. Also clears futures on some exchanges.                                                                                                     |
| **CME Clearing**                                    | CME Group                                 | **Yes — SIFMU** | **CFTC**          | Clears futures and OTC derivatives on CME, CBOT, NYMEX, COMEX. Largest derivatives clearinghouse globally.                                                                          |
| **ICE Clear Credit**                                | Intercontinental Exchange (ICE)           | **Yes — SIFMU** | **CFTC**          | Clears credit default swaps (CDS). Designated post-crisis to bring OTC derivatives into central clearing per G20 mandate.                                                           |
| LCH.Clearnet LLC (US)                               | London Stock Exchange Group (LSEG)        | No              | SEC/CFTC          | Clears interest rate swaps and other OTC derivatives in the US.                                                                                                                     |

**CCPs are the largest SIFMU category** (5 of 8). This reflects the post-2008 regulatory priority: after Lehman's collapse, the G20 mandated central clearing of OTC derivatives, making CCPs the critical chokepoints of systemic risk. If a CCP fails, every major bank is exposed simultaneously.

![image](/assets/financial-plumbing/ccps-tree.png)


## 5. Trade Repositories (TRs)

Entities that maintain centralised electronic records of transaction data.

These were a post-crisis creation. The opacity of the OTC derivatives market was a major lesson of 2008: nobody knew who owed what to whom. TRs exist so regulators can see aggregate exposures across the system. They don't move money or securities — they're purely a transparency and surveillance tool.

| Entity                     | Operator/Owner | Primary Regulator              | Notes                                                                                                                  |
| -------------------------- | -------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| DTCC Data Repository (DDR) | DTCC           | CFTC (as Swap Data Repository) | Records OTC derivatives transaction data per Dodd-Frank reporting mandate. Not SIFMU-designated despite critical role. |
| ICE Trade Vault            | ICE            | CFTC                           | Swap data repository for credit and interest rate derivatives.                                                         |
| CME Repository Services    | CME Group      | CFTC                           | Swap data reporting.                                                                                                   |
| Bloomberg SDR              | Bloomberg      | CFTC                           | Swap data repository.                                                                                                  |

Note: No US trade repository has been designated as a SIFMU. They record data but don't clear or settle, so don't really create systemic risk like CCPs or payment systems.

## Financial Asset Classes

Here is a breakdown of the typically used PFMIs for different asset classes.

| Asset class                   | PS (cash leg)                           | CSD / SSS (ownership + transfer) | CCP (netting / novation) | TR (trade record)             |
| ----------------------------- | --------------------------------------- | -------------------------------- | ------------------------ | ----------------------------- |
| **US Treasuries**             | Fedwire Funds                           | Fedwire Securities (Fed)         | FICC / GSD (DTCC)        | DTCC / TRACE                  |
| **Agency MBS**                | Fedwire Funds                           | Fedwire Securities (Fed)         | FICC / MBSD (DTCC)       | DTCC / TRACE                  |
| **US equities**               | NSS (EOD net) + Fedwire (intraday SPPs) | DTC (DTCC)                       | NSCC (DTCC)              | DTCC / TIW                    |
| **Corporate bonds**           | NSS + Fedwire                           | DTC (DTCC)                       | NSCC (DTCC)              | DTCC / TRACE                  |
| **Municipal bonds**           | NSS + Fedwire                           | DTC (DTCC)                       | NSCC (DTCC)              | MSRB / EMMA                   |
| **Money market**              | NSS + Fedwire                           | DTC (DTCC)                       | NSCC (DTCC)              | DTCC                          |
| **Non-agency ABS/MBS**        | NSS + Fedwire                           | DTC (DTCC)                       | Varies                   | DTCC                          |
| **Exchange-listed options**   | NSS (via OCC)                           | —                                | OCC                      | OCC register                  |
| **Futures**                   | Fedwire (daily margin)                  | —                                | CME Clearing / ICE Clear | CME / ICE + CFTC reporting    |
| **OTC interest rate swaps**   | Fedwire (margin)                        | —                                | LCH / CME                | DTCC GTR / SDR                |
| **Credit default swaps**      | Fedwire (margin)                        | —                                | ICE Clear Credit         | DTCC TIW                      |
| **Bilateral OTC** (uncleared) | Varies (Fedwire or correspondent)       | —                                | —                        | DTCC GTR (mandated post-2008) |


Note that the functions that are split across CSD + SSS + CCP for securities are collapsed into the CCP alone for derivatives. The main distinction is between assets (securities) and contracts (derivatives).

**Securities** (equities, bonds, Treasuries) are things that exist independently. A share of Apple exists whether or not anyone is currently trading it. Someone needs to maintain the definitive record of who owns it — that's the CSD. Someone needs to transfer it when ownership changes — that's the SSS. These are permanent records of real property.

**Derivatives** (futures, options, swaps, CDS) are contracts between parties. A futures contract doesn't exist in a vault somewhere — it comes into existence when two parties agree to it, and it ceases to exist when it expires, is exercised, or is closed out. There's nothing to "deposit" in a depository. The CCP that novates the trade and stands between the parties naturally becomes the record keeper of open positions. CME Clearing's books ARE the registry of who has what futures position. There's no need for a separate CSD because the contract only exists as an entry in the CCP's system.

What about uncleared bilateral derivatives? These are the instruments that caused the 2008 crisis. There's no CCP, so there's no central position register. [Trade repositories](#5-Trade-Repositories-TRs) were mandated post-crisis to at least record these trades. Before 2008, even that didn't exist — nobody knew how much CDS exposure was out there until it was too late.

## What makes a SIFMU significantly important?

Looking back at the list of SIFMUs, we see that the only non-Fed CSD/SSS, the DTC, is a SIFMU. Furthermore, almost all CCPs are SIFMUs. And the largest PSs (CHIPS and CLS) that settle trillions per day are SIFMUs. However, ACH operators like EPN, retail payment rails, exchanges, and trade repositories (TRs) are all excluded. Why?

The designation logic for being considered significantly important is roughly:
1. US private-sector entities
2. that concentrate financial risk, either:
    - credit (CCPs)
    - liquidity (large PSs)
    - or settlement (CSDs/SSSs)
3.  at a scale where failure would cascade through the US financial system
4.  AND where no ready substitute exists

Exchanges fail this test because they're substitutable (trades can route elsewhere) and don't hold risk (the CCP downstream does). Retail payment systems fail because they're either Fed-operated or substitutable. Trade repositories fail because they don't bear risk at all. LCH Ltd CCP is systemic globally, but it falls outside US jurisdiction.

The two interesting edge cases are EPN and card networks.

### Why EPN isn't a SIFMU

EPN handles 62% of US ACH volume, which sounds systemically important. But:

Substitutability: EPN interoperates seamlessly with FedACH. If EPN went down tomorrow, that traffic could theoretically flow through FedACH. It would be a massive operational strain, but the system wouldn't seize. Compare that to CHIPS: if CHIPS went down, \\$1.8T/day in wire transfers would flood into Fedwire, potentially overwhelming it. There's no "FedCHIPS" backup.

No risk concentration: EPN doesn't hold funds, doesn't become counterparty, doesn't take credit or liquidity positions. It processes ACH items and submits net files to NSS. The risk is operational, not financial. EPN's value isn't in bearing risk — it's in competitive pressure on the Fed. Before the Monetary Control Act of 1980, the Fed had a monopoly on ACH processing. Congress mandated that the Fed price its services to compete with private alternatives. EPN (and its predecessor) exists because The Clearing House saw an opportunity to offer banks faster processing, better features, and competitive pricing for ACH. The 62/38 split in EPN's favor suggests they've been winning that competition.

And finally, The Clearing House is already designated as a SIFMU for CHIPS. Since TCH operates both CHIPS and EPN under common infrastructure and governance, the Fed's continuous supervision of TCH for CHIPS purposes effectively covers EPN too. TCH itself noted that its Title VIII supervision "benefits all TCH services."

### Why card networks aren't SIFMUs

Cards do 3 things: real-time authorization, multilateral netting/clearing, and orchestrating settlement. They are immensely important for retail purchases, but they arguably don't concentrate financial risk:

Substitutability: If Visa went down, merchants can still accept Mastercard, Amex, debit, cash, ACH. There's no single card network whose failure would freeze retail commerce. Compare this to CHIPS (no equivalent backup for international USD wires) or CLS (no alternative PvP FX settlement system).

No settlement finality exposure: Card networks don't hold positions or funds (the issuing bank is the one extending the credit). They authorize and net, then hand off to ACH for actual settlement. If Visa's netting engine failed, the worst case is that a day's worth of card transactions would need to be re-routed or delayed — painful, but it doesn't create liquidity holes in the banking system. When a CCP fails, counterparties suddenly have unhedged exposures worth billions.

Short settlement cycle + small individual transactions: Card settlements are T+1/T+2 with small average tickets. The maximum unsettled exposure at any moment is manageable. Compare this to a CCP sitting on trillions in open derivatives positions.

Lobbying. This [2011 comment letter](https://www.federalreserve.gov/SECRS/2011/April/20110419/R-1412/R-1412_041711_69442_354673619135_1.pdf) is part of a broader effort by card networks and their trade groups to argue they shouldn't be classified as FMUs at all under Dodd-Frank. Visa and Mastercard pushed hard that they're "payment networks" not "financial market utilities," and that SIFMU designation would impose costs and regulatory burdens designed for entities with fundamentally different risk profiles. They largely won that argument.

### Operational vs Financial Risk

The important thing to notice is that EPN and card networks bear operational risk, but arguably not financial risk. This is similar to the argument made for exchanges.

|                                           | Doesn't bear financial risk                           | Bears financial risk                                                                     |
| ----------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Moves money (payments)**                | EPN, card networks, SWIFT (routing/netting/messaging) | Fedwire, FedACH, CHIPS, NSS, FedNow (settlement finality — the Fed bears sovereign risk) |
| **Moves securities / manages trade risk** | Exchanges (price discovery, matching)                 | CCPs (novation, margining, default management), CSDs (custody, DVP)                      |

There's also a useful spectrum relating these in terms of **depth of involvement in the transaction:**

```
SWIFT          → Card networks       → CHIPS/ACH        → CCPs
"here's a        "authorized,          "money moved,       "I'm now legally
message"          netted, here's        final and            your counterparty,
                  the settlement        irrevocable"         I guarantee
                  file"                                      completion"
```

SWIFT washes its hands after delivering the message. Card networks commit to routing and netting but not to the outcome. Payment systems commit to moving real money with finality. CCPs commit to guaranteeing the trade completes even if one party defaults.

## Questions to test your understanding

1. What's the difference between card networks and EPN?
2. Do card networks settle on CHIPS for international payments?
3. What's the difference between FedNow and CBDCs?
4. Where does SWIFT fit into the PFMI framework?
5. Why does CHIPS settle through Fedwire rather than NSS, even though it does netting like other NSS participants?

# References

- [Replumbing Our Financial System: Uneven Progress — Darrell Duffie](https://www.ijcb.org/sites/default/files/journal/v9supplement-1/ijcb-v9nsupplement-1-replumbing-our-financial-system-uneven-progress.pdf)
- [Overview of US Payment, Clearing, and Settlement Landscape — NY Fed](https://www.newyorkfed.org/medialibrary/media/banking/international/03.Overview-US-PCS-landscape-Merle.pdf)
- [Understanding the Role of Debt in the Financial System — Bengt Holmstrom](https://www.bis.org/publ/work479.pdf)
- [The US Financial System — Sabrina Howell, Daniel Rabetti (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4193569)