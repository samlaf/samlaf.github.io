---
title:  "US Payment Rails"
category: finance
---

We've already touched upon [US payment systems](https://samlaf.github.io/finance/financial-plumbing.html#1-payment-systems-ps) in the previous article on financial plumbing. In this article, we focus on these payment rails. We start with an exhaustive list. We will then build a taxonomy and look at various ways to classify them.

1. Central bank-operated (Fed runs these)
    - Fedwire Funds — RTGS, large-value, business hours only, irrevocable. Operates directly on Tier 1 reserves.
    - Fedwire Securities — RTGS for US government securities; the L1 ledger for Treasuries.
    - FedNow — instant, 24/7, push-only, $500K cap, settles in central bank money. Launched 2023.
    - FedACH — one of the two ACH operators (the other is private). Batch.
    - National Settlement Service (NSS) — the multilateral net settlement service that lets card networks, CHIPS, ACH, etc. settle their net positions on Fed books at end of cycle. Often invisible in rail discussions, but it's the rail the rails settle on.
    - Fed Check Services — yes, still exists; image-based since Check 21.
2. Private interbank (mostly TCH-operated)
    - CHIPS — large-value, netting-based, private. Owned by The Clearing House. Settles via Fedwire at end of day.
    - EPN (Electronic Payments Network) — the other ACH operator, run by TCH.
    - RTP — instant, 24/7, push-only, $10M cap. Launched 2017. Owned by TCH.
3. Card networks
    - Visa, Mastercard — the two open-loop scheme networks (both credit and debit modes).
    - American Express, Discover — closed-loop (issuer + acquirer + scheme are the same entity, more or less).
    - PIN debit networks — Star, Pulse, NYCE, Accel, Shazam, Jeanie. These ride on the back of debit cards but route around Visa/MC interchange via the Durbin Amendment's routing requirement.
    - Interlink (Visa's PIN debit), Maestro (Mastercard's, largely sunset in US).
    - Visa Direct, Mastercard Send — push-to-card (OCT) rails layered on top of the same card networks.
    - Visa B2B Connect — cross-border interbank rail Visa runs separately.
4. Cross-border / remittance
    - SWIFT — messaging, colloquially a "rail" for international wires. Settlement happens via correspondent nostros + Fedwire/CHIPS for USD legs.
    - Wise, Remitly, WorldRemit, Western Union, MoneyGram — remittance operators that pre-position liquidity in destination corridors (the prefunding-pool model).
    - CLS — PvP atomic settlement for major-currency FX. Banks-only, $7T+ daily.
    - Visa B2B Connect, Mastercard Cross-Border Services.
5. P2P and consumer wallet networks
    - Zelle — bank-consortium rail, owned by Early Warning Services. User-facing push; settles underneath via ACH or RTP.
    - Venmo — closed-loop intra-PayPal wallet; cash-out via ACH or Visa Direct.
    - Cash App — same shape, owned by Block.
    - PayPal — closed-loop wallet with bank/card funding and ACH/card cash-out.
    - Apple Cash — closed-loop, partner bank Green Dot; out via Visa Direct.
    - Google Pay (Send) — wallet-and-rail in some configurations, defunct as a P2P brand in the US.
6. Closed-loop merchant balances
    - Starbucks card (~$1.7B in stored value).
    - Amazon Pay / Amazon balance.
    - Gift cards generally — Visa gift, Mastercard gift, retailer-specific.
    - Transit cards — MetroCard, Clipper, OMNY, SmarTrip, etc. Each is a tiny closed-loop rail.
7. Stablecoin / crypto rails
    - USDC (Circle), USDT (Tether), PYUSD (PayPal/Paxos), DAI (MakerDAO), RLUSD (Ripple) — Tier 3 issuer ledgers.
    - Underlying blockchains as transport — Ethereum, Solana, Tron (huge for USDT), Base, Arbitrum, Polygon, Avalanche. Each is technically its own L2 messaging+settlement layer in your framework.
    - Bitcoin Lightning — second-layer payments rail; small but real.
