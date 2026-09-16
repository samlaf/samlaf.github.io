# Authorization as Data: ACLs, RBAC, ABAC, ReBAC, and Capabilities
# TODO: merge this with the other article

Authorization systems are often introduced as a collection of unrelated models: ACLs, RBAC, ABAC, ReBAC, capabilities, MAC, DAC, and so on.

A more useful way to understand them is to start underneath those names.

Every authorization system is ultimately trying to answer some version of:

```text
authorize(
    subject,
    object,
    action,
    context
) → allow / deny
```

For example:

```text
Can Alice read document X?
Can process P write file F?
Can service A call endpoint B?
Can user U administer project Q?
```

But even this formulation hides something important: the `subject` and `object` often aren't concrete things yet. They are references that must themselves be resolved.

And the permission relationship between them may live somewhere else entirely.

Conceptually, there are three bodies of mutable state:

```text
SUBJECT STATE
Who/what is acting?

OBJECT STATE
What is being acted upon?

AUTHORIZATION STATE
What relationships or rules connect them?
```

An authorization decision is therefore something like a query over these stores:

```text
subject reference ──► subject state ──┐
                                      │
object reference  ──► object state ───┼──► authorization ──► allow / deny
                                      │
                     policy state ────┘
```

This perspective makes many apparently different authorization systems fall into place.

The central questions become:

1. **How is the access relationship represented?**
2. **When is it evaluated?**
3. **How is the resulting authority exercised?**

---

## 1. The access matrix

The simplest abstract representation of authorization is an access matrix:

```text
                 objects

              file A   file B   server C

subjects
Alice           rw        r         -
Bob             -        rw       deploy
Carol           r         -       deploy
```

Each cell describes:

```text
(subject, object) → rights
```

In principle, we could store this entire matrix.

In practice, it would be enormous and sparse.

Most authorization models can be understood as different ways of **representing or deriving this matrix**.

---

# ACLs: store the matrix by object

An Access Control List stores the authorization relation from the object's perspective.

Instead of the whole matrix:

```text
file A:
    Alice → read/write
    Carol → read

file B:
    Alice → read
    Bob   → read/write
```

The representation is:

```text
object → [(subject, rights)]
```

Authorization becomes approximately:

```text
resolve object
      ↓
retrieve object's ACL
      ↓
find matching subject
      ↓
check requested permission
```

This is why ACLs are traditionally described as storing **columns of the access matrix**.

### Groups are an indirection

Instead of writing:

```text
file A:
    Alice → read
    Bob   → read
    Carol → read
```

we can write:

```text
Engineering = {
    Alice,
    Bob,
    Carol
}

file A:
    Engineering → read
```

Conceptually, the group can be expanded into its members.

So groups don't fundamentally change the model. They provide an indirection that compresses repeated ACL entries.

Unix permissions are essentially a particularly compact form of this idea:

```text
inode
├─ owner UID
├─ group GID
└─ mode
   ├─ owner: rwx
   ├─ group: rwx
   └─ other: rwx
```

POSIX ACLs generalize it further by allowing more named users and groups.

The important property is:

> Much of the authorization relation is attached directly to the object.

---

# Capabilities: transpose the matrix

Capabilities provide the classic dual of ACLs.

Instead of storing:

```text
file A:
    Alice → rw
    Carol → r
```

we can store:

```text
Alice:
    file A → rw
    file B → r

Carol:
    file A → r
```

Now the representation is:

```text
subject → [(object, rights)]
```

If ACLs store matrix **columns**, capability lists store matrix **rows**.

```text
ACL

object
  ├─ subject A → rights
  ├─ subject B → rights
  └─ subject C → rights


CAPABILITY LIST

subject
  ├─ object A → rights
  ├─ object B → rights
  └─ object C → rights
```

This is the real sense in which capabilities are the "reverse" of ACLs.

RBAC, as we'll see, is doing something different.

---

# RBAC: factor the matrix

Role-Based Access Control introduces an intermediary:

```text
subject → role → permission
```

Suppose Alice, Bob, and Carol all have the same permissions:

```text
Alice → repo:write
Alice → production:deploy

Bob   → repo:write
Bob   → production:deploy

Carol → repo:write
Carol → production:deploy
```

