#!/usr/bin/env python3
"""Exercise one owned native OmaWord window, without altering the desktop theme/clipboard."""
import argparse, base64, hashlib, json, os, pathlib, shutil, socket, subprocess, tempfile, time
p = argparse.ArgumentParser(); p.add_argument('binary'); p.add_argument('output'); p.add_argument('--port', type=int, default=18798); a=p.parse_args()
out=pathlib.Path(a.output).resolve(); out.mkdir(parents=True,exist_ok=True)
with socket.socket() as probe:
    if probe.connect_ex(('127.0.0.1',a.port))==0: raise RuntimeError('Refusing occupied test port')
work=pathlib.Path(tempfile.mkdtemp(prefix='omaword-native-'))
source=pathlib.Path.home()/'.local/state/omarchy/current/theme'
theme=work/'state/omarchy/current/theme'; theme.mkdir(parents=True)
for name in ('colors.toml','light.mode'):
    if (source/name).is_file(): shutil.copy2(source/name,theme/name)
original=(theme/'colors.toml').read_bytes(); live_before=hashlib.sha256((source/'colors.toml').read_bytes()).hexdigest()
env=os.environ.copy(); env.update(OMAWORD_PROFILE_DIR=str(work/'profile'),XDG_STATE_HOME=str(work/'state'),OMAWORD_WAYLAND='1',WAYLAND_DISPLAY='wayland-1',XDG_RUNTIME_DIR='/run/user/1000',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
env['HYPRLAND_INSTANCE_SIGNATURE']=next(pathlib.Path('/run/user/1000/hypr').iterdir()).name
log=(out/'runtime.log').open('w'); process=subprocess.Popen([a.binary,'--sample','--control',str(a.port)],env=env,stdout=log,stderr=subprocess.STDOUT)
stream=sock=None
try:
    keyfile=work/f'profile/control-key.local-{a.port}'
    deadline=time.monotonic()+60
    while not keyfile.exists():
        if process.poll() is not None: raise RuntimeError(f'Process exited {process.returncode}')
        if time.monotonic()>deadline: raise RuntimeError('Control startup timeout')
        time.sleep(.05)
    assert keyfile.stat().st_mode & 0o777 == 0o600
    # Unauthenticated access must fail before any application mutation.
    with socket.create_connection(('127.0.0.1',a.port),timeout=10) as denied:
        denied.sendall(b'{"id":1,"method":"document.inspect"}\n')
        refusal=json.loads(denied.makefile('rb').readline())
        assert not refusal.get('ok') and 'unauthorized' in refusal.get('error','')
    key=keyfile.read_text().strip(); sock=socket.create_connection(('127.0.0.1',a.port),timeout=20); stream=sock.makefile('rwb'); seq=0
    def request(method,params=None):
        global seq
        seq+=1; stream.write((json.dumps({'id':seq,'key':key,'method':method,'params':params or {}})+'\n').encode()); stream.flush()
        result=json.loads(stream.readline())
        if not result.get('ok'): raise RuntimeError(f'{method}: {result}')
        return result['result']
    def execute(command,params=None): return request('engine.execute',{'command':command,'params':params or {}})
    def render_hash(): return hashlib.sha256(base64.b64decode(request('ui.render',{'page':1,'scale':1})['png'])).hexdigest()
    def shot(name): return request('ui.screenshot',{'path':str(out/f'{name}.png')})
    time.sleep(2)
    clients=json.loads(subprocess.check_output(['hyprctl','-j','clients'],env=env))
    own=[{k:c.get(k) for k in ('pid','class','title','xwayland','size')} for c in clients if c.get('pid')==process.pid]
    assert len(own)==1 and own[0]['class']=='io.github.ustaaa.OmaWord' and own[0]['xwayland'] is False
    assert 'OmaWord' in own[0]['title']
    before=request('document.inspect'); doc_hash=render_hash(); screenshots={}
    screenshots['system']=shot('system')
    hashes=[doc_hash]
    for mode in ('light','dark','system'):
        execute('ui.theme',{'value':mode}); time.sleep(.2); screenshots[mode]=shot(mode); hashes.append(render_hash())
        assert request('document.inspect')==before
    # Swap gaps and malformed partial files retain the previous valid appearance.
    (theme/'colors.toml').unlink(); time.sleep(1.3); screenshots['missing']=shot('missing'); hashes.append(render_hash())
    (theme/'colors.toml').write_text('unfinished='); time.sleep(1.3); screenshots['invalid']=shot('invalid'); hashes.append(render_hash())
    (theme/'colors.toml').write_text("mode='dark'\nbackground='#101820'\nforeground='#e9f0fa'\naccent='#d6a940'\nlighter_background='#263444'\n")
    time.sleep(1.3); screenshots['live']=shot('live'); hashes.append(render_hash())
    (theme/'colors.toml').write_bytes(original); time.sleep(1.3); screenshots['restored']=shot('restored'); hashes.append(render_hash())
    assert len(set(hashes))==1 and request('document.inspect')==before
    assert hashlib.sha256((source/'colors.toml').read_bytes()).hexdigest()==live_before
    result={'passed':True,'window':own[0],'unauthenticated_refused':True,'key_mode':'0600','document_unchanged_across_appearance':True,'document_page_png_sha256':doc_hash,'page_hashes':hashes,'screenshots':screenshots,'live_theme_untouched_sha256':live_before,'limitations':['No physical IME/clipboard/drag/drop/printing or input-to-photon latency acceptance in this smoke.']}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result),flush=True)
finally:
    if stream: stream.close()
    if sock: sock.close()
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
    log.close(); shutil.rmtree(work)
