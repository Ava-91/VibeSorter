# Desktop platform support and signing policy

## Supported build targets

The current release candidate has these supported desktop build targets. "Supported" means the target is built and smoke-tested in CI; it does not imply that every Linux distribution or CPU architecture is covered.

| OS | Architecture | CI target | Artifacts | Status |
|---|---|---|---|---|
| Windows 10/11 | x86_64 | `x86_64-pc-windows-msvc` | NSIS `.exe`, MSI `.msi` | Supported build; clean install, launch, upgrade/reinstall, and uninstall are exercised in CI |
| macOS (Apple Silicon) | arm64 | `aarch64-apple-darwin` | DMG, app bundle | Supported build; installation/upgrade/uninstall still require manual release verification |
| Linux (Ubuntu 24.04 CI environment) | x86_64 | `x86_64-unknown-linux-gnu` | AppImage, DEB | Supported build; installation/upgrade/uninstall still require manual release verification |

### Known limitations

- **Intel macOS (x86_64) is not supported for the v1.0 release.** There is no Intel Mac build or installer test in the current CI matrix. Do not advertise a universal or Intel-compatible macOS build.
- Linux packages are built on Ubuntu 24.04. Other distributions and desktop environments may work, but are not covered by the current automated matrix.
- ARM64 Windows and ARM64 Linux are not currently build targets.
- CI checks buildability and basic startup; they are not a substitute for a manual release acceptance pass on each supported OS.

## Signing and notarization

The current workflow does not configure an Authenticode certificate, Apple Developer ID signing identity, or Apple notarization credentials. Therefore:

- Windows NSIS/MSI artifacts are **unsigned** and may trigger SmartScreen/unknown-publisher warnings.
- macOS DMG/app artifacts are **not signed or notarized** by this workflow and may be blocked or warned about by Gatekeeper.
- Linux artifacts are not cryptographically signed as OS packages.

Do not describe the artifacts as signed, verified-publisher, notarized, or production-trusted. Before a public release, either configure and test the relevant signing credentials in repository secrets or explicitly publish the release as unsigned. Publish SHA-256 checksums for release artifacts and explain the unsigned status in the release notes. Signing credentials must never be committed to the repository or printed in CI logs.

## Install, upgrade, and uninstall acceptance

- **Windows:** CI installs into a clean temporary directory, launches the installed executable, reruns the installer over the existing installation as an upgrade/reinstall check, then silently uninstalls and verifies the executable is gone.
- **macOS:** before release, install the DMG into a clean user account, launch the app, replace it with the new version, launch again, remove the app, and verify no running VibeSorter process remains.
- **Linux:** before release, install the DEB on a clean Ubuntu 24.04 VM and test launch/upgrade/uninstall; test the AppImage from a clean user directory, then remove it and verify no process remains.

For each manual test, record OS version, architecture, artifact checksum, app version, install/upgrade/uninstall result, and any OS security warning in the release checklist. A release must not claim successful manual checks that were not actually performed.
