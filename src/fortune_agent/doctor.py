"""Local installation checks; never print API credentials."""
import importlib.util
import json
import subprocess
from .ziwei import node_executable
from .config import ApiConfig


def main():
    checks={'python_packages':{name:importlib.util.find_spec(name) is not None for name in ('lunar_python','astronomy','openai')}}
    try:
        node=node_executable();result=subprocess.run([node,'--version'],capture_output=True,text=True,timeout=5)
        version=result.stdout.strip();checks['node']={'version':version,'supported':result.returncode==0 and int(version.lstrip('v').split('.')[0])>=18}
    except (RuntimeError,OSError,ValueError,subprocess.TimeoutExpired):checks['node']={'supported':False}
    try:
        config=ApiConfig.from_env();checks['api']={'configured':True,'model':config.model,'endpoint':config.base_url}
    except ValueError:checks['api']={'configured':False,'note':'离线排盘与选牌仍可用；模型解读需要环境变量'}
    print(json.dumps(checks,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
