# Security

## Reporting a vulnerability

Use GitHub's **private vulnerability reporting** on this repository (Security → Report a
vulnerability). It reaches the maintainer privately and needs no address published here.

Please do not open a public issue for anything exploitable.

## What this software does, and what it therefore cannot promise

epure reads recordings — tapes produced by `flight-recorder` at an application's
nondeterminism boundary — and checks them against a model. Two consequences are worth stating
plainly, because both are the kind of thing a user assumes wrongly:

**A tape may carry anything the recorded app handled.** Redaction and the forbidden-value
tripwire live in the recorder, at record time, where the values still exist; by the time a tape
reaches this library the decision has already been made. Treat a tape with the same care as the
data of the app that produced it, and check what you are about to publish before you publish it.

**A proof is only as good as its model.** Proof relocates risk into specification; it does not
remove it. A system can perfectly refine a proven model that is wrong. Nothing here — nothing
anywhere — makes a green result a statement about the world; it is a statement about the model,
and the model is a thing a human wrote.