RBAC factors out the repeated structure:

```text
Alice ─┐
Bob   ─┼──► Developer
Carol ─┘

Developer:
    repo       → write
    production → deploy
```

So there are two relations:

```text
User → Role

Role → Permission
```

where a permission can itself be understood as:

```text
(object, operation)
```

In matrix language, RBAC is roughly a **factorization**:

```text
Users × Permissions

        ≈

(Users × Roles)
        ×
(Roles × Permissions)
```

Not numerical matrix multiplication literally, but relationally the analogy is useful.

This is why RBAC should not be thought of as "put the ACL on the subject."

That's capabilities.

RBAC instead inserts a reusable semantic layer between subjects and permissions.

---

# ABAC: compute the matrix

Attribute-Based Access Control makes a larger conceptual jump.

Instead of explicitly storing:

```text
Alice → document A → read
```

we might store facts about Alice and the document.

```text
Alice:
    department = engineering
    clearance  = 4

Document A:
    department  = engineering
    sensitivity = 3
```

Then write a policy:

```text
allow read if

    subject.department == object.department
    AND
    subject.clearance >= object.sensitivity
```

The access relation is no longer directly enumerated.

It is **computed**.

```text
f(
    subject attributes,
    object attributes,
    action,
    environment
) → allow / deny
```

A useful database analogy is a predicate:

```sql
WHERE subject.department = object.department
  AND subject.clearance >= object.sensitivity
```

So there is an important progression:

```text
ACL
    store the access relation

RBAC
    factor the access relation

ABAC
    compute the access relation
```

And attributes can live in many places:

```text
subject attributes
├─ identity provider
├─ HR database
├─ LDAP
├─ token claims
└─ process credentials

object attributes
├─ database
├─ filesystem metadata
├─ resource service
└─ labels

environment
├─ time
├─ source network
├─ device state
└─ risk score
```

This makes ABAC extremely expressive.

It can also make authorization increasingly look like a distributed query.

---

# ReBAC: authorization as graph data

Relationship-Based Access Control takes another interesting step.

Many real application domains aren't naturally described by flat attributes.

They contain actual relationships:

```text
Alice
  │ member
  ▼
Team A
  │ owns
  ▼
Project X
  │ contains
  ▼
Folder F
  │ contains
  ▼
Document D
```

The authorization question becomes:

> Is there an allowed relationship path from Alice to Document D?

A Zanzibar-like system might store relationship tuples conceptually like:

```text
Alice member TeamA
TeamA owner ProjectX
FolderF parent ProjectX
DocumentD parent FolderF
```

along with a relatively small model defining how relations compose.

Authorization then resembles recursive graph evaluation:

```text
Alice
  → member
Team A
  → owner
Project X
  → parent-of
Folder F
  → parent-of
Document D
```

This makes ReBAC feel almost like:

> **recursive, typed, composable ACLs**

There is still policy, because the system must define which relationships imply others.

But much more of the authorization meaning now lives in structured data.

---

## Why ReBAC?

It is tempting to think of ReBAC as a reaction to ABAC being computationally expensive.

That is only part of the story.

The deeper problem is that application authorization is frequently **relational by nature**.

Consider:

```text
users
teams
organizations
projects
folders
documents
owners
members
guests
parents
delegates
```

You can flatten these into attributes:

```text
user.project = X
document.project = X
```

but eventually you're encoding a graph inside a pile of attributes.

And generic ABAC can introduce its own operational problems:

```text
Where does this attribute come from?

How fresh is it?

Which service must the PDP query?

What if two attributes disagree?

Why exactly was Alice allowed?

Which users would lose access if this relationship changed?
```

ReBAC promotes the relationships themselves into first-class authorization data.

So one useful characterization is:

```text
ABAC

authorization ≈ policy evaluation problem


ReBAC

authorization ≈ graph/data query problem
```

---

# A full Linux example

The Linux kernel is useful because it contains several of these models simultaneously.

Consider:

```text
open("/srv/acme/report.txt", O_RDONLY)
```

At a high level, the kernel first has a **subject**:

