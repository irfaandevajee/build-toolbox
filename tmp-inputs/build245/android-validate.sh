#!/usr/bin/env bash
set -euo pipefail
trap 'if [ "$?" -ne 0 ]; then adb logcat -d -b crash; fi' EXIT
BT="$ANDROID_HOME/build-tools/36.0.0";APK="$RUNNER_TEMP/TMC-Talent-Intelligence-build245.apk"
unzip -t "$APK" > "$RUNNER_TEMP/zip-test.txt"
"$BT/zipalign" -c -P 16 -v 4 "$APK" > "$RUNNER_TEMP/align.txt"
"$BT/apksigner" verify --verbose --print-certs "$APK" > "$RUNNER_TEMP/signer.txt"
grep -qi '2a6a9fe597c18356408d42972eeb023366a94af53998576c155a9f22c973ff8b' "$RUNNER_TEMP/signer.txt"
grep -q 'Verified using v2 scheme (APK Signature Scheme v2): true' "$RUNNER_TEMP/signer.txt"
grep -q 'Verified using v3 scheme (APK Signature Scheme v3): true' "$RUNNER_TEMP/signer.txt"
"$BT/aapt2" dump badging "$APK" > "$RUNNER_TEMP/badging.txt"
grep -q "package: name='com.openai.recruiterhelpv4' versionCode='245' versionName='2.0.0-native-rc5.70'" "$RUNNER_TEMP/badging.txt"
grep -q "targetSdkVersion:'36'" "$RUNNER_TEMP/badging.txt"
unzip -p "$APK" assets/recruiter_engine.js > "$RUNNER_TEMP/recruiter-engine.js"
grep -q "0.4.4-adaptive-search" "$RUNNER_TEMP/recruiter-engine.js"
if grep -Eqi 'bright[ _-]?data|connectsafely' "$RUNNER_TEMP/recruiter-engine.js"; then echo 'Forbidden sourcing provider found in recruiter engine'; exit 1; fi
adb wait-for-device
adb install "$RUNNER_TEMP/upgrade244.apk"
adb install "$RUNNER_TEMP/qa.apk"
adb shell am instrument -w -e mode seed com.tmc.nativeqa/com.openai.recruiterhelpv4.nativeapp.NativeInstrumentation | tee "$RUNNER_TEMP/qa-seed.txt"
grep -q 'Encrypted Build 241 session seeded' "$RUNNER_TEMP/qa-seed.txt"
adb install -r "$APK" | tee "$RUNNER_TEMP/qa-upgrade.txt"
grep -q 'Success' "$RUNNER_TEMP/qa-upgrade.txt"
adb logcat -c
adb shell am instrument -w com.tmc.nativeqa/com.openai.recruiterhelpv4.nativeapp.NativeInstrumentation | tee "$RUNNER_TEMP/qa-mobile.txt"
for check in nativeWorkspace noWorkspaceWebView pipelineStageCounts quickStageChange swipeBottomTabs noMobileSourcingUi stationaryNotificationBell circularFitRestored candidateFlickStability headerBranding pullToRefresh chatGptConnectedLabel upgradeSessionPreserved chatGptUpgradePreserved candidate360 browserBackHistory browserInsets browserBottomFullHeight doubleBackExit noAssistantLauncher; do grep -q "$check=PASS" "$RUNNER_TEMP/qa-mobile.txt"; done
adb logcat -d -b crash > "$RUNNER_TEMP/qa-crash.txt"
if grep -q 'FATAL EXCEPTION' "$RUNNER_TEMP/qa-crash.txt"; then cat "$RUNNER_TEMP/qa-crash.txt"; exit 1; fi
python ops/native-243/validate_apk.py
mkdir -p "$RUNNER_TEMP/native-evidence"
adb pull /sdcard/Android/data/com.openai.recruiterhelpv4/files/home-native243.png "$RUNNER_TEMP/native-evidence/home-native243.png"
adb pull /sdcard/Android/data/com.openai.recruiterhelpv4/files/candidate-native243.png "$RUNNER_TEMP/native-evidence/candidate-native243.png"
cp "$RUNNER_TEMP/qa-mobile.txt" "$RUNNER_TEMP/native-evidence/interaction-checks.txt"
(cd "$RUNNER_TEMP/native-evidence" && zip -q "$RUNNER_TEMP/native245-evidence.zip" home-native243.png candidate-native243.png interaction-checks.txt)
TOKEN="$(curl -fsS -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=owner-release-build" | python -c 'import json,sys;print(json.load(sys.stdin)["value"])')"
curl -fsS --max-time 120 -H "Authorization: Bearer $TOKEN" --data-binary @"$RUNNER_TEMP/native245-evidence.zip" "$BUILD_BROKER_URL?kind=evidence&target=android" >/dev/null
