# VOCANTA v2.8.0, Production Recovery Release

## Root cause of the empty automation queue

VOCANTA v2.7.1 combined four restrictions that eliminated almost every job:

1. The automatic-application threshold was 85, while realistic entry and
   coordinator roles usually scored below that level.
2. Global remote detection recognised only a narrow set of exact phrases.
3. The existing Lever connector was never registered, so a major source of
   administrative and operations roles returned zero jobs.
4. Static profile records referenced documents inside old release folders.

## Production changes

- Automation threshold reduced from 85 to 70.
- Maximum required experience reduced to three years.
- Manager titles are blocked for the current campaign.
- The target taxonomy is restricted to the approved entry and mid-level roles.
- Worldwide, anywhere, global and all-countries signals are recognised.
- Lever is enabled with curated remote-work boards.
- Remote is added as a Greenhouse source.
- Himalayas remains disabled and Cloudflare pages are never opened.
- CV, cover letter and certificate are copied into:
  `%LOCALAPPDATA%\VOCANTA\assets`
- Existing profile paths are repaired automatically.
- Empty queues now show the precise rejection breakdown.

## Production estimate

The release is ready for immediate controlled live use. The first run should be
treated as a ten-application production pilot. Review the Action Centre after
the run, confirm form quality, then increase volume only after successful
submissions are verified.
