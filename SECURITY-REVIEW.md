# SDM source and dependency review

Reviewed on 2026-10-12. This is a focused source review, not a security
certification or proof that all dependencies are free of malicious behavior.

## Findings

- No fixed collection server, analytics endpoint, remote command channel,
  credential harvesting routine or arbitrary local-file upload was found in
  the eight application Python source files inspected.
- Network use in application code is downloading user-selected URLs with
  requests and retrieving video metadata/media with yt-dlp. Download sites
  and their infrastructure can see the client's public IP address.
- The single-instance lock binds to 127.0.0.1:49281. The new browser bridge
  binds to 127.0.0.1:49282. It requires an exact extension Origin, loopback
  Host and a random per-user token obtained through native messaging.
  Supported page hosts are checked; local addresses and spoofed domains
  are rejected. The bridge accepts format lookup and queued downloads only.
- Original extension permissions were limited to native messaging, local bridge
  access and content scripts on listed video sites. No cookies or password
  storage permissions are requested.
  Update 0.3.0 adds the downloads permission to intercept user/browser
  file downloads. It does not add cookies or password access. File URLs
  and each redirect are checked against local/private network targets.
  The original download is resumed if preflight/transfer fails.
- Clipboard monitoring reads local clipboard text when enabled. Full URL
  logging was removed because URLs may contain private tokens. Opening a
  detected video dialog may fetch metadata from that video site.
- Download history, URLs and custom headers are persisted locally in SQLite.
  They are not encrypted. Error logs can contain URLs from library errors.
- File opening uses os.startfile after a user action. Explorer is started
  with an argument list, without shell=True. Downloaded files are not
  automatically executed by the download engine.
- Base64 in assets/icon.py encodes a locally generated PNG icon.
- Original download validation accepted HTTP 200 for Range requests and
  did not reject incomplete segments. These cases now fail safely; segment
  byte ranges and lengths are checked, and non-resumable downloads restart.

## Verification

- Source GUI startup and packaged executable startup checks completed with
  exit code 0, using separate test data directories.
- Ten local regression tests passed, covering download validation,
  bridge authentication, host restrictions, quality and MP3 queue handling.
- In isolated Chromium, the actual extension displayed its button and
  fetched formats through the authenticated bridge. 1080p and MP3 choices
  reached the queue correctly. The fixture replaced native transport and
  media metadata; live YouTube extraction was tested separately.
- A public YouTube video was downloaded at 144p with merged audio/video;
  MP3 conversion also completed. FFmpeg and Deno downloads were verified
  against publisher-provided SHA256 values. Both are bundled with licenses.
- An installer with a separate test application ID was installed in a
  workspace test directory. Real Chromium native messaging launched the
  packaged app; real format extraction, MKV video download and MP3 output
  completed. Uninstall removed the test application, and existing native-host
  registry values were preserved. Existing SDM was left running.
- Window icon initialization now uses PIL.ImageTk rather than the invalid
  ttkbootstrap.PhotoImage call. ICO resources and an explicit Windows
  AppUserModelID are included. Packaged startup validation passed.
- pip-audit reported no known vulnerabilities after upgrading the build
  environment's pip. See dependency-audit.json and requirements-lock.txt.
- Installer compiler download had a valid Authenticode signature from
  Pyrsys B.V. The generated SDM application and installer are not signed.

## Limits

No full manual dependency audit, Windows Defender scan or packet capture
has completed. The standalone Opera browser has not been exercised; the
shared Chromium extension has been tested. Store publication is not included;
one-time manual unpacked-extension approval is required in each browser.

## 0.3.0 validation

18 regression tests passed, including file-host restrictions, constant-rate, warm-up, burst,
concurrency and resumed-byte speed calculations. Native white UI validation
covered black table text, downloaded bytes, detail controls and saved columns.
An isolated real Chromium download test verified normal file capture and
browser fallback when the app's preflight was rejected.


## 0.3.1 validation

27 motor/security tests passed, including distinct temporary files, legacy deletion,
Canva/subdomain capture exclusions, pause timers, file types, credential-free backups,
Windows DPAPI token protection, update hash validation, redirect credential isolation,
and real concurrent yt-dlp HTTP range downloads with exact output bytes.
Native UI tests verified both themes, icons, HUD, cancel/close, capture decisions,
queue start/pause, completion UI, five settings sections and native drag/drop registration.
Chromium tests exercised normal capture/fallback and video/MP3 selections.
The final test installer was installed under a separate application ID. Actual native messaging, YouTube MKV and MP3 downloads completed; uninstall passed and prior native-host registry values were restored. Existing SDM was not replaced. pip-audit reported zero known vulnerabilities including tkinterdnd2 0.6.4.
