# Where every claim in this repository comes from

| Document | Status | Published | Relationship and errata |
|---|---|---|---|
| RFC 6811 | Proposed Standard | 2013-01 | origin validation; updated by 8481 and 8893; no errata; implemented here |
| RFC 8481 | Proposed Standard | 2018-09 | updates 6811; updated by 9324; no errata |
| RFC 9324 | Proposed Standard | 2022-12 | updates 8481 (policy without route refresh); no errata |
| RFC 8893 | Proposed Standard | 2020-09 | updates 6811 (origin validation on export, effective origin); no errata; not yet read |
| RFC 9774 | Proposed Standard | 2025-05 | obsoletes 6472; updates 4271 and 5065 (AS_SET and AS_CONFED_SET deprecated); no errata; not yet read in full |
| RFC 4271 | Draft Standard | 2006-01 | BGP-4; 9 verified errata; updated by many, including 9774; AS_PATH segment types 1 and 2 |
| RFC 5065 | Draft Standard | 2007-08 | confederations; updated by 9774; 1 verified erratum; segment types 3 and 4 |
| RFC 9234 | Proposed Standard | 2022-05 | BGP roles and the OTC attribute; no errata |
| RFC 6480 | Informational | 2012-02 | RPKI architecture; not the specification of origin validation |
| RFC 9319 | Best Current Practice | 2022-10 | maxLength use (BCP 185); advisory |
| RFC 2622 | Proposed Standard | 1999-06 | RPSL; route class key is route plus origin (section 4); updated by 4012 (route6) and 7909; 3 verified errata |
| RFC 7854 | Proposed Standard | 2016-06 | BMP, the observation source routevalid correlates; updated by 8671, 9069, 9515, 9736; 3 verified errata |
| RFC 6396 | Proposed Standard | 2011-10 | MRT; 2 verified errata on the Appendix A examples; routevalid does not parse MRT itself |

Every row above was read from `rfclib.info` on 2026-11-13. ASPA verification exists only as `draft-ietf-sidrops-aspa-verification`, cited by RFC 9774, and is not in the library; it is an unciteable draft and not a row.

Citation rules, in the order they most often get broken:

1. Cite the document. A secondary write-up is a lead, not a source.
2. A section number is cited only if that section was read in full.
3. Errata are checked at each milestone freeze, not once at the start.
4. Where a claim came from a body outside the RFC series, that body is named here.

Re-verify with the RFC library rather than memory: `info('RFCnnnn')` for current status, `errata('RFCnnnn')` for corrections, and `read('RFCnnnn', view='normative')` for the MUST and SHOULD statements that become obligation rows.
