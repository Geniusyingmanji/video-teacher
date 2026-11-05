# Shared layout repair for generated teaching videos

The shared generator and renderer now handle source ownership and label spacing
for every versioned lesson, without dispatching on task IDs or subject names.

- Portrait source images get a left reference area and a right teaching panel;
  landscape references get an upper reference area and a lower teaching panel.
  Both leave a separate title area. Source edits use original pixel coordinates.
- The renderer exposes its single source as `self.source_image`. Code preflight
  rejects another ImageMobject, copies, resizing, movement or common animations
  of that reference, including direct aliases. Generation can correct this
  preflight finding twice before rendering, retaining every model response.
- Before reveals and holds, text uses actual bounding boxes to find the nearest
  clear position inside its panel. Plain-text explanations wrap at the available
  width; undersized glyphs enlarge. Source edit text stays fixed at its authorized
  target. Captions reserve their own space. No text is deleted to clear a clash.
- Layout diagnostics additionally detect overlapping opaque images, text over a
  protected source, and text outside its teaching panel. Transparent annotation
  layers are not treated as duplicate opaque images. Unsolvable overcrowding
  remains an explicit failed check rather than a fabricated pass.

Validation: 59 focused regression tests, plus the strict-contract and generation
repair suites. Four actual scenes were rendered: a worked mathematics solution,
two standalone physics diagrams, and a source-image completion. All passed layout
and exact-duration checks; the source task also passed pixel preservation. The
mathematics and both physics scene programs were reused without task-specific
edits. The source scene was migrated to the shared source primitives, retaining
its original target boxes and chapter timing.

Three narrated previews are in
`/root/本轮成功视频_20261105_round02/通用排版修正版/`.
Their original audio tracks were remuxed without changing chapter boundaries.
These are layout regressions, not new full teaching-quality certifications.
Full fixed-ten validation must run from the committed version in a fresh round.
