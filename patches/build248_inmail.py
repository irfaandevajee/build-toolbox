from pathlib import Path

ROOT = Path('private-input')
activity = ROOT / 'app/src/main/java/com/openai/recruiterhelpv4/nativeapp/LinkedInSessionActivity.kt'
gradle = ROOT / 'app/build.gradle.kts'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


src = activity.read_text(encoding='utf-8')

src = replace_once(
    src,
    "function name(){const xs=[...document.querySelectorAll('main h1,h1,[data-anonymize=\"person-name\"],[data-test-id*=\"name\" i]')].filter(visible).map(txt).filter(v=>v&&v.length<120&&!/linkedin|recruiter/i.test(v));return xs[0]||''}",
    "function name(){const xs=[...document.querySelectorAll('[data-anonymize=\"person-name\"],[data-test-id*=\"person-name\" i],[data-test-id*=\"profile-name\" i],main h1,h1')].filter(visible).map(txt).filter(v=>v&&v.length<120&&!/linkedin|recruiter|from public profile/i.test(v));return xs[0]||''}",
    'prefer candidate name selectors',
)

src = replace_once(
    src,
    "if(/24 hour|24-hour|already sent an inmail|already contacted|cannot send another|unable to send another|wait .* before sending/.test(body)){s.state='cooldown';s.detail='Recruiter reports recent contact.';return JSON.stringify(s)}",
    "const cooldownText=[...document.querySelectorAll('[role=alert],.artdeco-inline-feedback,.artdeco-toast-item,[data-test-id*=\"inmail\" i],[data-test-id*=\"message\" i]')].filter(visible).map(txt).join(' ').toLowerCase();if(/24 hour|24-hour|already sent an inmail|cannot send another|unable to send another|wait .* before sending/.test(cooldownText)){s.state='cooldown';s.detail='Recruiter reports an explicit InMail cooldown.';return JSON.stringify(s)}",
    'scope cooldown detection',
)

src = replace_once(
    src,
    "const action=[...document.querySelectorAll('button,a,[role=button]')].filter(visible).sort((a,b)=>meta(a).length-meta(b).length).find(e=>/send inmail|inmail|send message|^message /.test(meta(e)));\n                if(action&&!s.composerAt){s.composerAt=Date.now();action.click();s.state='opening_composer'}else s.state='finding_composer';",
    "const action=[...document.querySelectorAll('button,a,[role=button]')].filter(visible).sort((a,b)=>meta(a).length-meta(b).length).find(e=>{const m=meta(e);return m==='message'||m==='send inmail'||m==='inmail'||m==='send message'||m.startsWith('message ')||m.includes('send inmail')});\n                if(action&&(!s.composerAt||Date.now()-s.composerAt>2500)){s.composerAt=Date.now();action.click();s.state='opening_composer'}else s.state='finding_composer';",
    'open exact Message/InMail action and retry',
)

src = replace_once(
    src,
    "if(subjectField&&subject&&String(subjectField.value||'').trim()!==subject.trim())setVal(subjectField,subject);\n              const current=bodyField.isContentEditable?String(bodyField.innerText||bodyField.textContent||'').trim():String(bodyField.value||'').trim();if(current!==message.trim())setVal(bodyField,message);\n              const send=[...root.querySelectorAll('button,[role=button],input[type=submit],input[type=button]')].filter(visible).find(e=>{const m=meta(e);return m==='send'||m==='send inmail'||m==='send message'||m==='send now'||/^send\\b/.test(m)&&!/cancel|close|template|schedule|dropdown/.test(m)});",
    "if(subjectField&&subject&&String(subjectField.value||'').trim()!==subject.trim())setVal(subjectField,subject);\n              const current=bodyField.isContentEditable?String(bodyField.innerText||bodyField.textContent||'').trim():String(bodyField.value||'').trim();if(current!==message.trim())setVal(bodyField,message);\n              const subjectReady=!subjectField||!subject||String(subjectField.value||'').trim()===subject.trim();const bodyNow=bodyField.isContentEditable?String(bodyField.innerText||bodyField.textContent||'').trim():String(bodyField.value||'').trim();if(!subjectReady||bodyNow!==message.trim()){s.state='filling';return JSON.stringify(s)}\n              const send=[...root.querySelectorAll('button,[role=button],input[type=submit],input[type=button]')].filter(visible).find(e=>{const m=meta(e);return m==='send'||m==='send inmail'||m==='send message'||m==='send now'||/^send\\b/.test(m)&&!/cancel|close|template|schedule|dropdown/.test(m)});",
    'verify composer fields before send',
)

src = src.replace(
    "/\\/talent\\/api\\/graphql/.test(x.__tmcu||'')&&/messagePostPayloads/.test(body)",
    "/\\/(talent|voyager)\\/api\\/graphql/.test(x.__tmcu||'')&&/(messagePostPayloads|sendInMail|inmail)/i.test(body)",
)
src = src.replace(
    "/\\/talent\\/api\\/graphql/.test(u)&&typeof b==='string'&&/messagePostPayloads/.test(b)",
    "/\\/(talent|voyager)\\/api\\/graphql/.test(u)&&typeof b==='string'&&/(messagePostPayloads|sendInMail|inmail)/i.test(b)",
)
if src.count("/(messagePostPayloads|sendInMail|inmail)/i.test") != 2:
    raise RuntimeError('network send confirmation hook patch was not applied twice')

src = replace_once(
    src,
    "if(send&&!(send.disabled||send.getAttribute('aria-disabled')==='true')&&!s.clickedAt){s.clickedAt=Date.now();s.state='clicked';send.click();return JSON.stringify(s)}\n              s.state=send?'send_disabled':'finding_send';return JSON.stringify(s)",
    "if(send&&!(send.disabled||send.getAttribute('aria-disabled')==='true')&&!s.clickedAt){s.clickedAt=Date.now();s.state='clicked';send.click();return JSON.stringify(s)}\n              if(s.clickedAt){const confirmation=[...document.querySelectorAll('[role=alert],.artdeco-toast-item,.artdeco-inline-feedback')].filter(visible).map(txt).join(' ').toLowerCase();if(/message sent|inmail sent|sent successfully/.test(confirmation)){s.state='sent';s.detail='Recruiter confirmed the InMail.';return JSON.stringify(s)}}\n              s.state=send?'send_disabled':'finding_send';return JSON.stringify(s)",
    'accept explicit Recruiter UI send confirmation',
)

activity.write_text(src, encoding='utf-8')

gradle_src = gradle.read_text(encoding='utf-8')
gradle_src = replace_once(gradle_src, 'versionCode = 247', 'versionCode = 248', 'version code')
gradle_src = replace_once(gradle_src, 'versionName = "2.0.0-native-rc5.72"', 'versionName = "2.0.0-native-rc5.73"', 'version name')
gradle.write_text(gradle_src, encoding='utf-8')

# Build-time assertions: preserve TMC-only Recruiter automation and do not silently
# weaken identity/delivery safeguards.
final = activity.read_text(encoding='utf-8')
required = [
    "MODE_OUTREACH",
    "confirmRecruiterOutreachSent",
    "m==='message'",
    "state='filling'",
    "Recruiter confirmed the InMail.",
    "same(expected,shown)",
]
for marker in required:
    if marker not in final:
        raise RuntimeError(f'missing required outreach safeguard: {marker}')

print('Build 248 InMail automation patch applied')
