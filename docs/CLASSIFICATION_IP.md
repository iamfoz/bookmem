# Classification and IP Notes

BookMem uses **BookMem Decimal Classification (BMDC)** as its internal subject-routing scheme.

## Operating position

BMDC is designed to be **number-compatible with the familiar decimal library classification tradition** wherever that is useful. In practice, that means a BookMem class code such as `510` should be usable for mathematics, `332` for finance and investing, `610` for medicine and health, and so on.

The numbers are treated as interoperable routing identifiers. The project name, scheme name, labels, aliases, notes and documentation remain BookMem's own.

## Boundaries

The safe working distinction is:

- **Use the numbers** as class identifiers.
- **Use our own words** for labels, aliases, explanations and documentation.
- **Do not copy protected editorial text** from proprietary classification manuals or products.
- **Do not use protected names** as the name of BookMem's internal scheme, CLI flags, config keys or user-facing features.

This is not legal advice, but it is the project's practical operating rule.

## Rules for this repository

1. Use `BMDC`, `BookMem Decimal Classification`, `class_code`, `primary_class` and `secondary_class` in code and docs.
2. BMDC class numbers should track the corresponding widely used decimal library class numbers where an equivalent subject class exists.
3. Labels and aliases in `config/bmdc.yaml` must be original BookMem working labels, written in our own words.
4. Do not paste proprietary captions, schedules, relative index entries, manual notes, table notes, hierarchy explanations or long descriptions from external classification products.
5. If more precision is needed, add BookMem-specific aliases, routing groups and topic tags instead of copying external editorial prose.
6. If a book already has an externally assigned catalogue classification, it may be stored as external metadata, but it should be clearly marked as imported metadata and kept separate from BMDC's internal routing fields.

## Recommended metadata split

Use BMDC for internal routing:

```yaml
classification:
  scheme: bmdc
  primary_class: "332"
  primary_label: Finance, investing and financial markets
  secondary_class:
    - "153"
    - "158"
  routing_aliases:
    - finance
    - investing
  topics:
    - risk
    - compounding
```

If external catalogue metadata is imported, keep it separate:

```yaml
external_catalogue_metadata:
  source: example_catalogue
  external_class_number: "332"
  imported_at: "2026-05-18"
```

Do not merge third-party editorial text into BMDC labels, aliases or documentation.

## Why this matters

BookMem is intended to be a practical agent retrieval layer. BMDC gives the agent stable, filterable class numbers that can interoperate with existing catalogue habits, while keeping the project wording, routing aliases and documentation under our own control.
