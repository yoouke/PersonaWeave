"""Runtime self-description, injected into engines without granting tools."""
from pathlib import Path
from .store import atomic_text

GUIDE_PATH = Path(__file__).with_name('agent-guide.md')
WORKSPACE_GUIDE = 'PERSONAWEAVE_CONTEXT.md'


def agent_context(mode):
    if mode not in ('sdk', 'web', 'chat', 'astrbot'):
        raise ValueError('未知运行上下文')
    notes = {
        'sdk': '当前为宿主提交的 Agent 任务。使用引擎本次提供的工具，回复由宿主管理返回。',
        'web': '当前为原生 Agent 控制台运行环境，可能接收桥接任务。实际身份与工具授权由引擎及通信桥检查。',
        'chat': '当前为纯对话或受限对话，没有电脑操作和插件工具。只能交流、整理文案和解释步骤，不声称执行操作。',
        'astrbot': '当前为通信角色环境，工具以通信引擎本次提供的列表为准。主人可通过 /dsh 提交 Agent 任务，不将普通聊天当作已执行的电脑操作。',
    }
    return GUIDE_PATH.read_text(encoding='utf-8')+'\n\n## 本次运行方式\n'+notes[mode]


def persona_text(char, mode):
    return agent_context(mode)+'\n\n## 用户角色设定\n'+char['personality']+'\n'+char.get('behavior', '')


def export_context(workspace, mode):
    """Export only the public runtime guide; never export account/config/identity data."""
    path = Path(workspace)/WORKSPACE_GUIDE
    if path.is_symlink():
        raise ValueError('运行说明路径不能是符号链接')
    atomic_text(path, agent_context(mode))
    return path
