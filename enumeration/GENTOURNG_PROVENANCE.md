# gentourng regeneration provenance

## Upstream source

- Project: nauty and Traces
- Authors: Brendan McKay and Adolfo Piperno
- Version: 2.9.3
- Official page: `https://users.cecs.anu.edu.au/~bdm/nauty/`
- Source archive:
  `https://users.cecs.anu.edu.au/~bdm/nauty/nauty2_9_3.tar.gz`
- Retrieved: 2026-07-24 (Asia/Shanghai)
- Archive size: 5,496,724 bytes
- HTTP `Last-Modified`: Wed, 31 Dec 2025 12:56:43 GMT
- HTTP `ETag`: `"53df94-6473f021451b3"`
- Archive SHA-256:
  `9fc4edae04f88a0f5883985be3b39cf7f898fd6cc96e96b9ee25452743cc1b5b`

## Build

```bash
./configure
make -j2 gentourng labelg
```

Recorded environment:

```text
Ubuntu 22.04.5 LTS under WSL2
gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0
GNU Make 4.3
```

Locally built executable SHA-256 values:

```text
gentourng  1bf9ad91eea91da85d2b3984019b4c798f4378acf542143d338c84182d103257
labelg     2e1a5213ebfcc26ab48d677eb58d532cf69783df801821b705cb7e6ddfaf6071
```

The executables and source tree are not committed.

## Complete regeneration

The complete generation command was:

```bash
gentourng -d6 -D6 13
```

`gentourng` reported:

```text
1495297 graphs generated
```

Its default upper-triangle ASCII stream was piped directly into
`verify_rt13_catalog`. The verifier independently checked that every record
was a 6-regular tournament and obtained the same distribution as the
downloaded catalogue:

```text
11 strong vertices:        13 classes
12 strong vertices:        48 classes
13 strong vertices: 1,495,236 classes
```

The 61 exceptional outputs from both routes were converted to digraph6 and
canonically labelled with the freshly built `labelg`. Their canonical sets
were identical, and the strong count agreed class by class. See
[EXCEPTION_SET_COMPARISON.json](EXCEPTION_SET_COMPARISON.json).

The source archive is authenticated before extraction by
[run_gentourng.sh](run_gentourng.sh), which rebuilds both upstream tools and
repeats the entire generation, verification, and comparison.