8. Specialized / niche
    - Direct Express — Treasury-issued prepaid card for federal benefits recipients without bank accounts. Comerica is the program manager.
    - TreasuryDirect — direct-from-Fed government securities (not really a payment rail, but the closest thing to a CBDC the US has).
    - Paper checks + Check 21 image clearing — still ~3-4 billion checks/year in the US, mostly B2B.
    - Money orders — USPS, Western Union, MoneyGram. Prepaid bearer instruments.

## Hierarchy of Money Classification

Not all money is equal. Ledgers naturally line up into a [3-tier pyramid](https://dirtroads.substack.com/p/4-a-taxonomy-of-stablecoins), called the hierarchy of money:
- Tier 1 operators: Fed (Fedwire Funds, Fedwire Securities, FedNow, FedACH, NSS). CBDCs would give retail access to this layer.
- Tier 2 operators: TCH (CHIPS, EPN, RTP), card networks, Zelle, banks, correspondent banking + SWIFT.
- Tier 3 operators: Venmo, Cash App, PayPal, Apple Cash, Starbucks, stablecoins, gift card programs, transit cards.

![](/assets/us-payment-rails/hierarchy-of-money-tiers.png)

It should go without saying that all models are wrong. Indeed, not all Tier 2 claims are equivalent: Eurodollars sitting in a London bank are not FDIC insured like those sitting in a Chase account in the US. Tier 3 stablecoins are currently built on top of commercial bank money, but this might change with Fed ["Skinny" Payment Accounts](https://bpi.com/wp-content/uploads/2025/12/Whats-the-Skinny-on-Federal-Reserve-Skinny-Master-Accounts-A-Primer.pdf) being allocated to Fintechs and [Crypto exchanges](https://bpi.com/bpi-statement-on-kraken-master-account/), effectively bypassing Tier 2.

## Messaging+Legal Classification

At a high-level, every payment system in the world reduces to:
- Layer 1: Ledger. Where the value lives, including:
    - What kind of balance is it (deposit, credit, prefunded)
    - What kind of ledger is it? Closed (Venmo), Partially open (open banking), fully open (blockchain)
    - What kind of operator controls that ledger (commercial bank, central bank, fintech, blockchain distributed validators)
- Layer 2: Messaging and clearing.
    - What kind of message gets sent and by whom: mandate management, recurring authorizations, RtP, CoP
    - Authorization and extra features: push-vs-pull, netting computation
    - How instructions get routed between ledger operators.
    - eg: SWIFT, UPI's switch, Visa's authorization network, NACHA's ACH switching
- Layer 3: Rules and enforceability. 
    - What gets enforced: settlement finality, return windows, dispute regimes, liability allocation
    - By whom: the legal authority of the operator, and the network of contractual relationships between participants. The existence (or not) of a bridging entity with two-sided leverage like credit card operators will be very important for customer protection
    - With what leverage: regulatory requirements, Reg E, UK APP reimbursement regime, etc.

![](/assets/us-payment-rails/ledger-messaging-rules.png)

Unlike the internet where the network(ing) is meant to be dumb and invisible, and the intelligence living at the ends; in payment systems, the messaging layer is the intelligence. The reason it is so consequential is that most of the interesting variation between payment systems lives here. Two systems can sit on the same ledger layer (same bank deposits, same Fed reserves underneath) and behave completely differently because their messaging layer is different. For example, Zelle vs credit cards.[^1]

In any case, we can use this perspective to further refine the 3 tiers of the Hierarchy of Money classification.

![](/assets/us-payment-rails/hierarchy-of-money-full.png)

## Use case classification

Payment competition has segmented by use case, and the segments have different equilibria. In particular, chargebacks are only relevant for C2B.

![](/assets/us-payment-rails/use-cases-classification.png)

- P2P: Banks (via Zelle, Pix, UPI, Bizum, Twint, etc.) are fighting Venmo, Cash App, and Wise for P2P money movement. Disputes mostly aren't relevant here because the dominant fraud vector (APP) isn't well-handled by either side, and most P2P doesn't involve fraud. The competition is on UX, network effects, and access to bank infrastructure.
- B2B: FPS rails (RTP, FedNow, SEPA Instant, CHIPS for large-value) are eating into the wire and ACH market. Disputes really aren't relevant — counterparties are professional, recourse is contractual, and instant settlement plus rich data is genuinely valuable. This is where FPS has the cleanest case.
- P2M domestic: Cards remain dominant in card-entrenched markets, FPS-at-POS dominant in card-thin markets. Chargebacks are the structural reason cards are sticky — when consumers have card alternatives, the dispute capability genuinely affects rail choice. When they don't, the merchant economics win.
- P2M cross-border: Cards have FX markup as a major weakness; this is where stablecoins and cross-border FPS like Project Nexus are making real inroads. Chargebacks matter less because the consumer protection expectation for cross-border was always lower.
- B2C disbursements (G2P, insurance payouts, marketplace payouts): Push rails (OCT, Visa Direct, FedNow, FPS) are eating ACH for speed. Disputes irrelevant — money is going to the consumer.

## Feature-based Classification

At an even more fine-grained level, it's useful to look at various features of payment rails that are important to different use cases:
- Funding source (ledger). deposit / credit / prefunded balance. It's a property of which ledger gets touched, and what the rules are on the accounts (overdraft? minimum balance requirements? etc)
- Authorization model (messaging): who initiates, with what credential, against what mandate. This captures push/pull plus richer cases like tokenized authorizations, standing orders, etc.
- Clearing/netting (messaging): Multilateral net at a switch (Visa, ACH, CHIPS) vs. gross (Fedwire, FPS) vs. bilateral (correspondent banking).
- Settlement path (inter-layer): path + time to (ultimate) settlement at the Fed
- Trust/Legal topology (rules): is there a bridging entity with leverage over both sides? Is there a chain of accountable counterparties between sender and receiver?

### Funding Source

A common mistake is to think that only the issuing bank can extend credit, which is naturally what credit cards do. But Zelle's receiving bank also fronts funds to the recipient before ACH settlement completes. That's literally "extending credit" — the receiving bank is taking a credit risk against the sending bank for the few hours or days until ACH settles. But Zelle is not reversible. The credit extension doesn't produce reversibility because there's no dispute protocol sitting on top of it.

#### Buy Now Pay Later (BNPL)

A further mistake is to think that only banks can extend credit.

Indeed, the BNPL category (Affirm/Klarna/Afterpay) is functionally a non-bank credit-line issuer — it extends credit to the consumer, settles immediately to the merchant via card rails, then collects from the consumer over four installments via ACH/card debits.

Note that credit card networks don't themselves extend credit! They rely on the partner banks to do so. BNPL are thus quite different! They are a non-bank-issued, transaction-specific credit line, often zero-interest, often with no credit pull, that sits as a wedge between the consumer's bank account and the merchant. They are a credit product layered on top of existing rails. It's a Tier 3 funding source that uses Tier 2 rails for both legs (merchant payout and consumer collection).

### Authorization: Push vs Pull Based

Push vs pull is really about who holds the credential/authority at the moment of transfer: sender holds it for push; receiver holds delegated authority for pull.

Richard Gendal Brown still has the best graphical explanation of [push vs pull based payment methods](https://gendal.me/2014/07/29/think-payment-cards-are-insecure-just-wait-until-push-payments-hit-primetime/).

In card-based pull payments, the card is presented and "tap-to-pay" is really just giving the merchant the card-holder's bank information. The authorization ultimately resides with the consumer's (issuing) bank, which the merchant must request authorization to "pull" funds from.

![](/assets/us-payment-rails/pull-based.png)

In push-based payments, the consumer scans a QR code that opens their bank application, and then needs to authorize the transaction themselves. Intelligence (and responsibility!) is at the consumer's phone, not at their bank account.

![](/assets/us-payment-rails/push-based.png)


Push-based (sender initiates, sends funds):
- Wires (Fedwire, CHIPS, SWIFT) — sender's bank initiates transfer to receiver
- Instant payment rails (FedNow, RTP, Pix, UPI) — sender initiates
- ACH credit — sender pushes funds (direct deposit is the canonical example: your employer pushes your salary to your account)
- Zelle — user-facing push, settles over ACH credits or RTP
- OCT (Visa Direct, Mastercard Send) — sender pushes to recipient's card
- Blockchain transfers — sender signs a transaction that broadcasts funds to the recipient's address
- Checks — arguably push (you write and hand over the check), though the deposit step is pull-like

Pull-based (receiver initiates, pulls funds with prior authorization):
- ACH debit — merchant/biller pulls funds from customer (utility autopay, mortgage autopay, gym membership)
- Card transactions (credit and debit) — merchant initiates the authorization request to pull from your card
- AFT (Account Funding Transaction) — the debit leg of a card-funded P2P transfer, pulls from sender's card
- Direct debits generally (UK's Direct Debit, SEPA DD in Europe) — biller-initiated pulls


#### Push-based with tap-to-pay experience

There are two big downsides to push-based payments compared to cards' tap-to-pay UX. One is simply friction, since one has to take out the phone, scan a QR code, authenticate with one's bank application, and finally verify and approve the payment. The other one is that this whole process requires an internet connection.

One thus naturally wonders whether it's possible to get the same tap-to-pay benefits with a push-based system. It turns out that there is a way to get the UX benefits, and it requires pre-loading a wallet. India's UPI Lite X works this way. There are limits to how much can be pre-loaded and spent to prevent fraud, but otherwise the feeling is very similar.

![](/assets/us-payment-rails/passport-based.png)


### Clearing/Netting

Clearing/netting/batching deserves its own article, but is one of the main features that distinguishes instant payments from non-instant payments. Gross settlement — Fedwire, RTP, FedNow — touches the underlying ledger on every individual transaction; each payment must be funded in full at the moment of sending. Net settlement — ACH, CHIPS, the card networks — batches transactions across a window, offsets them bilaterally and multilaterally at a switch, and only the net positions settle on the underlying ledger. CHIPS clears around $1.8T in daily gross volume against a fraction of that in net settlement at end of day; that liquidity multiplier is why net systems exist at all. Every card network is fundamentally a multilateral-netting clearinghouse with a settlement file dropped onto NSS at cycle close.

The trade-off is finality vs. liquidity. Gross gives immediate finality but forces banks to pre-fund every payment. Netting collapses the liquidity requirement but introduces a settlement window during which someone — usually the switch operator, sometimes a participating bank — absorbs counterparty risk. That window is also where the dispute regime lives: ACH returns work because settlement is delayed enough for the receiving bank to claw back unauthorized debits. Anything that does gross instant settlement forecloses on rail-level reversibility, which is one reason FedNow and RTP are push-only and irrevocable by design — the architectural choice and the legal posture come together.

Cost goes the other way too: per-transaction operator costs run roughly Fedwire ≫ FedNow/RTP ≫ ACH ≫ card-bundled-NSS, because netting amortizes a single Fed-level settlement across millions of underlying payments. ACH being a thousand times cheaper than Fedwire per item isn't a function of technology — it's a function of net settlement.

### Settlement Path

Every rail that isn't at the Fed is an overlay on top of other rails. Zelle is an overlay on RTP/ACH. Visa Direct is an overlay on Visa. PayPal cash-out is an overlay on ACH/Visa Direct. The user-visible rail is rarely the settling rail, and ultimately users shouldn't care how the payment system they are using settles. But when building a taxonomy, it is good to keep this in mind, as it is an important feature that influences cost and time.

### Trust/Legal Topology

Every payment system rests on a network of trusted third parties (TTPs), but what matters isn't their existence — it's the shape of the network: who has leverage over whom, where accountability lives, and whose future cash flows can be coerced if something goes wrong. This trust topology is what determines the real notion of finality (as opposed to the nominal one), and is largely what customer protection reduces to in practice.

Immediate final settlement is incompatible with rail-level reversal. If you want reversibility, you need some combination of:
1. A settlement delay (intentional or through fronting mechanics)
2. A bridge party absorbing risk during that delay
3. A binding dispute protocol that operates during the delay window
4. A business model that pays for the dispute infrastructure (interchange, float, premium, etc.)

Cards work by having long-term trust relationship with merchants, and being able to claw-back funds from their future cash flows to compensate for previous customer chargebacks. The network doesn't claw the original dollar back — it executes a new transaction in the opposite direction, and recovers it from the merchant's future settlement flow. The leverage is the merchant's continuing relationship with their acquirer. Critically, this survives the receiver having already spent the money. It only fails when the merchant has no future flows — folded, offshore, fraud-and-flee — which is exactly the chargeback-abuse scenario acquirers underwrite against.

Contrast with rails that miss one or more ingredients:
- Wires (Fedwire, RTP, FedNow): no settlement delay, no bridge party, no dispute protocol. Stolen wire? Effectively unrecoverable absent voluntary cooperation from the receiving bank.
- Zelle: instant from the consumer's view and irreversible at the rail level. The receiving bank fronts funds before ACH settles, but it has no leverage over its own customer comparable to an acquirer's leverage over a merchant, and no binding dispute protocol that survives the receiver having spent the money. This is exactly why APP fraud is Zelle's structural weakness: the rail can't reach into the recipient's pocket the way cards can.
- Crypto/stablecoin transfers: same shape as wires, plus often no legal counterparty to direct a claim against in the first place.

Reversibility, in other words, is not a feature you add to a rail; it's a credit-and-leverage topology you build on top of one.

## Conclusion

Payment systems can seem daunting from the outside but decompose cleanly when you separate ledger from messaging from rules. The ledger tier mostly settles what kind of money you're holding — Fed reserves, commercial bank deposits, fintech IOU. The messaging tier is where the interesting variation lives — push vs. pull, gross vs. net, the credentials and mandates that authorize transfers, the routes instructions take, the netting machinery. The rules tier is what makes those messages enforceable, and determines whether your money is reversible, who eats the loss, and what disputes look like. Two rails sitting on the same Tier 1 reserves can behave nothing alike — Zelle and credit cards both ultimately settle on Fed money, but only one of them gives the consumer recourse, because the messaging and rules stacked on top are different.

The use-case lens explains why the landscape is fragmented rather than consolidating. P2M demands chargebacks. B2B demands speed and rich data. P2P demands UX and network effects. Cross-border demands FX-efficient corridors. No single rail optimizes all four, and the regulatory regimes anchoring each (Reg E, contract law, AML) reinforce the boundaries between them. What's worth watching is where those boundaries are eroding: stablecoins and Project Nexus making real headway in cross-border, FPS-at-POS displacing cards in card-thin markets, fintechs and crypto exchanges getting Fed skinny accounts and bypassing the Tier 2 banking layer entirely. The next decade of US payments is a story about which rail boundaries dissolve and which get fortified by the incumbents sitting on either side.


# References

- https://www.federalreserve.gov/econres/notes/feds-notes/pay-by-bank-and-the-merchant-payments-use-case-benefits-20250707.html
- https://www.ftc.gov/system/files/ftc_gov/pdf/csn-annual-data-book-2024.pdf
- https://currencci.com/post/200915-rtp-part-i/
- https://www.mastercard.us/content/dam/public/mastercardcom/na/global-site/documents/chargebacks-made-simple-guide.pdf
- https://www.financialresearch.gov/working-papers/files/OFRwp-24-09_central-clearing-and-trade-cancellation.pdf
- https://fastpayments.worldbank.org/sites/default/files/2025-10/Prominent%20Overlay%20Services%20in%20Fast%20Payment%20Systems_Final%20%281%29.pdf
- https://www.youtube.com/playlist?list=PLJq-63ZRPdBvQnN9YQlpe5dKKg56MDpx4
- https://stripe.com/guides/payfacs

[^1]: We are focusing on payment systems in this article, but note that this breakdown also works for other financial systems. For example, for [securities](https://samlaf.github.io/finance/financial-plumbing.html), CSDs (central security deposits) are the Layer 1 and SSSs (securities settlement systems) are the Layer 2, and CCPs (central counterparties) play an important Layer 3 role by becoming the legal middleman party to any transaction (not unlike credit cards!).