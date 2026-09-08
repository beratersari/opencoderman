---
name: cpp
description: C and C++ review. Load when the diff changes *.c, *.cc, *.cpp, *.cxx, *.h, *.hh, *.hpp, *.hxx, or *.inl. Detect the dialect here. Do not load when no C/C++ files changed.
license: MIT
compatibility: opencode
---

# C / C++

Load when C or C++ files changed. Detect the dialect before
reviewing. Project rules still win.

## Dialect

Prefer an explicit standard in `agent/rules/CODE_REVIEW.md`,
`AGENTS.md`, `CLAUDE.md`, or `CONTRIBUTING.md` (for example
"C++98", `-std=c++11`). If none state it, read only these
(skip missing): `CMakeLists.txt`, `CMakePresets.json`,
`Makefile`, `meson.build`, `compile_commands.json`,
`.clang-tidy`. Look for `CMAKE_CXX_STANDARD`, `-std=c++`,
`/std:c++`. Use the oldest standard you can confirm.

Then load exactly one dialect skill:

- C++98 or C++03 → `skill({ name: "cpp98" })`
- C++11 or later → `skill({ name: "modern-cpp" })`

Do not load both. Do not load either if the standard is
unknown; say so in the summary and do not assume modern C++.
Never suggest features newer than the confirmed dialect.

Then load only the extra skills the **hunk** matches
(typically 0–3):

- `strcpy` / `sprintf` / `memcpy` / `new[]` → `cpp-memory-safety`
- thread / mutex / atomic / pthread → `cpp-concurrency`
- try / catch / throw / `noexcept` → `cpp-exceptions`
- `template` / `concept` → `cpp-templates`
- changed `*.h` / `*.hpp` / `*.hxx` / `*.inl` → `cpp-headers-odr`
- `vector` / `string` / `map` / `<algorithm>` → `cpp-stl`
- size / index / shift / float → `cpp-numerics`
- new `#define` / `#ifdef` → `cpp-preprocessor`
- `CMakeLists.txt` / meson / Makefile / vcxproj → `cmake-cpp`
- gtest / Catch2 / `add_test` → `cpp-testing`

## Do not flag

- Style, naming, or include order unless project rules say so.
- Pre-existing issues this change did not cause.
