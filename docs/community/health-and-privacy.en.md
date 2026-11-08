# Health and privacy

[Read in Chinese](health-and-privacy.md)

**PTDS results are signals for your attention. They do not provide a diagnosis or treatment advice.** Lab report recognition can make mistakes. Check each test, value, unit and date against the original before you decide to save it. You can store raw genetic files and look up individual loci. PTDS does not interpret disease risk. [Release capabilities](../../README.en.md#capabilities-and-evidence) · [Recognition guide](../OCR-FAQ.en.md)

## Using PTDS on your Mac

The default installation listens only on the loopback address. Your chosen data space stays on your Mac. Pages and fonts come with the program. Health records, saved originals, genetic files and local logs have no application-level encryption. We recommend turning on FileVault in macOS and protecting separate backups. [Privacy guide](../handbook/privacy.en.md) · [Threat model](threat-model.en.md)

## If you choose to connect Oura

If you choose Oura, use the personal space selected at installation. Check the app and the requested access before you authorize it. By default the authorization page opens at `cloud.ouraring.com` or `developer.ouraring.com`. Token exchange, approved data requests and token revocation use `api.ouraring.com`. The default callback returns to `127.0.0.1` on your Mac. Settings can override these destinations. The app does not enforce a fixed list of hosts. Check the provider address and local callback before granting access. Stop if you see an unfamiliar destination. Oura manages the data already held in its cloud. [Oura guide](../guides/oura.en.md) · [Service addresses](../../app/oura.py) · [Space binding](../../app/device_targets.py)

## Giving feedback

Use a bundled fictional sample to reproduce the issue. Include the version, steps and a screenshot with personal details covered. Keep real lab reports, genetic files, databases, logs, settings and credentials out of feedback. Report security vulnerabilities privately. [Feedback guide](feedback.en.md) · [Private reporting](../../SECURITY.en.md)