```text
process credentials
├─ UID / GID
├─ supplementary groups
├─ Linux capabilities
├─ LSM security context
└─ namespace context
```

and must resolve an **object**:

```text
"/srv/acme/report.txt"
          │
          ▼
pathname resolution
          │
          ▼
mount → dentry → inode
```

The resulting filesystem object has state such as:

```text
inode
├─ owner UID
├─ group GID
├─ mode bits
├─ POSIX ACL
└─ LSM security label
```

Conceptually:

```text
                    open("/srv/acme/report.txt")

                               │

              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼

       SUBJECT STATE                      OBJECT STATE

       struct cred                        pathname
       ───────────                           ↓
       UID / GID                       mount/dentry/inode
       groups                                │
       Linux caps                            ├─ UID/GID
       LSM context                           ├─ mode
       namespaces                            ├─ ACL
                                             └─ LSM label

              │                                 │
              └────────────────┬────────────────┘
                               ▼

                        AUTHORIZATION
```

And several different policy mechanisms can participate.

---

## Unix DAC

Classic Unix permissions use:

```text
subject:
    UID
    groups

object:
    owner UID
    group GID
    mode
```

For example:

```text
report.txt

owner = alice
group = engineering
mode  = rw-r-----
```

This is essentially a tiny fixed-layout ACL.

---

## POSIX ACL

The file can carry a more explicit ACL:

```text
report.txt:

alice        → rw
bob          → r
engineering  → r
```

This is straightforward object-oriented ACL authorization:

```text
object → subjects + permissions
```

---

## Linux capabilities

Linux also gives the process privilege bits such as:

```text
CAP_DAC_OVERRIDE
CAP_NET_ADMIN
CAP_SYS_ADMIN
```

These modify what the subject is allowed to do.

But the terminology here is unfortunate:

> **Linux "capabilities" are not object capabilities.**

A Linux capability such as:

```text
CAP_DAC_OVERRIDE
```

is a broad privilege associated with a process.

Conceptually:

```text
process
   │
   └── CAP_DAC_OVERRIDE
          ↓
   broad authority to bypass
   certain filesystem checks
```

An object capability is instead something closer to:

```text
process
   │
   └── fd 7
          ↓
   this particular open file
```

Linux capability bits are therefore still largely part of the process's **ambient credentials**.

---

# SELinux: MAC, Type Enforcement, RBAC, and labels

SELinux adds another authorization layer through Linux Security Modules.

A process might carry:

```text
system_u:system_r:backup_t:s0
```

and a file:

```text
system_u:object_r:finance_file_t:s0
```

The most important part of ordinary SELinux authorization is often the **type**.

Conceptually:

```text
subject type = backup_t
object type  = finance_file_t
action       = read
```

and policy might say:

```text
allow backup_t finance_file_t:file read;
```

So:

```text
subject type
      +
object type
      +
operation
      ↓
SELinux policy
      ↓
allow / deny
```

This resembles ABAC structurally because the decision is based on properties of both subject and object.

But SELinux is better described specifically as **label-based mandatory access control**, particularly Type Enforcement, rather than as a generic ABAC system.

SELinux also has an RBAC component:

```text
SELinux user
      ↓
     role
      ↓
    domain
```

For example:

```text
Alice
  ↓
staff_r
  ↓
backup_t
```

The role constrains which execution domains a user can enter.

Actual access to objects is then largely governed by Type Enforcement.

So SELinux combines several ideas:

```text
SELinux
├─ mandatory access control
├─ security labels
├─ Type Enforcement
├─ RBAC
└─ optional MLS/MCS constraints
```

---

# Where is ReBAC in Linux?

Mostly, it isn't.

Linux certainly contains relationships:

```text
process → supplementary group
process → user namespace
process → cgroup → parent cgroup
file → mount → filesystem
```

But Linux does not expose a general authorization engine that asks things like:

```text
process
   → member-of container
   → owned-by project
   → belongs-to tenant
   → permitted-on filesystem
   → contains file
```

and recursively searches that relationship graph.

Why?

Partly because the kernel's authorization domain is much simpler.

Application-level systems contain semantically rich relationships:

```text
employee
team
organization
project
folder
document
guest
owner
delegate
```

