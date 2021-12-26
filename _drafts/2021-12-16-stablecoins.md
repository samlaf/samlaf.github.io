---
title:  Stablecoin Monetary Policies
category: blockchain
---

Friedrich Hayek published [The Denationalization of Money](https://en.wikipedia.org/wiki/The_Denationalization_of_Money) in 1976, in which he argued that society would be better off were central banks to give up their monopoly on money and let the private sector create different kinds of money and in the process test a large number of different monetary policies. It is now 2022, and just might be starting to [live in such a world](https://www.coingecko.com/en). In 1978, two years after his initial book, Hayek published a revised version in which he speculated that his private money society would end up converging on a single or at most a few different money standards. Many of the crypto tokens that we see today don't pretend to be money and have their own utility outside of payments, such as eth being used to pay for gas to run code on the ethereum blockchain. This fact notwithstanding, their ease of access, combined with unique attributes and supply rules, often lead to people [promoting them as money](https://newsletter.banklesshq.com/p/eth-is-money).

Although delving into [ethereum's monetary policy](https://decrypt.co/38271/so-what-is-the-ethereum-eth-total-supply) is fascinating and enlightening in of itself, we will limit the scope of this article to stablecoins, taking the generally accepted stance that [price stability](https://en.wikipedia.org/wiki/Price_stability) is necessary for anything money-like to function as a medium of exchange. Stablecoins, just like the USD, use different mechanisms to reduce their volatility, with aim to get rid of the speculative behavior associated with bitcoin, ethereum, and only leave their currency behavior relevant. Interestingly enough, almost all stablecoins do so by pegging themselves to the USD, instead of defining their own [measure of inflation](https://en.wikipedia.org/wiki/Consumer_price_index#:~:text=The%20annual%20percentage%20change%20in%20a%20CPI%20is%20used%20as%20a%20measure%20of%20inflation.) through a basket of goods and fixing that.

There are three categories of stablecoins: off-chain collateralized, on-chain collateralized, and not collateralized (also called algorithmic stablecoins). We will analyse in details the different mechanisms used within these three families to peg the different stablecoins to the USD.

![](/assets/stablecoins/stablecoins-taxonomy.jpg)

## Money as a Balance Sheet Liability

We first start by taking a look at money in the traditional financial system.

![](/assets/stablecoins/stablecoins-balance-sheets.jpg)

## First things first!

Stablecoins are cryptocurrencies with an added economic structure that aims to stabilize their price and purchasing power. This is IMPOSSIBLE at the macro level, and ONLY possible at the individual level by having a set of people/entities/institutions take the volatility out, which they only do at a certain cost of course. This is why people crying that the Fed and Banks are [stealing from us](https://en.wikipedia.org/wiki/Criticism_of_the_Federal_Reserve#Republican_and_Tea_Party_criticism) are generally just ignorant of economic issues and risk tradeoffs.

If `Coin Demand = P * Q`, coin demand WILL change when new people start valuing the currency and want more of it. The only way to keep P (individual's purchasing power) is to increase Q. Rebasing everyone (helicopter) money is one such way, but it simply trades P volatility for Q volatility, and doesn't solve the problem. The other way is to have certain people eat up the new Q. These people can be arbitrageurs or shareholders, depending on the mechanics of the coin.

## Algorithmic stablecoins

### Rebasing (Amplefort)

What's wrong with rebasing currencies? They trade price volatility for quantity volatility, so their purchasing power is still volatile! If the currency is appreciating (demand is increasing), the holders will see their wallet increase with new coins. In this respect, it makes the currency also an investment medium, and make people want to hold on to it when speculating that its value will increase. (see Roberts Sam's note) Even Ferdinando Ametrano, creator of Hayek money, acknowledged that this was a problem and [updated his money](https://youtu.be/dvgb2YOm1y4?t=2923) to use seigniorage coins.

### Seigniorage Shares (Basis)

Basis is the simplest model of seigniorage shares, and is very similar to the Fed: contract the money supply by selling bonds (possibly at a discount) when price under peg/target, and expend the money supply by issuing basis tokens (first to repay bonds, then to shareholders) when price over peg/target. 

## Bibliography
- [A Note on Cryptocurrency Stabilisation: Seigniorage Shares](https://blog.bitmex.com/wp-content/uploads/2018/06/A-Note-on-Cryptocurrency-Stabilisation-Seigniorage-Shares.pdf)
- [Decentralized Finance: On Blockchain- and Smart Contract-Based Financial Markets](https://research.stlouisfed.org/publications/review/2021/02/05/decentralized-finance-on-blockchain-and-smart-contract-based-financial-markets)
_Note that rebase tokens such as Ampleforth or YAM do not qualify as stablecoins. They only provide a stable unit of account but still expose the holder to volatility in the form of a dynamic token quantity._