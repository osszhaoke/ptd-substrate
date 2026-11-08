# Agent installation protocol · v0.3.0-alpha.2

[简体中文](AGENT_INSTALL.md)


## Source and verification
Download only the archive and SHA256SUMS from [this GitHub Release](https://github.com/osszhaoke/ptd-substrate/releases/tag/v0.3.0-alpha.2). Go offline afterwards. In a fresh directory run `shasum -a 256 -c SHA256SUMS` before extraction. Enter the extracted directory and run `sh scripts/verify_release.sh`. Continue only if all files match. Stop on missing, extra or changed files. The release is unsigned. The hashes check consistency with the manifest you obtained. Publisher identity requires a separate check.

## Environment
Check only `sw_vers`, `python3 --version` and the Python SQLite import. See [Quick start](README.en.md) for the tested environment. No pip install, npm packages, administrator access or model is needed. If a requirement is missing, report it and stop.

## Let the user choose a space
Ask the user for a new data root, instance ID, display name, time zone and configuration output location. Create that space with the supplied initializer. The user then operates the bundled installer in Terminal. It accepts an initialized directory. Never guess the target, list personal directories, overwrite existing settings or reuse an old space. The public example configuration is for reference. Follow the two Python commands in [Quick start](README.en.md). Choose 1 for a fictional trial. The installer creates the initial settings file once.

## Start and import
Run `python3 -B scripts/start_trial.py --root "$SPACE_ROOT" --config "$TRIAL_CONFIG"`. Give the printed loopback address to the user. The random port belongs to this process. Let the user choose a language. Open `data/sample-import.csv` in the CSV import screen. Stop at review. Both identical rows should be present. Only the user can press Save. Use Ctrl+C to quit. To reopen an existing space, start it directly without creating it again.

## Optional Oura and boundaries
Real account access needs a separate user decision. See the [Oura guide](docs/guides/oura.en.md). The user enters credentials into the local keychain in Terminal and grants access in their browser. The agent must not query the keychain, collect or repeat secrets or read health values. Do not install dependencies, change source or settings, upload data, enable blocked channels or read other user files. Reproduce errors with fictional data. Stop when the result of an operation is uncertain.

## Raw genetic files

The person chooses the file and declares its data type. An agent may invoke import only at their request. The agent must not open, read, repeat or analyze the contents of a personal genetic file. Use app/fixtures/fictional-genotype-sample.txt for rehearsal.

For a fictional trial, pass `--accept SYNTHETIC` when creating the space, then choose 1. For an explicitly dual-type personal space, pass `--accept REAL SYNTHETIC` with `--kind REAL` and choose 2. Stop if the installer reports different data types. It does not change an existing space.

For lab report OCR, ask the user before guiding them to install the Xcode Command Line Tools. Do not read or repeat the contents of a user’s report. Never confirm a row or save the report for the user. Use app/fixtures/fictional-lab-report.png to demonstrate how to start a review.