Kernel objects are much lower-level:

```text
task
inode
socket
device
namespace
```

The relationships between those objects are often implementation structure rather than business authorization semantics.

There is also an important performance difference.

Kernel checks occur on extremely hot paths:

```text
open
read
write
send
recv
signal
mmap
```

A local comparison involving already-loaded credentials and labels is much easier to make fast and predictable than arbitrary graph traversal.

---

# Authorization is a consistency problem

Now return to the original model:

```text
authorize(
    subject,
    object,
    action,
    policy,
    context
)
```

Each of those inputs can be mutable.

More accurately:

```text
subject reference ──resolve──► S

object reference  ──resolve──► O

authorization DB ──query─────► P

environment ─────────────────► C
```

Then:

```text
authorize(S, O, action, P, C)
```

followed eventually by:

```text
perform operation
```

Conceptually, authorization starts looking like a transaction:

```text
BEGIN

S = resolve(subject)
O = resolve(object)
P = read_authorization_state()

assert authorize(S, O, P)

perform_operation(S, O)

COMMIT
```

And now a familiar systems question appears:

> Were all of these facts true at the same logical moment?

This connects authorization directly to classic concurrency and distributed-system problems:

```text
stale reads
race conditions
non-atomic updates
snapshot consistency
cache invalidation
revocation latency
TOCTOU
```

---

# TOCTOU problem 1: object binding

The classic example is pathname resolution.

```text
t0:

check("/tmp/foo")
        │
        ▼
      inode A


        path changes


t1:

open("/tmp/foo")
        │
        ▼
      inode B
```

The object that was checked isn't the object that gets used.

The problem is the repeated indirection:

```text
path → object
```

A file descriptor fixes much of this problem because the path is resolved once:

```text
"/tmp/foo"
      │
      ▼
   inode A
      │
      ▼
    fd 7
```

Later:

```text
read(7)
```

continues using the bound file object rather than resolving the pathname again.

---

# TOCTOU problem 2: subject or authority binding

There is a symmetrical issue on the subject side.

Identity or credentials can themselves be an indirection.

Conceptually:

```text
ambient context
      │
      ▼
current subject/authority
```

Suppose a check occurs using one credential context, but the operation later executes with another.

Then:

```text
CHECK

context ──► authority A


USE

context ──► authority B
```

The object may be identical, but the authority being exercised changed.

This gives us a useful symmetry:

```text
pathname
    = indirect reference to an object

ambient credentials
    = indirect reference to authority
```

Both require resolution.

Both can potentially change.

---

# A third problem: authorization state itself changes

There is also a different class of problem.

Suppose neither subject nor object changes.

At `t0`:

```text
Alice
  │ member
  ▼
Engineering
  │ viewer
  ▼
Document D
```

so:

```text
authorize(Alice, D, read) = allow
```

At `t1`, Alice is removed from Engineering:

```text
Alice   ✕──► Engineering
```

Now:

```text
authorize(Alice, D, read) = deny
```

This isn't a subject-binding race.

It isn't an object-binding race.

The underlying **authorization database changed**.

ABAC has the same issue:

```text
t0:
device.trusted = true

t1:
device.trusted = false
```

So authorization has at least three independently mutable inputs:

```text
1. subject binding
2. object binding
3. policy / relationship / contextual state
```

---

# Capabilities as materialized authorization decisions

Now consider what happens when we stop recomputing those inputs for every operation.

Suppose:

```text
subject
   +
object
   +
policy
   +
context
      ↓
 authorization
      ↓
    allow
```

Instead of throwing away that answer, we produce:

```text
capability(object, rights)
```

We have turned the result of an authorization query into an object.

This creates two distinct phases.

### Authority acquisition

```text
subject + object + policy + context
                 ↓
             authorize
                 ↓
             capability
```

### Authority exercise

```text
capability
    ↓
 operation
```

The second phase no longer needs to reconstruct the original authorization query.

A useful analogy is a database **materialized view**.

```text
authorization policy
        ≈ query

capability
        ≈ materialized query result
```

---

# Linux file descriptors are a good example

Return to:

```text
open("/srv/acme/report.txt", O_RDONLY)
```

