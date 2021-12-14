---
title:  Ethereum Core Dev Speed Run
category: blockchain
---


So you can't get enough of ethereum and want to learn all of its gory technical details? Perhaps you would even like to contribute to the project as a core dev? Now is the best time to join. Ethereum has already found product-market fit in DeFi and NFTs, and thus created tons of high-paying and very exciting [jobs](https://cryptocurrencyjobs.co/). Newcomers to the space who aspire to become blockchain developers and write smart contracts for a living have already been well served by Austin Griffith's very popular [Ethereum Dev Speed Run](https://medium.com/@austin_48503/%EF%B8%8Fethereum-dev-speed-run-bd72bcba6a4c) which is a must-study for anyone new to the solidity language and ethereum in general.

But for those who are more research minded, and prefer working on core infrastructure, whether it be consensus protocols, compilers, the ethereum virtual machine, etc., the barrier to entry remains quite a bit high. Developments are clearly happening, as exemplified by Vitalik's recent ethereum protocol development [roadmap](https://twitter.com/VitalikButerin/status/1466411377107558402), but looking at it with novice eyes leaves one wondering where it is still possible to make a contribution.

One might further look at Ethereum Improvement Proposals' (EIPs) diminishing publishing rate and fear that "ossification" is near, potentially largely reducing the demand for core devs.

<p>
    <img src="/assets/ethereum-core-dev-speed-run/eips_published_per_year.png">
    <center> Data scraped from <a href="https://eips.ethereum.org/all"> eips.ethereum.org </a> using this <a href="https://gist.github.com/samlaf/8965461492d37b48b11b5e3338ef9fed"> script</a></center>
</p>

Should one instead be better off joining some of the newer platforms like Avalanche, Solana and Polkadot? Not so fast... some people, myself included, believe that ossification is unlikely, and actually [not even beneficial](https://twitter.com/LukeDashjr/status/1382905887237550081?s=20). Furthermore, looking at the internet's Request for Comments publishing rate for comparison, we could instead conclude that the EIP publishing rate will calm down for a few years, giving you time to become comfortable with the ecosystem, before bouncing back!

<p>
    <img src="/assets/ethereum-core-dev-speed-run/rfcs_published_per_year.jpg">
    <center> 
        Data from <a href="https://www.rfc-editor.org/rfcs-per-year/"> rfc-editor.org</a>
    </center>
</p>

The Ethereum foundation seems to agree with this view, and have just started their very own [core developer apprenticeship program](https://blog.ethereum.org/2021/09/06/core-dev-apprenticeship-second-cohort/) to attract new talent. The program's first cohort ran over the summer, and the second cohort is currently under way. They even let people join the weekly meetings without being part of the program, so there's no excuse not to get started. You might even get a scholarship if you are serious about your project and can show progress! I myself just found out about the program, so I am writing this post to share the good news. The best way to get started is to join the [Eth R&D](https://discord.gg/gHwU3CpH) discord server, and either ask in the apprenticeship-program channel, or message Merriam Piper, who leads the project, directly.


## Ethereum Basics

This [github repo](https://github.com/ethereum-cdap/cohort-one) is the starting point for anyone joining the apprenticeship program. It includes a very terse [reading list](https://github.com/ethereum-cdap/cohort-one/blob/master/stage-0-getting-started.md) for apprentices to catch up to the current state of research, but let's be honest: no single individual without a reading group or friends to discuss is going to go through that list without sweating their eyeballs out and regret ever thinking they were smart enough to catch up to a roughly ten year old field moving at the speed of light. My goal with this post is thus to expand on the list of subjects with ELI5 explanations, hopefully helping some fellow programmers out. Please also feel free to email me or reach out to me (user @samlaf) on the Eth R&D discord server. So let's get started!

The first thing you will run into in the list is this conceptual overview diagram

<img id="monster-diagram" src="/assets/ethereum-core-dev-speed-run/ethereum-conceptual-diagram.svg">

and a link to the [yellow paper](https://ethereum.github.io/yellowpaper/paper.pdf)[^yellow-paper] for explanation of the Ethereum Virtual Machine (EVM). This already is enough to scare anyone away; there is only so much that one can learn by drinking from a firehose. I would instead recommend starting from the [Ethereum EVM illustrated](https://takenobu-hs.github.io/downloads/ethereum_evm_illustrated.pdf) guide, which is suggested as the "Visual guide to the yellow paper". This deck of slides is just amazing, and it is after reading it that I first understood why some people prefer to call blockchains "global computers"[^chain-of-state-or-blocks], or in the yellow paper's words, "transactional singleton machine with shared-state".

<!-- ![](/assets/ethereum-core-dev-speed-run/ethereum-chain-of-blocks.svg)
![](/assets/ethereum-core-dev-speed-run/ethereum-chain-of-states.svg) -->

After having digested the illustrated guide, the next natural progression would be to read the [Mastering Ethereum](https://github.com/ethereumbook/ethereumbook) book by Andreas M. Antonopoulos (author of the related Mastering Bitcoin book) and Gavin Wood (author of the yellow paper and one of ethereum's founders). More specifically, [chapter 13](https://github.com/ethereumbook/ethereumbook/blob/develop/13evm.asciidoc) describes the EVM starting from the below diagram, which although still complex looking, is at least readable without a microscope. But most importantly, the whole chapter is full of examples and practically interesting details. Anyone reading this book will quickly understand why Gavin Wood was the first to manage to implement the EVM fully. The guy is smart.

![](/assets/ethereum-core-dev-speed-run/evm-architecture-ethereum-book.png)

## Non-Fungible Tokens (NFTs)

NFTs are controversial, to say the least. Justin Sun payed over half a million dollars for a [rock](https://twitter.com/justinsuntron/status/1429346110405890048?lang=ca). I'm personally not a big fan, but since they are part of the apprenticeship list, let's at least devote a small section to their architecture. Let's take a random CryptoKitty from [opensea.io](https://opensea.io/assets/0x06012c8cf97bead5deae237070f9587f8e7a266d/229795). Right clicking on the image brings you to... [google photos](https://lh3.googleusercontent.com/sdy97_Rs91B8taHT3DbvR7ub1aGeoTzfJ_OdK91Bn-PiQdjJArRGE1baA40RIimwaz0thLCz1reUvvlp6rJSyu6l=w600)! So what exactly are people buying when they buy NFTs? NFTs is still a wild west market, without standardizations, so each project is structured differently; but the general structure very often looks like:

<center>
<img src="/assets/ethereum-core-dev-speed-run/NFT.drawio.svg">
</center>

The rationale for this choice is that on-chain storage is more expensive (by a lot) than [IPFS](https://ipfs.io/) storage, which is more expensive than the centralized google photos and amazon s3. Hopefully once NFT architectures become more standard, the images themselves will be hosted on decentralized platforms such as IPFS or [swarm](https://www.ethswarm.org/). [NFT Storage](https://nft.storage/) is one solution that I am aware of, but there are probably many more.

## Data Structures

If you start reading anything related to ethereum's infrastructure, you will inevitable come across Recursive Length Prefix (RLP) and Patricia-Merkle Tries (PMTs). If you look back at the [monster diagram](#monster-diagram) above, you will notice in the bottom gray square, a State Trie, a Transaction Trie, and a Receipts Trie. These tries are the state database of ethereum. Blockchain blocks are very small. They only contain simple integers, such as the gasLimit and timestamp. Otherwise it stores hashes, which index into these Patricia-Merkle Tries. The Patricia part refers to the radix trie used to locate a value in the trie. The Merkle part refers to the merkle hash tree which is stored alongside the keys and values in the trie, to enable short proofs that certain elements are included in these tries. This in turn enables [light ethereum clients](https://ethereum.org/en/developers/docs/nodes-and-clients/#node-types) to be created, giving the ability to anyone with a semi-decent laptop to verify the integrity of the information he cares about in the blockchain, without needing to rely on third parties such as infura or alchemy. Eth wiki has a [theoretical article](https://eth.wiki/fundamentals/patricia-tree) on Patricia-Merkle Trees, which is nicely complemented by my friend Gabriel Rocheleau's [practical article](https://rockwaterweb.com/ethereum-merkle-patricia-trees-javascript-tutorial/), which walks you through using the [javascript implementation](https://github.com/ethereumjs/ethereumjs-monorepo) of the EVM to get a hands on feeling for PMTs.

As for RLP, it is Ethereum's serialization protocol. Every value in PMTs are RLP encoded, and so is everything moving between nodes and frontend clients. Although there is value in understanding its [details](https://eth.wiki/fundamentals/rlp), I think its enough to understand that RLP was chosen for its simplicity. If you are wondering why Ethereum chose to reinvent the wheel instead of using another one of the other gazillion serialization protocols out there, Vitalik has a [response for you](https://blog.ethereum.org/2014/02/09/why-not-just-use-x-an-instructive-example-from-bitcoin/)[^vitalik-has-an-answer].


## Future of Ethereum

Now that we have a reasonable understanding of the current ethereum core, the actual fun stuff can start happening.

## Bibliography
- [The ultimate guide to L2s on Ethereum](https://mirror.xyz/dcbuilder.eth/QX_ELJBQBm1Iq45ktPsz8pWLZN1C52DmEtH09boZuo0)

## Footnotes

[^yellow-paper]: Vitalik first wrote the ethereum [white paper](https://ethereum.org/en/whitepaper/) to detail his precursory design and vision for the platform. Gavin Wood, one of the first few dozen people to get acces to this paper, almost immediately started working on an actual implementation of the Ethereum Virtual Machine (EVM). He later wrote the yellow paper as the complete mathematical specification of the EVM, which every ethereum client such as geth now use as reference. For a more detailed historical recounting of Ethereum's beginning, see Vitalik's [A Prehistory of the Ethereum Protocol](https://vitalik.ca/general/2017/09/14/prehistory.html) blog post.

[^chain-of-state-or-blocks]: Compare the two slides on p.9 and p.10.

[^vitalik-has-an-answer]: This is another observation that you will likely make early on while navigating the space. Most of the smart questions you will ask yourself, Vitalik will already have written a piece to answer them. I cannot recommend reading his [personal blog](https://vitalik.ca/) and earlier [ethereum R&D blog](https://blog.ethereum.org/category/research-and-development/) posts enough. 