# PBR Duplas — launcher Windows

Windows GUI executable built with the .NET Framework/WPF already present in Windows 10/11.
No Python, administrator installation, browser server, CMD or external UI runtime is required.
The game remains the modified Dolphin edition, not a native port of Battle Revolution.

The existing CMD receives a core update and installs the launcher under the existing
LocalAppData/PBR-Duplas folder. Desktop and Start menu shortcuts use a stable, windowless
entry point. Game state, Dolphin settings, source paths, original image and saves are preserved.
Game and launcher versions are separate. Launcher-only updates do not reconstruct the RVZ.

Updates are HTTPS downloads from the existing GitHub channel, pinned by SHA-256,
with repository/tag checks, bounded ZIP extraction, a single updater lock and hidden workers.
A damaged download does not replace the installed game. Offline play uses the last verified RVZ.
Self-updates install executable versions side by side and update the stable shortcut.

For existing installations, graphics are recovered automatically from the hash-verified
managed RVZ into a persistent, revisioned library. Later updates reuse that library.
Changing a graphics revision explicitly invalidates the previous cache. No model picker
is opened by normal updates. Missing originals/dependencies are reported in the launcher.
Recovered graphics stay private on the user's PC and are not published on GitHub.

Windows CI compiles the WinExe, verifies package handling, legacy state migration,
hidden workers, graphics recovery, and renders the real WPF window. The preview command
uses illustrative installed-state labels and never starts Dolphin or accesses game files.
These tests do not claim gameplay or GPU rendering validation in Dolphin.
