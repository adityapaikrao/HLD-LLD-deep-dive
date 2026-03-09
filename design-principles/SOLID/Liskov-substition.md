# The Liskov Substitution Principle

## Definition

> *"If for each object o₁ of type S there is an object o₂ of type T such that for all programs P defined in terms of T, the behavior of P is unchanged when o₁ is substituted for o₂, then S is a subtype of T."*
> — Barbara Liskov, *Data Abstraction and Hierarchy*, 1987

In plain language: **any subclass must be usable wherever its parent class is expected, without the calling code needing to know the difference.** If you have to check what type something is before using it, or a subclass silently breaks a contract its parent established, you have violated LSP.

---

## Historical Context

Barbara Liskov introduced this principle at OOPSLA '87, later formalizing it with Jeannette Wing in 1994. At the time, inheritance was widely treated as a code-reuse mechanism. Liskov's insight was that inheritance is primarily a *behavioral contract* — and that a geometric "is-a" relationship does not automatically translate to a behavioral one. Robert Martin later popularized it as the "L" in SOLID, restating it as: *"subtypes must be substitutable for their base types."*

---

## Why It Matters

The purpose of polymorphism is to let calling code work against an abstraction and remain indifferent to which concrete implementation sits behind it. LSP is the guarantee that makes this safe. Without it, polymorphism becomes nominal — the calling code works against the abstraction in name only, and must in practice be written defensively around each subtype.

The damage is visible: `isinstance` checks, unexpected exceptions, and conditional branches that encode knowledge about subclass internals. New subtypes require auditing every call site. The abstraction stops doing its job.

The example used throughout is a **notification system**: a base `Notification` class with delivery channels — Email, SMS, Push. A `NotificationService` calls `.send()` on each. The polymorphic goal is that it never needs to know which channel it holds.

```
NotificationService
       │ uses
       ▼
  Notification  (ABC)
       ▲
       │
┌──────┼──────────────┐
│      │              │
Email  SMS            Push
```

---

## The Violation: Anti-Pattern First

```python
class Notification:
    def __init__(self, recipient: str, message: str):
        self.recipient = recipient
        self.message = message

    def send(self) -> None:
        raise NotImplementedError


class EmailNotification(Notification):
    def send(self) -> None:
        print(f"Emailing {self.recipient}: {self.message}")


class SMSNotification(Notification):
    def send(self) -> None:
        if len(self.message) > 160:
            raise ValueError("SMS messages cannot exceed 160 characters")
        print(f"Texting {self.recipient}: {self.message}")


class PushNotification(Notification):
    def __init__(self, recipient: str, message: str):
        super().__init__(recipient, message)
        self.device_token = None  # must be set separately after construction

    def send(self) -> None:
        if self.device_token is None:
            raise RuntimeError("Cannot send: no device token set")
        print(f"Pushing to {self.device_token}: {self.message}")
```

The calling code is forced to defend itself:

```python
def dispatch_all(notifications: list[Notification]) -> None:
    for notification in notifications:
        if isinstance(notification, SMSNotification):
            if len(notification.message) > 160:
                continue
        if isinstance(notification, PushNotification):
            if notification.device_token is None:
                continue
        notification.send()
```

Two behavioral violations are present. `SMSNotification.send()` raises a `ValueError` the parent's contract never declared. `PushNotification` requires post-construction setup before it is safe to use — callers of `Notification` have no reason to expect this. The `isinstance` branches are the symptom: the subtypes are not genuinely substitutable, so the calling code has internalized knowledge about each of them. Every new channel forces a revision of `dispatch_all`.

---

## The Fix: Applying the Principle

The contract `Notification` must establish:

- An instance is fully valid and ready to send immediately after construction.
- `send()` raises only `NotificationError` on failure — nothing else.
- No extra setup is required after construction.

Length constraints and token requirements are preconditions for a valid object. They belong in the constructor, not deferred to `send()`.

```python
from abc import ABC, abstractmethod


class NotificationError(Exception):
    pass


class Notification(ABC):
    def __init__(self, recipient: str, message: str):
        self.recipient = recipient
        self.message = message

    @abstractmethod
    def send(self) -> None:
        """Send the notification. Raises NotificationError on delivery failure."""
        ...


class EmailNotification(Notification):
    def send(self) -> None:
        print(f"Emailing {self.recipient}: {self.message}")


class SMSNotification(Notification):
    MAX_LENGTH = 160

    def __init__(self, recipient: str, message: str):
        if len(message) > self.MAX_LENGTH:
            raise ValueError(f"SMS message exceeds {self.MAX_LENGTH} characters.")
        super().__init__(recipient, message)

    def send(self) -> None:
        print(f"Texting {self.recipient}: {self.message}")


class PushNotification(Notification):
    def __init__(self, recipient: str, message: str, device_token: str):
        if not device_token:
            raise ValueError("device_token is required.")
        super().__init__(recipient, message)
        self.device_token = device_token

    def send(self) -> None:
        print(f"Pushing to {self.device_token}: {self.message}")
```

The calling code is now genuinely polymorphic:

