'use strict';

async function upstreamPlugins(){
 const c=card('复用 DSQQ / AstrBot 插件');
 hint(c,'直接使用 DSQQ 同款插件，由 AstrBot 原生运行。每个角色连接一个独立实例；不导入固定人格。');
 c.append(safeLink('DSQQ 官方安装包与说明','https://github.com/Jack-Cherish/DSQQ'),document.createTextNode(' · '),safeLink('AstrBot 官方控制台文档','https://docs.astrbot.app/'));
 const sel=characterSelect(c),url=field(c,'AstrBot 后台地址','http://127.0.0.1:6185'),user=field(c,'后台账号','dafeiyu'),password=field(c,'后台密码（留空保留）','','password');
 const state=node('p','尚未连接','muted'),list=node('div');
 organizeFields(c,[['连接现有实例','DSQQ 已包含 AstrBot 与 NapCat；使用它的后台地址和登录密码。',[sel,url,user,password]]]);
 actions(c,button('连接现有 DSQQ / AstrBot',async()=>{
  const result=await api('astrbot/bind',{character_id:sel.value,url:url.value,username:user.value,password:password.value});
  password.value='';notice(result.message);await refresh();
 }),button('刷新真实安装状态',refresh,'secondary'),button('打开 AstrBot 控制台',()=>{const u=new URL(url.value);if(!['http:','https:'].includes(u.protocol)||!['127.0.0.1','[::1]'].includes(u.hostname)||u.username||u.password)throw Error('仅允许本机控制台');window.open(u.href,'_blank','noopener,noreferrer');},'secondary'),button('移除管理连接',async()=>{const r=await api('astrbot/unbind',{character_id:sel.value});notice(r.message);await refresh();},'secondary'));
 c.append(state,list);
 c.append(button('同步当前角色设定到 AstrBot',async()=>{const r=await api('astrbot/persona',{character_id:sel.value});notice(r.message);},'secondary'));
 async function refresh(){
  const result=await api('astrbot/catalog?character_id='+encodeURIComponent(sel.value||''));
  if(result.binding){url.value=result.binding.url;user.value=result.binding.username;state.textContent='已连接插件接口；QQ 登录及消息由 AstrBot / NapCat 管理。';}
  else state.textContent='此角色尚未连接实例。下方是上游插件清单，尚未安装。';
  list.replaceChildren();
  for(const p of result.plugins){
   const row=node('article',undefined,'list-item');row.append(node('h3',p.name),safeLink(p.id,p.repository),node('p',p.source+' · '+(p.installed?'已安装 '+p.version:'未安装')));
   if(p.enabled!==undefined&&p.enabled!==null)row.append(node('span',p.enabled?'已启用':'未启用','tag'));
   actions(row,...(p.installed?['enable','disable','update','reload']:['install']).map(action=>button({install:'安装上游插件',enable:'启用',disable:'禁用',update:'更新',reload:'重载'}[action],async()=>{
    const r=await api('astrbot/operate',{character_id:sel.value,id:p.id,action});notice(r.message);await refresh();
   },'secondary')));list.append(row);
  }
 }
 sel.onchange=async()=>{password.value='';try{await refresh();}catch(e){error(e);}};
 await refresh();
 const bridge=card('连接现有 DSH 桥接插件');
 hint(bridge,'采用 CCYellowStar2 的 astrbot_plugin_dsh + dsh-astrbot-ingress。先安装两侧插件，在原生 DSH 控制台配置模型与工作区。AstrBot 需仅主人一位管理员，消息白名单仅包含主人私聊。');
 const ingress=field(bridge,'外部 DSH ingress 地址（自动连接时可不改）','http://127.0.0.1:3188'),token=field(bridge,'外部 ingress token（留空自动连接本角色）','','password');
 actions(bridge,button('配置主人专用 DSH 桥',async()=>{const r=await api('astrbot/bridge',{character_id:sel.value,url:ingress.value,token:token.value});token.value='';notice(r.message);await refresh();}),safeLink('上游桥接说明','https://github.com/CCYellowStar2/dsh-astrbot-ingress'));
 hint(bridge,'日常人格聊天由 AstrBot 及其插件处理；主人发送 /dsh 任务，由现有桥接插件转交 DSH。');
 const native=card('DSH 原生插件：桥接与画图');
 hint(native,'安装到当前默认角色的 DSH 控制台，使用插件自带界面与能力。');
 actions(native,button('安装现成 DSH ingress 插件',()=>job('native_ingress')),button('安装现成画图插件',()=>job('native_image'),'secondary'),button('启动原生 DSH 控制台',()=>job('native_web'),'secondary'),button('停止原生 DSH 控制台',()=>api('native/stop',{}),'secondary'),button('打开原生 DSH 控制台',()=>api('console',{kind:'dsh'}),'secondary'));
 native.append(safeLink('dsh-image-gen · OpenAI / Gemini / ComfyUI 等','https://github.com/shanliuling/dsh-image-gen'));
 hint(native,'画图需要在插件原生设置中配置图像服务及凭据。尚未验证自动将生成图片回传 QQ，不能将“插件安装成功”当作“QQ 画图验收通过”。');
}
