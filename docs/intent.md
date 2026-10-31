# Medixio — Intent

> **Status:** Draft v2 · Last updated: 2026-10-31 · Companion: [design.md](design.md)

This document says **why** Medixio exists and **what** it must do. It avoids implementation details; those live in `design.md`.

---

## 1. Problem

People in Colombia living with a chronic illness (or caring for someone who does) spend a large part of their energy on the healthcare system's paperwork, not on the illness itself:

- An **orden / fórmula médica** is issued for N months (typically 3). It expires, and a new one must be requested from the doctor *before* the medicine runs out.
- Many medicines and procedures need an **autorización** from the EPS, which has its own validity window and must be used before it lapses.
- Medicine is **dispensed monthly** at an EPS-contracted pharmacy (Audifarma, Cruz Verde, Colsubsidio, etc.). Stock-outs produce **pendientes** that must be followed up.
- Appointments with specialists are hard to get and easy to forget.
- When the EPS denies or delays, the person may need to file a **PQRS** or a **tutela**, both with deadlines.

Missing any single step usually means interrupting treatment. Existing apps are generic reminder tools that don't know this flow.

## 2. Vision

A WhatsApp contact that knows the Colombian health bureaucracy and remembers it on the user's behalf. The user sends a message or a photo of a document; Medixio understands it, stores it, and reminds the user at the right moment of the next step.

WhatsApp is the only interface. No app to install, no web UI.

## 3. Users

- **Primary:** adults in Colombia with chronic illness, managing their own treatment via an EPS.
- **One WhatsApp number = one patient.** A number cannot manage several patients. A caregiver who chats on behalf of a relative is treated as that patient's account; managing a second patient needs a second number.
- **Access:** open — any WhatsApp number can start a conversation. First contact requires accepting a data-treatment notice (Habeas Data, Ley 1581 de 2012).
- **Language:** Spanish (es-CO), informal but respectful tone.

## 4. What Medixio does (v1 scope)

| # | Capability | Example |
|---|---|---|
| C1 | **Appointments** — create, list, reschedule, cancel; reminders before and follow-up after. | "Tengo cita con el reumatólogo el 12 de noviembre a las 3 pm" |
| C2 | **Medical orders (fórmulas)** — read a photo or text of an order, extract medicines, doses, duration; remind **15 days before the order expires** to request a renewal. | *(photo of fórmula for 3 months)* |
| C3 | **Authorizations (autorizaciones)** — track what is authorized, by which EPS, until when; remind before expiry and when it hasn't been used yet. | *(photo of autorización)* |
| C4 | **Dispensing** — remind the monthly pharmacy pickup, then **ask the user to confirm** they picked it up (fully, partially, or not); track **pendientes** and nudge the user to follow up. Never assume a pickup happened. | "En Audifarma me quedó pendiente la insulina" |
| C5 | **PQRS / tutela guidance** — when the user reports a denial or delay, explain the next step, what documents to gather, and remind legal deadlines. Informative, not legal representation. | "La EPS no me quiere autorizar la resonancia" |
| C6 | **Free-form reminders** — any recurring or one-off reminder in natural language. | "Recuérdame tomar la metformina todos los días a las 8 am" |
| C7 | **Image understanding** — photos of fórmulas, autorizaciones, and appointment slips are read and turned into structured records, with confirmation from the user before saving. **Images are never stored**: data is extracted and the image is discarded. | |
| C8 | **Per-user profile** — EPS, régimen (contributivo/subsidiado), usual pharmacy, city, preferred reminder hour, and any deviation from the standard flow. | "Mi EPS me entrega los medicamentos a domicilio" |

### Shared knowledge vs per-user preferences

The bureaucratic flow is **the same for everyone** and lives in a shared knowledge base (rules, typical validity windows, PQRS/tutela steps). Each user can **override** defaults (e.g. "my orders last 6 months", "remind me 20 days before", "I get home delivery"). The bot always applies: user override → shared default.

## 5. Non-goals

- **No medical advice.** Never diagnoses, recommends doses, or interprets symptoms or lab results. Redirects to the doctor.
- **No legal representation.** PQRS/tutela help is informational; the bot doesn't file on the user's behalf.
- **No integration with EPS or pharmacy systems.** Everything comes from the user.
- **No voice notes** in v1.
- **Colombia only** for now; other countries are future work.
- **No web or mobile UI.**

## 6. Principles

1. **Confirm before saving.** Anything extracted by the LLM, especially from images, is read back to the user before it becomes a record.
2. **Ask one thing at a time.** Missing data is requested in short, single questions.
3. **Proactive but not spammy.** Few messages, each actionable. Reminders are batched per day where possible.
4. **The user owns their data.** They can ask what is stored and ask to delete everything.
5. **Minimum data out.** Only WhatsApp and Anthropic receive user data. No analytics.
6. **Self-hosted and cheap.** One server, one SQLite file, one process.

## 7. Success criteria (v1)

- A user can photograph a 3-month fórmula and receive a renewal reminder 15 days before it expires, without typing dates manually.
- No reminder is lost or duplicated across server restarts.
- A new user is onboarded (consent + name + EPS) in under 5 messages.
- Operating cost stays within a hobby budget (target: < USD 20/month in LLM spend at ~50 active users).

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| WhatsApp bans the bot number (neonize is unofficial) | Bot goes dark | Low message rate, no broadcast, channel behind an interface so Cloud API can replace it |
| LLM misreads a date in an image | Missed renewal | Mandatory user confirmation before saving; user can re-send the photo (images aren't kept) |
| Sensitive health data on a home server | Privacy breach | Disk encryption, no public DB, backups encrypted, delete-on-request |
| Bureaucracy rules change | Wrong guidance | Knowledge base is data with cited sources, reviewed by the admin, editable without code changes |

## 9. Decisions

1. **One number per patient.** A WhatsApp number maps to exactly one patient. No multi-patient or caregiver mode.
2. **Always confirm dispensing.** After each pickup reminder the bot asks "¿Ya reclamaste el medicamento?" and records the answer (dispensed / partial / pending). Unanswered cycles are asked about again; they're never assumed done.
3. **Knowledge base is admin-reviewed.** Rules and deadlines are researched from official sources (Minsalud, Supersalud, Corte Constitucional, the laws themselves). Each entry cites its source and carries `reviewed_by` / `reviewed_on`. Entries the admin hasn't reviewed are not used in user-facing guidance. See design §5.
4. **No image retention.** Images are processed in memory: extract → confirm → save the structured data → discard the image. No image is written to disk, the DB, or backups.
5. **Single admin.** Only the project author reviews and approves the knowledge base.
6. **Quarterly review.** All knowledge sources are re-checked every quarter, plus whenever a user reports a mismatch.
