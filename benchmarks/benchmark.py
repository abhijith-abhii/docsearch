#!/usr/bin/env python3
"""Reproducible synthetic local benchmarks; never measures production users.

Run with Python 3.12. For Flask projects, install Flask==3.1.2 and
gunicorn==23.0.0. For Health Passport, build its JAR with Java 21 first.
"""
import argparse, concurrent.futures, contextlib, datetime, hashlib, http.client
import importlib.util, json, math, os, pathlib, platform, secrets, shutil
import socket, statistics, subprocess, sys, tempfile, time


def percentile(values, q):
    return sorted(values)[max(0, math.ceil(q * len(values))-1)]


def stats(values):
    return {'count':len(values),'median_ms':round(statistics.median(values),3),
            'p95_ms':round(percentile(values,.95),3),'min_ms':round(min(values),3),'max_ms':round(max(values),3)}


def http_call(conn, method, path, payload=None, headers=None):
    data=json.dumps(payload).encode() if payload is not None else None
    hh={'Content-Type':'application/json','X-Portfolio-Request':'1',**(headers or {})}
    start=time.perf_counter()
    conn.request(method,path,body=data,headers=hh)
    response=conn.getresponse();raw=response.read();elapsed=(time.perf_counter()-start)*1000
    assert response.status==200, (response.status,raw[:120])
    return elapsed,json.loads(raw),dict(response.getheaders())


