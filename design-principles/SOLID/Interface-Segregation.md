# Interface Segregation Principle (ISP)

## 4. The Interface Segregation Principle

### Definition

> *"Clients should not be forced to depend upon interfaces they do not use."*
> — Robert C. Martin, *Agile Software Development: Principles, Patterns, and Practices* (2002)

Martin introduced this principle as the fourth of the five SOLID design guidelines. Its intent is deceptively simple: when you define the contract a class must fulfill, that contract should contain only what the fulfilling class actually needs. Forcing a class to implement methods it has no business knowing about is a form of coupling — a quiet tax paid every time the codebase evolves.

---

### Historical Context

The principle emerged from Martin's consulting work at Xerox in the early 1990s. The Xerox team had built a print-server job-scheduling system in which a single monolithic `Job` class implemented every operation the system could perform: printing, stapling, faxing, scanning, and more. Every new device driver — even a bare-bones printer with no fax capability — had to implement the full `Job` interface, leaving dozens of methods either empty or raising `NotImplementedError`. Changes to any part of the interface cascaded across all drivers, regardless of whether they were affected.

The lesson Martin drew was not merely about keeping interfaces small. It was about recognising that **a single wide interface serves no one well** — it couples every implementor to every capability, and it couples every caller to every implementor. ISP is the discipline that keeps those two kinds of coupling from spiralling together.

---

### Why It Matters — and What Goes Wrong Without It

The goal of good object-oriented design is **polymorphism**: the ability to treat different objects uniformly through a shared contract, without caring about their concrete type. Interfaces are the primary tool for achieving that goal. When an interface is too wide, polymorphism degrades. You end up with implementations that are technically substitutable but practically unreliable — they satisfy the type system while silently doing nothing, or worse, raising errors at runtime.

The problems that follow from a bloated interface are predictable:

- **Forced stub implementations.** A class that cannot sensibly fulfil a method is forced to implement it anyway, typically as a no-op or an exception. This is a lie encoded in the type system.
- **Fragile downstream effects.** A change to any part of the fat interface requires every implementor to be recompiled and re-tested, even if the change is irrelevant to them.
- **Leaking abstraction.** Callers who receive an object typed to the fat interface can see — and accidentally invoke — capabilities that the underlying object does not actually support.
- **Harder testing.** Mocking a fat interface means stubbing out irrelevant methods. The test noise grows proportionally.

The fix is not to make interfaces smaller for their own sake. The fix is to **segregate interfaces around the needs of the callers**, so that each caller depends only on the behaviour it actually uses.

---

### The Running Example: A Media Device System

Throughout this chapter we will use a single example: a media device management system. The system needs to model three kinds of devices — **Printers**, **Scanners**, and **Fax Machines** — and route work to each. Some physical devices support all three functions (an all-in-one office unit). Others support only one (a dedicated laser printer). The software must control all of them uniformly wherever possible, without lying about what any given device can do.

---

### The Violation: A Fat Interface

The natural first instinct is to define one interface that captures everything a media device might do.

```
┌─────────────────────────────────┐
│        <<interface>>            │
│         IMediaDevice            │
├─────────────────────────────────┤
│ + print(document) -> None       │
│ + scan(document) -> bytes       │
│ + fax(document, number) -> None │
└─────────────────────────────────┘
         ▲             ▲
         │             │
  BasicPrinter    FaxMachine
  (no scan,       (no scan,
   no fax)         no print)
```

In Python, this looks like:

```python
from abc import ABC, abstractmethod

class IMediaDevice(ABC):
    @abstractmethod
    def print(self, document: str) -> None: ...

    @abstractmethod
    def scan(self, document: str) -> bytes: ...

    @abstractmethod
    def fax(self, document: str, number: str) -> None: ...


class BasicPrinter(IMediaDevice):
    def print(self, document: str) -> None:
        print(f"Printing: {document}")

    def scan(self, document: str) -> bytes:
        raise NotImplementedError("This device cannot scan.")

    def fax(self, document: str, number: str) -> None:
        raise NotImplementedError("This device cannot fax.")


class FaxMachine(IMediaDevice):
    def print(self, document: str) -> None:
        raise NotImplementedError("This device cannot print.")

    def scan(self, document: str) -> bytes:
        raise NotImplementedError("This device cannot scan.")

    def fax(self, document: str, number: str) -> None:
        print(f"Faxing '{document}' to {number}")
```

On the surface, both classes satisfy `IMediaDevice`. The type-checker is satisfied. But the design has already broken down:

- `BasicPrinter` claims to be a device that can scan and fax — it simply fails at runtime.
- `FaxMachine` claims it can print and scan — it cannot.
- Any caller holding an `IMediaDevice` reference cannot trust the object it receives. It must either check the type at runtime (defeating polymorphism entirely) or accept that calls may blow up.
- Every time the `IMediaDevice` interface gains a method — say, `copy()` — every implementor must be touched, even those for which copying is meaningless.

The `NotImplementedError` stubs are the most honest symptom. They are the codebase's way of admitting that the abstraction is wrong. (It is worth noting that this pattern often signals a simultaneous violation of the Liskov Substitution Principle: a `BasicPrinter` cannot be safely substituted wherever an `IMediaDevice` is expected, because callers cannot rely on the full contract being honoured — two SOLID violations that tend to arrive together.)

---

### The Fix: Segregated Interfaces

ISP calls for splitting `IMediaDevice` along the lines of what each *caller* actually needs, not along the lines of what the most capable device can do. Three natural **role interfaces** emerge — a term used in formal ISP literature to describe an interface that captures a single, coherent responsibility as seen from the perspective of a specific type of caller:

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│  <<interface>>   │  │  <<interface>>   │  │      <<interface>>       │
│    IPrinter      │  │    IScanner      │  │        IFaxer            │
├──────────────────┤  ├──────────────────┤  ├──────────────────────────┤
│ + print(doc)     │  │ + scan(doc)      │  │ + fax(doc, number)       │
└──────────────────┘  └──────────────────┘  └──────────────────────────┘
       ▲                      ▲                          ▲
       │                      │                          │
 BasicPrinter           DeskScanner                FaxMachine
       ▲
       │◄── also implements IPrinter
  AllInOnePrinter ──────────────────────────────────►(all three)
```

The all-in-one device implements all three role interfaces. The dedicated devices implement only the interface that describes their actual capability.

```python
from abc import ABC, abstractmethod


class IPrinter(ABC):
    @abstractmethod
    def print(self, document: str) -> None: ...


class IScanner(ABC):
    @abstractmethod
    def scan(self, document: str) -> bytes: ...


class IFaxer(ABC):
    @abstractmethod
    def fax(self, document: str, number: str) -> None: ...


class BasicPrinter(IPrinter):
    def print(self, document: str) -> None:
        print(f"Printing: {document}")


class DeskScanner(IScanner):
    def scan(self, document: str) -> bytes:
        return f"[scanned bytes of {document}]".encode()


class FaxMachine(IFaxer):
    def fax(self, document: str, number: str) -> None:
        print(f"Faxing '{document}' to {number}")


class AllInOnePrinter(IPrinter, IScanner, IFaxer):
    def print(self, document: str) -> None:
        print(f"[AIO] Printing: {document}")

    def scan(self, document: str) -> bytes:
        return f"[AIO scanned bytes of {document}]".encode()

    def fax(self, document: str, number: str) -> None:
        print(f"[AIO] Faxing '{document}' to {number}")
```

Now consider the callers. A `PrintQueue` only needs to send documents to something that can print. It takes an `IPrinter`. It never sees `scan` or `fax`. A `ScanService` takes an `IScanner`. The `AllInOnePrinter` can be passed to any of them, because it satisfies all three contracts — but each caller sees only the slice relevant to its work.

```python
class PrintQueue:
    def __init__(self, printer: IPrinter) -> None:
        self._printer = printer

    def process(self, documents: list[str]) -> None:
        for doc in documents:
            self._printer.print(doc)


class ScanService:
    def __init__(self, scanner: IScanner) -> None:
        self._scanner = scanner

    def digitise(self, document: str) -> bytes:
        return self._scanner.scan(document)


# Works with a dedicated printer
queue = PrintQueue(BasicPrinter())
queue.process(["memo.pdf", "report.pdf"])

# Works equally with the all-in-one
aio = AllInOnePrinter()
queue2 = PrintQueue(aio)       # sees only IPrinter
scan_svc = ScanService(aio)    # sees only IScanner
```

There are no stubs. There are no `NotImplementedError` landmines. Polymorphism works correctly: `PrintQueue` can accept any printer, and callers can pass any object that honours the `IPrinter` contract.

---

### How It Is Achieved Mechanically

ISP is realised through two complementary mechanisms: **interface decomposition** and **composition**. They are not separate strategies — they work together, and understanding how they relate is essential.

**Interface decomposition** is the act of splitting a wide interface into focused role interfaces, each representing a single capability as seen from a caller's perspective. This is what we did above when `IMediaDevice` became `IPrinter`, `IScanner`, and `IFaxer`. Each interface is now a minimal contract.

**Composition** is what allows a single class to satisfy multiple role interfaces simultaneously. `AllInOnePrinter` composes all three roles by simply inheriting from all three abstract base classes. Python's multiple inheritance makes this syntactically natural, but the concept is language-agnostic: a class asserts that it fulfils multiple roles, and callers can request whichever role they need.

The relationship between the two is this: *decomposition creates the roles; composition allows objects to play multiple roles without forcing callers to know about it.* Without decomposition, there is nothing to compose. Without composition, decomposed interfaces would force artificial restrictions on capable devices.

**Type annotations as caller-side contracts.** In Python, the mechanism for enforcing ISP at the call site is straightforward: annotate parameters with the narrowest interface the function actually uses. A function that only prints should accept `IPrinter`, not `AllInOnePrinter` and not `IMediaDevice`. This is where the discipline lives — not in the class definitions, but in what each consumer asks for.

```python
# This is too wide — the function only prints, yet it knows about scanners
def send_to_printer(device: AllInOnePrinter, doc: str) -> None:
    device.print(doc)

