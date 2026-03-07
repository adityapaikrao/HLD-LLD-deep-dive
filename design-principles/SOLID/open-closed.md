## Open-Closed Principle (OCP)

---

### Definition
> *"Software entities (classes, modules, functions) should be open for extension, but closed for modification."*
> — Bertrand Meyer, 1988, popularised by Robert C. Martin

A class is **open for extension** meaning its behaviour can be augmented or changed. It is **closed for modification** meaning its existing, tested source code should not need to be touched to achieve that. The goal is to add new functionality by adding new code, not by editing old code.

---

### Historical Evolution

It is worth distinguishing between how the principle was originally conceived and how it is practiced today, as the two differ meaningfully.

| Concept | Meyer's Original (1988) | Martin's Polymorphic OCP |
|---|---|---|
| Primary Mechanism | Implementation inheritance | Interfaces and composition |
| Closed means | Base class code is unchanged | Consumer depends on a stable abstract interface |
| Open means | Create a subclass that inherits from parent | Implement the abstract interface in a new concrete class |

When Bertrand Meyer coined the term in *Object-Oriented Software Construction* (1988), he specifically advocated for implementation inheritance — you close a class by compiling it, and open it by subclassing. Robert C. Martin later popularised a modernised version known as the **Polymorphic Open-Closed Principle**, which is what is practiced in modern software design and what this write-up focuses on.

---

### Why It Matters
Every time you reopen a class to modify it you risk:
- Introducing bugs into behavior that was already working
- Breaking other parts of the system that depend on that class
- Having to re-test everything that touches that class

OCP protects stable, tested code from the churn of new requirements.

---

### The Example — A Discount System

We have an e-commerce platform that applies discounts to orders based on customer type. We will use this example throughout.

---

### Violation — The Classic Mistake

```python
class DiscountCalculator:
    def calculate(self, customer_type: str, price: float) -> float:
        if customer_type == "regular":
            return price * 0.95
        elif customer_type == "vip":
            return price * 0.80
        elif customer_type == "student":       # added later
            return price * 0.85
```

Every time a new customer type is introduced, `DiscountCalculator` must be reopened and edited. This is fragile because:
- The class grows unboundedly with every new customer type
- A mistake in the student branch could break the regular and vip logic
- The class knows too much — it owns the rules for every single discount type

---

### Fix — Applying OCP

Define a stable abstraction that each discount type must implement. The calculator works against that abstraction and never needs to change:

```python
from abc import ABC, abstractmethod

# The stable abstraction — this never changes
class DiscountStrategy(ABC):
    @abstractmethod
    def apply(self, price: float) -> float:
        pass

# Each discount type is its own closed, self-contained unit
class RegularDiscount(DiscountStrategy):
    def apply(self, price: float) -> float:
        return price * 0.95

class VIPDiscount(DiscountStrategy):
    def apply(self, price: float) -> float:
        return price * 0.80

class StudentDiscount(DiscountStrategy):
    def apply(self, price: float) -> float:
        return price * 0.85

# Closed for modification — this never needs to change
class DiscountCalculator:
    def calculate(self, strategy: DiscountStrategy, price: float) -> float:
        return strategy.apply(price)
```

Adding a `SeniorDiscount` now means writing a new class. `DiscountCalculator` is untouched.

```
DiscountCalculator ──────► DiscountStrategy (abstract)
                                   ▲
                    ┌──────────────┼──────────────┐
               RegularDiscount  VIPDiscount  StudentDiscount
```

---

### How OCP Is Achieved

The mechanism behind OCP is best understood as one overarching goal enabled by two structural tools:

**Polymorphism is the goal.** It is what allows `DiscountCalculator` to call `.apply()` on any discount type without knowing or caring which one it is. The right behavior fires automatically based on the actual object at runtime. This is what insulates the consumer from change.

**Interfaces and composition are the tools used to achieve it.** You define a stable abstract interface (`DiscountStrategy`) and compose `DiscountCalculator` with it. Every concrete discount class implements that interface. Polymorphism then works because every object shares the same contract.

```python
customers = [
    (RegularDiscount(), 100),
    (VIPDiscount(), 200),
    (StudentDiscount(), 150),
]

calculator = DiscountCalculator()

for strategy, price in customers:
    print(calculator.calculate(strategy, price))
    # 95.0, 160.0, 127.5
```

The loop is completely indifferent to which discount type it processes. Each object knows its own rule. This is polymorphism paying off — and it was made possible by the interface and composition structure underneath.

```
     [RegularDiscount, VIPDiscount, StudentDiscount]
                        │
                  .apply(price)
                        │
              ┌─────────┼─────────┐
            95.0      160.0     127.5
```

---

### The Pythonic Alternative — Registry Pattern

In Python specifically, because functions are first-class citizens, you can achieve OCP without the boilerplate of abstract base classes entirely. The **Registry Pattern** maps customer types to callable functions using a dictionary and a decorator:

```python
discount_registry = {}

def register_discount(customer_type):
    def decorator(func):
        discount_registry[customer_type] = func
        return func
    return decorator

@register_discount("regular")
def regular_discount(price: float) -> float:
    return price * 0.95

@register_discount("vip")
def vip_discount(price: float) -> float:
    return price * 0.80

@register_discount("student")
def student_discount(price: float) -> float:
    return price * 0.85

class DiscountCalculator:
    def calculate(self, customer_type: str, price: float) -> float:
        discount_func = discount_registry.get(customer_type, lambda p: p)
        return discount_func(price)
```

Adding a new discount simply requires writing a new decorated function — `DiscountCalculator` never changes. The decorator registers the function at definition time, and the calculator dynamically looks it up at runtime. This eliminates class overhead while maintaining strict OCP compliance.

The tradeoff versus the abstract class approach is worth noting however. Abstract classes enforce the contract at definition time — if you forget to implement `apply()` Python will raise an error immediately. The registry pattern is more flexible but silent — if you forget to decorate a function, the calculator silently falls back to no discount with no warning.

---

### The Rule of Thumb

> If adding new behavior forces you to edit an existing, working class — OCP is being violated. New behavior should always arrive as **new code**, not **modified code**.