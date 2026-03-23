# Graph Summary
_Generated: 2026-03-23 (scan gaps)_

## Stats
- **Nodes:** 10
- **Edges:** 16
- **Confidence distribution:** 3 high, 7 medium, 0 low, 0 stub

---

## Clusters

### 1. Kankyō Ongaku / Ambient Minimalism
**5 artists.** Brian Eno as root; two Japanese branches (Yoshimura and Shimizu); two heirs (Ishiguro, Kruczynski).

| Artist | Country | Era | Confidence | Edges |
|--------|---------|-----|------------|-------|
| Brian Eno | GB | 1970s–present | high | 4 |
| Hiroshi Yoshimura | JP | 1980s–2000s | high | 4 |
| Yasuaki Shimizu | JP | 1980s–present | medium | 2 |
| Hiroki Ishiguro | JP | 1990s–2020s | medium | 3 |
| Bartosz Kruczynski | PL | 2010s–present | medium | 3 |

**Through-line:** Music as environment rather than sequence. All five treat atmosphere as composition — music you inhabit, not follow.

**Weak link:** Yasuaki Shimizu is the odd member. His only edges are Eno (basilect) and Yoshimura (sonic — explicitly flagged as a scene connection, not a discovery). He's philosophically distinct from the rest of Cluster A: playful, cyclical, jazz-rooted, not meditative or attentive. He may be a better bridge candidate between the two clusters than a core kankyo ongaku node.

---

### 2. Jazz-Adjacent / Cinematic Groove
**5 artists.** BADBADNOTGOOD as the contemporary hub; Verocai and Azymuth as the Brazilian anchors; Piccioni as the Italian outlier; Washington as the spiritual-jazz extension.

| Artist | Country | Era | Confidence | Edges |
|--------|---------|-----|------------|-------|
| BADBADNOTGOOD | CA | 2010s–present | high | 4 |
| Arthur Verocai | BR | 1970s–present | medium | 4 |
| Azymuth | BR | 1970s–present | medium | 3 |
| Piero Piccioni | IT | 1950s–2000s | medium | 4 |
| Kamasi Washington | US | 2010s–present | medium | 2 |

**Through-line:** Jazz sensibility extended into cinematic, psychedelic, or spiritual forms. Shared belief that jazz is a means toward a larger atmospheric or emotional goal, not an end in itself.

**Weak links:** Kamasi Washington has only 2 edges. The Azymuth–Piccioni edge is low-confidence and deserves ear verification. The Brazilian cluster (Verocai + Azymuth) currently depends on BBNG for all its cross-cultural connections — it has no internal cross-era or cross-cultural bridging.

---

## Edge Summary

| From | To | Type | Strength | Confidence | Cross-cultural | Cross-era |
|------|----|------|----------|------------|----------------|-----------|
| brian_eno | hiroshi_yoshimura | lineage | strong | high | yes | no |
| brian_eno | yasuaki_shimizu | basilect | moderate | medium | yes | no |
| brian_eno | hiroki_ishiguro | lineage | moderate | medium | yes | yes |
| brian_eno | bartosz_kruczynski | basilect | strong | medium | yes | yes |
| hiroshi_yoshimura | yasuaki_shimizu | sonic | moderate | medium | no | no |
| hiroshi_yoshimura | hiroki_ishiguro | basilect | strong | medium | no | yes |
| hiroshi_yoshimura | bartosz_kruczynski | basilect | strong | medium | yes | yes |
| hiroki_ishiguro | bartosz_kruczynski | basilect | moderate | low | yes | no |
| badbadnotgood | arthur_verocai | basilect | strong | high | yes | yes |
| badbadnotgood | azymuth | basilect | strong | medium | yes | yes |
| badbadnotgood | piero_piccioni | basilect | strong | medium | yes | yes |
| badbadnotgood | kamasi_washington | basilect | strong | medium | no | no |
| arthur_verocai | azymuth | basilect | medium | medium | no | no |
| arthur_verocai | piero_piccioni | basilect | strong | medium | yes | yes |
| arthur_verocai | kamasi_washington | basilect | medium | medium | yes | no |
| azymuth | piero_piccioni | basilect | medium | low | yes | yes |

---

## Priority Ear-Checks

High-strength / low-confidence edges — most worth validating:

1. **Hiroki Ishiguro → Bartosz Kruczynski** — moderate / low
   Both downstream of Yoshimura's ambient lineage; directionally correct but both profiles are thin. Don't add further connections through either node until this is ear-checked.
2. **Azymuth → Piero Piccioni** — medium / low
   Brazilian jazz-funk and Italian jazz-lounge; cross-cultural, credible but speculative. The sonic surfaces may be near-opposites. Ear-check before using either node as a bridge.

---

## Critical Gap: No Cross-Cluster Bridge

The two clusters share **zero edges**. Every artist in Cluster A is unreachable from every artist in Cluster B. This is the highest-priority structural gap.

