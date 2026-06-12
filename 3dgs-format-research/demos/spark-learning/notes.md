# Spark RAD Streaming Learning Notes

This folder is a small learning snapshot from reading Spark 2.x RAD streaming LoD code.

## Demo

- `rad-streaming-demo.html` opens a minimal Three.js scene and loads a remote `.rad` 3DGS scene with `new SplatMesh({ url, paged: true })`.
- `spark-rad-fullscreen-test.html` is the larger fullscreen HUD version that was originally left in the repository root as `index.html`; it is now archived here with the Spark learning demos.
- The demo wraps `window.fetch` to print `.rad` requests, so Chrome DevTools can show Spark's `Range: bytes=...` chunk loading.
- The page imports Spark from npm CDN instead of committing the full Spark source tree.

## Source Code Trail

The Spark source was inspected from `https://github.com/sparkjsdev/spark`.

Key implementation areas:

- `src/SplatMesh.ts`: `paged: true` creates a `PagedSplats` source.
- `src/SplatPager.ts`: reads RAD metadata, fetches chunks by HTTP Range, decodes chunks, and uploads pages.
- `src/SparkRenderer.ts`: drives LoD traversal from the current camera and pushes requested chunks into the pager.
- `src/worker.ts` and `rust/spark-rs/src/lod_tree.rs`: traverse the LoD tree and return render indices plus chunk requests.
- `rust/build-lod` and `rust/spark-lib/src/*_lod.rs`: generate the offline LoD tree.

## LoD Tree Summary

Spark's `.rad` file contains a precomputed LoD tree. The tree is built offline by merging nearby and visually similar splats into coarser parent splats. Each LoD node stores `child_count` and `child_start`, which let runtime traversal expand a coarse node into its children when the camera needs more detail.

At runtime Spark does not generate the tree from scratch. It reads the encoded tree data from downloaded chunks, maps chunks into GPU pages, and traverses the available tree according to camera position, view direction, screen-size threshold, and splat budget.
