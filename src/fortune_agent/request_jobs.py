"""Bounded local background requests, observable stages and cooperative cancellation."""
from copy import deepcopy
from dataclasses import dataclass,field
import secrets
import threading
import time


class RequestCancelled(Exception):pass


@dataclass
class Job:
    id:str
    payload:dict=field(default_factory=dict)
    created:float=field(default_factory=time.monotonic)
    status:str='running'
    stage:str='正在核对资料'
    preview:dict|None=None
    result:dict|None=None
    error:str|None=None
    session_id:str|None=None
    cancel_event:object=field(default_factory=threading.Event)
    lock:object=field(default_factory=threading.Lock)
    done:object=field(default_factory=threading.Event)
    def check(self):
        if self.cancel_event.is_set():raise RequestCancelled('已取消本次解读；正在进行的服务商请求可能仍产生费用，返回内容不会采用。')
    def progress(self,stage,session_id=None,preview=None):
        self.check()
        with self.lock:
            self.stage=stage
            if session_id:self.session_id=session_id
            if preview is not None:self.preview=deepcopy(preview)


class ProgressResponses:
    def __init__(self,inner,job):self.inner=inner;self.job=job
    def create(self,**kwargs):
        tool=kwargs.get('tool_choice')
        stage='正在生成解读'
        if isinstance(tool,dict) and tool.get('name')=='choose_action':stage='正在识别问题与选择工具'
        elif isinstance(tool,dict) and tool.get('name')=='draw_tarot':stage='正在核对已抽取的牌面'
        self.job.progress(stage)
        try:response=self.inner.create(**kwargs)
        except Exception:
            self.job.check()
            raise
        self.job.check()
        return response


class ProgressClient:
    def __init__(self,inner,job):self.inner=inner;self.job=job;self.responses=ProgressResponses(inner.responses,job);self.closed=False
    def close(self):
        if self.closed:return
        self.closed=True
        close=getattr(self.inner,'close',None)
        if close:close()


class RequestJobs:
    def __init__(self,limit=64,active_limit=4,ttl=3600):self.limit=limit;self.active_limit=active_limit;self.ttl=ttl;self.jobs={};self.lock=threading.Lock()
    def start(self,payload,run):
        with self.lock:
            now=time.monotonic();self.jobs={k:j for k,j in self.jobs.items() if not j.done.is_set() or now-j.created<self.ttl}
            if len(self.jobs)>=self.limit:
                settled=sorted((j for j in self.jobs.values() if j.done.is_set()),key=lambda j:j.created)
                for old in settled:
                    del self.jobs[old.id]
                    if len(self.jobs)<self.limit:break
            if len(self.jobs)>=self.limit or sum(not j.done.is_set() for j in self.jobs.values())>=self.active_limit:raise ValueError('正在处理的请求较多，请稍后再试')
            job=Job(secrets.token_urlsafe(24),deepcopy(payload));self.jobs[job.id]=job
        payload=deepcopy(payload)
        def worker():
            try:
                job.check();result=run(payload,job);job.check()
                with job.lock:
                    job.check();job.result=result;job.status='completed';job.stage='已完成'
            except RequestCancelled:
                with job.lock:job.status='cancelled';job.stage='已取消'
            except (ValueError,RuntimeError) as e:
                with job.lock:job.status='failed';job.error=str(e);job.stage='未完成'
            except Exception:
                with job.lock:job.status='failed';job.error='模型请求或本地处理失败，已计算的牌面或会话可重试。';job.stage='未完成'
            finally:job.done.set()
        threading.Thread(target=worker,daemon=True,name='fortune-request').start()
        return {'job_id':job.id}
    def get(self,identifier):
        with self.lock:
            job=self.jobs.get(identifier)
            if not job or (job.done.is_set() and time.monotonic()-job.created>=self.ttl):raise ValueError('请求不存在或已过期')
            return job
    def status(self,identifier):
        job=self.get(identifier)
        with job.lock:
            return {'job_id':job.id,'status':job.status,'stage':job.stage,'elapsed_seconds':round(time.monotonic()-job.created,1),'session_id':job.session_id,
                    'result':deepcopy(job.result) if job.status=='completed' else None,'error':job.error,
                    'preview':deepcopy(job.preview),'cancelling':job.cancel_event.is_set() and not job.done.is_set()}
    def cancel(self,identifier):
        job=self.get(identifier)
        with job.lock:
            if job.status=='running':job.cancel_event.set();job.status='cancelled';job.stage='已取消，正在等待当前请求结束'
        return self.status(identifier)

    def retry(self,identifier,run):
        job=self.get(identifier)
        if not job.done.is_set():raise ValueError('当前服务商请求仍在结束，请稍后再重试')
        with job.lock:
            if job.status=='completed' and (not isinstance(job.result,dict) or job.result.get('status')!='failed'):raise ValueError('请求已成功，无需重试；新问题请重新提交')
            payload=deepcopy(job.payload)
            if payload.get('mode')=='chat' and job.session_id:
                payload['session_id']=job.session_id
                if job.preview:payload['message']='重试解读'
            if payload.get('mode')=='iching' and job.preview and job.preview.get('cast'):
                payload['lines']=job.preview['cast']['lines_bottom_to_top']
                payload['retry_job_id']=job.id
            if payload.get('mode')=='tarot' and job.preview:
                payload['retry_job_id']=job.id
        return self.start(payload,run)
