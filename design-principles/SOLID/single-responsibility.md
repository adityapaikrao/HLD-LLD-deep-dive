# The Single Responsibility Principle

---

The Single Responsibility Principle (SRP) is about ensuring that a module has only one reason to change — meaning its behaviour is driven by a single actor, so that a change request from one team never forces edits to code owned by another.

---

## Definition

Robert C. Martin introduced the Single Responsibility Principle as the first of the SOLID principles. His original formulation is deceptively simple:

> **A module should have one, and only one, reason to change.**

Martin later sharpened this in *Clean Architecture* (2017) with an actor-based restatement:

> **A module should be responsible to one, and only one, actor.**

The word *actor* is doing the real work here. An actor is a person or team that creates change pressure — the finance team that owns pricing rules, the platform team that owns database schemas, the communications team that owns notification templates. "Reason to change" is not about technical categories like persistence or validation; it is about *who would file the ticket*. If two different actors can independently demand changes to the same class, that class is violating SRP regardless of how focused it looks on the surface.

This is stricter and more practical than the informal gloss of "does one thing." A class can do one thing and still serve two masters.

---

## Historical Context

SRP has its roots in the concept of *cohesion*, introduced by Larry Constantine in the late 1960s and expanded by Tom DeMarco in *Structured Analysis and System Specification* (1979). High cohesion — grouping things that change together — was a design goal long before SOLID existed. What Martin added was the *actor* lens: cohesion should be measured not by functional similarity but by the organisational source of change pressure.

This shift matters because it moves SRP from an aesthetic judgment ("these methods feel related") to a structural one ("these methods are pulled by the same team"). It also explains why SRP scales: from functions, to classes, to modules, to microservices, the same question applies at every level — *who owns this, and who can demand it change?*

Martin has noted that SRP is the principle most frequently misunderstood. The common misreading — that a class should do exactly one thing — leads to over-fragmentation: microscopic classes with a single method, indirection for its own sake, and code that is harder to follow than the violation it replaced. The actor framing guards against this by anchoring the decision in real organisational dynamics rather than subjective judgments about granularity.

---

## What Goes Wrong Without It

Consider the domain we will use throughout this write-up: **an invoicing system used by a finance team, a database team, and a billing communications team.**

Without SRP, all three concerns end up in a single `Invoice` class. This also seems harmless at first — invoices involve totals, storage, and notifications, so putting them together feels natural. Then the finance team changes the discount model. The database team migrates to a new schema. The communications team switches email providers. Each change lands in the same file, touching code the other teams depend on.

Here is what the `Invoice` class pays for that mixing:

- **Fragility:** A schema migration can accidentally break discount logic in the same edit.
- **Rigidity:** Changing the email provider requires opening a file that owns financial rules.
- **Untestability:** You cannot unit-test total calculations without a database connection or mail server.
- **Merge conflicts:** Two teams working on unrelated requirements collide in the same file.

SRP is the structural answer to all four problems, because it aligns code ownership with organisational ownership. When one actor's requirements change, the edit stays local to that actor's module.

---

## The Violation: Anti-Pattern First

Here is an `Invoice` class written without SRP. Three actors' concerns are collapsed into one unit.

```python
class Invoice:
    def __init__(self, items: list, customer_email: str):
        self.items = items
        self.customer_email = customer_email

    # Finance actor: pricing and business rules
    def calculate_total(self) -> float:
        return sum(item["price"] * item["quantity"] for item in self.items)

    def apply_discount(self, discount_pct: float) -> float:
        return self.calculate_total() * (1.0 - discount_pct / 100.0)

    # DB team actor: persistence and schema
    def save_to_database(self, conn) -> None:
        conn.execute(
            "INSERT INTO invoices (total) VALUES (?)",
            (self.calculate_total(),)
        )

    # Billing/comms actor: notification templates and providers
    def send_email(self, smtp_host: str) -> None:
        print(f"[{smtp_host}] Sending invoice to {self.customer_email}")
```

The three axes of change are visually easy to spot here, but in a real codebase they are typically interleaved across hundreds of lines. An ASCII responsibility diagram makes the coupling explicit:

```
                        Invoice
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    Finance actor      DB actor       Comms actor
  (pricing rules)   (persistence)  (notifications)
```

One class, three owners. Because `save_to_database` and `send_email` both call `calculate_total()`, a refactor of the pricing logic risks breaking persistence and delivery behaviour in the same pass. And because everything lives together, you cannot unit-test discount logic without also importing database and SMTP dependencies.

---

## The Fix: Applying the Principle

The fix splits the class along actor boundaries. Each unit is now pulled by exactly one team. Crucially, where one module needs to communicate with another — the repository talking to a database, the emailer talking to a mail provider — those dependencies cross actor boundaries and should therefore follow DIP: depend on an abstraction, not a concrete type. SRP tells you *where* to draw the boundary; DIP tells you *how* to connect across it.

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class LineItem:
    sku: str
    price: float
    quantity: int


