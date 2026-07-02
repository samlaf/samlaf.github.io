---
title:  "Availability: Uptime, Redundancy, and Recovery"
series: "Applied Crypto, Appendix"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-14
---

The rest of this series keeps deferring availability. The intro calls it "deliberately not a major crypto topic"; the capstone files it under *Killable* and notes it "mostly lives in redundancy, rate limits, capacity, isolation, admission control, backup/restore, and operational discipline — not in ciphers." This appendix is where that leg gets its own short treatment, so the other articles can point here instead of re-litigating it.

Availability is the **A** in CIA, and it is the one goal crypto cannot deliver — it can only *subtract* from it. But it slots into the same reasoning ladder as every other concern, and it is the cleanest illustration of a point the [taxonomy post](/programming/security-acronyms.html) makes in the abstract: **one goal fans out into several capabilities**, each with its own policy and mechanism rungs. The compressed grids elsewhere print a single "rate-limit / admission control" cell for uptime; that cell is really four.

## Cube coordinates

```text
Concerns:
  uptime (availability)

Data state:
  at rest | in transit | in use

Reasoning layers:
  goal → capability → policy → mechanism

Control modality:
  technology + process + human  (heavy on the last two)
```

## One goal, four capabilities

Goal is fixed at the top — keep the service reachable (`availability` / *is it reachable?*). It fans out into four capabilities, and each drops through its own *policy* (which rules?) and *mechanism* (which runtime engine?):

| Capability · *what?* | Policy · *which?* (rules / specs) | Mechanism · *how?* (runtime engine) |
|---|---|---|
| **Rate-limiting / admission control** — cap the load any one source can impose | per-key quotas ("100 req/s/tenant", "10 req/min anon"); token-bucket refill rate + burst size; QoS priority classes (premium served first under contention); over-limit action (429 vs. queue vs. drop) | token/leaky-bucket counters (Redis-backed); `nginx limit_req`; API-gateway limiters (Envoy/Kong); concurrency limiters / load shedding; **SYN cookies** at the TCP layer |
| **Redundancy / replication** — keep spares so one failure isn't fatal | replication factor (N=3); placement constraints (spread across 3 AZs/racks); consistency level (quorum W+R>N, sync vs. async); failover policy (auto- vs. manual-promote); how many faults to tolerate (f) | Raft/Paxos consensus; primary-replica DB replication; load balancer + health checks; k8s ReplicaSets; anycast / DNS failover; heartbeats + VIP failover (keepalived) |
| **Backup / recovery** — be able to *restore* after loss or corruption | schedule (hourly/daily) + retention (GFS rotation: 30 dailies, 12 monthlies); **RPO** (tolerable data loss) & **RTO** (max time-to-restore); 3-2-1 rule; backup immutability / air-gap (ransomware); restore-test cadence | snapshots (ZFS/EBS); incremental tools (restic, borg, `pg_basebackup`+WAL); versioned object store w/ object-lock (S3 WORM); cold storage (Glacier); point-in-time recovery |
| **Incident response** — detect, contain, recover when the automated layers fail | severity classes (SEV1/2/3) + escalation paths; on-call / paging rotation; SLOs + error budgets that *trigger* response; who may declare an incident / initiate failover; blameless post-mortem requirement; comms plan (status-page updates) | PagerDuty/Opsgenie; alert rules (Prometheus/Grafana/Datadog); Slack war-room; status-page tooling; feature-flag kill switches; automated rollback pipelines; chaos drills (the rehearsal) |

Two things this grid makes visible, both reinforcing the taxonomy:

- **The policy rung here is *thresholds and schedules*, not access predicates.** For the *access* concern, policy is the multi-W predicate — *who* may do *what* to *which* object *when*. For availability it collapses to numbers and timetables: quotas, replication factors, RPO/RTO, severity thresholds. Same rung, very different flavor of rule — good evidence the layer axis is real and concern-independent.
- **The control modality drifts toward process and people.** A backup *retention policy* and an IR *escalation path* are process controls; the on-call human is a people control. Where crypto's cells (AEAD, signatures) are nearly pure technology, availability's policy/mechanism cells are dominated by McCumber's process/human modality. That is exactly *why* it sits in ops, not in ciphers.

## Why crypto only subtracts

Crypto delivers none of the four capabilities above. Worse, it tends to *cost* availability — the same six failure modes the capstone's [*Killable*](/programming/what-crypto-still-doesnt-give-you.html) section enumerates:

- expensive handshakes create DoS surface
- lost keys are permanent denial of access
- ransomware is confidentiality turned against the owner
- KMS outages make encrypted data unreadable
- certificate expiry takes down production
- revocation mistakes brick fleets

The only places crypto *helps* uptime are indirect and second-order: authenticating admission-control cookies (SYN-cookie-style), and protecting the *confidentiality and integrity* of backups so recovery is trustworthy. The reachability itself comes from redundancy, limits, and recovery drills.

## Across the data states

Availability changes shape by where the data is — the same split the [intro's uptime row](/programming/crypto-series-intro.html) sketches:

| State | Dominant capability | Typical mechanisms |
|---|---|---|
| **At rest** | backup / recovery | snapshots, immutable/offline backups, point-in-time restore, key-escrow tradeoffs |
| **In transit** | rate-limiting / admission control | SYN cookies, retries with backoff, anti-DoS, load balancing |
| **In use** | redundancy / failover | replicas, resource isolation, graceful degradation, circuit breakers |

## Where this connects

- The [taxonomy post](/programming/security-acronyms.html) places `uptime` as the availability leg of the concern grid and notes crypto "only *subtracts*" from it — this page is the worked expansion of that one cell.
- The [storage post](/programming/data-at-rest-storage-kms-and-recovery.html) covers the *backup / recovery* capability in depth (immutable backups, ransomware, rollback, lost-key recovery).
- The [keys post](/programming/keys.html) covers the flip side: a key is "both a security control and an availability dependency" — non-extractability improves secrecy but forces availability through a mediator.
- The [capstone](/programming/what-crypto-still-doesnt-give-you.html) is where availability appears as negative space; this appendix is the positive version.
