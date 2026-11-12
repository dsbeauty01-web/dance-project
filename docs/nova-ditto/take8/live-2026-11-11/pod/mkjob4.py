s = open("/dev/shm/t8/up/job3.sh").read()


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('say "stage 1 DONE: branch=$BRANCH  PYTHONPATH=$PYPATH"',
    'say "stage 1 DONE: branch=$BRANCH  PYTHONPATH=$PYPATH"\n'
    '# DITTO-LIVE.md section 7: the volume\'s resampy has no core; heal it EARLIER on PYTHONPATH than the volume tree\n'
    'env -u PYTHONPATH python3 -m pip install --no-input -q --target "$TFX" resampy > "$OUT/resampy_fix.log" 2>&1\n'
    'say "stage 1e: resampy -> $TFX rc=$? import: $(PYTHONPATH="$PYPATH" python3 -c \'import resampy.core;print(\\"OK\\")\' 2>&1 | tail -1)"')
rep('  cp -p "$PG" /root/freeze.html.orig\n',
    '  [ -s /root/freeze.html.orig ] || cp -p "$PG" /root/freeze.html.orig   # job3 already saved the TRUE original\n')
rep('say "stage 0b: CMD channel is job2\'s (/root/in/CMD_<name>.sh)"',
    'say "stage 0b: job4 = job3 + resampy fix (job3 stopped by CMD_job4)"\n: > "$OUT/STAGES.job4"')
open("/dev/shm/t8/up/job4.sh", "w").write(s)
open("/dev/shm/t8/up/CMD_job4.sh", "w").write(
    'pkill -f "[j]ob3.sh"; sleep 2\n'
    'cp /root/out/live/STAGES /root/out/live/STAGES.job3 2>/dev/null\n'
    'ls -la /root/freeze.html.orig; md5sum /root/freeze.html.orig /workspace/pages/beta/freeze.html\n'
    'nohup bash /root/in/job4.sh > /root/out/logs/job4.log 2>&1 &\necho started job4\n')
print("ok")
