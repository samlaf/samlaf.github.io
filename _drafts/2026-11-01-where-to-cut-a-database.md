---
title:  "Carving a database at its joints"
category: programming
date:   2026-11-01
---

> [The second principle is] that of dividing things again by classes, where the natural joints are, and not trying to break any part, after the manner of a bad carver.
> -- Plato, *Phaedrus* 265e

- [Database engine and its interfaces](#database-engine-and-its-interfaces)
- [Two cuts, and who may write](#two-cuts-and-who-may-write)
  - [Where nodes couple](#where-nodes-couple)
  - [Where data is copied](#where-data-is-copied)
  - [Who may write](#who-may-write)
- [Three designs up close](#three-designs-up-close)
  - [Aurora: the log is the database](#aurora-the-log-is-the-database)
  - [DSQL: every layer its own fleet](#dsql-every-layer-its-own-fleet)
  - [Calvin: the log comes first](#calvin-the-log-comes-first)
- [What no cut removes](#what-no-cut-removes)
- [References](#references)
- [Appendix: every system in one table](#appendix-every-system-in-one-table)

## Database engine and its interfaces

If Plato was alive today and tasked with scaling a database engine, he would look for the natural joints at which to split it.

![One engine: the buffer pool and the log side by side above the disk, with what crosses each interface](/assets/db-cuts/01-engine-stack.svg)

The joints are the various interfaces between each component, from SQL statements at the top to disk blocks at the bottom:[^hellerstein]

- **SQL:** parse, plan, and execute queries. The executor asks for rows.
- **Access methods:** tables and indexes, stored as heaps, B-trees, or LSM trees. They turn a request for a row or a key into reads and writes of pages. Each change to a page also produces a log record.
- **Buffer pool:** hot pages in RAM. Reads stop here, or go to the data files on a miss. Before it writes a dirty page back, the buffer pool flushes the log up to that page's log sequence number (LSN). This rule is write-ahead logging.
- **Log:** the recovery log, kept beside the buffer pool. A commit is durable once its records are on disk. After a crash, recovery rebuilds pages from the log, so the log is the truth and the data files are a copy. [Aurora](#aurora-the-log-is-the-database) takes this literally and never writes data pages at all. Depending on the design, the log holds redo records, undo records, or both.
- **Disk:** blocks that hold the data files and the log files.
- **Concurrency control:** locks, MVCC versions, and the commit. It sits beside the stack because the executor, the access methods, and the log all take part in it.

[^hellerstein]: Hellerstein, Stonebraker, and Hamilton's [Architecture of a Database System][hellerstein-arch] (2007) draws the main components as blocks, not as a stack. Its Figure 1.1 puts the access methods, buffer manager, lock manager, and log manager side by side in one transactional storage manager, next to a process manager and shared utilities. This post orders the parts in a line for simplicity, so that each interface is one place to cut. Process management and the shared utilities don't change where a design cuts, so the figure leaves them out.

Past a certain database size, the storage layer must be sharded. But as we will see, how sharding, replication, and concurrency control are handled when splitting an engine is a vast design space.

Some designs run the layers below a joint on machines of their own, sized and scaled apart from the machines above it. This is called disaggregation. It doesn't have to change what crosses the joint: Postgres on EBS reads blocks over the network, as it would from a local disk. Aurora goes further and changes the interface, so that redo records cross instead of pages. DSQL runs everything below SQL on separate fleets, concurrency control included.

## Two cuts, and who may write

Scaling out means making two cuts in the stack:

1. **Distribution: where does the stack stop running once per node?** This joint is the coupling point. Above it, every node runs its own instance of each layer and can serve any query. Below it, each piece of data has exactly one home.
2. **Replication: where is data copied?** This is the copy point. Below it, every layer exists once per replica, so the data survives a lost machine.

A third decision depends on both cuts. **Concurrency control** has no joint of its own; it sits beside the stack. Where it sits relative to the coupling point decides who may write: above it, only one node may; at or below it, many nodes may. And where the copy point sits decides whether concurrency control must be deterministic.

What crosses each chosen joint decides what the design pays. The map below draws seven designs, one column per family, with both cuts and concurrency control marked. Aurora's read replica sits beside its writer, with the redo stream drawn as an arrow between their buffer pools. The bottom row stands for both the data files and the log files.

![Seven designs in four families, as side-by-side node stacks: where each couples nodes, where each copies data, and where concurrency control sits](/assets/db-cuts/03-couple-and-copy.svg)

The subsections below take the two cuts, then concurrency control. [Three designs up close](#three-designs-up-close) then applies them to Aurora, DSQL, and Calvin.

### Where nodes couple

Every design has a coupling point, and it is where cloning ends. Above it, every node runs its own instance of each layer, and that instance sees the whole database. Below it, each piece of data has exactly one home, and nodes reach it only through the interface at the joint. Correctness rests on what crosses there.

A large home is sharded across many machines, but the joint may hide that. A shared disk offers one address space, while CockroachDB's nodes send each key to its owner.

Reads and writes cross the same joint, but not always as the same thing or at the same time. A read leaves the node only on a cache miss. A write may wait until commit, as in DSQL. And Aurora sends writes down as redo records, but reads pages back up.

The classic names for coupling points are shared memory, shared disk, and shared nothing. They describe hardware: what the processors physically share. By that measure, almost every cloud database today is shared nothing, so the labels stop telling designs apart. This post reads "shared X" as the name of a coupling point instead: X is the highest layer that all nodes share, and above it each node has its own instance. Read this way, the three names become four families. Each holds two designs that cut at the same joint and differ in one other way.

**Shared memory** is one machine. Its threads couple in RAM, through one buffer pool and one lock table. Scaling it up means buying a bigger machine. **Read replicas** add machines for reads, but nothing couples writers.

**Shared nothing** cuts above SQL. The two designs differ in how much the router understands.

- **Independent shards.** Each shard is an independent database, and the application decides which one to talk to. Cross-shard queries and transactions are the application's problem. A routing proxy such as Vitess or [Figma's DBProxy][figma-dbproxy] moves routing out of the application, but the shards still never talk to each other.
- **Distributed query.** The router is a query planner. A coordinator splits a query that spans shards into fragments, sends them to the nodes that own the data, and merges the results. This is function shipping. For `SELECT region, sum(amount) FROM orders GROUP BY region`, each node sums its own rows and returns a small partial result. Joins on a key other than the shard key shuffle rows between nodes mid-query, and multi-shard writes add a commit protocol such as two-phase commit (2PC). Citus, Greenplum, and Teradata work this way.

**Shared key-value store** cuts between SQL and the access methods. Every node runs SQL over the whole database and reads and writes rows through one key-value interface. Below the joint, keys are split into ranges, and each range has an owner. The two designs differ in when the owner learns about a write.

- **Range owners.** Each range's owner, its leaseholder, receives key-value reads and writes as a transaction runs, and enforces the locks for its range. Each owner runs its own access methods. Spanner, CockroachDB, TiDB, and YugabyteDB work this way.
- **Unbundled.** No owner enforces locks while a transaction runs. Concurrency control becomes a service of its own. In DSQL, query processors read rows straight from storage and keep their writes until commit. Then a commit check by the adjudicators, which own key ranges too, decides which writes win. [FoundationDB][foundationdb] has the same shape. [DSQL](#dsql-every-layer-its-own-fleet) covers the details.

No family cuts at the next joint down, between the access methods and the buffer pool. A B-tree lookup touches several pages one after another, and across that joint each page would cost a round trip. Research systems such as NAM-DB and Sherman cut there anyway, over fast RDMA networks.

**Shared disk** cuts below the buffer pool and the log. The two designs differ in what crosses the joint, and so in how many writers there can be.

- **Coherent caches.** The buffer pools also talk to each other. Every node runs SQL, access methods, a buffer pool, and its own log over the whole database, and all of them read and write one set of shared volumes. The hard part is keeping the buffer pools coherent and the locks global. This is data shipping: pages and lock messages cross between nodes. Oracle RAC (Cache Fusion) and Db2 pureScale are the long-lived examples. ScaleStore, a research system, keeps buffer pools coherent the same way, over RDMA and without shared disk.
- **Log-based storage.** The log is the interface. The writer sends redo records to a storage service, and storage sends pages back on a miss. Aurora, Neon, Azure SQL Hyperscale, and AlloyDB work this way, each with one writer. [Aurora](#aurora-the-log-is-the-database) shows why.

No design removes the cost of coordination; each chooses where to pay it.

| Design | What it buys | Where it pays |
| --- | --- | --- |
| Read replicas | Reads scale, and writers never coordinate | One writer; replicas lag behind it |
| Independent shards | Shards that never coordinate | Application code for anything that spans shards |
| Distributed query | Transparent cross-shard queries | Fragment shipping, shuffles, and 2PC for multi-shard writes |
| Range owners | Any node runs any query; each range fails over on its own | A network hop per key access, 2PC across ranges, and a hot range stuck on one node |
| Unbundled (DSQL) | Any query processor writes; every layer scales on its own | Contention becomes aborts; every read and commit crosses the network |
| Coherent caches | Any node writes any row | Cache coherence and global locking |
| Log-based storage (Aurora) | Cheap durability, fast failover, read replicas sharing one volume | One writer; a cold cache costs page round trips |

### Where data is copied

The copy point is where the data is copied, so it survives a lost machine. Below it, every layer exists once per replica. Layers above it can run on each replica too, as a Postgres standby runs its own buffer pool and SQL engine, but nothing is copied into them: each replica rebuilds them from the layers below. Only the log and the data files need a copy point. A cache that dies with its machine costs speed, not data.

The coupling point and the copy point are independent. Oracle RAC couples at its buffer pools and its disk, and copies at the disk by mirroring its shared volumes. A single primary with read replicas never couples writers at all, but it still copies its log. Most designs shard first, then replicate each shard: a Raft group per range, a primary and replicas per Vitess shard. They copy at or below where they couple, because a replica can only copy what one owner has already decided. Above the coupling point, no single node decides the result: it depends on data that other nodes hold. [Calvin][calvin] does the opposite. It replicates first, by copying its input log above SQL, and each replica then shards the data among its partitions. That works only because every replica reaches the same result on its own, as [Who may write](#who-may-write) explains.

The kind of log a design copies sets the height of its copy point. A physical log describes changes to pages. It copies below the buffer pool, and each replica's pages mirror the primary's. A logical log describes changes to rows or keys. It copies above the access methods, so each replica runs its own access methods and builds its own pages. A command log describes the transactions themselves, before they run. It copies above SQL, so each replica executes every transaction again.

| Design | Log it copies | Kind: what it describes | Who must acknowledge a write |
| --- | --- | --- | --- |
| Postgres + replicas, Citus | WAL, per shard | Physical: page changes | The primary, plus any synchronous standbys |
| Vitess | MySQL binlog, per shard | Logical: committed row changes | The primary, plus one replica if semi-synchronous |
| CockroachDB | Raft log, per range | Logical: key-value writes, including write intents | A Raft majority |
| Aurora | Redo records, sent to storage | Physical: page changes | A storage quorum |
| DSQL | Journal | Logical: write sets of committed transactions | The journal, across zones |
| [Calvin][calvin], VoltDB | Input log of ordered transactions | Command: each transaction and its arguments | The replicas of the input log |

[Alex Miller][miller-decomposing] gives another way to see this. He splits every transaction into four steps: execute, order, validate, and persist. Systems differ in the order they run them. This post asks where each step runs instead. Distribution places execution, concurrency control places ordering and validation, and replication places persistence. The two views meet at the copy point. Every step that comes after persist runs again on each replica, so where persist falls in time sets how high the copy point sits in the stack. Aurora persists after execution, so its replicas only build pages. Calvin persists before execution, so every replica runs every transaction.

### Who may write

Concurrency control decides the order of conflicting writes. What matters is which side of the coupling point it lands on.

![Two panels. Left: each node runs SQL and its own locks above the coupling point, so only one node writes. Right: concurrency control sits below the coupling point, in the home of the data, so every node can take writes](/assets/db-cuts/03b-who-may-write.svg)

Above the coupling point, each node keeps its own locks, and those locks see only that node's transactions. Two nodes could lock the same row and never know it. So only one node may write. At or below the coupling point, every write to a key meets the same check, whichever node sent it. That check may be a lock held by the key's owner, a global lock, or a conflict check at commit. So:

**A design allows many writers only if concurrency control sits at or below the coupling point.**

The dashed grey bars in [the map](#two-cuts-and-who-may-write) mark where concurrency control sits in each design. [Ziegler, Bernstein, Leis and Binnig][ziegler-cidr23] (CIDR 2023) turn that question into a classification. They argue that shared nothing versus shared disk no longer predicts how a system scales. Aurora and SQL Hyperscale share storage but allow only one writer, and a MySQL primary with private-storage replicas behaves the same way. So they classify systems by who may update a data item:

- **Single-Writer:** one read-write node; reads scale with replicas, writes do not. Concurrency control runs on that node, above the coupling point.
- **Partitioned-Writer:** one writer per shard; uniform writes scale, but a hot key is always handled by the same node. Concurrency control sits with each owner, below the coupling point.
- **Shared-Writer, coherent cache:** any node writes, and compute caches are kept consistent by a coherence protocol. Hot data is replicated on demand, so skewed reads scale too. Concurrency control runs on every node, kept global by coherence and global locks.
- **Shared-Writer, no coherent cache:** any node writes, and every access goes to shared storage, which can become the bottleneck under skew. Concurrency control moves to the shared side, for example as a check at commit.

They advocate the coherent-cache design, which their ScaleStore system implements.

Shared-Writer is not multi-leader replication: conflicting writes are still ordered before they commit, through global locks, a coherent cache, or a commit check.

Cross where nodes couple with who may write, and the rule shows up again: any-node writes exist only where something below SQL arbitrates them, either a coherent cache or a commit-time conflict check.

![Designs placed by where their nodes couple and by who may write a row; Aurora and DSQL highlighted](/assets/db-cuts/04-archetype-map.svg)

DSQL and CockroachDB share a column: both cut at the same joint, below SQL, and both split keys among owners. They differ only in the row, which is when the owner hears about a write. CockroachDB sends each write to its range's owner while the transaction runs, as a write intent that blocks other writers. DSQL keeps every write in the query processor until commit, then sends the whole write set to the adjudicators, which check it for conflicts. DSQL postdates the paper, so its row is my classification: a Shared-Writer without a coherent cache, since no query processor caches data. The paper scores that archetype weakest on latency, and DSQL counters it with row-level storage and pushdown, a lever the paper itself names.

The copy point constrains concurrency control too. Everything above the copy point runs again on each replica, so it must reach the same result everywhere. With a [command log](#where-data-is-copied), every replica executes every transaction, so concurrency control must be deterministic: replicas agree on an order first, then execute in that order. Row-level locks and MVCC let each replica decide on its own, so they don't fit.

## Three designs up close

Aurora, DSQL, and Calvin each cut the engine in a different way. They differ most in where they put the log:

- **Aurora** puts it at the bottom: redo records, written after the writer runs the transaction. It keeps one writer.
- **DSQL** puts it in the middle: write sets, written once the adjudicators approve them. Any node may write.
- **Calvin** puts it at the top: transaction inputs, written before anything runs. Any node may write, and conflicts make transactions wait instead of abort.

Each design gets a chart that shows both views from [replication](#where-data-is-copied). Across is time: Miller's four steps, in that design's order. Down is space: the layer that runs each step. The orange line is the copy point, and the shaded area holds the steps that every replica repeats.

I picked Aurora and DSQL because I know them best, and Calvin because no other design here puts the log above execution. None of them is alone. Azure SQL Hyperscale ([Socrates][socrates]), Google's AlloyDB, and Neon have Aurora's shape: one writer over shared, log-based storage. Socrates and Neon go one step further and separate the log service from the page servers. FoundationDB has DSQL's shape, as a key-value store without SQL on top. VoltDB, like Calvin, replicates transactions rather than their results.

### Aurora: the log is the database

Aurora keeps a single writer running the full SQL and transaction engine, but moves logging and page storage into a shared, quorum-replicated service. The writer sends storage only redo records, never pages.

![Aurora's steps over time and across layers: the one writer executes and orders; storage persists redo below the buffer pools and builds pages; read replicas apply the redo stream to their caches](/assets/db-cuts/05-aurora.svg)

In [Werner Vogels' description][aurora-ascendant] (2019), Aurora treated caching and logging as the layers ripe for reinvention. The storage service builds page images from the log on demand, so instances never flush dirty pages. Every write goes to six copies across three AZs and succeeds once four acknowledge. Up to 15 read replicas share the same volume.

**Why the cache sits on the joint.** The buffer pool is RAM on each instance, so physically it belongs to compute. Its rules, though, are set by the storage contract:

- **Misses:** a miss is a request to storage for a page at a specific LSN.
- **Eviction:** a dirty page can be dropped once its redo is durable, because storage can always rebuild it. There is no flush.
- **Replicas:** a read replica gets no copy of the data, because it reads the writer's storage. The writer still streams its redo to each replica. Per the [Aurora paper][aurora-paper], the replica applies each record to a page it has cached and drops the rest. That stream keeps caches fresh: it is a cache-coherence protocol, not a durability one.

**Why there is still exactly one writer.** The lock manager and the buffer pool are in-memory structures inside one process, and the writer assigns every LSN. Storage persists the log and replays it, but never decides its order. Aurora offloaded the log's durability and page construction, not its authorship. A second writer would need distributed locking and cache coherence, which brings back the shared-disk problem. [Stonebraker][stonebraker-sn] listed three such problems in 1985: copies of the lock table, buffer pools that must agree, and a log that several writers share. Aurora sits in the shared-disk family but avoids all three, because it has one writer.

**Getting more writers.** AWS has tried three ways. Only sharding adds real write capacity:

| Approach | How it works | More write capacity? |
| --- | --- | --- |
| Multi-Master (MySQL 5.6 only, discontinued) | Several writers on one volume; conflicting writes abort at the storage layer | Not reliably |
| [Global Database write forwarding][aurora-write-forwarding] | Replicas in secondary regions accept writes and forward them to the one writer | No |
| [Aurora Limitless Database][aurora-limitless] (PostgreSQL) | Tables sharded behind a router; each shard is a single-writer Aurora | Yes |

Limitless cuts above SQL, like [independent shards](#where-nodes-couple): there are more writers in total, but every key range still has exactly one owner.

### DSQL: every layer its own fleet

Aurora DSQL keeps Postgres's SQL engine but replaces everything beneath it with separately scaled services. Marc Brooker's walkthrough ([Reads and Compute][dsql-reads], [Transactions and Durability][dsql-writes]) describes each piece.

![DSQL's steps over time and across layers: query processors execute, adjudicators validate and order, the journal persists, and each storage replica applies the write sets](/assets/db-cuts/06-dsql.svg)

- **Query processors** run a customized Postgres engine. They never talk to each other, and they cache no table data, only rarely-changing metadata such as table definitions.
- **Adjudicators** own key ranges and check each write set at commit. A transaction aborts if another one has written its keys since it started. Isolation is snapshot isolation, so write skew is possible.
- **The journal** orders and persists committed transactions. Appending is the commit.
- **Storage** is sharded, and serves rows as of a timestamp rather than pages.

**How it gets many writers.** Aurora avoids Stonebraker's three shared-disk problems by having one writer. DSQL removes each one instead. Concurrency control lives in the adjudicators, so no query processor keeps a lock table. Query processors cache no data, so there are no buffer pools to keep coherent. And the journal is the log that many writers share, built as a service that scales. The [cost table](#where-nodes-couple) shows the price: contention becomes aborts, and every read and commit crosses the network.

### Calvin: the log comes first

[Calvin][calvin] runs the steps in the opposite order from Aurora and DSQL. It agrees on the order of transactions first, makes that order durable, and only then runs them. It began as a research system, and FaunaDB later built a commercial database on its design.

![Calvin's four steps over time and across layers: order and persist in the sequencer, above execution; then every replica locks, executes, and writes its own storage](/assets/db-cuts/07-calvin.svg)

- **Sequencers** collect transaction requests into 10 ms batches, called epochs, and replicate each batch, by Paxos or asynchronously. Once the batch is replicated, the transaction will run: this is the commit.
- **Schedulers**, one per partition (Calvin's name for a shard of each replica), take the locks each transaction needs, in log order. Replicas that read the same log take the same locks in the same order.
- **Executors** run the transaction. When it spans partitions, each partition reads its own rows and sends them to the partitions that write. Each writing partition then has every input, and computes the same result.
- **Storage** can be any store that reads and writes by key.

**How it gets many writers without aborts.** Every partition, on every replica, sees the same order. Nothing that happens after the order is fixed can change the outcome, so no partition needs to vote: there is no two-phase commit. A crashed node recovers by replaying the input log. And because locks follow the log order, contention makes transactions wait, not abort.

**What it pays.** A transaction must be deterministic, and the scheduler must know which keys it will touch before it runs. When those keys depend on data, Calvin first runs a read-only query to find them, then restarts the transaction if that data has changed. This is the one case where contention costs a retry. And one slow transaction holds its locks while every later transaction that needs them waits.

## What no cut removes

Every design in this post pays for coordination somewhere, as the [cost table](#where-nodes-couple) shows. The two cuts, and where concurrency control sits, say where. One cost none of them escapes is a hot key: Ziegler et al. find that no archetype scales skewed writes.

## References

1. [Amazon Aurora ascendant][aurora-ascendant] — Vogels, 2019; why Aurora reinvented the caching and logging layers
2. [Amazon Aurora: Design Considerations for High Throughput Cloud-Native Relational Databases][aurora-paper] — Verbitski et al., SIGMOD 2017; the log is the database, and how replica caches follow it
3. [Aurora Global Database write forwarding][aurora-write-forwarding] — AWS docs; secondary regions forward writes to the one writer
4. [Aurora PostgreSQL Limitless Database][aurora-limitless] — AWS docs; single-writer shards behind a router
5. [DSQL Vignette: Reads and Compute][dsql-reads] — Brooker, 2024; query processors and timestamped reads
6. [DSQL Vignette: Transactions and Durability][dsql-writes] — Brooker, 2024; adjudicators, the journal, and optimistic commits
7. [Is Scalable OLTP in the Cloud a Solved Problem?][ziegler-cidr23] — Ziegler, Bernstein, Leis, Binnig, CIDR 2023; the data-access archetypes
8. [FoundationDB: A Distributed Unbundled Transactional Key Value Store][foundationdb] — Zhou et al., SIGMOD 2021; proxies, resolvers, and logs
9. [Multi-AZ DB cluster deployments][rds-multi-az-cluster] — AWS docs; semisynchronous replication to two readers
10. [How Figma's databases team lived to tell the scale][figma-dbproxy] — Figma, 2024; DBProxy, colos, and logical before physical sharding
11. [The Case for Shared Nothing][stonebraker-sn] — Stonebraker, HPTS 1985; shared memory, shared disk, and shared nothing, compared on twelve points
12. [Calvin: Fast Distributed Transactions for Partitioned Database Systems][calvin] — Thomson et al., SIGMOD 2012; deterministic ordering before execution
13. [Socrates: The New SQL Server in the Cloud][socrates] — Antonopoulos et al., SIGMOD 2019; Azure SQL Hyperscale, with the log service apart from the page servers
14. [Architecture of a Database System][hellerstein-arch] — Hellerstein, Stonebraker, Hamilton, Foundations and Trends in Databases, 2007; the components of a relational engine
15. [Decomposing Transactional Systems][miller-decomposing] — Miller, 2025; execute, order, validate, and persist, and the orders systems run them in

[aurora-ascendant]: https://www.allthingsdistributed.com/2019/03/amazon-aurora-design-cloud-native-relational-database.html "Amazon Aurora ascendant: How we designed a cloud-native relational database"
[aurora-paper]: https://www.allthingsdistributed.com/files/p1041-verbitski.pdf "Amazon Aurora: Design Considerations for High Throughput Cloud-Native Relational Databases"
[aurora-write-forwarding]: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-write-forwarding.html "Aurora Global Database write forwarding"
[aurora-limitless]: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/limitless.html "Aurora PostgreSQL Limitless Database"
[dsql-reads]: https://brooker.co.za/blog/2024/12/04/inside-dsql.html "DSQL Vignette: Reads and Compute"
[dsql-writes]: https://brooker.co.za/blog/2024/12/05/inside-dsql-writes.html "DSQL Vignette: Transactions and Durability"
[ziegler-cidr23]: https://www.cidrdb.org/cidr2023/papers/p50-ziegler.pdf "Is Scalable OLTP in the Cloud a Solved Problem?"
[foundationdb]: https://www.foundationdb.org/files/fdb-paper.pdf "FoundationDB: A Distributed Unbundled Transactional Key Value Store"
[rds-multi-az-cluster]: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html "Multi-AZ DB cluster deployments"
[figma-dbproxy]: https://www.figma.com/blog/how-figmas-databases-team-lived-to-tell-the-scale/ "How Figma's databases team lived to tell the scale"
[stonebraker-sn]: https://dsf.berkeley.edu/papers/hpts85-nothing.pdf "The Case for Shared Nothing"
[calvin]: http://cs.yale.edu/homes/thomson/publications/calvin-sigmod12.pdf "Calvin: Fast Distributed Transactions for Partitioned Database Systems"
[socrates]: https://www.microsoft.com/en-us/research/wp-content/uploads/2019/05/socrates.pdf "Socrates: The New SQL Server in the Cloud"
[hellerstein-arch]: https://dsf.berkeley.edu/papers/fntdb07-architecture.pdf "Architecture of a Database System"
[miller-decomposing]: https://transactional.blog/blog/2025-decomposing-transactional-systems "Decomposing Transactional Systems"

## Appendix: every system in one table

This table extends [the map](#who-may-write) with the copy point, concurrency control, and where hot data is cached.

| System | Archetype (Ziegler et al.) | Couples at | Copies at | Who writes a row | Concurrency control | Hot data cached in |
| --- | --- | --- | --- | --- | --- | --- |
| Postgres or MySQL, primary + replicas | Single-Writer | Nowhere | Log of the whole database; replicas replay it, asynchronously or synchronously | Primary only | Locks + MVCC | Each node's buffer pool |
| Amazon RDS | Single-Writer | Nowhere | Multi-AZ instance: blocks, synchronously, to a standby that serves no reads. Read replicas: the engine's log, asynchronously. Multi-AZ DB cluster: the log, semisynchronously; one of two readers must acknowledge | Primary only | Locks + MVCC | Each instance's buffer pool |
| Aurora (provisioned) | Single-Writer | Below the buffer pool: redo down, pages up | Log records: six copies of each 10 GB segment, four must acknowledge | One writer | Locks + MVCC on the writer | Compute buffer pool; misses served by storage |
| Neon | Single-Writer | Below the buffer pool: WAL to safekeepers, pages from pageservers | Log: Paxos across safekeepers | One writer | Postgres locks + MVCC | Buffer pool + local file cache |
| Azure SQL Hyperscale | Single-Writer | Below the buffer pool: log service, page servers | Log, in the log service | One writer | SQL Server locks + versioning | Compute memory + local SSD cache |
| AlloyDB | Single-Writer | Below the buffer pool: log-based shared storage | Log, in regional storage across zones | One writer | Postgres locks + MVCC | Buffer pool + columnar cache |
| PolarDB, PolarDB Serverless | Single-Writer | Blocks on shared PolarFS volumes; Serverless keeps read-only nodes current with a coherence protocol | Storage: PolarFS chunks, by ParallelRaft | One writer | Locks + MVCC | Buffer pool |
| App-level sharding | Partitioned-Writer | Above SQL, in the application | Log, per shard | One writer per shard | Per shard | Per shard |
| Citus, Vitess, Figma DBProxy, Aurora Limitless | Partitioned-Writer | Above SQL, in a router or coordinator | Per shard: log shipping (Citus, Vitess, Figma), Aurora storage (Limitless) | One writer per shard | Per shard; 2PC across shards | Per shard |
| Teradata, Greenplum | Partitioned-Writer | Above SQL, in an MPP coordinator | Per node: mirror segments (Greenplum), fallback copies (Teradata) | Shard owner | Per node; 2PC across nodes | Per node |
| Spanner, CockroachDB, TiDB, YugabyteDB | Partitioned-Writer | Below SQL: key-value reads and writes | Log, per range, by Paxos or Raft | Leader of each range | Timestamps + 2PC over consensus groups | Per node, per range |
| DynamoDB | Partitioned-Writer | Key-value requests to partitions | Log, per partition, by Paxos across three zones | Leader of each partition | Per item; transactions across items | Per partition |
| Oracle RAC, Db2 pureScale | Shared-Writer, coherent cache | Pages between buffer pools; blocks on shared disk | Storage: mirrored shared volumes | Any node | Global locks, coherent cache | Coherent cache across nodes |
| Aurora Multi-Master (retired) | Shared-Writer, weakly coherent cache | Below the buffer pool, on Aurora storage | Aurora storage | Any writer | OCC at storage; losing writes abort | Per node, refreshed by update propagation |
| Aurora DSQL | Shared-Writer, no coherent cache (my classification) | Below SQL: row reads; write sets at commit | Journal, across zones | Any query processor | OCC at adjudicators; snapshot isolation | Inside storage; rows + pushdown |
| FoundationDB | Shared-Writer, no coherent cache (my classification) | Below the client: key reads; write sets at commit | Transaction logs, synchronously | Any client | OCC at resolvers; serializable | Storage servers |

The RDS row follows AWS's [Multi-AZ DB cluster documentation][rds-multi-az-cluster]. Archetypes, and the PolarDB and Aurora Multi-Master details, come from Ziegler et al. Other details are summarized from public descriptions.

## Footnotes <!-- omit in toc -->
