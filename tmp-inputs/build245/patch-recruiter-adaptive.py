from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
def one(old,new,label):
    global s
    n=s.count(old)
    if n!=1: raise AssertionError(f'{label}: expected 1, got {n}')
    s=s.replace(old,new,1)

one("""  function eligible(method, value) {
    const info = endpoint(value);
    if (!info) return null;
    const path = new URL(value, location.href).pathname;
    return method === 'GET' || (method === 'POST' && ([SEARCH_PATH, '/talent/api/talentRecruitingProfiles/'].includes(path) || path===HISTORY_RESOURCE || !!profilePath(value))) ? info : null;
  }
""","""  function eligible(method, value) {
    const info = endpoint(value);
    if (!info) return null;
    const path = new URL(value, location.href).pathname;
    if (method === 'GET') return info;
    // Recruiter changes search endpoint names over time. Observe scoped Recruiter API POSTs,
    // then only promote a request after its response proves it contains candidate search hits.
    if (method === 'POST' && /^\\/(?:talent(?:\\/search)?|voyager)\\/api\\//.test(path)) return info;
    return null;
  }
""",'eligible')
one("if (!active() || opened.method !== 'POST' || new URL(opened.url, location.href).pathname !== SEARCH_PATH || replayXhr) return null;","if (!active() || opened.method !== 'POST' || profilePath(opened.url) || replayXhr) return null;",'remember guard')
one("const template = { url: new URL(opened.url, location.href).href, body: original, raw, parsed, codec, headers, valid: false, requestShape: shape(parsed), paging: null };\n        searchTemplate = template; return template;","const template = { url: new URL(opened.url, location.href).href, endpointPath: new URL(opened.url, location.href).pathname, body: original, raw, parsed, codec, headers, valid: false, requestShape: shape(parsed), paging: null, responsePath: '' };\n        return template;",'tentative request')
marker='  function collectionSummary() {\n'
if s.count(marker)!=1: raise AssertionError('collection marker')
helpers=r'''  function unwrapSearchHit(value, depth=0) {
    if (!value || typeof value !== 'object' || depth > 5) return null;
    if (!Array.isArray(value) && typeof value.linkedInMemberProfileUrn === 'string' && value.linkedInMemberProfileUrnResolutionResult && typeof value.linkedInMemberProfileUrnResolutionResult === 'object') return value;
    if (Array.isArray(value)) return null;
    for (const [key, child] of Object.entries(value)) {
      if (privateKey.test(key) || !child || typeof child !== 'object') continue;
      const found = unwrapSearchHit(child, depth + 1);
      if (found) return found;
    }
    return null;
  }
  function searchEnvelope(body) {
    let best = null, fallbackPaging = null;
    function walk(value, path, depth) {
      if (!value || typeof value !== 'object' || depth > 8) return;
      if (!Array.isArray(value)) {
        if (!fallbackPaging && Number.isInteger(value?.paging?.count) && Number.isInteger(value?.paging?.start)) fallbackPaging = value.paging;
        if (!fallbackPaging && Number.isInteger(value.count) && Number.isInteger(value.start) && (Number.isInteger(value.total) || Number.isInteger(value.pageSize))) fallbackPaging = value;
      }
      if (Array.isArray(value)) {
        const hits = value.map(row => unwrapSearchHit(row)).filter(Boolean);
        if (hits.length && (!best || hits.length > best.rows.length)) best = { rows:hits, path:path || '$', paging:null };
        return;
      }
      for (const [key, child] of Object.entries(value)) {
        if (privateKey.test(key) || !child || typeof child !== 'object') continue;
        const next = path ? path + '.' + key : key;
        if (Array.isArray(child)) {
          const hits = child.map(row => unwrapSearchHit(row)).filter(Boolean);
          if (hits.length && (!best || hits.length > best.rows.length)) {
            const localPaging = Number.isInteger(value?.paging?.count) && Number.isInteger(value?.paging?.start) ? value.paging : null;
            best = { rows:hits, path:next, paging:localPaging };
          }
        }
        walk(child, next, depth + 1);
      }
    }
    walk(body, '', 0);
    if (!best) return null;
    best.paging = best.paging || fallbackPaging || (Number.isInteger(body?.paging?.count) && Number.isInteger(body?.paging?.start) ? body.paging : null);
    return best;
  }
  function promoteSearchTemplate(template, body, code) {
    if (!template || template.kind === 'PROFILE' || code !== 200) return null;
    const envelope = searchEnvelope(body);
    if (!envelope || envelope.rows.length < 1) return null;
    template.valid = true;
    template.responsePath = envelope.path;
    template.paging = envelope.paging ? {count:envelope.paging.count,start:envelope.paging.start,total:Number.isInteger(envelope.paging.total)?envelope.paging.total:null} : null;
    searchTemplate = template;
    bodyFormat = { type: template.codec || 'unknown', bytes: new TextEncoder().encode(template.raw || '').length, parsed: true, endpoint: safePath(template.endpointPath || new URL(template.url, location.href).pathname), responsePath: envelope.path };
    return envelope;
  }

'''
s=s.replace(marker,helpers+marker,1)

