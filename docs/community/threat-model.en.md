# Threat model

[Read in Chinese](threat-model.md)

## What the program protects

| Situation | Protection in this release | Evidence |
|---|---|---|
| Import into the wrong space or save by mistake | Choose the receiving space at installation. The partner routes check the target. Tables and lab reports show candidates first. Review lab results one at a time. Saved results keep their source relationships. Use your own copy for the original CSV text. | [Target checks](../../app/trial_target.py) · [Review flow](../../app/partner_ocr.py) · [Source lookup](../../app/evidence_navigation.py) |
| Another device tries to reach the app | The partner service binds to a loopback address. It admits permitted routes and checks local write requests. | [Service entry](../../app/server.py) · [Request checks](../../app/trial_target.py) |
| Unintended transmission | Third-party device connections are off in the default installation. Oura requires configuration and your consent. It uses the matching data space. Settings can override service addresses. Check the provider address and local callback before granting access. | [Installer](../../app/tools/partner_trial_setup.py) · [Oura setup](../guides/oura.en.md) |
| Credentials included in data or feedback | In the default macOS setup, Oura uses the system keychain under service `ptds-oura`. Entries are specific to the instance. If you choose file storage, the app creates new directories and files with owner-only permissions. The credentials in them are plain text. Updating an existing file does not tighten its permissions or those of its directory. Check that only you can read an existing store. | [Credential storage](../../app/oura.py) · [Security reporting](../../SECURITY.en.md) |

## Data stored without encryption

**This release has no application-level encryption.** Both main databases in your chosen space use standard SQLite. Saving a lab report keeps the original bytes and stores recognition details separately. PTDS keeps genetic originals as supplied and builds a SQLite locus index. The event log and genetic import receipts use readable text. File permissions, checksums and database transactions do not encrypt these files. We recommend turning on disk encryption in System Settings → Privacy & Security → FileVault. Protect backups separately. [Main databases](../../app/core/sqlite_util.py) · [Lab report originals](../../app/partner_ocr.py) · [Genetic originals and receipts](../../app/gene_assets.py) · [Locus index](../../app/gene_db.py) · [Event log](../../app/server.py)

## Your Mac and third parties

Someone who has compromised your Mac, a local program with permission to read the files or someone using your unlocked account may be able to read health records. FileVault protects data at rest. Programs with permission can still read files in a signed-in session. PTDS cannot control data already held by the device provider, copies you exported or separate backups. Lock your screen and use separate accounts on a shared Mac. [Local data guide](../handbook/privacy.en.md) · [Deletion and uninstall](uninstall.en.md)