Before the call succeeds:

```text
pathname
+
process credentials
+
inode metadata
+
ACL
+
LSM policy
        ↓
    authorization
```

If access is allowed:

```text
fd = 7
```

Now the program can do:

```text
read(7)
read(7)
read(7)
fstat(7)
mmap(...)
```

without repeatedly asking:

```text
What pathname did this come from?

Who owns it now?

What path would resolve to it now?

Which ACL entry originally allowed the open?
```

The FD binds to an already-open file object.

So Linux effectively moves from:

```text
ambient credentials
+
object name
+
policy evaluation
```

to:

```text
explicit handle
```

at the `open()` boundary.

That is extremely capability-like.

---

# But capabilities create a new problem: revocation

Materialization avoids repeated lookup.

But what if the source data changes?

At `t0`:

```text
Alice member Engineering
Engineering viewer Document D

        ↓

allow

        ↓

capability(D, read)
```

At `t1`:

```text
Alice removed from Engineering
```

The source-of-truth authorization relation now says Alice should no longer have access.

But Alice may still possess:

```text
capability(D, read)
```

This isn't necessarily a TOCTOU vulnerability.

It may simply be the semantics of the grant:

> Authority remains valid until the capability is revoked, closed, destroyed, or expires.

The problem is better described as:

```text
revocation
authorization staleness
materialized-authority staleness
```

This is the classic tradeoff:

```text
LIVE POLICY                     MATERIALIZED AUTHORITY
EVALUATION

fresh state                     stable authority
easy revocation                 cheap repeated use
dynamic context                 fewer lookups
more dependencies               easy delegation
more race surfaces              harder invalidation
```

Once a capability system adds:

```text
revocation list lookup
```

on every use, it begins to recover some of the live-state dependency it was trying to avoid.

Short-lived capabilities are one common compromise.

---

# Ambient authority

Materialization alone, however, isn't the deepest property of capability systems.

Consider ordinary Unix:

```text
open("/etc/shadow")
```

The call explicitly supplies an **object name**.

It does not explicitly supply the authority.

The kernel implicitly uses the process's surrounding security context:

```text
EUID
groups
Linux capability bits
LSM context
...
```

So conceptually:

```text
explicit object designation
          +
implicit ambient authority
          ↓
      authorization
```

The authority is **ambient** because code does not need to explicitly name or receive it.

Any code executing inside the process can potentially ask the OS:

```text
Can "whoever I currently am" access this object?
```

---

# Object capabilities remove that implicit authority lookup

With an object capability:

```text
read(fd)
```

the reference itself both:

1. identifies the object;
2. conveys authority over it.

This is often called the fusion of **designation and authority**.

Compare:

```text
PATH / IDENTITY MODEL

"/foo"
   │
   └── designates object

process credentials
   │
   └── separately provide authority
```

with:

```text
CAPABILITY MODEL

capability-to-foo
       │
       ├── designates foo
       └── conveys authority to foo
```

The program no longer asks:

```text
"Given my current identity, may I access foo?"
```

Instead it says:

```text
"Use this authority I explicitly possess."
```

---

# Why ambient authority matters

Suppose Alice can access:

```text
~/documents
~/photos
~/.ssh
AWS credentials
company source code
```

Alice calls:

```text
convert_image(input)
```

If the image-processing library executes inside Alice's process, it inherits Alice's ambient authority.

It can potentially do:

```text
open("~/.ssh/id_ed25519")
```

even though Alice never intended to delegate access to the SSH key.

The policy engine may behave perfectly:

```text
Does Alice have access to ~/.ssh/id_ed25519?

yes
```

The problem is that the wrong component is able to **exercise Alice's authority**.

A capability-oriented design instead gives the library:

```text
input_image_fd
output_image_fd
```

and nothing else.

```text
caller
  │
  ├── cap(input)
  └── cap(output)
          │
          ▼
       library
```

The library cannot simply name Alice's SSH key and fall back to Alice's broader identity.

So ACL, RBAC, ABAC, and ReBAC mainly answer:

> **Should this subject have this authority?**

Capability discipline adds a different question:

> **Which authority has this particular piece of code actually been given?**

---