# Finance actor: pricing and business rules only
class Invoice:
    def __init__(self, invoice_id: str, items: list[LineItem]):
        self.invoice_id = invoice_id
        self.items = items

    def calculate_total(self) -> float:
        return sum(item.price * item.quantity for item in self.items)

    def apply_discount(self, discount_pct: float) -> float:
        return self.calculate_total() * (1.0 - discount_pct / 100.0)

    def is_overdue(self, due_date, today) -> bool:
        return today > due_date


# Abstraction owned by the DB actor's consumer needs —
# InvoiceRepository defines what it needs from a connection,
# not what any particular database driver happens to provide.
class DatabaseConnection(Protocol):
    def execute(self, query: str, params: tuple) -> Any: ...
    def fetchone(self) -> dict: ...


# DB team actor: persistence and schema details only.
# Depends on DatabaseConnection (abstraction), not a concrete driver.
class InvoiceRepository:
    def __init__(self, conn: DatabaseConnection):
        self._conn = conn

    def save(self, invoice: Invoice) -> None:
        self._conn.execute(
            "INSERT INTO invoices (id, total) VALUES (?, ?)",
            (invoice.invoice_id, invoice.calculate_total())
        )

    def find_by_id(self, invoice_id: str) -> dict:
        self._conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        )
        return self._conn.fetchone()

    def mark_as_paid(self, invoice_id: str) -> None:
        self._conn.execute(
            "UPDATE invoices SET paid = 1 WHERE id = ?", (invoice_id,)
        )


# Abstraction owned by the emailer's consumer needs —
# InvoiceEmailer defines what it needs from a mail provider.
class Mailer(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...


# Billing/comms actor: notification templates and provider details only.
# Depends on Mailer (abstraction), not a concrete SMTP client.
class InvoiceEmailer:
    def __init__(self, mailer: Mailer):
        self._mailer = mailer

    def send_new_invoice(self, invoice: Invoice, customer_email: str) -> None:
        self._mailer.send(
            to=customer_email,
            subject=f"Invoice {invoice.invoice_id}",
            body=f"Your total is £{invoice.calculate_total():.2f}."
        )

    def send_payment_reminder(self, invoice: Invoice, customer_email: str) -> None:
        self._mailer.send(
            to=customer_email,
            subject="Payment reminder",
            body=f"Invoice {invoice.invoice_id} is overdue."
        )

    def send_receipt(self, invoice: Invoice, customer_email: str) -> None:
        self._mailer.send(
            to=customer_email,
            subject="Payment received",
            body=f"Thanks — invoice {invoice.invoice_id} is paid."
        )
```

The responsibility and dependency diagram now reflects both principles together:

```
  Invoice            InvoiceRepository        InvoiceEmailer
  (Finance)              (DB team)             (Comms team)
      │                      │                      │
      ▼                      ▼                      ▼
 pricing rules       DatabaseConnection           Mailer
                       (abstraction)           (abstraction)
                            ▲                      ▲
                            │                      │
                     SqliteConnection        SmtpMailer
                     (low-level detail)    (low-level detail)
```

One unit per actor, and every cross-boundary dependency points at an abstraction. A database migration touches only `InvoiceRepository` and whatever implements `DatabaseConnection`. Switching email providers touches only the `Mailer` implementation — `InvoiceEmailer` never changes. The finance team iterates on discount logic without risk of disturbing either.

---

## Mechanics: Cohesion, Actor Alignment, and the Two Questions

SRP is enforced by asking two questions during design and code review:

- *If this requirement changes, how many unrelated places do I have to touch?*
- *Who would request this change — same actor or different actors?*

The second question is the stronger signal. If two methods in the same class would be changed by different teams in response to unrelated requirements, those methods belong in different units. The first question catches the consequence: the "shotgun surgery" smell, where a single small requirement ripples into edits across multiple unrelated files.

**Cohesion** is the underlying metric SRP is optimising. High cohesion means that everything inside a module changes for the same reason — it is pulled by the same actor. Low cohesion means the module is a bag of loosely related concerns, each with its own change trajectory. Martin's actor framing makes cohesion measurable: you do not need to make a subjective call about whether two methods "feel related"; you ask whether the same team owns both.

It is worth being explicit about what SRP is not optimising for. It is not minimising the number of methods per class, and it is not a mandate to split every function into its own file. A class with fifteen methods can satisfy SRP perfectly if all fifteen are owned by the same actor. A class with two methods can violate SRP if those two methods answer to different teams. Granularity follows from ownership, not from aesthetics.

Once you have separated modules by actor, DIP governs how they communicate. The protocols `DatabaseConnection` and `Mailer` are not arbitrary interfaces — they are expressions of what each consumer *needs*, defined in the consumer's vocabulary. `InvoiceRepository` does not reach for a `psycopg2` connection; it defines the minimal surface it requires and lets the composition root wire in a concrete driver. This is the direct collaboration between SRP and DIP: SRP creates the boundaries, DIP keeps those boundaries clean.

---

## A Pythonic Alternative: Module-Level SRP with Pure Functions

In Python, SRP often lands most naturally at the *module* level rather than the class level. Python's module system is a first-class organisational unit: a `.py` file has its own namespace, its own import boundary, and its own testability surface. Grouping by reason to change at the module level — rather than wrapping everything in classes — is idiomatic and effective.

The additional Python-specific habit worth cultivating is keeping domain logic *pure*: no I/O, no side effects, just data in and data out. This makes the finance actor's code trivially testable and completely decoupled from infrastructure without requiring any mocks or abstractions at all — purity is a stronger guarantee than an interface.

```python
# invoice_domain.py  — Finance actor: pricing rules change here
from dataclasses import dataclass

@dataclass(frozen=True)
class LineItem:
    sku: str
    unit_price: float
    quantity: int

def calculate_total(items: list[LineItem]) -> float:
    return sum(i.unit_price * i.quantity for i in items)

def apply_discount(total: float, discount_pct: float) -> float:
    return total * (1.0 - discount_pct / 100.0)
```

```python
# invoice_repo.py  — DB actor: storage and schema details change here
from typing import Any, Protocol

class DatabaseConnection(Protocol):
    def execute(self, query: str, params: tuple) -> Any: ...
    def fetchone(self) -> dict: ...

class InvoiceRepository:
    def __init__(self, conn: DatabaseConnection):
        self._conn = conn

    def save(self, invoice_id: str, total: float) -> None:
        self._conn.execute(
            "INSERT INTO invoices (id, total) VALUES (?, ?)",
            (invoice_id, total)
        )

    def load(self, invoice_id: str) -> dict:
        self._conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        )
        return self._conn.fetchone()
