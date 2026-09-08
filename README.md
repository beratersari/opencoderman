# OpenCoderman

OpenCode agents and a general skill library. One home: `~/.opencode`.
The `code-reviewer` agent is OpenCoderman. **derman-build**
implements; **derman-plan** plans. They are general unattended
agents, not stock OpenCode `build` / `plan`. Language, style, build
commands, and commit format come from the target repo (`AGENTS.md`
and `git log`). They load the same `skills/` tree. Installers copy
every `skills/*/SKILL.md`. Each skill says when to load.

```
agents/           # -> ~/.opencode/agents/<name>.md
  code-reviewer.md    # Reviewer for GitLab MRs and Azure PRs
  derman-build.md     # General unattended implementer (not stock build)
  derman-plan.md      # General unattended planner (not stock plan)
skills/           # -> ~/.opencode/skills/<name>/SKILL.md
```

## Skills

General library. C++ is one language group, not the product focus.
Load the skill that matches the files you touch.

**Languages:** `python` `javascript` `typescript` `go` `rust`
`java` `kotlin` `csharp` `swift` `php` `ruby` `dart` `scala`
`elixir` `shell` `powershell` `lua` `r-lang`

**C++ (when the repo is C++):** `cpp` `cpp98` `modern-cpp`
`cpp-memory-safety` `cpp-concurrency` `cpp-exceptions`
`cpp-templates` `cpp-headers-odr` `cpp-stl` `cpp-numerics`
`cpp-preprocessor` `cmake-cpp` `cpp-testing`

**Web / UI:** `html-css` `frontend-ui` `react` `vue` `nodejs`
`nextjs` `accessibility` `i18n`

**Mobile:** `android` `ios`

**Frameworks:** `django` `spring` `rails`

**Data / API:** `sql` `postgresql` `mongodb` `redis` `rest-api`
`graphql` `grpc` `protobuf` `websocket` `api-compat` `caching`
`messaging`

**Security:** `secrets` `web-security` `auth` `oauth-oidc`
`security-owasp` `cryptography`

**Cloud / infra:** `aws` `linux` `ci` `docker` `kubernetes`
`terraform` `dependencies` `networking` `licensing`

**ML / quality:** `machine-learning` `performance` `observability`
`privacy-logging` `error-handling` `documentation` `testing`
`refactoring` `root-cause` `verification`

**Implementer-only** (do not allow on `review`): `tdd` `debugging`
`git-commits` `planning`

Drawn from [oh-my-opencode](https://github.com/code-yeongyu/oh-my-opencode),
[obra/superpowers](https://github.com/obra/superpowers),
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills),
[anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review),
[waybarrios/opencode-power-pack](https://github.com/waybarrios/opencode-power-pack).
Not copied wholesale (no browser/commit bots on the review agent).

Add a new agent by dropping `agents/<name>.md`. Add a skill as
`skills/<name>/SKILL.md`. Installers copy every file they find.

## Replace install (this repo)

`install.py` **renames** `~/.opencode` to
`~/.opencode_backup_YYYYMMDD_HHMMSS`. A leftover `~/.config/opencode`
is renamed to `~/.config/opencode_backup_YYYYMMDD_HHMMSS` so OpenCode
does not load a second tree. The installer does **not** write anything
under `~/.config/opencode`. It does not delete those backup trees. If
another OpenCode exists (another folder on PATH, or `OPENCODE_HOME` /
`OPENCODE_INSTALL` / `OPENCODE_BIN`), those files stay where they are.
That directory is removed from the user PATH so `opencode` does not
resolve there. Put the old path back if you still want that copy.
System dirs such as `/usr/local/bin` are not stripped.

A CI artifact (or `vendor.sh`) ships `vendor/bin/<os>/opencode`.
`install.py` copies that CLI into `~/.opencode/bin`. If vendor is
missing, it reuses the binary from the newest backup. A git checkout
without `vendor/` is agents/skills only.

```bash
# Offline: unpack the GitHub Actions artifact, then:
install.bat
./install.sh

# Online checkout: download the CLI once, then install:
vendor.bat
./vendor.sh
python install.py --root .
```

Windows: user PATH in `HKCU\Environment`. Linux: `PATH` plus a marked
block in `~/.profile`. Other products (for example Creasy) can call
the same `install.py`, then copy their own `vendor/bin` if they have
one.

## CI artifacts

Push to `main` uploads folders named
`opencoderman-1.18.10-windows` and
`opencoderman-1.18.10-linux` (`OPENCODE_VERSION` in
`packaging/versions.env`). GitHub wraps each folder as a zip; the
download is not a zip of a zip. Each artifact has `agents/`,
`skills/`, the install scripts, and `vendor/bin/<os>/` with the
OpenCode CLI. Target install does not need network.

On a machine with network you can vendor into a checkout:

```bash
python packaging/build_artifact.py --in-place
```

`--skip-binary` stages an agents/skills-only folder (no CLI download).

## Use in another repo

```bash
git submodule add https://github.com/beratersari/opencoderman.git opencoderman
git submodule update --init --recursive
```
