# Partner trial FAQ

[Read in Chinese](faq.md)

## What if verification fails?

Stop the installation. Check that the archive and external checksum file came from the same release. Keep their original names in the same download directory. Run the first command there. If it passes, extract into a new empty directory. Enter the extracted program directory and run the second command. If a fresh download still fails, report the affected filename and version. [Installation guide](../../AGENT_INSTALL.en.md) · [Verifier](../../scripts/verify_release.py)

```sh
shasum -a 256 -c SHA256SUMS
```

```sh
sh scripts/verify_release.sh
```

## Can I use my Python version?

This release was tested on Apple silicon with macOS 27.0.1 and Python 3.14.8. Check the versions on your Mac. Confirm that the same Python can load SQLite. If a step fails, share the versions and error type with the maintainer before proceeding. [Test environment](../guides/install-macos.en.md)

```sh
sw_vers
python3 --version
python3 -c 'import sqlite3; print(sqlite3.sqlite_version)'
```

## What if the port is in use?

From the program directory, run the command below using the two path variables you selected at installation. With the port omitted, PTDS selects a local port. Open the address printed for this run. Other programs can continue running. [Startup script](../../scripts/start_trial.py) · [Choosing paths](../../README.en.md#quick-start)

```sh
python3 -B scripts/start_trial.py --root "$SPACE_ROOT" --config "$TRIAL_CONFIG"
```

## What if macOS cannot verify the developer?

This release is unsigned and unnotarized. Signing and notarization are planned. Check the release source and complete both verification steps first. Use a macOS exception for **this item only** if you trust the verified copy and accept the risk of opening unverified software. After attempting to open it, go to System Settings → Privacy & Security. Check the blocked item name before choosing Open Anyway, if available. Stop and report the issue if the system reports damage or malware or does not offer a matching option. Keep system security protections enabled. [Release limitations](../../README.en.md#known-issues) · [Apple guide to opening unnotarized software](https://support.apple.com/guide/mac-help/mh40616/mac)

## What if an import fails?

Try the bundled fictional table at `data/sample-import.csv`. Check the selected space, accepted data type and column names. You should see two rows in review. Saving both unchanged rows with the same time returns `DUPLICATE_KEY_IN_BATCH` and writes neither row. For saving, correction and withdrawal, follow the [trial tasks](trial-tasks.en.md) to create and import a fictional copy with two times. For a lab report, use a clear image or PDF with labelled test, result and unit columns. Review each result against the original. If the outcome of saving is unclear, check the list and history before deciding what to do next. Report steps you can reproduce with fictional data. [First import](../guides/first-run.en.md) · [Recognition troubleshooting](../OCR-FAQ.en.md)

## What if Oura authorization does not finish?

In a fictional trial space, the Oura page offers setup instructions. If you choose to connect a real account, open Oura from My sources in a separate personal space that accepts real data. Check the receiving space and the provider address, then read the setup prompt. Make sure the callback registered for your developer app matches the callback for this PTDS installation. Set the secret for this instance in Terminal and authorize access yourself in your browser. Check the connection state and last sync time when you return. Keep secrets, authorization links and screenshots of the callback address bar out of agent conversations. [Oura setup](../guides/oura.en.md) · [Connection state display](../../app/device_links.py)

## How do I change the language?

Select the globe in the header. Choose English, Simplified Chinese or System. You can also choose a language on first launch. Your browser remembers the preference when local storage is available. [First launch guide](../guides/first-run.en.md) · [Language preference](../../app/web/language_switch.js)

## How do I delete one record?

Open the record in My data. Check the space, metric and date before selecting Delete and confirming. A retracted record leaves the current list. Earlier versions remain in its history. Genetic files have a separate Delete file action. See the uninstall guide to remove an entire space. [Version history](../../app/core/startorch_outbox.py) · [Genetic file deletion](../handbook/privacy.en.md)

## How do I remove PTDS completely?

Exit your own PTDS process first. Use the checklist to list and review the program, data space, settings, credentials and local preferences. You choose what to remove. Check your own source files and backups separately. [Uninstall and complete removal](uninstall.en.md)

## Why does some Chinese text remain in English?

Instance names, names you create, source descriptions, original filenames and historical records keep their original text. Some unrecognized system templates may also appear in Chinese. If a fixed button or heading appears in Chinese, reproduce it in a fictional space and send feedback. [Known issues](../../README.en.md#known-issues) · [Feedback guide](feedback.en.md)

## Are my data encrypted?

This release has no application-level encryption. A program with file access may be able to read SQLite databases, original lab reports, genetic files and local logs. Oura credentials are stored separately in the macOS keychain by default. We recommend enabling FileVault and protecting backups. [Threat model](threat-model.en.md)