```

```python
# invoice_email.py  — Comms actor: templates and providers change here
from typing import Protocol

class Mailer(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...

class InvoiceEmailer:
    def __init__(self, mailer: Mailer):
        self._mailer = mailer

    def send_invoice(self, *, to: str, invoice_id: str, total: float) -> None:
        self._mailer.send(
            to=to,
            subject=f"Invoice {invoice_id}",
            body=f"Your total is £{total:.2f}."
        )
```

Each module is owned by one actor and imports nothing from the other two. The `DatabaseConnection` and `Mailer` protocols live inside the modules that consume them — the consumer owns the contract, which is precisely what DIP prescribes. A good rule of thumb: if a function needs network or database access, it is almost certainly not the same responsibility as the domain calculation it supports.

---

## SRP and Architecture: From Classes to Services

The same actor question that guides class design also guides larger architectural decisions. Teams often discover clean component and service boundaries by asking it repeatedly at increasing scale: which packages would different teams want to deploy independently? Which services have different change cadences?

A finance rule change should not require redeploying the notification service. A database migration should not require redeploying the pricing engine. SRP, applied at the service level, is how those boundaries become explicit rather than accidental. And at every level of that architecture, DIP governs the seams: inter-service communication goes through contracts — API schemas, message formats, event definitions — that neither service owns unilaterally, for exactly the same reason that `InvoiceRepository` does not reach directly for a `psycopg2` connection.

The important caveat is that splitting too early can recreate the same coupling via network calls. A microservice that must synchronously call three other services to complete a single business operation has not eliminated the coupling — it has made it slower and harder to observe. Use SRP to clarify *ownership and change reasons*, not as an automatic trigger to split everything. The principle scales up; the judgment about when to apply it must scale with it.

---

## Practical Rule of Thumb

> **If a change request from one team forces you to open a file owned by another team, SRP has been violated. If crossing a module boundary requires importing a concrete type, DIP has been violated.**

The actor framing makes the first part concrete:

- If a database schema migration forces you to edit pricing logic, `Invoice` is mixing the finance and DB actors.
- If switching email providers requires touching discount calculation, the comms and finance actors are sharing a module.
- If your domain service imports `psycopg2`, `boto3`, or `smtplib`, infrastructure has leaked into policy.

Run this quick checklist during code review:

- Does this unit mix domain rules with I/O — database, HTTP, email, filesystem?
- Would a schema change force editing pricing logic, or vice versa?
- Are there multiple actors who could independently file issues against this module?
- Can I unit-test domain behaviour without mocks for external systems?
- Do cross-boundary dependencies point at abstractions, or at concrete types?

When you align code ownership with organisational ownership (SRP) and connect those owners through abstractions (DIP), you gain cheap unit tests, safe parallel development, pluggable infrastructure, and architectural clarity. Neither principle alone is sufficient: SRP without DIP produces well-separated modules that are still brittle at their seams; DIP without SRP produces clean interfaces inside a tangled monolith. Together, they give you boundaries that are both stable and independently evolvable.