**Most plausible direct bridges (without adding new nodes):**

- **Piccioni ↔ Eno / Yoshimura** — Piccioni's "music as emotional weather, sustained atmosphere over event" is philosophically adjacent to kankyo ongaku. Italian film scoring vs. British/Japanese ambient: different tools, same spatial posture. Highest potential.
- **Verocai ↔ Yoshimura** — Verocai's cinematic orchestral restraint and Yoshimura's environmental minimalism both treat space as load-bearing. Cross-cultural (BR/JP), same era. Medium potential.
- **Kamasi Washington ↔ Eno** — both argue music can hold something larger than itself; Washington's internal/spiritual reality framing has overlap with Eno's peripheral-attention philosophy. Grandeur vs. restraint is a real tension, but the posture toward music's purpose is similar. Medium potential.

---

## Intra-Cluster Missing Edges

**Cluster A:**
- **Shimizu ↔ Ishiguro** — Not recommended. Already connected via Yoshimura and Eno. Philosophically distinct (playful/cyclical vs. meditative/attentive). Adding would inflate density without insight.
- **Shimizu ↔ Kruczynski** — Worth evaluating. Shimizu's loops-as-environment and Kruczynski's haze-as-atmosphere are different routes to similar spatial music. Cross-cultural (JP/PL). Medium potential.

**Cluster B:**
- **Piccioni ↔ Kamasi** — Worth evaluating. Both deploy jazz harmony in service of orchestral/elevated emotional writing. Italian cinema vs. LA spiritual jazz; cross-cultural, cross-era. Medium potential.
- **Azymuth ↔ Kamasi** — Thin. They share jazz vocabulary but that's the whole cluster. Surface difference (electric samba groove vs. spiritual grandeur) doesn't yield philosophical depth.

---

## Nodes Needing More Sourcing

These profiles limit reasoning quality on every edge they touch:

| Node | Confidence | Gap |
|------|------------|-----|
| **Hiroki Ishiguro** | medium | No interviews. Profile inferred from compilation placement (Heisei no Oto) and artist bio. Multiple edges already flag "strengthen before use." Highest priority. |
| **Yasuaki Shimizu** | medium | No primary interview found. Philosophical framing is inferred from critical descriptions of *Kakashi*. |
| **Piero Piccioni** | medium | No longform interview (deceased 2004). Relies on biography pages. Anthology Film Archives essay and Forced Exposure writeups worth checking. |
| **Kamasi Washington** | medium | Well-documented publicly but profile could go deeper. The Creative Independent and Dazed interviews are worth fetching. |

---

## Blindspots

- **Cross-cluster bridge artists** — the two clusters are islands; this is the graph's most urgent structural problem
- **Eastern European ambient** — Kruczynski implies a broader scene; likely more candidates in Polish/Czech/Baltic circles
- **Contemporary Japanese kankyo ongaku heirs** — Ishiguro is one, but the Heisei no Oto compilation context implies a larger unresearched scene; Music From Memory's catalog is the best entry point
- **South American ambient/minimalist** — no coverage of environmental or minimal music from Brazil or Argentina beyond the jazz-groove cluster
- **Pre-1970s antecedents** — Satie, Cage, Feldman all predate Eno and inform the same tradition; useful for deepening the ambient cluster's historical reach
- **African and Southeast Asian jazz** — the jazz cluster is Brazil, Italy, Canada, US. Enormous blind spot.

---

## Suggested Next Additions

Ranked by bridge value:

1. **Nujabes** *(JP, instrumental hip-hop / jazz rap, 1990s-2000s)* — highest value addition in the graph. Japanese (connects to Cluster A: restraint, space, loops as meditative form) + hip-hop/jazz (connects to Cluster B: jazz vocabulary deployed outside jazz). Natural bridge node. Significant critical writing available; should be sourceable to high confidence. Would likely connect to Yoshimura/Ishiguro and BBNG/Kamasi simultaneously.

2. **Laraaji** *(US, ambient / new age / zither, 1970s-present)* — ready-made bridge with documented cross-cluster links. Eno produced his *Day of Radiance* (1980) → direct Cluster A lineage. Named as a *Talk Memory* collaborator in BBNG's notes → Cluster B connection. Spiritual, ambient, and loose at the edges — exactly what the graph needs to link the two traditions.

3. **Floating Points** *(GB, electronic/jazz, 2010s-present)* — electronic/ambient sensibility (Cluster A) combined with genuine jazz practice. *Promises* with Pharoah Sanders is one of the most discussed ambient-jazz crossovers of the 2020s. Well-documented with interview material.

4. **Midori Takada** *(JP, percussionist / minimalist, 1970s-present)* — already named in the original Eno seed. Japanese, minimalist, uses repetition and silence structurally. Deepens Cluster A and potentially bridges to European minimalism or spiritual jazz.
