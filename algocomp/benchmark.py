"""Empirical benchmark engine: time arbitrary Python files in a subprocess."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field

_RUNNER = (
    "import json,sys,time,tracemalloc,inspect\n"
    "target=sys.argv[1]\n"
    "ns={}\n"
    "code=open(target,'r',encoding='utf-8').read()\n"
    "exec(compile(code,target,'exec'),ns)\n"
    "cfg=json.loads(sys.argv[2])\n"
    "fn=ns.get(cfg.get('function') or 'main')\n"
    "cands=sorted([k for k,v in ns.items() if callable(v) and not k.startswith('_')])\n"
    "if not callable(fn):\n"
    "    print(json.dumps({'ok':False,'error':'no callable; found: '+str(cands)}))\n"
    "    raise SystemExit(0)\n"
    "mk=ns.get(cfg.get('input_factory') or '')\n"
    "n=cfg['n']\n"
    "kind=cfg.get('input','list')\n"
    "arg=''\n"
    "try:\n"
    "    arg=mk(n) if callable(mk) else (list(range(n)) if kind in ('list','sorted') else ('a'*n if kind=='string' else list(range(n))))\n"
    "except Exception as exc:\n"
    "    print(json.dumps({'ok':False,'error':'input failed: '+str(exc)}))\n"
    "    raise SystemExit(0)\n"
    "reps=max(1,int(cfg.get('repeats',3)))\n"
    "takes=len(inspect.signature(fn).parameters)>0\n"
    "tracemalloc.start()\n"
    "samples=[]\n"
    "peak=0\n"
    "try:\n"
    "    x=1\n"
    "    for _ in range(reps):\n"
    "        payload=list(arg) if isinstance(arg,list) else arg\n"
    "        t0=time.perf_counter()\n"
    "        fn(payload) if takes else fn()\n"
    "        samples.append(time.perf_counter()-t0)\n"
    "        _,pk=tracemalloc.get_traced_memory()\n"
    "        peak=max(peak,pk)\n"
    "except Exception as exc:\n"
    "    print(json.dumps({'ok':False,'error':type(exc).__name__+': '+str(exc)}))\n"
    "    raise SystemExit(0)\n"
    "finally:\n"
    "    tracemalloc.stop()\n"
    "print(json.dumps({'ok':True,'samples':samples,'peak_bytes':peak}))\n"
)


@dataclass
class BenchPoint:
    n: int
    seconds: float
    repeats: int = 1
    peak_bytes: int = 0
    samples: list = field(default_factory=list)

    def to_dict(self):
        return {"n": self.n, "seconds": self.seconds, "repeats": self.repeats,
                "peak_bytes": self.peak_bytes, "samples": list(self.samples)}


@dataclass
class BenchResult:
    target: str
    function: str
    points: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dict(self):
        return {"target": self.target, "function": self.function,
                "points": [p.to_dict() for p in self.points],
                "warnings": list(self.warnings)}


def _run_once(target, n, *, function, repeats, timeout, input_kind, factory):
    cfg = json.dumps({"n": n, "function": function, "repeats": repeats,
                      "input": input_kind, "input_factory": factory})
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _RUNNER, target, cfg],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout at n=%d" % n
    out = (proc.stdout or "").strip().splitlines()
    if not out:
        return None, "no output at n=%d: %s" % (n, (proc.stderr or "")[-300:])
    try:
        payload = json.loads(out[-1])
    except ValueError:
        return None, "bad runner output at n=%d" % n
    if not payload.get("ok"):
        return None, "target error at n=%d: %s" % (n, payload.get("error"))
    samples = sorted(float(s) for s in payload.get("samples", []))
    if not samples:
        return None, "no samples at n=%d" % n
    med = samples[len(samples) // 2]
    return (med, int(payload.get("peak_bytes", 0)), samples), ""


def run_benchmark(target, sizes, *, function="main", repeats=5,
                  timeout=20.0, input_kind="list", input_factory="",
                  max_time=5.0):
    """Benchmark *target* file across *sizes*; subprocess-isolated per size."""
    import os
    res = BenchResult(target=target, function=function)
    if not os.path.exists(target):
        res.warnings.append("file not found: %s" % target)
        return res
    for raw in sizes:
        n = int(raw)
        if n < 1:
            continue
        got, warn = _run_once(target, n, function=function, repeats=repeats,
                              timeout=timeout, input_kind=input_kind,
                              factory=input_factory)
        if got is None:
            res.warnings.append(warn)
            if "timeout" in warn or "error" in warn:
                break
            continue
        med, peak, samples = got
        res.points.append(BenchPoint(n=n, seconds=med, repeats=len(samples),
                                    peak_bytes=peak, samples=samples))
        if med > max_time:
            res.warnings.append("stopping: %.3fs exceeded max_time at n=%d" % (med, n))
            break
    if len(res.points) < 2:
        res.warnings.append("fewer than 2 usable sizes; fits unreliable")
    return res


__all__ = ["BenchPoint", "BenchResult", "run_benchmark"]

