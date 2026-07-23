# Complete-catalogue enumeration audit

## Scope

This audit checks the sharp order-13 result by a route that does not use
the SAT generator, CNF instances, solver, symmetry branches, or RUP
certificates. Its external input is Brendan McKay's catalogue of all
1,495,297 non-isomorphic regular tournaments of order 13.

## Checks performed

1. The downloaded `rt13.txt.gz` passed `gzip -t`, had exactly 1,495,297
   records of 78 bits, and matched the pinned SHA-256 in
   [DATASET_PROVENANCE.md](DATASET_PROVENANCE.md).
2. The C++ verifier was compiled with
   `g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -Werror`.
3. Every record was decoded and checked to be a 6-regular tournament.
4. Each of the 19,438,861 rooted vertex instances was decided both by
   exhaustive Hall-subset enumeration and by a separately implemented
   augmenting-path maximum matching. There were zero disagreements.
   The complete run is recorded in
   [REPRODUCTION_RUN.log](REPRODUCTION_RUN.log).
5. A second full run produced a byte-identical `RESULTS.json`
   (`cdf8c323cfb943f5cd1ed07e250ad090170b985364d2d3a3eaad0c71b7c11fac`);
   see [REPRODUCTION_RUN_REPEAT.log](REPRODUCTION_RUN_REPEAT.log).
6. An AddressSanitizer/UndefinedBehaviorSanitizer build checked the first
   1,000 records without a diagnostic; see
   [SANITIZER_SAMPLE.log](SANITIZER_SAMPLE.log).
7. A separate Python program decoded the first tight witness and recomputed
   all thirteen matching sizes by exhaustive partial injections, then
   checked all Hall defects and the original catalogue record.

## Environment

```text
Ubuntu 22.04.5 LTS under WSL2
g++ (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0
Python 3.10.12
```

The optimized executable was built locally and was not committed. Its
SHA-256 for the recorded run was
`07cbf61ac0d05848588a307cc87b9c057bb227b186ee673a312421c283c21094`.

## Outcome

The minimum number of strong Seymour vertices was 11. It was attained by
13 isomorphism classes. There were 48 classes with 12 strong vertices and
1,495,236 classes with all 13 vertices strong.

This establishes an independent cross-check of the SAT reduction, subject
to the catalogue trust boundary stated in [README.md](README.md).