def index_comparison(repo,tmp):
    spec=importlib.util.spec_from_file_location('benchmark_docsearch',repo/'docsearch.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    corpus=tmp/'corpus';corpus.mkdir();count=1000
    for i in range(count):
        content=f'# Runbook {i}\nService service{i} handles requests in region {i%10}.\n'
        for j in range(8):
            content+=f'## Procedure {j}\n'+(f'Validate backup policy{i%25} and restore checkpoints for service{i}.\n'*8)
        (corpus/f'runbook-{i:04}.md').write_text(content)
    full=[];unchanged=[];one_percent=[]
    indexed=tmp/'incremental.sqlite';module.sync(corpus,indexed)
    for trial in range(7):
        # Pair full and incremental runs on the SAME unchanged corpus, alternating order.
        fresh=tmp/f'full-{trial}.sqlite'
        operations=['full','unchanged'] if trial%2==0 else ['unchanged','full']
        for operation in operations:
            start=time.perf_counter();result=module.sync(corpus,fresh if operation=='full' else indexed)
            elapsed=(time.perf_counter()-start)*1000
            if operation=='full':assert result['updated']==count;full.append(elapsed)
            else:assert result['updated']==0 and result['unchanged']==count;unchanged.append(elapsed)
        changed_paths=[corpus/f'runbook-{i:04}.md' for i in range(10)]
        for path in changed_paths:path.write_text(path.read_text()+f'\nRevision {trial}.\n')
        start=time.perf_counter();result=module.sync(corpus,indexed)
        one_percent.append((time.perf_counter()-start)*1000)
        assert result['updated']==10 and result['unchanged']==990
        # Restore equal input for the following paired full/incremental measurements.
    queries=['backup policy'+str(i%25) for i in range(300)]
    for q in queries[:20]:assert module.search(indexed,q)
    search=[]
    for q in queries:
        start=time.perf_counter();result=module.search(indexed,q);search.append((time.perf_counter()-start)*1000)
        assert len(result)==10
    return {'documents':count,'passages':9000,'paired_repetitions':7,
        'full_rebuild_ms':full,'unchanged_sync_ms':unchanged,'one_percent_changed_sync_ms':one_percent,
        'full_rebuild_median_ms':round(statistics.median(full),3),
        'unchanged_sync_median_ms':round(statistics.median(unchanged),3),
        'one_percent_changed_median_ms':round(statistics.median(one_percent),3),
        'unchanged_time_reduction_percent':round(100*(1-statistics.median(unchanged)/statistics.median(full)),2),
        'unchanged_speedup_ratio':round(statistics.median(full)/statistics.median(unchanged),2),
        'search_latency':stats(search),
        'comparison':'Same implementation and corpus: fresh full index vs digest-based unchanged sync. A feature comparison, not a historical before/after optimization. Local filesystem caches may affect both.'}


def run(kind,repo,out,java):
    result={'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'project':kind,'source_commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
        'environment':{'os':platform.system(),'os_release':platform.release(),'architecture':platform.machine(),
                       'python':platform.python_version(),'cpu_count':os.cpu_count()},
        'scope':'Synthetic local loopback HTTP benchmark. Not production capacity, real users, clinical validation or user growth.',
        'concurrency':8,'requests_per_round':800,'rounds':3,'warmup_requests':40}
    with tempfile.TemporaryDirectory(prefix='portfolio-benchmark-') as tmp_s:
        tmp=pathlib.Path(tmp_s)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env=os.environ.copy();env['NOTES_DB']=str(tmp/'notes.sqlite')
        if kind=='health-passport':
            password=secrets.token_urlsafe(24)
            env.update(DEMO_MODE='true',DEMO_PASSWORD=password,DATABASE_URL='jdbc:h2:mem:benchmark;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE',PORT=str(port),BIND_ADDRESS='127.0.0.1')
            jar=repo/'apps/backend/target/health-passport-api-0.1.0.jar'
            assert jar.is_file(),'Build the JAR first with Java 21.'
            command=[java,'-jar',str(jar)];cwd=tmp;ready='/api/health'
            result['environment']['database']='H2 in-memory, synthetic demo seed'
            result['environment']['java']=subprocess.check_output([java,'-version'],stderr=subprocess.STDOUT,text=True).splitlines()[0]
        else:
            (tmp/'benchmark_app.py').write_text('from app import app\nimport core, os\nfrom pathlib import Path\nif os.environ.get("BENCHMARK_DOCS_ROOT"): core.ROOT=Path(os.environ["BENCHMARK_DOCS_ROOT"])\n')
            if kind=='docsearch':
                shutil.copytree(repo/'examples/docs',tmp/'examples/docs');env['BENCHMARK_DOCS_ROOT']=str(tmp)
            command=[sys.executable,'-m','gunicorn','--chdir',str(repo),'--pythonpath',str(tmp),'--workers','1','--threads','8','--bind',f'127.0.0.1:{port}','--access-logfile','/dev/null','benchmark_app:app']
            cwd=repo;ready='/health'
            result['environment']['server']='Gunicorn 23.0.0, 1 gthread worker, 8 threads'
        with (tmp/'server.log').open('w') as log:
            process=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=log)
            try:
                for attempt in range(120):
                    if process.poll() is not None:raise RuntimeError((tmp/'server.log').read_text()[-5000:])
                    try:
                        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=2);http_call(conn,'GET',ready);conn.close();break
                    except (OSError,AssertionError,http.client.HTTPException):time.sleep(.5)
                else:raise RuntimeError('Server startup timed out')
                auth={};health_path=''
                if kind=='health-passport':
                    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
                    _,csrf,headers=http_call(conn,'GET','/api/csrf')
                    cookie=headers.get('Set-Cookie','').split(';')[0]
                    _,identity,headers=http_call(conn,'POST','/api/auth/login',{'username':'patient','password':password},{'Cookie':cookie,'X-CSRF-TOKEN':csrf['token']})
                    cookie=headers.get('Set-Cookie',cookie).split(';')[0];auth={'Cookie':cookie};health_path='/api/patients/'+identity['id']+'/timeline';conn.close()
                    result['workload']='Authenticated reads of one synthetic patient timeline; shared session; login excluded; no network, disk database or native client benchmark.'
                elif kind=='notemesh':result['workload']='50/50 GET/PUT note operations, 8 independent rooms, 2048-character notes, SQLite file database; optimistic revision correctness checked.'
                elif kind=='docsearch':result['workload']='Source-linked extractive question answering over 5 bundled runbooks. Local-model generation excluded.'
                else:result['workload']='POST /api/run SHA-256 fingerprints of 100000 ASCII characters; digest correctness checked. Native Gunicorn process, not a Docker benchmark.'
                body='b'*2048;fingerprint='benchmark-data-'*6666+'x'*10;assert len(fingerprint)==100000
                digest=hashlib.sha256(fingerprint.encode()).hexdigest()
                def worker(worker_id,iterations,round_id):
                    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=30)
                    values=[];revision=0;room=f'bench-{round_id}-{worker_id}'
                    try:
                        for i in range(iterations):
                            if kind=='notemesh':
                                if i%2==0:
                                    elapsed,data,_=http_call(conn,'PUT','/api/notes/'+room,{'body':body,'revision':revision,'author':'Synthetic benchmark'});revision+=1
                                else:elapsed,data,_=http_call(conn,'GET','/api/notes/'+room)
                                assert data['revision']==revision and data['body']==body
                            elif kind=='docsearch':
                                elapsed,data,_=http_call(conn,'POST','/api/run',{'question':'How long is the backup retention period?','mode':'extractive'})
                                assert '14 days' in data['answer'] and data['rows']
                            elif kind=='shipyard':
                                elapsed,data,_=http_call(conn,'POST','/api/run',{'text':fingerprint})
                                assert data['answer']==digest and data['metrics']['UTF-8 bytes']==100000
                            else:
                                elapsed,data,_=http_call(conn,'GET',health_path,headers=auth)
                                assert isinstance(data,list) and len(data)>0
                            values.append(elapsed)
                        if kind=='notemesh':
                            _,history,_=http_call(conn,'GET','/api/notes/'+room+'/history')
                            assert len(history)==revision
                    finally:conn.close()
                    return values
                worker(0,40,'warmup')
                rounds=[];all_values=[]
                for round_id in range(3):
                    start=time.perf_counter()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                        values=sum(list(pool.map(lambda i:worker(i,100,round_id),range(8))),[])
                    wall=time.perf_counter()-start
                    rounds.append({**stats(values),'elapsed_seconds':round(wall,3),'requests_per_second':round(len(values)/wall,2),'failed_requests':0})
                    all_values.extend(values)
                result['http_rounds']=rounds
                result['http_summary']={**stats(all_values),'median_round_requests_per_second':round(statistics.median(r['requests_per_second'] for r in rounds),2),'failed_requests':0,'total_measured_requests':len(all_values)}
            finally:
                process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        if kind=='docsearch':result['index_comparison']=index_comparison(repo,tmp)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'project':kind,'http':result['http_summary'],'index_comparison':result.get('index_comparison')},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=['notemesh','docsearch','shipyard','health-passport'])
    parser.add_argument('--repo',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=pathlib.Path,required=True)
    parser.add_argument('--java',default='java')
    args=parser.parse_args();run(args.kind,args.repo.resolve(),args.output.resolve(),args.java)
