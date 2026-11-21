# If the lead session stops: how to continue

**State at 2026-11-21 05:00: the handoff is final** (`MORNING-HANDOFF.md`). Item 5 below is done: join checks,
sample loader, smoke test and the live-API cross-check are committed. What follows is only needed if work resumes.

For a continuation session (for example Opus 5.5) taking over the lead role. Everything needed is on disk.

1. Read `lead/CONTRACT.md` (rules), then `MORNING-HANDOFF.md` (state), then each folder's `STATUS.md`.
2. You are the only committer. Workers never stage. Never push, never open a PR, never touch files outside
   `bern-research/`.
3. Identity, verified on 2026-11-21 with `gh api user` (login `ktr0a`, id 107317602). Use it per commit, do not
   change git config:
   `git -c user.name="ktr0a" -c user.email="107317602+ktr0a@users.noreply.github.com" commit -m "..."`
   No co-author or tool attribution lines. After each commit run
   `git log -1 --format='%an <%ae> | %cn <%ce>%n%B'` and check it.
4. Snapshot routine, per folder that marks paths ready in its `STATUS.md`:
   - `python -I bern-research/lead/validate/validate.py` and read `lead/validate/REPORT.md`;
   - a FAIL blocks that folder's commit: tell the owning thread what failed, do not fix their files yourself;
   - stage explicit paths only (`git add -- bern-research/<folder>/...`), never `git add -A`; check
     `git diff --cached --stat` for size and for anything outside the folder; commit one folder per commit;
   - update the snapshot table and coverage numbers in `MORNING-HANDOFF.md` and commit it.
5. Still owed by the lead: cross-folder join checks (`lead/validate/joins.py`, loaded by `validate.py`), a thin
   sample loader under `lead/sample/` (one page that overlays the outputs on the swisstopo map style; not an app),
   and the final `MORNING-HANDOFF.md` by 07:00 Europe/Zurich. Independent data reviews run at 03:00 and 05:00 and a
   handoff review at 06:40; fold their findings into the handoff.
6. Worker thread ids: transit `bafab213-6bd0-4829-aa1b-8e0ad45c900e`, city3d
   `590c38a9-d4b9-4bfa-bebb-c771b71a475a`, stations `aaf860f8-a5da-49ad-bdb4-b6d33024426f`, references
   `ffae8393-bcbe-4856-9110-961efbf752a1`. Freeze for workers is 06:15.
