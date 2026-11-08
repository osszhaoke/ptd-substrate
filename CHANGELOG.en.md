# Changelog

## v0.3.0-alpha.2

Older lab reports can have a row number printed before the test name. You can open a saved result and see the original line, including its row number. A number that is part of the test name stays in that name.

When you trace a result, PTDS checks the recorded source text against the original line. If they conflict, the source is shown as unavailable. Your saved result stays in your data space.

A flag column can contain a note such as “Normal”. When you open a saved result, PTDS checks the original line, including the result and its unit.

A lab report can have an empty flag or reference range. PTDS can show the original line when the remaining columns identify a single result. In the evidence graph, the document details use your chosen language and keep the original filename.

If the result in the saved source text contradicts the recorded result, the app reports that it cannot identify the source line. A matching number in the reference range does not qualify.

When an earlier batch and a whole-report import share a PDF, PTDS checks the page, original text and saved record before showing its source. If the line cannot be identified, PTDS reports that it is unavailable.

The reader requires a new result header after a table section ends. A conflict in previously stored source evidence, including page-specific records, stops the save.

The reader needs separate labelled columns for the test, result and unit. A reference limit, ambiguous value or unrecognised unit cannot be selected for saving. The running reader is verified on this Mac before it starts reading the file. Review unmatched lines against the original and enter them manually if needed.

The partner reader uses a Vision helper compiled from this installation. After you restart PTDS, the first recognition or PDF preview requires the Xcode Command Line Tools again. Separate readings for the same metric appear as separate rows. Review each one against its source.

The partner edition reads lab reports on your Mac with Vision and a local synonym list. No model is used or downloaded. First use needs the Xcode Command Line Tools. Handwriting and blurry images can reduce accuracy. Check each selected value, unit and sampling time against the original before saving. Only one report up to 64 MiB may be in review at once. A review expires after 30 minutes; discard it to clear the draft. The bundled lab report is fictional.

## v0.3.0-alpha.1

Partner trial. Adds the English disclaimer on inner pages, accessible labels and whole-page checks with fictional data.

Adds local raw genetic file storage, per-file deletion and data type checks. Verified with fictional files only.

The creator, installer and startup checks now agree on the data types a space accepts. Import, correction, deletion and accessible text follow the selected language. The font inventory identifies both embedded families. The first language choice saves one local preference.

Keep StarTrack database coordination files stable for the application lifetime. Translate the correction and deletion success receipts.
