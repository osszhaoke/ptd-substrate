# Partner trial tasks

Use v0.3.0-alpha.2, a new fictional data space and the bundled samples for tasks 1 to 7. Choose whether to connect your own account in task 8. Note the task number if you report a problem. [Chinese version](trial-tasks.md)

## Prepare a copy for the save exercise

The two observations in the bundled `data/sample-import.csv` have the same time. You can review both rows. Saving them unchanged together returns `DUPLICATE_KEY_IN_BATCH` and writes neither row. For tasks 3 to 6, run the command below in Terminal **from the extracted program folder**. It keeps the bundled file intact and changes the second fictional observation from 08:00 to 08:01 in a new copy. Note the path printed in Terminal.

```sh
python3 - <<'PY'
from pathlib import Path
import tempfile
source = Path("data/sample-import.csv")
rows = source.read_bytes().splitlines(keepends=True)
assert len(rows) == 3 and rows[1].rstrip() == rows[2].rstrip()
old = b"2026-11-01T08:00:00+08:00"
new = b"2026-11-01T08:01:00+08:00"
assert rows[2].count(old) == 1
rows[2] = rows[2].replace(old, new)
copy = Path(tempfile.mkdtemp(prefix="ptds-trial-")) / "sample-two-times.csv"
copy.write_bytes(b"".join(rows))
print(copy)
PY
```

| Task | What to do | Expected result | What to report if it differs |
| --- | --- | --- | --- |
| 1. Verify and install | Download the archive and external SHA256SUMS for the same version. Verify the archive, extract it and run the checks inside. Follow the installation guide to create a fictional space. | Both checks pass. After startup, Terminal shows a local address starting with 127.0.0.1. | Give the step where verification or startup stopped and the short error message. Stop installation if verification fails. |
| 2. Choose a language | Open that address in a browser using the trial for the first time. Choose English, Simplified Chinese or the system language. Open the space you just created. | The page uses your chosen language. The globe in the top bar lets you change it later. | Give the options you saw, your choice and the page that used a different language. |
| 3. Import, review and save | Open My sources → Files and reports → CSV file and choose the sample-two-times.csv copy created above. Check that the values and units match the copy and that the times read 08:00 and 08:01. Confirm the save yourself. | Both rows appear for review. After saving, you can find the imported data in My data and open its details. | Say whether the problem happened when selecting the file, reviewing it or saving it. Give the number of rows you saw. If the save result is unclear, check the list first. |
| 4. Correct one record | Open the 08:00 fictional record in My data. Choose the correction action. Change the value on that record and follow the steps to save it. | The details show the corrected value. The version history keeps the original value. | Identify the view and whether the current value or an earlier version differs from what you expected. |
| 5. Delete one record | In the fictional space, open the record you corrected. Choose the delete action and confirm it yourself. | The record is withdrawn from the current list. The other record remains available. The history keeps the withdrawal. | Say whether you checked the current list, the history or the other record. |
| 6. Open the evidence graph | Open StarTrace → Evidence graph. Select Body temperature, then the only row showing 36.50 °C. Compare its details with the second observation in your saved copy of sample-two-times.csv. | The details show 2026-11-01 08:01 and 36.50 °C, matching your copy. The Table import node shows the import relationship. It cannot open this CSV file. | Say whether you selected the metric or the import node and give the row, time or message you saw. |
| 7. Query and delete the genetic sample | Under Files and reports, import the bundled fictional genetic sample. Choose fictional data. View its properties and look up rs9100000000. Choose Delete file under the filename and confirm. | You can find the sample locus before deletion. After deletion, the file disappears. With only this sample imported, the locus also disappears. | Say whether import, lookup or deletion stopped. Share only the fictional sample name and the state shown on screen. |
| 8. Optional Oura connection | The fictional space used in tasks 1 to 7 offers Oura instructions only. If you choose to connect your own account, use a separate personal space that accepts real data. Check the receiving space and provider address on the Oura page, then follow the setup guide. Enter credentials in Terminal yourself. Sign in and grant access in your browser. | After authorization, check the connection state on the device page. Check the last sync time after the first successful sync. | Identify the step in setup, the return from authorization or sync and give the state on screen. Leave out account details, credentials and health readings. |

[Installation guide](../../AGENT_INSTALL.en.md) · [First run and review](../guides/first-run.en.md) · [CSV sample](../../data/sample-import.csv) · [Fictional genetic sample](../../app/fixtures/fictional-genotype-sample.txt) · [Oura guide](../guides/oura.en.md) · [Give feedback](feedback.en.md)