```python
def dispatch_all(notifications: list[Notification]) -> None:
    for notification in notifications:
        try:
            notification.send()
        except NotificationError as e:
            print(f"Delivery failed for {notification.recipient}: {e}")
```

No `isinstance`. No type-specific branching. Adding a `SlackNotification` tomorrow requires zero changes to `dispatch_all`.

---

## How It Is Achieved Mechanically

### Encode preconditions in the constructor

An `SMSNotification` with a 300-character message is not a valid object — it should never exist. Constructing it and then failing at `.send()` defers a problem that could be caught immediately, and forces callers to handle it at the wrong layer.

### Use `ABC` and `@abstractmethod`

This makes the contract explicit and raises `TypeError` at instantiation time if a subclass forgets to implement `send()`, rather than silently failing later.

### Restrict the exception surface

Subclasses must raise `NotificationError` (or a declared subclass of it) on delivery failure — never raw, implementation-specific exceptions. A common real-world case is a network timeout leaking out of a push notification gateway. The fix is to catch it at the boundary and wrap it:

```python
import requests

class PushNotification(Notification):
    def __init__(self, recipient: str, message: str, device_token: str):
        if not device_token:
            raise ValueError("device_token is required.")
        super().__init__(recipient, message)
        self.device_token = device_token

    def send(self) -> None:
        try:
            requests.post(
                "https://push.example.com/send",
                json={"token": self.device_token, "message": self.message},
                timeout=5,
            )
        except requests.Timeout as e:
            raise NotificationError(
                f"Push delivery timed out for {self.recipient}"
            ) from e
```

Callers catching `NotificationError` are unaffected by the underlying transport. The `from e` clause preserves the original traceback for debugging without leaking the implementation detail into the contract.

### Honour the history constraint

Liskov and Wing's 1994 formalization includes a rule that is easy to overlook: a subclass must not introduce new methods that allow state mutations impermissible in the base class. The most common violation is subclassing an effectively immutable object to produce a mutable one. If `Notification` treats `recipient` and `message` as fixed at construction, a subclass that exposes setters for them breaks calling code that reasonably assumes those values are stable across the lifetime of the object. The fix is straightforward — do not expose mutation that the base class does not permit, and if mutability is genuinely needed, make the base class explicit about it.

### Method signature variance

LSP imposes formal rules on how overridden method signatures may vary. Return types must be **covariant** — a subclass may narrow the return type (returning a more specific type than the parent declared), but never widen it. Parameter types must be **contravariant** — a subclass may accept a broader argument type than the parent declared, but never a narrower one. Narrowing a parameter type is a violation because it means the subclass rejects inputs the parent's contract promised to accept.

In practice, Python does not enforce variance at runtime, but `mypy` and Pyright do. Violating these rules produces type errors that are often the first mechanical signal of an LSP violation in a statically-analysed codebase.

### Compose when inheritance would force a violation

If a subclass would need to weaken the contract — a no-op test double, or a wrapper that adds logging — composition is cleaner. `LoggedNotification` below wraps any `Notification` and honors the full contract:

```python
class LoggedNotification(Notification):
    def __init__(self, inner: Notification):
        self._inner = inner

    @property
    def recipient(self) -> str:
        return self._inner.recipient

    @property
    def message(self) -> str:
        return self._inner.message

    def send(self) -> None:
        print(f"[LOG] Sending to {self._inner.recipient}")
        self._inner.send()
```

This is what LSP, when internalized, tends to push you toward: asking *"is this genuinely a behavioral subtype?"* before reaching for inheritance, and preferring composition when the answer is no.

---

## A Pythonic Alternative: `Protocol`

Python's `typing.Protocol` offers structural subtyping — any class implementing the required methods satisfies the contract, without explicit inheritance:

```python
from typing import Protocol


class Sendable(Protocol):
    recipient: str
    message: str

    def send(self) -> None: ...
```

A `SlackNotification` that never inherits from `Notification` or `Sendable` still satisfies `Sendable` as long as it has the right shape. `dispatch_all` typed against `list[Sendable]` accepts it automatically.

| Characteristic | Abstract Base Class (`ABC`) | `Protocol` |
|---|---|---|
| Subtyping mechanism | Nominal — explicit inheritance required | Structural — matching shape is sufficient |
| Verification phase | Runtime, on instantiation | Static, via `mypy` / Pyright |
| Coupling | Subclasses must declare inheritance | No shared ancestry needed |
| Runtime safety net | Yes — `TypeError` without a type checker | No — silent at runtime without tooling |

Neither is universally superior. `ABC` gives you a runtime safety net that works regardless of tooling; `Protocol` gives you flexibility across module boundaries without coupling classes to a shared base. Both enforce the same behavioral promise — they differ only in when and how the enforcement fires.

---

## Rule of Thumb

> **If you are writing `isinstance` checks in code that is supposed to work against a base type, you are not using polymorphism — you are working around a broken inheritance hierarchy.**

The fix is almost always one of three things: move the precondition into the constructor so every instance is already valid; narrow the hierarchy by splitting responsibilities; or abandon inheritance in favor of composition or a structural protocol. LSP is the principle that tells you whether your abstraction is sound. Polymorphism is the goal. Interfaces, abstract base classes, and protocols are the tools that get you there.