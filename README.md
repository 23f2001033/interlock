# Interlock

**AI coding agents pass alone and break together. Interlock lands their changes safely.**

Give Interlock a goal, like "land these AI-written branches on `main`". It finishes only when every change is merged **and** the combined code is proven consistent. It finds changes that pass alone but fail together, proves each with a test that passes on its own branch and fails on the merge, tells the responsible coding agent exactly what changed, and re-verifies, even while `main` keeps moving.

Built for [#neatHack](https://neatlogs.com/hackathon) with [neatlogs](https://neatlogs.com) (tracing), [Entire](https://entire.io) (checkpoints + entire-graph) and [cfo.ai](https://cfo.ai) (business plan).

> 🚧 Being built live during the hackathon (Oct 10-12, 2026). See the [build log](hackathon.md), the [design spec](docs/SPEC.md) and the [demo scenario](docs/DEMO_SCENARIO.md). Demo environment: [interlock-demo-shop](https://github.com/23f2001033/interlock-demo-shop).