# This is correct — the function declares exactly what it needs
def send_to_printer(device: IPrinter, doc: str) -> None:
    device.print(doc)
```

The second version accepts `BasicPrinter`, `AllInOnePrinter`, or any future printer. The first version accepts only `AllInOnePrinter`, tying the function's fate to a concrete class's entire surface area.

---

### A Pythonic Alternative: Structural Subtyping with `Protocol`

Python 3.8 introduced `typing.Protocol`, which enables **structural subtyping** (sometimes called duck typing with static verification). Rather than requiring a class to explicitly declare which interfaces it implements, a `Protocol` simply describes the shape — the method names and signatures — that an object must have. A class satisfies a Protocol automatically if it has the right methods, regardless of inheritance.

For ISP purposes, `Protocol` is often a cleaner mechanism than `ABC` because it decouples role definition entirely from class hierarchy.

```python
from typing import Protocol


class IPrinter(Protocol):
    def print(self, document: str) -> None: ...


class IScanner(Protocol):
    def scan(self, document: str) -> bytes: ...


class IFaxer(Protocol):
    def fax(self, document: str, number: str) -> None: ...


# No inheritance required — this satisfies all three protocols structurally
class AllInOnePrinter:
    def print(self, document: str) -> None:
        print(f"[AIO] Printing: {document}")

    def scan(self, document: str) -> bytes:
        return f"[AIO scanned bytes of {document}]".encode()

    def fax(self, document: str, number: str) -> None:
        print(f"[AIO] Faxing '{document}' to {number}")


def send_to_printer(device: IPrinter, doc: str) -> None:
    device.print(doc)

aio = AllInOnePrinter()
send_to_printer(aio)  # passes static type-checking without any explicit declaration
```

The tradeoff is real and worth stating plainly. `ABC` gives you *nominal* typing: a class must explicitly opt into an interface, and Python will raise a `TypeError` at instantiation time if any abstract method is missing. `Protocol` gives you *structural* typing: the check is purely static (via mypy or pyright) and there is no runtime enforcement unless you explicitly add `@runtime_checkable` and call `isinstance`.

A practical rule of thumb for choosing between them: reach for **`Protocol`** when designing a library or public API where you want maximum flexibility for external callers — they can satisfy your interface without taking on your inheritance hierarchy. Reach for **`ABC`** for internal core services where you want the runtime safety net of instantiation-time enforcement and an explicit, navigable inheritance tree that documents intent. The two approaches are also compatible: you can define a `Protocol` for external callers and an `ABC` for internal implementations, letting them coexist at different layers of the same system.

---

### Common Tradeoffs and Honest Caveats

Applying ISP faithfully carries some costs worth acknowledging.

**More types to manage.** Splitting one interface into three means three names to import, three things to document, and three things to keep consistent when the domain model evolves. In a small codebase with few implementors, the fat interface may genuinely be less friction than the segregated one.

**Interface proliferation can itself become a smell.** If you have twenty single-method interfaces, the design may have swung too far. The goal is interfaces that align with caller roles, not interfaces that are as small as physically possible.

**Composition requires discipline.** A class that implements six role interfaces can become hard to reason about. At some point, it may be worth asking whether the class itself should be decomposed — a question that leads toward the Single Responsibility Principle.

---

### Rule of Thumb

> **Ask what the caller needs, not what the object can do. Define interfaces from the outside in.**

If you are writing a function and reaching for a wide interface or a concrete class as your parameter type, pause and ask: *which methods of this object will I actually call?* If the answer is a strict subset, define or reach for a narrower role interface that captures only that subset. The caller should be the one that dictates the contract — not the most capable implementor in the system.

When you find yourself writing `raise NotImplementedError` inside a method you are forced to implement, that is the clearest possible signal that the interface is violating ISP. The codebase is telling you, in the most direct terms it can, that the abstraction does not fit.