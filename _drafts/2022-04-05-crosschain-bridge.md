---
title:  Transfer of assets, cross-chain bridge, and consensus
category: blockchain
---

## Intro/analogy/example
ya une analogie a faire entre blockchain et bridge: les 2 tentent de solver le probleme: how do I transfer an asset between 2 parties securely?
Mettons j'ai 1000$ et jveux te le transferer securely, en echange de 800USD. On peut
1) passer par un custodian (une banque) - aka 1 central party
2) passer par un consortium pour le consensus - on transfers nos assets dans un "compte" avec m'man, p'pa, joanne, gaetan, et mado, et quand 3/5 personnes acceptent avoir recu nos 2 montants, ils nous les transferts.
3) p-e PBFT/tendermint ca rentre qqpart ici, mais jles comprends pas assez
4) PoW/PoS - la c'est la "totale" decentralisation - on fait confiance a un protocole et au fait que la majorite des "miners"/"validators" vont etre honest et pas collide offchain
Mais le probleme avec 4 reste....
ok fine on a ce mecanisme magique de PoW/PoS parfaitement decentraliser. Mais le probleme c'est que il peut juste transferer des assets qui sont DEJA dans son systeme. Donc pour te swap mon 1000$ en 800USD, je dois
1) transferer mon 1000 en 1000 cadc
2) tu transfers ton 1000 usd en usdc
3) la on fait le swap avec l'aide dun smart contract
mais pour executer 1) et 2)... on dirait qu'on a besoin d'une des solutions plus centralises du debuts (1, 2, ou p-e 3)
pour les cross-chain bridges... c'est le meme maudit probleme, mais un level meta au dessus
Problem: jveux transferer mes assets d'une blockchain a une autre qui se parlent pas. Je peux
1) passer par un custodian bridge
2) passer par un consortium bridge (comme celui de ronin je penses?)
3) passer par un PBFT/tendermint bridge (aucune idee si cest qqch)
4) passer par une blockchain of blockchain (mais la le probleme reste, how do we first transfer our assets to that blockchain?)
ah et aussi dnas le cas de cross-chain transfer, on a en plus l'option d'utiliser le consensus protocol qui existe deja sur la source blockchain, au lieu dutiliser un signature-based consortium bridge. Ca c'est lapproche light client

# Classifications
From Gang Wang's SoK (not sure I understand this classification...):
- Chain-based interoperability (mainly targets public blockchains)
  - sidechain
  - notary scheme
  - hash-locking
- Bridge-based interoperability (targets the implementation of a "bridge" as a connection component between homogeneous and heterogeneous blockchains)
  - trusted relay
  - blockchain engine
- dApp-based interoperability
  - blockchain of blockchains
  - blockchain adaptor
  - blockchain agnostic protocol

From Peter Robinson's survey:
- how is crosschain consensus achieved
  - including analysis of ACID properties?
- what trust assumptions are made
  - how does the system fail (safety and/or liveness and/or ?) if your trust assumption is violated?
- permissioned vs permissionless (is this a trust assumption...?)
- staking/slashing

## Trust
HYPOTHESIS: All (?) approaches come down to a threshold number of relayers, validators, or attestors signing or doing multi-party computation, on some information from the source blockchain.

Trust models:
- trustless (technically, still trust that >50% of miners are honest)
  - HTLC
  - modified HTLC (connext bridge uses a relayer to do 2nd part of tx for user - TRUSTED)
- Almost trustless (at least one party is honest)
  - SPV / light client / Relay
  - eg. rainbow bridge eth<>NEAR (but only works while eth is PoW)
- Trusted / Semi Trusted (single party / threshold number (eg. 2⁄3 majority) are honest)
  - Block Header Transfer (RELAYER)
    - Each relayer separately submits block all headers (eg. Clearmatics' Ion Framework)
    - Each relayer separately submits block only needed headers
    - Relayers cooperate and send a single signed tx
  - Event sign (ATTESTOR)
    - users ask a threshold number of attestors for signed event
    - Attestors cooperate to first gather all signatures, then user asks a for a single event
    - "Attestors" submit multiply signed event to source (eg. solana wormhole)
  - Event sign (RELAYER)
    - Each relayer separately submits signed event (eg. chainsafe's chainbridge)
    - Relayers submit signed Merkle Roots to destination blockchain (eg. Celo Optics)

The trusted model can be summarized by:
- WHAT is transferred (all events or only headers/merkle roots)
- WHERE are the signatures held: on source chain ("ATTESTOR"?), offchain (ATTESTOR), or on target chain (RELAYER)

Trust models should probably be fine-grained to M/N categories (https://vitalik.ca/general/2020/08/20/trust.html):
<img src="/assets/crosschain-bridge/trust-models-vitalik.png" width="50%">

Different steps of the bridge can also have different trust models (as connext):
1. commit on source chain
2. verify + commit on target chain
3. (maybe) abort source chain

Also can narrow down even more by looking at what ACTIONS are required/trusted:
- Sign individual messages, or sign a Merkle Root?
- Create a Merkle Tree of messages, or use block headers and transactions within blocks?
- Have relayers / attestors cooperatively sign, or have them separately submit information to
blockchains?
- Do relayers / attestors have to respond to requests from users?
- Who submits the transaction on the destination blockchain?

## Questions to think through
- Who is being trusted?
- How many transactions are needed to facilitate a transfer?
- Who is submitting what transactions to which blockchain?
- Can a user who has no value on the destination blockchain use this?
- How are infrastructure components (relayers, attestors etc) compensated?
- Do infrastructure components need to handle requests from users?
- How many components need to be compromised / bribed for the system to fail?
- What attacks are possible?
- Would you use this technique to transfer a billion $ ?????


# References
- [ACID: the wrong way to think about concurrency](https://www.cs.utexas.edu/users/witchel/pubs/witchel12systor-keynote-acid.pdf)
- [Safety and Liveness: Eventual Consistency Is Not Safe](http://www.bailis.org/blog/safety-and-liveness-eventual-consistency-is-not-safe/)
- [Not ACID, not BASE, but SALT](http://www.ise.tu-berlin.de/fileadmin/fg308/publications/2017/2017-tai-eberhardt-klems-SALT.pdf)
- [Overview of consensus algorithms in distributed systems - Paxos, Zab, Raft, PBFT](http://borisburkov.net/2021-10-03-1/)
- [Consensus cheat sheet](https://decentralizedthoughts.github.io/2021-10-29-consensus-cheat-sheet/)