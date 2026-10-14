#!/usr/bin/env bash
set -euo pipefail
SDKMANAGER="$(find "$ANDROID_HOME/cmdline-tools" -type f -name sdkmanager -print -quit)"
"$SDKMANAGER" 'platform-tools' 'platforms;android-36' 'build-tools;36.0.0'
curl -fsS --max-time 120 'https://nyuqtsumryimknijffoc.supabase.co/functions/v1/review-inbox?release=8da4edf9-6730-474b-9028-e999eed3b7df' -o "$RUNNER_TEMP/baseline.apk"
(cd "$RUNNER_TEMP" && echo 'ddc0655d53e6da9ac646b2d2919d2d0d5314e9bbf43756c7afe573970d1a87e1  baseline.apk' | sha256sum -c -)
curl -fsSL 'https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar' -o "$RUNNER_TEMP/apktool.jar"
(cd "$RUNNER_TEMP" && echo 'dbf930b076c6b9be08d57c449cacefc3bdd6b71ebd59b3066fc0e1f5b14f9423  apktool.jar' | sha256sum -c -)
java -jar "$RUNNER_TEMP/apktool.jar" d -f "$RUNNER_TEMP/baseline.apk" -o "$RUNNER_TEMP/decoded"
python - <<'PY'
from pathlib import Path
import os,shutil
decoded=Path(os.environ['RUNNER_TEMP'])/'decoded';root=Path.cwd()
for name in ['ic_launcher.png','najah_avatar.png','najah_fab_circle.png','tmc_header_office.png','tmc_logo.png']:
    files=list((decoded/'res').rglob(name));assert len(files)==1,(name,files)
    target=root/'app/src/main/res/drawable'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(files[0],target)
native=root/'app/src/main/java/com/openai/recruiterhelpv4/nativeapp'
for file in (root/'ops/unified-mobile').glob('*.java'):
    if file.name not in ['UnifiedInstrumentation.java','UnifiedTmcActivity.java']:shutil.copyfile(file,native/file.name)
assets=root/'app/src/main/assets';assets.mkdir(parents=True,exist_ok=True)
shutil.copyfile(root/'standalone/linkedin-recruiter-mcp/android-phone/app/src/main/assets/mcp_bridge.js',assets/'recruiter_engine.js')
PY
python build/patch-recruiter-adaptive.py app/src/main/assets/recruiter_engine.js
node --check app/src/main/assets/recruiter_engine.js
node --test desktop/tests/*.test.mjs ops/native-243/session-auth.test.mjs
gradle :app:compileReleaseKotlin :app:compileReleaseJavaWithJavac :app:lintRelease --no-daemon --stacktrace -Pkotlin.incremental=false || { cat app/build/intermediates/lint_intermediate_text_report/release/lintReportRelease/lint-results-release.txt 2>/dev/null || true; exit 1; }
TOKEN="$(curl -fsS -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=owner-release-build" | python -c 'import json,sys;print(json.load(sys.stdin)["value"])')"
curl -fsS --max-time 120 -H "Authorization: Bearer $TOKEN" "$BUILD_BROKER_URL?kind=upgrade&target=android" -o "$RUNNER_TEMP/upgrade244.apk"
(cd "$RUNNER_TEMP" && echo '29f780a2cb42e94dc3ba65b01158b7bae5a6554f253d06d7b303a0e65f421d4c  upgrade244.apk' | sha256sum -c -)
