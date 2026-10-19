"""Bounded supported-entry probe; never bypass the closed Forecast scope guard."""
import ctypes,hashlib,json,subprocess,sys,time,tempfile
from ctypes import wintypes
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone

LIMITS=dict(max_work=250000,max_seconds=30,watchdog_seconds=35,sampled_stop_bytes=384*1024*1024,poll_seconds=0.02)
OUTPUT=Path('benchmarks/player_match_groups/initial-seven-uniform-entry-results.json')


def worker():
    def mark(stage):print(json.dumps(dict(progress_stage=stage)),flush=True)
    mark('imports')
    from .cut_out_user_seven_uniform_preparation import comparison_game,prepare
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.information_set_forecast import Pending
    from werewolf.calculation_budget import calculation_budget,budget_usage,CalculationBudgetExceeded
    from .cut_out_uniform_game_fixture import peak_bytes
    mark('input');start=time.perf_counter();result=dict(stage='input',value=None,forecast_completed=False)
    c=None
    try:
        with calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
            original,game=comparison_game()
            assert (game['players'],game['wolves'],game['mediums'],game['seers'],game['hunters'])==(7,2,1,1,0)
            assert game['claims']==['seer','seer','medium','latent','latent','latent','latent']
            assert sorted((r['reporter'],r['day'],r['target'],r['color']) for r in game['seer_inputs'])==[(1,1,4,'white'),(2,1,4,'white')]
            assert all(game['policy'][k]=='random' for k in ('day','night','fake_reports'))
            result['game']=game;result['game_sha256']=hashlib.sha256(json.dumps(game,sort_keys=True).encode()).hexdigest()
            result['stage']='independent_initial_preparation';mark(result['stage'])
            prepared=prepare(game);assert hasattr(prepared,'source')
            result['stage']='closed_constructor';mark(result['stage'])
            c=ClosedCalculation(prepared.data,grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=LIMITS['max_work'],max_seconds=LIMITS['max_seconds'])
            root=c.root;source=root.read()
            assert source==prepared.source and root.groups==prepared.groups
            result.update(stage='root_forecast',initial_joint_hypotheses=len(source.public_state.hypotheses),groups=root.groups,initial_independent_source_equal=True,initial_alive=source.public.alive,initial_phase=source.public.phase,initial_day=source.public.day)
            mark(result['stage'])
            try:
                result['value']=str(root.forecast().village_win);result['forecast_completed']=True
            except Pending as error:
                result.update(status='unsupported',reason=error.reason)
            result['budget']=budget_usage()
    except CalculationBudgetExceeded as error:result.update(status='budget_stopped',reason=error.kind)
    finally:
        result['seconds']=time.perf_counter()-start;result['peak_working_set_bytes']=peak_bytes()
        if c is not None:result['states']=c.stats()
    print(json.dumps(result),flush=True)


class Counters(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]


def run():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    start=time.perf_counter();output_file=tempfile.TemporaryFile();error_file=tempfile.TemporaryFile()
    p=subprocess.Popen([sys.executable,'-X','utf8','-m','benchmarks.player_match_groups.initial_seven_entry_probe','worker'],stdout=output_file,stderr=error_file,creationflags=subprocess.CREATE_NO_WINDOW)
    handle=kernel.OpenProcess(0x410,False,p.pid);samples=0;peak_private=0;peak_ws=0;stop=None
    try:
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        while p.poll() is None:
            counters=Counters();counters.cb=ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(handle,ctypes.byref(counters),counters.cb):
                if p.poll() is not None:break
                raise ctypes.WinError(ctypes.get_last_error())
            samples+=1;peak_private=max(peak_private,counters.PeakPagefileUsage);peak_ws=max(peak_ws,counters.PeakWorkingSetSize)
            if max(counters.PagefileUsage,counters.WorkingSetSize)>=LIMITS['sampled_stop_bytes']:stop='sampled_memory_limit'
            elif time.perf_counter()-start>=LIMITS['watchdog_seconds']:stop='watchdog_time_limit'
            if stop:p.terminate();break
            time.sleep(LIMITS['poll_seconds'])
        p.wait(timeout=5);output_file.seek(0);error_file.seek(0)
        out=output_file.read().decode('utf-8');err=error_file.read().decode('utf-8')
    finally:
        if p.poll() is None:p.kill();p.wait(timeout=5)
        if handle:kernel.CloseHandle(handle)
        output_file.close();error_file.close()
    result=dict(completed_at=datetime.now(timezone.utc).isoformat(),limits=LIMITS,limits_note='20ms sampled early-stop at384MiB private committed or working set; not an OS hard memory reservation. No scope guard is removed.',supervisor_seconds=time.perf_counter()-start,samples=samples,peak_private_committed_bytes=peak_private,observed_peak_working_set_bytes=peak_ws,termination=stop,returncode=p.returncode,stderr=err)
    if stop is None:
        assert p.returncode==0,err
        result['worker']=json.loads(out.splitlines()[-1])
    else:result['partial_stdout']=out
    result['progress']=[json.loads(line) for line in out.splitlines() if 'progress_stage' in line]
    result['source_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in map(Path,('werewolf/closed_calculation.py','werewolf/grouped_forecast.py','werewolf/morning_publications.py','benchmarks/player_match_groups/initial_seven_entry_probe.py'))}
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker()
    else:print(json.dumps(run()))