def replace_capture_segment(function_name, response_code_expr, replay_guard=''):
    global s
    start=s.index('  '+function_name)
    a=s.index('      const schema = shape(body);',start)
    b=s.index('      record(info,',a)
    if function_name.startswith('async function captureXhr'):
        new="""      const schema = shape(body);
      const envelope = promoteSearchTemplate(template, body, code) || searchEnvelope(body);
      const searchSchema = !!envelope;
      if (!template && code === 200 && searchSchema && xhr !== replayXhr) skip('SEARCH_RESPONSE_WITHOUT_REQUEST_TEMPLATE');
"""
    else:
        new="""      const envelope = promoteSearchTemplate(template, body, response.status) || searchEnvelope(body);
      if (!template && response.status === 200 && envelope) skip('SEARCH_RESPONSE_WITHOUT_REQUEST_TEMPLATE');
"""
    s=s[:a]+new+s[b:]
replace_capture_segment('async function captureXhr', 'code')
replace_capture_segment('async function captureResponse', 'response.status')
one("testResult = { state: 'RUNNING', endpoint: SEARCH_PATH, method: 'POST', requestCount: 1 };","testResult = { state: 'RUNNING', endpoint: safePath(new URL(t.url, location.href).pathname), method: 'POST', requestCount: 1 };",'test endpoint')
one("const paging=body?.paging, rows=body?.elements;","const envelope=searchEnvelope(body), paging=envelope?.paging, rows=envelope?.rows;",'collect envelope')
one("} else if (method === 'POST' && new URL(url, location.href).pathname === SEARCH_PATH) {","} else if (method === 'POST') {",'fetch post')
one("if (active() && opened && ((opened.method === 'POST' && new URL(opened.url, location.href).pathname === SEARCH_PATH)||profilePath(opened.url)) && /^(csrf-token|x-restli-protocol-version|x-restli-method|x-http-method-override|accept|content-type|x-li-lang)$/i.test(String(name))) opened.headers[String(name)] = String(value);","if (active() && opened && (opened.method === 'POST'||profilePath(opened.url)) && /^(csrf-token|x-restli-protocol-version|x-restli-method|x-http-method-override|accept|content-type|x-li-lang)$/i.test(String(name))) opened.headers[String(name)] = String(value);",'xhr headers')
one("const template = active() && info ? (profilePath(opened.url)?historyRemember(opened,body):rememberSearch(opened, body)) : null;","const template = active() && info ? (profilePath(opened.url)?historyRemember(opened,body):(opened.method==='POST'?rememberSearch(opened, body):null)) : null;",'xhr template')
one("...historySnapshot(),mode: 'PASSIVE_SCHEMA_AND_PATHS', earlyHooks: early, observedRequests, excludedRequests, requestPaths: requests.slice(), resourcePaths: resources.slice(), responseFormats: formats.slice(), observedSearchBodyFormat: bodyFormat, collection: collectionSummary(),","...historySnapshot(),mode: 'PASSIVE_SCHEMA_AND_PATHS', earlyHooks: early, observedRequests, excludedRequests, requestPaths: requests.slice(), resourcePaths: resources.slice(), responsePaths: state.events.slice(-12).map(e=>({path:e.path,status:e.status,transport:e.transport})), responseFormats: formats.slice(), observedSearchBodyFormat: bodyFormat, collection: collectionSummary(),",'status paths')
versions=["version: '0.4.2-fetch-parser'","version: '0.4.3-form-parser'"]
found=sum(s.count(v) for v in versions)
if found!=1: raise AssertionError(f'version marker count {found}')
for v in versions: s=s.replace(v,"version: '0.4.4-adaptive-search'",1)
p.write_text(s)
print('adaptive parser patched -> 0.4.4-adaptive-search')
