---
title:  Answering Moxie's web3 piece
category: blockchain
---

Moxie Marlinspike, creator of Signal, recently wrote a blog post entitled [My first impressions of web3](https://moxie.org/2022/01/07/web3-first-impressions.html) where he critiques web3's growing centralization tendencies. His stint into the blockchain world is surely a very short one, and he mostly focuses on his recent NFT related experiments, but one month for an engineer of his caliber is worth a year's time for us mere mortals. His cogent, powerful, and thought-provoking piece has certainly impacted my thinking greatly, and I cannot but recommend taking the time to read it.

His main critique, that "people don't want to run their own servers", isn't technical but rather involves a blend of psychology, sociology, and philosophy which I personally tend to align with. Vitalik, on the other hand, doesn't, and has already [taken a go at it](https://www.reddit.com/r/ethereum/comments/ryk3it/comment/hrrz15r/?utm_source=share&utm_medium=web2x&context=3). He accepted the critique that the *current* state of "crypto" does indeed lack cryptography, but complemented this admission with the challenging "cutting edge cryptography such as Verkle trees, ZK-SNARKs of the EVM, and BLS signature aggregation are currently being implemented." 

Vitalik stood up and defended our space as any great figurehead should, but in doing so he decided not to touch on the small, technical and less broad-reaching, not complete accurate critiques that Moxie makes. My goal here is just to point them out.

## 1. NFTs are only a pointer to the data

Let's take a look at some random [CryptoKitty NFT](https://opensea.io/assets/0x06012c8cf97bead5deae237070f9587f8e7a266d/229795) on opensea. Right clicking on the image leads to... [google photos](https://lh3.googleusercontent.com/sdy97_Rs91B8taHT3DbvR7ub1aGeoTzfJ_OdK91Bn-PiQdjJArRGE1baA40RIimwaz0thLCz1reUvvlp6rJSyu6l=w600)! An oft seen NFT architecture looks like

<center>
<img id="nft-architecture-img" src="/assets/answering-moxie-web3/NFT.drawio.svg">
</center>

which Moxie critiques:

> Instead of storing the data on-chain, NFTs instead contain a URL that points to the data. What surprised me about the standards was that there’s **no hash commitment** for the data located at the URL. Looking at many of the NFTs on popular marketplaces being sold for tens, hundreds, or millions of dollars, that URL often just points to some VPS running Apache somewhere. Anyone with access to that machine, anyone who buys that domain name in the future, or anyone who compromises that machine can change the image, title, description, etc for the NFT to whatever they’d like at any time (regardless of whether or not they “own” the token). There’s nothing in the NFT spec that tells you what the image “should” be, or even allows you to confirm whether something is the “correct” image.

NFT data indeed shouldn't be hosted on apache or google servers. These two choices are bad for separate, distinct reasons. Google is the ultimate centralization, which goes against the crypto ethos. But in reality apache VPS are much worse. As Moxie puts it, "Anyone with access to that machine, anyone who buys that domain name in the future, or anyone who compromises that machine can change the image, title, description, etc for the NFT to whatever they’d like at any time (regardless of whether or not they “own” the token)." There are two different solutions to this problem.

### 1.1 Hash commitments

Moxie mentions this in his quote, so he is probably unaware that we already have working implementations of hash commited data. These are called content-addressable file systems, and the two main projects are the Inter Platenary FileSystem ([IPFS](https://ipfs.io/)) and [Swarm](https://www.ethswarm.org/). We just need to standardize NFT hosting and try to enforce people to, unlike in the above [architecture](#nft-architecture-img), not only host metadata on IPFS or Swam, but also the image itself! [NFT Storage](https://nft.storage/) is one solution that I am aware of which helps onboard new users to this technology. Unfortunately though, this current state of affair might be the result of on-chain storage being more expensive (by a lot) than IPFS storage, which is itself more expensive than their centralized counterparts. Hopefully with [sidechains](https://defillama.com/chains) and [layer2](https://l2beat.com/) projects gaining traction, we might eventually become decentralized, again.

### 1.2 Accepting decentralized dynamic NFTs

The other solution is to accept NFTs being dynamic, and actually standardize that. Chainlink has already written an article on creating [oracle based dynamic NFT](https://blog.chain.link/how-to-build-dynamic-nfts-on-polygon/?_ga=2.245625863.247179535.1641346768-1813089108.1636139149), which would just like Moxie's NFT be changing based on some world state, but unlike his, be decentralized and tamper resistant.


## 2. ERC-721 and NFT royalties

The second problem he mentions having come accross, and uses as an argument for centralization overpowering decentralization, is token standards such as ERC20 (fungible tokens) and ERC721 (non-fungible tokens, aka NFTs) being slow to upgrade.

> People are excited about NFT royalties for the way that they can benefit creators, but royalties aren’t specified in ERC-721, and it’s too late to change it, so OpenSea has its own way of configuring royalties that exists in web2 space. Iterating quickly on centralized platforms is already outpacing the distributed protocols and consolidating control into platforms.

ERC-20 didn't exist in the early days of ethereum, and different protocols had their own, slightly different and often uninteroperable, token implementations. Until people settled on [ERC-20](https://eips.ethereum.org/EIPS/eip-20). Protocols like MakerDAO were then forced to change their implementation to follow along with the community and remain interoperable with newer protocols, such as lending platforms and decentralized exchanges, being developed using the standard. But the community has most definitely not stopped improving on token standards, which might be less obvious to newcomers who get showered with ERC20 and ERC721. New standards do keep coming out, with [ERC-223, ERC-777, ERC-1155, ERC-1337](https://www.gemini.com/cryptopedia/ethereum-token-standards-erc777-erc1155-erc223-erc1337) being a few of the important ones. As to Moxie's critique and NFT royalties, [EIP-2981](https://eips.ethereum.org/EIPS/eip-2981) has been created with hope to standardize them. So just like MakerDAO was forced to adopt ERC20, so too most likely will Opensea eventually be forced to adapt EIP-2981. Consensys has a great [article](https://consensys.net/blog/blockchain-explained/can-nfts-crack-royalties-and-give-more-value-to-artists/) on this specific topic.

## Conclusion

Overall, Moxie's piece has shaped and transformed my thinking, and its only healthy to get intelligent and constructive critiques coming into this space. Let's not get too gloomy to quickly however. I hoped I have convinced you with this short response that "crypto" is still blooming, and very fast, and there is much to do. So let's keep buidling.