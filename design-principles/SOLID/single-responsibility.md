Here’s a textbook-style SRP write-up you can keep as a reference, with the “actor” framing, cohesion note, scaling guidance, and a Python-friendly example included.  

## SRP definition (actor-based)

The Single-Responsibility Principle says a module (class, function, or file) should have **one** reason to change—meaning it should be responsible to “one, and only one, actor” (a person/team that requests changes). [en.wikipedia](https://en.wikipedia.org/wiki/Single-responsibility_principle)
This is stricter and more practical than “does one thing,” because it ties design to who creates change pressure. [e4developer](https://www.e4developer.com/2018/10/04/single-responsibility-principle-do-you-know-the-real-one/)

## What SRP is really optimizing

SRP is mainly about keeping changes localized: when one actor’s requirements change, you shouldn’t have to touch code owned by other actors. [e4developer](https://www.e4developer.com/2018/10/04/single-responsibility-principle-do-you-know-the-real-one/)
This tends to increase cohesion (related behavior changes together) and reduce “shotgun surgery” (small requirement → many unrelated edits). [en.wikipedia](https://en.wikipedia.org/wiki/Single-responsibility_principle)

## When SRP pays off (and when it doesn’t)

SRP is a scaling tool: it pays dividends when multiple people work in the same area, ownership boundaries matter, and the codebase is expected to evolve often.  
On small, stable code, aggressively splitting things “because SRP” can add indirection and make the simplest path harder to follow.

## The practical SRP test (2 questions)

Use SRP when a change request would otherwise force you to edit multiple unrelated places.

- “If this requirement changes, how many unrelated places do I have to touch?”  
- “Who would request this change—same actor or different actors?” [e4developer](https://www.e4developer.com/2018/10/04/single-responsibility-principle-do-you-know-the-real-one/)

If the second answer is “different actors,” that’s your strongest signal you’re mixing responsibilities. [e4developer](https://www.e4developer.com/2018/10/04/single-responsibility-principle-do-you-know-the-real-one/)

## What SRP is not

SRP is not “one method per class,” and it’s not “classes are better than functions.”  
SRP applies equally to functions, modules (files), packages, and services; the boundary is whatever unit you deploy, test, review, and assign ownership to. [en.wikipedia](https://en.wikipedia.org/wiki/Single-responsibility_principle)

## Example: SRP violation (mixed actors)

```python
class Invoice:
    def calculate_total(self): ...
    def save_to_database(self): ...
    def send_email(self): ...
```

This mixes at least three axes of change: business rules, persistence, and communication, which often map to different actors/teams. [e4developer](https://www.e4developer.com/2018/10/04/single-responsibility-principle-do-you-know-the-real-one/)

## Example: SRP-respecting OO design (aligned actors)

```python
class Invoice:
    def __init__(self, items):
        self.items = items

    def calculate_total(self):
        return sum(item.price * item.quantity for item in self.items)

    def apply_discount(self, discount): ...
    def is_overdue(self): ...


class InvoiceRepository:
    def save(self, invoice): ...
    def find_by_id(self, invoice_id): ...
    def mark_as_paid(self, invoice_id): ...


class InvoiceEmailer:
    def send_new_invoice(self, invoice, customer): ...
    def send_payment_reminder(self, invoice, customer): ...
    def send_receipt(self, invoice, customer): ...
```

Now each unit is “pulled” primarily by one actor: finance/pricing logic, DB concerns, and billing/notifications. [e4developer](https://www.e4developer.com/2018/10/04/single-responsibility-principle-do-you-know-the-real-one/)
This separation also makes testing cheaper: you can unit-test totals without a database, and you can mock sending email without loading business rules.

## Pythonic SRP: prefer module boundaries + pure functions

In Python, SRP often lands best at the *module* level: group code by “reason to change,” and keep the core business logic pure (no I/O).  

```python
# invoice_domain.py  (Finance actor: pricing rules change here)
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
# invoice_repo.py  (DB actor: storage details change here)
class InvoiceRepository:
    def __init__(self, conn):
        self._conn = conn

    def save(self, invoice_id: str, items_json: str, total: float) -> None:
        # SQL, transactions, schema decisions live here
        ...

    def load(self, invoice_id: str) -> dict:
        ...
```

```python
# invoice_email.py  (Billing/Comms actor: templates + providers change here)
class InvoiceEmailer:
    def __init__(self, mailer):
        self._mailer = mailer

    def send_invoice(self, *, to: str, invoice_id: str, total: float) -> None:
        # provider integration, templates, retry policy live here
        ...
```

A good rule of thumb: if a function needs network/database access, it’s probably not the same responsibility as the domain calculation it supports.

## SRP and architecture (from classes to services)

The same “actor” rule is often how teams discover clean boundaries for components, packages, and eventually microservices: you separate when different groups need independent change cadence and independent deployment safety. [e4developer](https://www.e4developer.com/2018/10/04/single-responsibility-principle-do-you-know-the-real-one/)
Conversely, splitting into separate services too early can recreate the same coupling via network calls—so use SRP to clarify *ownership and change reasons*, not as an automatic “split everything” trigger.

## Quick checklist (use during code review)

- Does this unit mix domain rules with I/O (DB, HTTP, email, filesystem)?  
- Would a DB schema change force editing pricing logic (or vice versa)?  
- Are there multiple actors who would file issues against the same module? [e4developer](https://www.e4developer.com/2018/10/04/single-responsibility-principle-do-you-know-the-real-one/)
- Can I unit-test domain behavior without mocks for external systems?