# Sandboxing as removing ambient authority

This gives a useful way to understand sandboxing.

A normal process may ambiently inherit access to:

```text
filesystem
network
environment variables
SSH credentials
cloud credentials
local sockets
devices
```

A sandbox tries to remove those ambient powers:

```text
normal process

filesystem
network
SSH keys
cloud credentials
sockets
devices

        ↓ sandbox

restricted process

workspace only
specific network endpoint
specific socket
specific secret
```

Then the necessary authority is selectively reintroduced.

From a capability perspective, sandboxing can therefore be understood as:

> **removing ambient authority and replacing it with explicit authority.**

This is particularly relevant to untrusted plugins, automation agents, and LLM agents.

---

# Rich policy and capabilities are complementary

It is therefore misleading to frame the choice as:

```text
ReBAC vs capabilities
```

or:

```text
ABAC vs capabilities
```

They can operate at different stages.

A sophisticated authorization service can decide whether authority should be issued:

```text
user
 │
 ▼
RBAC / ABAC / ReBAC
 │
 ▼
authorization decision
 │
 ▼
short-lived capability
```

Then the capability can be used cheaply on the data path:

```text
worker
   │ capability
   ▼
resource
```

This gives:

```text
CONTROL PLANE

rich, dynamic policy
        ↓
authority acquisition


DATA PLANE

explicit capability
        ↓
cheap repeated exercise
```

This is remarkably similar to what happens with Linux file descriptors.

---

# Three different questions

This gives us a cleaner taxonomy than treating every acronym as a competing authorization system.

## 1. How is the access relation represented?

```text
ACL
    object → subjects

Capability list
    subject → objects

RBAC
    subject → role → permissions

ABAC
    attributes + predicate → permissions

ReBAC
    relationship graph + composition → permissions
```

---

## 2. When is authorization evaluated?

At one extreme:

```text
every operation
     ↓
consult latest state
```

At the other:

```text
authority acquisition
       ↓
materialize result
       ↓
capability
       ↓
repeated use
```

This is the freshness-versus-revocation tradeoff.

---

## 3. How is authority exercised?

At one extreme:

```text
ambient authority

"Use whatever authority my current
identity/context happens to have."
```

At the other:

```text
explicit authority

"Use exactly this authority-bearing reference."
```

This is where object capabilities are most distinctive.

---

# And what can change between check and use?

Finally, there are several independent sources of instability:

```text
1. SUBJECT

check:
    context → subject A

use:
    context → subject B


2. OBJECT

check:
    pathname → object A

use:
    pathname → object B


3. AUTHORIZATION STATE

check:
    Alice member Engineering

use:
    relationship removed


4. ENVIRONMENT

check:
    device trusted

use:
    device untrusted
```

Repeated policy evaluation keeps those inputs fresh but repeatedly exposes the system to resolution and consistency problems.

Materializing authority stabilizes more of them, but introduces revocation and staleness.

---

# Authorization as a systems problem

The deeper lesson is that authorization is not merely about writing better policy languages.

It is also a state-management problem.

The system must resolve:

```text
Who is acting?
What object is being referenced?
What policy or relationships currently apply?
What contextual facts matter?
```

and somehow ensure that the answer remains meaningful when the operation actually occurs.

ACLs, RBAC, ABAC, and ReBAC can be understood as different ways of organizing or deriving the underlying access relation:

```text
ACL
    store it

Capabilities
    transpose/store it from the other side

RBAC
    factor it

ABAC
    compute it

ReBAC
    represent it as a graph and recursively derive it
```

Capabilities then introduce another architectural move:

```text
resolve subject
+
resolve object
+
consult authorization state
+
evaluate policy
        ↓
      allow
        ↓
materialize authority
        ↓
explicit capability
```

This collapses a dynamic multi-input authorization query into a stable authority-bearing reference.

That reduces repeated indirection, makes delegation explicit, and limits ambient authority.

But it also means the system is no longer continuously consulting its source of truth.

And therefore the same tradeoff appears that we see everywhere else in systems design:

> **Do we keep querying mutable state, or do we materialize a result and deal with invalidation?**

Authorization turns out to be another version of that very old problem.
