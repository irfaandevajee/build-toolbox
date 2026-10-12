"""Generic authenticated private-input transfer; never prints private payloads."""
import argparse,base64,hashlib,json,os,pathlib,subprocess,sys,urllib.request,urllib.parse
ROOT=pathlib.Path('private-input')
AUDIENCE='owner-release-build'

def broker():
    url=os.environ.get('BUILD_BROKER_URL','').rstrip('/')
    if urllib.parse.urlparse(url).scheme!='https':raise ValueError('HTTPS build broker required')
    return url

def identity():
    url=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']+'&audience='+AUDIENCE
    req=urllib.request.Request(url,headers={'Authorization':'bearer '+os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']})
    with urllib.request.urlopen(req,timeout=30) as response:token=json.load(response)['value']
    print('::add-mask::'+token)
    return token

def transfer(kind,target,payload=None):
    url=broker()+'?'+urllib.parse.urlencode({'kind':kind,'target':target})
    req=urllib.request.Request(url,data=payload,headers={'Authorization':'Bearer '+identity(),'Content-Type':'application/octet-stream'},method='POST' if payload is not None else 'GET')
    with urllib.request.urlopen(req,timeout=120) as response:return response.read()

def fetch(target):
    data=json.loads(transfer('bundle',target));ROOT.mkdir(exist_ok=True)
    for file in data['files']:
        path=pathlib.PurePosixPath(file['path'])
        if path.is_absolute() or '..' in path.parts or ':' in str(path) or path.parts[0] in ('.git','.github'):raise ValueError('Unsafe input path')
        content=base64.b64decode(file['dataB64'],validate=True)
        if hashlib.sha256(content).hexdigest()!=file['sha256']:raise ValueError('Input fingerprint mismatch')
        destination=ROOT.joinpath(*path.parts);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(content)
    print('Authorized private build inputs restored')

def phase(name,target):
    logs=ROOT/'private-logs';logs.mkdir(exist_ok=True)
    log=logs/(name+'.txt')
    env={**os.environ,'BUILD_INPUT_ROOT':str(ROOT.resolve())}
    with log.open('wb') as stream:
        result=subprocess.run([sys.executable,'build/phases.py',name,target],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,env=env)
    if result.returncode:
        try:transfer('diagnostics',target,log.read_bytes())
        except Exception:pass
        print('Build phase failed; diagnostics remain private: '+name)
        raise SystemExit(result.returncode)
    print('Build phase passed: '+name)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['fetch','phase']);parser.add_argument('target',choices=['android','windows']);parser.add_argument('--name');args=parser.parse_args()
    try:
        if args.operation=='fetch':fetch(args.target)
        elif args.name in ('prepare','build','validate','stage','cleanup'):phase(args.name,args.target)
        else:raise ValueError('Unknown build phase')
    except Exception:
        print('Build operation failed; private details were not printed',file=sys.stderr);raise SystemExit(1)
