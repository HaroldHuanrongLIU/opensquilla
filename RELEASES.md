# OpenSquilla Releases

| Version | Tag | Date | Notes |
|---|---|---|---|
| 0.1.0rc1 | v0.1.0rc1 | 2026-05-12 | First public preview |

`0.1.0rc1` publishes one cross-platform wheel plus Windows-only portable
runtime assets:

- `OpenSquilla-<version>-windows-x64-py312-recommended-portable.zip`
- `OpenSquilla-windows-x64-portable.zip`
- `opensquilla-<version>-py3-none-any.whl`
- `opensquilla-latest-py3-none-any.whl`
- `SHA256SUMS`

GitHub source archives remain available for code review and developer
reference; source installs should use `git clone` plus Git LFS. Public
wheelhouse zips, macOS portable zips, and Linux portable zips are intentionally
not published for this preview. macOS and Linux users install the same
`opensquilla-latest-py3-none-any.whl` wheel through the `uv tool install`
command documented in the README.

## Preview tag SOP

1. Verify `git status` is clean.
2. Update `CHANGELOG.md`: move entries from `[Unreleased]` to `[0.1.0rc1] - <date>` section; reopen empty `[Unreleased]`.
3. `git tag -a v0.1.0rc1 -m "OpenSquilla 0.1.0 Preview 1"`
4. `git push origin v0.1.0rc1` (this triggers `.github/workflows/wheelhouse-release.yml`)
5. Wait for the Windows release workflow → review the draft GitHub Release.
   Confirm it contains exactly the five OpenSquilla assets listed above, plus
   GitHub's generated source archives, before publishing.
6. Publish the GitHub Release, then run the post-publish latest URL checks:

   ```sh
   curl --fail --head --location https://github.com/opensquilla/opensquilla/releases/latest/download/OpenSquilla-windows-x64-portable.zip
   curl --fail --head --location https://github.com/opensquilla/opensquilla/releases/latest/download/opensquilla-latest-py3-none-any.whl
   ```

7. For subsequent previews: bump `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, and the tag to `0.1.0rc2`, `v0.1.0rc2`, etc.

## GitHub-only release checks

These checks cannot be fully proven by local artifact generation:

- The tag exists on GitHub and matches `pyproject.toml`.
- The release workflow can fetch hydrated Git LFS router assets.
- The GitHub Release contains the versioned assets, stable aliases, and
  `SHA256SUMS` after `gh release upload --clobber`.
- After the GitHub Release is published, the stable release URLs resolve:
  `.../releases/latest/download/OpenSquilla-windows-x64-portable.zip` and
  `.../releases/latest/download/opensquilla-latest-py3-none-any.whl`.
- Windows browser downloads may carry Mark-of-the-Web; SmartScreen,
  Smart App Control, enterprise policy, and unsigned binary reputation must be
  checked on a real Windows machine.

## Why the package version uses rc

Release zips are distributed as built artifacts, so the package filename,
manifest, zip name, and tag should describe the same preview build. PEP 440
accepts `0.1.0rc1`, while the public GitHub Release title can use the friendlier
name "OpenSquilla 0.1.0 Preview 1".
