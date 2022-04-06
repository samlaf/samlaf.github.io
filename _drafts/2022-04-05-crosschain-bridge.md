---
title:  Transfer of assets, cross-chain bridge, and consensus
category: blockchain
---

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