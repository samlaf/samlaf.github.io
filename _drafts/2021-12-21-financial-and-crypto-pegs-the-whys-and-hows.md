---
title:  "Financial and Crypto Pegs: the Whys and Hows"
category: blockchain
---

Agustín Carstens, head of the Bank for International Settlements (BIS), said in a [2018 interview](https://www.bis.org/speeches/sp180704a.htm): "My message to young people: stop trying to create money." It remains unclear to me if he had specific projects in mind at the time, or whether he even understands the distinctions between BTC, ETH, USDC, DAI, COMP, UNI, and the rest of the DeFi tokens zoo. Nonetheless, one can quite easily guess why he was raising alarms after browsing [CoinGecko](https://www.coingecko.com/) for a short while:

<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/bitcoin-crash.jpg" style="width:50%">
<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/dsd-crash.png" style="width:49%">
<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/iron-titanium-crash.jpg" style="width:50%">
<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/squid-game-crash.jpg" style="width:49%">

It is now 2021, and the crypto regulations state of affair is getting more interesting by the day. SEC Chair Gary Gensler stated in October that the SEC [has no plans to ban crypto](https://www.coindesk.com/policy/2021/10/05/sec-chair-gensler-a-ban-on-crypto-would-be-up-to-congress/). Again very ambiguous word choices imbuing, which seems to be a favorite amongst regulators. One could further question his use of the generic word "crypto" given that the SEC is currently suing [Ripple](https://www.sec.gov/news/press-release/2020-338) and [Terra](https://www.coindesk.com/policy/2021/12/20/do-kwon-terra-claim-sec-violated-procedure-in-ongoing-legal-fight/), among others. So it is probably fair to infer that he meant "more established projects, such as Bitcoin and Ethereum." Bitcoin, for one, even after having been [deemed a commodity](https://www.cftc.gov/sites/default/files/2019-12/oceo_bitcoinbasics0218.pdf) falling under the CFTC's jurisdiction, still seems to have a [regulation problem](https://www.investopedia.com/news/bitcoin-has-regulation-problem/), so the SEC could potentially have wanted to further add restraints to the project. But their decision to let bitcoin free does align with previous results from the [Howey test](https://www.investopedia.com/terms/h/howey-test.asp), which the [Crypto Rating Council](https://www.cryptoratingcouncil.com/asset-ratings) uses to rate cryptoassets on a scale of 1 (token) to 5 (security), with bitcoin being ranked a 1. As to the rest of the DeFi jungle, the SEC put out a generic [statement](https://www.sec.gov/news/statement/crenshaw-defi-20211109) in early november, making clear their intention to continue overlooking the state of the space and be unforgiving if need arises.

They has thus for the moment passed the ball over to congress, who wasn't so lenient and started by [clamping](https://www.nytimes.com/2021/12/08/business/dealbook/crypto-congress.html) down [hard](https://www.coindesk.com/policy/2021/11/01/biden-administration-to-congress-put-stablecoins-under-federal-supervision-or-we-will/) on [stablecoins](https://home.treasury.gov/system/files/136/StableCoinReport_Nov1_508.pdf). Stablecoins, being the 1:1 pegged on-chain representations of the USD, are most likely the closest cryptoassets to what Carstens had in mind when he used the word ["money"](http://127.0.0.1:4000/blockchain/financial-and-crypto-pegs-the-whys-and-hows.html#:~:text=%E2%80%9CMy%20message%20to%20young%20people%3A%20stop%20trying%20to%20create%20money.%E2%80%9D). Furthermore, with current volumes going into them, he now has even more reasons to be worried compared to when he made his statement in 2018:

<center>
<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/top-stablecoins-by-market-cap.png" style="width:75%">
</center>

I must at this point confess that I am no lawyer, and nor am I here to make market predictions, so I will turn you over to [crypto-law](https://www.crypto-law.us/) for the latest regulatory news, and finally get to the crux of this post. My goal here is to first expose my views as to why stablecoins, being the only non-volatile cryptoassets, have been getting so much traction, and kickstart a series of articles exploring their financial and technical engineering and delving into the fascinating world of pegging mechanisms used both in the traditional finance world as well as in the crypto world.

## Money vs Credit

Decentralized Finance (DeFi) is inventing new ways to allocate risk and resources, but it's certainly not reinventing all of finance, so let's not forget these important roots and start by looking at the difference between money and credit, which is fundamental to explaining stablecoins' importance. Ray Dalio breaks down their difference better than I ever will, so I recommend investing the time to carefully study this [article](https://www.linkedin.com/pulse/money-credit-debt-ray-dalio/) of his, or at least watch his [summary video](https://www.youtube.com/watch?v=PHe0bXAIuk0). Otherwise, the main takeaway of importance to us is that banks (and other financial institutions), through fractional-reserve lending practices, "create money out of thin air"[^create-money-out-of-thin-air].

<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/stablecoins-money-credit-pyramid.jpg" style="width:50%">
<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/money-supply-historical-chart.png" style="width:49%">

At the coarsest level, one should think of money as physical currency (coins and banknotes) and of credit as the money that you hold in your bank account. Common parlance doesn't make a distinction between them, but that only speaks to the stability and security that our financial institutions are bringing to us. On more technical grounds, the money supply is generally broken down into different levels of "money". M0 (confusingly labelled "currency" in green on the graph on the right) only consists of the money that the Central Bank creates (coins, notes, as well as bank reserves on the central bank's ledger). Everything above this level, namely M1, M2, and M3, is **credit** created by banks. The precise distinction between these different bank accounts and deposit types is unimportant to us, so we can lump them all into M0 (money) vs M1-M3 (credit). What is important however is to notice the enormous magnitude difference between M0 and M3. Whatever amount of currency the central bank releases into the economy pales in comparison to the amount of credit created by our banking system!

Its important to rid yourself of any preconceptions or negative feelings towards this fractional-reserve practice, as is unfortunately too common on Main Street. The credit system, invented around 1350, certainly does have tendencies to overextend itself sometimes, but is claimed by Ray Dalio to be the most direct factor explaining our current levels of wealth and prosperity. In his recent [Bridgewater Bitcoin letter](https://www.bridgewater.com/research-and-insights/our-thoughts-on-bitcoin), he compares Bitcoin to the credit system, claiming both to be ingenious "types of alchemy".

But interestingly, bridging these two alchemic inventions actually requires inventing a third: stablecoins! Have you ever heard of people borrowing gold, other than for short selling? Neither have I. And I have similarly yet to hear of anyone borrowing bitcoin outside of bear markets. Companies like [Nexo](https://nexo.io/?v=t5) and [BlockFi](https://blockfi.com/) do offer the possibility, but their platform's main use remains on the contrary, people keeping their bitcoin and using them as collateral to borrow stablecoins, the same way that people use their gold or real estate collateral to borrow USD in traditional finance.

<center>
<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/stablecoins-crypto-credit-system.jpg" style="width:60%">
</center>

As previously mentioned, credit money (M1 and above) represents the largest quantity of circulating money, by far. This money is created through loans, which people borrow to invest in projects that they hope will appreciate and enable them to repay their debt, with interest, at a later date. If they borrowed bitcoin, which then went on to appreciate by 100%, their debt would have equally increased by that amount. This basic fact explains why people prefer to borrow a money that is stable. In traditional finance, this stable money is USD, or any other fiat money. The entire US credit system thus depends on the Fed's [promise to keep a 2% inflation rate per year](https://www.federalreserve.gov/faqs/economy_14400.htm). Very similarly, the DeFi credit system that platforms like Aave and Compound create very much depends on stablecoins like [USDT](https://www.coingecko.com/en/coins/tether), [USDC](https://www.coingecko.com/en/coins/usd-coin), and [DAI](https://www.coingecko.com/en/coins/dai).

We're leaving out a lot of details in this introductory post, but we now have a tentative answer as to what Augustin Carstens was scared of, and what he meant by *money*. Bitcoin, even 10 years after its creation, is still unusefully volatile, and nowhere close to reaching its initial goal of becoming a global medium-of-exchange. In fact, its volatility is so high that it still isn't even seen as a viable alternative to [digital gold](https://en.wikipedia.org/wiki/Digital_gold_currency) for large [institutional investors](https://www.bridgewater.com/research-and-insights/our-thoughts-on-bitcoin#:~:text=we%20do%20not%20see%20it%20as%20a%20viable%20storehold%20of%20wealth%20for%20large%20institutional%20investors). This explains why all the kids in town are trying to create their own stablecoins: they are the only true crypto-*currencies*, and are the key to unlocking a possibly massive crypto-credit system.

## The currency problem facing cryptoassets and emerging moneys

So where does volatility come from, both for bitcoin and other financial assets? Economics 101 has a simple answer: prices are determined by supply and demand. If we look at the simplest case, that of fixed supply (eg. bitcoin as of 2140[^btc-fixed-supply]), then a changing demand will directly reflect in a change of price.

<center>
<img id="fixed-supply-decreasing-demand-curve" src="/assets/financial-and-crypto-pegs-the-whys-and-hows/stablecoins-fixed-supply-increasing-demand.jpg" style="width:35%">
</center>

Demand increasing from `D` to `D'` will be reflected in prices appreciating from `P` to `P'`. And bitcoin, however great, cannot escape this basic fact, so its volatility can simply be explained by its demand not following its programmed [supply increase](https://en.bitcoinwiki.org/wiki/Bitcoin_Supply). But that is only to be expected for such an ambitious project facing regulatory, competitive, and technological risks. As new information hits the news, so follows its price, both upwards and downwards.

As we've explained in the previous section, this scares people away from borrowing bitcoin for spending purposes. And quite naturally, as volatile assets force their users to become [speculators](https://twitter.com/samlafer/status/1474262070170460162). But not everyone was born to [break the Bank of England](https://www.investopedia.com/ask/answers/08/george-soros-bank-of-england.asp); some people just want to use their money worry-free, buy an Xbox, and enjoy the holidays.

## How do stablecoins fix this problem?

Stablecoins manage to get rid of volatility, but how? Coming back to our [supply-demand](#fixed-supply-decreasing-demand-curve) curve, the answer seems simple: they just need to increase/decrease the supply to balance out the changing demand!

<center>
<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/stablecoins-increasing-supply-to-fix-price.jpg" style="width:35%">
</center>

This is the exact same process used by central and commercial banks to stabilize fiat money! However, DeFi being built on a blockchain emables new ways to distribute the newly minted coins, as opposed to them being shared between the Fed-Treasury-Banks triangle. What remains though is that these pegged currencies, even though theoretically "equivalent", in fact create a chain, with [risks](https://en.wikipedia.org/wiki/Currency_crisis) compounding along the way.

<center>
<img src="/assets/financial-and-crypto-pegs-the-whys-and-hows/stablecoins-peg-hierarchy.jpg">
</center>

<!-- TODO: 
1) Maybe use color coding to show full-reserve vs fractional-reserve vs... ?
2) Include more stablecoins (and maybe countries): turn this chain into a tree 
-->

Each of these different monies have their own peculiar way of maintaining their peg, and with this series of articles, we will be exploring all of these different mechanisms along with their associated risks. As a sneak peak, I have two equal favorites that I would encourage everyone to look into. The first one is the Fed, because of its inability, as can be seen from the diagram, of pegging itself off of another money, making its stabilising problem a control problem more involved than a traditional peg. The second one is rebasing stablecoins such as Ampleforth and Yam, who keep their price stable in a simplistic way which does not keep their purchasing power stable. This beautiful tradeoff between price volatility and quantity volatility is what first got me into all of this, and opened my eyes to the beautiful subject of stablecoins and pegging mechanisms.

Stay tuned for these upcoming posts:
- Traditional Finance
    - Cuban Pesos, Chinese Yuan, etc.
    - Fed and the federal funds rate
    - Fed and inflation / interest rates ?
    - ETFs
    - Synthetic position
    - inverse etf
- Cryptoassets
    - USDC, USDT, etc.
    - MakerDao
    - Basis
    - Terra
    - Etc.

## Footnotes

[^create-money-out-of-thin-air]: Staying true to this section's main point, this saying should actually say "create **credit** out of thin air".

[^btc-fixed-supply]: Actually, as noted earlier in this post, bitcoin's fixed supply is just a big illusion, as bitcoin banks such as Nexo and BlockFi will increase the supply through bitcoin credit, if people are wanting to borrow it.