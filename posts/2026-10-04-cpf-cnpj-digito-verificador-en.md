---
title: "CPF and CNPJ: What the Check Digit Actually Guarantees"
date: "2026-10-04"
category: "tutorial"
tags: ["cpf", "cnpj", "business-logic", "validation"]
excerpt: "Everyone has typed a CPF and entered one digit too many. The check digit exists to catch exactly that — but it does not prove the document exists. That gap is where almost everyone goes wrong."
share_hook: "A valid check digit does not mean the CPF exists. It only means nobody mistyped it."
lang: "en"
---

There is a small, quiet difference between two sentences that sound like they mean
the same thing:

- "this CPF is valid"
- "this CPF exists"

The first is checkable with a pen and a three-line rule. The second requires
querying the Brazilian tax authority. The confusion between the two is the root of
nearly every system that "validated" an invented document and only found out far
too late.

This post is about the first one: the check digit, what it guarantees, and where
that guarantee runs out.

## The check digit is not security, it is error detection

The name already warns you: *verifier*, not *authenticator*. Its job is
accidentally technical: catching typing errors.

A CPF has 11 digits. The first 9 are the base; the last 2 are computed. A CNPJ has
14: the first 12 are the base, the last 2 are computed. The computation is the same
in both cases — modulo 11.

For the CPF, with the 9 base digits `d₁…d₉`:

```
sum  = 10·d₁ + 9·d₂ + 8·d₃ + 7·d₄ + 6·d₅ + 5·d₆ + 4·d₇ + 3·d₈ + 2·d₉
rest = sum % 11
d₁₀  = rest < 2 ? 0 : 11 − rest
```

You repeat it with the first 10 digits to get `d₁₁`. The weights descend from 10
to 2, and the CNPJ uses the same idea with a different weight set and a special
case on the last two digits — but the essence is identical: one weighted sum, one
remainder, and a correction for the case where the remainder lands on 0 or 1.

None of that queries the tax authority. None of it looks anyone up. It is pure
arithmetic over digits you already typed.

## What it guarantees, and what it does not

The check digit guarantees two specific things:

1. **The shape is right.** Eleven digits for a CPF, fourteen for a CNPJ.
2. **It is not a typo.** The weighted sum only closes for one specific digit
   sequence; swap a digit and recompute, and it closes for a different one.

What it does **not** guarantee is that the person exists, that the CNPJ is active,
or that the information provided is true. A CPF with a correct check digit can
belong to someone who does not exist — just make the first 9 digits plausible and
compute the last 2 from them. That is trivial to do by hand, and it is not fraud:
it is exactly what a demo form does.

This is why validating documents only on the frontend is fragile. The frontend can
say "format valid" — and be right. But if the backend accepts the same value
without consulting an official source, the system accepts invented documents with
the same confidence it accepts real ones.

## Why "all digits the same" is rejected

Notice a detail in the code: a CPF like `111.111.111-11` passes the modulo 11
computation, but is rejected. Why?

Because it passes for the wrong reason. A repeated digit is almost always a sign of
auto-filled input — the user typed one digit into every field, or a form echoed
the same value back. That is a form error, not a document. The rule exists to catch
exactly that.

The same applies to `000.000.000-00`: mathematically valid, semantically impossible.

It is a good example of validation in two layers. The arithmetic layer says "the
numbers add up". The sanity layer says "this shape is plausible". A serious
validation tool has both.

## The mutation that passes: why that is not a bug

There is a detail that tends to alarm people the first time they study the
algorithm. If you take a valid CPF and change a single digit, the result will often
still be **valid**.

That looks like a hole, but it is mathematical redundancy. Take a
mathematically generated base CPF: `00000000604`. Change the first digit from `0`
to `1`: `10000000604`. Recompute the two check digits — and they match.

This is not a failure. It is modulo 11 admitting more than one sequence per result.
A single-digit mutation has a measurable chance of landing on another valid
sequence, because the verification space has 11×11 = 121 possible combinations for
those two digits.

The practical consequence is the same as the opening of this post: **a correct
check digit is a weak claim.** It filters out typos. It does not prove identity,
existence, or ownership. If your system needs any of those three, the check digit
is a starting point, never the finish line.

## What to validate, and where

The practical rule for a signup form:

- **On the frontend:** shape and check digit. Instant feedback, no round trip to a
  server, and it eliminates the overwhelming majority of typing errors.
- **On the backend:** the same check digit, again. Never trust the client — the
  user's JavaScript is under their control.
- **Only when the data is consequential:** a lookup against an official source. And
  that is an asynchronous flow, with caching, with cost, with a retention policy —
  not a call on the field's `blur` event.

It is tempting to always run the official lookup to "be sure". But each call costs
money, and a person's CPF does not change. You validate the shape every time; you
look up existence when the value actually matters, and you cache the result.

A validator that only does the first part is not wrong — it is honest about what it
knows. The problem appears when the whole system treats "format valid" as "person
verified", and that is an architecture decision, not a validation one.

## Summary

- The check digit is pure arithmetic: it catches typos, it does not verify
  existence.
- Modulo 11, with descending weights and a correction for remainder 0 or 1.
- Repeated digits are rejected by a sanity rule, not by the arithmetic.
- A single-digit mutation can stay valid; that is redundancy, not a flaw.
- The frontend filters shape; the backend repeats the check; an official source
  only when the data carries weight.

If you came here wanting to validate a document in a form, the honest part is
this: what you can verify in milliseconds is about shape, not about the person. When
shape is all you need, there is no reason to pay more. When it is not, the check
digit has already done the work of filtering the junk for you — but the decision of
whom to query stays on the other side.

Want to test whether a CPF or CNPJ adds up? The
[CPF/CNPJ Validator](/ferramentas/validar-cpf-cnpj) tool does the computation and
states explicitly what it is and is not verifying.
