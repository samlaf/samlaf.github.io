---
title:  Distributed Systems and Consensus
category: blockchain
---

Distributed systems need consensus to "agree" on a set of value.

The easiest way to reach consensus is just to dedicate a leader, and have all other computers be "clients", whose answers the leader aggregates. Example of this include SETI, GIMPS, [Foldit](https://en.wikipedia.org/wiki/Foldit), and even [human-based computation games](https://en.wikipedia.org/wiki/Human-based_computation_game). See [How do I stop parasites, spoilers and faulty clients?](https://billpg.com/bacchae-co-uk/docs/dist.html#:~:text=How%20do%20I%20stop%20parasites%2C%20spoilers%20and%20faulty%20clients) for simple "consensus" reaching methods (really ways to prevent byzantine clients for tricking our reward system). (zk-proofs might be the more "advanced" versions of these methods)

The next problem in reaching consensus is: what happens if the leader computer crashes?
[MapReduce](https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf) might have solutions, or maybe we need to use a paxos-like algorithm on top...

Finally, we get into questions of byzantine fault tolerance algorithms that switch the leader: PBFT, tendermint, PoW, etc.

# References
See the crosschain-bridge draft for resources.
- Robert Morris' MIT [6.824 distributed systems class](http://nil.csail.mit.edu/6.824/2020/schedule.html)
- Martin Kleppmann's [Distributed Systems lecture series](https://www.youtube.com/playlist?list=PLeKd45zvjcDFUEv_ohr_HdUFe97RItdiB)