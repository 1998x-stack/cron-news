'use strict';
const $=id=>document.getElementById(id);
const names={market:'市场与新闻联播',tech:'AI 与技术',china:'中国研究'};
const pathRule=/^reports\/(market|tech|china)\/20\d{2}\/\d{2}\/\d{2}\/(MARKET|TECH|CHINA)-20\d{2}-\d{2}-\d{2}-(?:\d{4}|MANUAL-\d{4})\/(?:report\.(?:md|pdf|docx|pptx)|data\.json)$/;
const fmtNames={md:'Markdown',json:'数据 JSON',pdf:'PDF',docx:'Word',pptx:'PPTX'};
let catalog=[];
const hasNumber=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const safePath=(p,r)=>typeof p==='string'&&pathRule.test(p)&&p.startsWith('reports/'+r.agent+'/')&&p.includes('/'+r.run_key+'/');
function el(tag,text,cl){const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cl)n.className=cl;return n}
function appendText(id,text){$(id).replaceChildren(el('div',text,'notice'))}
function link(path,label){const a=el('a',label);a.href=new URL(path,document.baseURI).href;a.target='_blank';a.rel='noopener noreferrer';return a}
function svgChart(target,entries,{valueKey='value',unit='',labelKey='name',allowNegative=false}={}){
 const area=$(target);area.replaceChildren();const data=entries.filter(r=>hasNumber(r[valueKey])).slice(-14);
 if(!data.length){area.append(el('p','没有足够的可验证数值用于图表。','muted'));return}
 const w=740,h=174,pad=38,base=allowNegative?87:145,values=data.map(d=>Number(d[valueKey]));
 const largest=Math.max(1,...values.map(v=>Math.abs(v))),span=(w-pad*2)/data.length;
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.setAttribute('role','img');svg.setAttribute('aria-label',`可核验数据图表，共${data.length}项`);
 function shape(tag,attrs,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(text!==undefined)n.textContent=text;svg.append(n)}
 shape('line',{x1:pad,y1:base,x2:w-pad,y2:base,stroke:'#9aacc1','stroke-width':1});
 data.forEach((d,i)=>{const v=Number(d[valueKey]),height=Math.max(2,Math.abs(v)/largest*(allowNegative?66:112));const x=pad+i*span+span*.19;const y=allowNegative?(v>=0?base-height:base):base-height;
 shape('rect',{x,y,width:Math.max(5,span*.6),height,rx:4,fill:v>=0?'#269e96':'#e58b6a'});
 const label=String(d[labelKey]??'').slice(0,10);shape('text',{x:x+span*.3,y:165,'font-size':10,fill:'#718499','text-anchor':'middle'},label);
 shape('text',{x:x+span*.3,y:Math.max(10,y-6),'font-size':10,fill:'#5c7995','text-anchor':'middle'},`${v>0&&allowNegative?'+':''}${v}${unit}`);
 });area.append(svg)
}
function stats(){for(const a of ['market','tech','china'])$('stat-'+a).textContent=catalog.filter(r=>r.agent===a).length;$('stat-total').textContent=catalog.length;$('last-updated').textContent=catalog.length?catalog[0].date+' · 最近归档':'尚无已归档报告';
 const counts=new Map();catalog.forEach(r=>counts.set(r.date,(counts.get(r.date)||0)+1));
 svgChart('activity',[...counts].sort((a,b)=>a[0].localeCompare(b[0])).slice(-14).map(([name,value])=>({name:name.slice(5),value})))}
function render(){
 const agent=$('agent').value,date=$('date').value,q=$('query').value.trim().toLocaleLowerCase();
 const rows=catalog.filter(r=>(!agent||r.agent===agent)&&(!date||r.date===date)&&(!q||[r.title,r.summary,r.run_key].join(' ').toLocaleLowerCase().includes(q)));
 $('count').textContent=`${rows.length} 份匹配 · ${catalog.length} 份已归档`;const area=$('items');area.replaceChildren();
 if(!rows.length){area.append(el('div',catalog.length?'未找到匹配报告。':'还没有经过审计的真实报告；首次成功归档后将在此展示。','notice'));return}
 rows.slice(0,120).forEach(r=>{const item=el('article',undefined,'entry'),body=el('div'),tags=el('div',undefined,'tags');
 tags.append(el('span',names[r.agent]||r.agent,'tag'),el('span',r.date+' · '+r.scheduled_time,'tag dim'),el('span',r.status,'tag dim'));
 body.append(tags,el('h3',r.title),el('p',r.summary));
 const actions=el('div',undefined,'actions');const button=el('button','查看详情');button.type='button';button.addEventListener('click',()=>openReport(r));actions.append(button);
 for(const fmt of ['md','pdf','docx','pptx'])if(safePath(r.files?.[fmt],r))actions.append(link(r.files[fmt],fmtNames[fmt]));
 item.append(body,actions);area.append(item)});
}
async function openReport(r){
 $('detail').hidden=false;$('detail-heading').textContent=r.title;$('detail-meta').textContent=`${names[r.agent]} · ${r.date} ${r.scheduled_time} · ${r.run_key} · ${r.status}`;
 $('detail-summary').textContent=r.summary;$('detail-links').replaceChildren();
 for(const fmt of ['md','json','pdf','docx','pptx'])if(safePath(r.files?.[fmt],r))$('detail-links').append(link(r.files[fmt],fmtNames[fmt]));
 $('report-text').textContent='正在载入研究正文…';$('signals').replaceChildren();$('indices').replaceChildren();$('detail-sources').replaceChildren();
 if(safePath(r.files?.md,r)){fetch(r.files.md).then(x=>{if(!x.ok)throw Error('HTTP '+x.status);return x.text()}).then(s=>$('report-text').textContent=s).catch(e=>$('report-text').textContent='Markdown 获取失败：'+e.message)}
 else $('report-text').textContent='历史档案没有 Markdown 正文，请使用附件链接。';
 if(safePath(r.files?.json,r)){
 try{const res=await fetch(r.files.json,{cache:'no-store'});if(!res.ok)throw Error('HTTP '+res.status);const data=await res.json();if(data.schema_version!==1||data.run_key!==r.run_key)throw Error('数据标识不匹配');
 const signals=Array.isArray(data.signals)?data.signals:[];const indices=Array.isArray(data.indices)?data.indices:[];
 svgChart('signal-chart',signals.map(s=>({name:s.title,value:s.score})).filter(s=>hasNumber(s.value)),{valueKey:'value'});
 svgChart('market-chart',indices.map(i=>({name:i.name,value:i.change_pct})).filter(i=>hasNumber(i.value)),{allowNegative:true,unit:'%'});
 for(const s of signals){const row=el('div',undefined,'signal');row.append(el('strong',s.title||'未命名信号'),el('small',`评分 ${s.score??'未评'} · 置信度 ${s.confidence||'未定'}`),el('div',s.summary||''));$('signals').append(row)}
 if(!signals.length)$('signals').append(el('div','暂无可验证的结构化信号。','notice'));
 for(const m of indices){const row=el('div',undefined,'signal');row.append(el('strong',m.name||'指标'),el('small',`${m.value??'无数据'} · 涨跌 ${m.change_pct??'—'}% · ${m.as_of||''}`));$('indices').append(row)}
 if(!indices.length)$('indices').append(el('div','暂无可核验行情，可能是非交易日或数据未取得。','notice'));
 const sources=el('div',undefined,'source-list');sources.append(el('h3','来源索引'));for(const s of data.sources||[])if(typeof s.url==='string'&&/^https?:\/\//.test(s.url)){const a=el('a',s.title||s.url);a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';sources.append(a)}$('detail-sources').append(sources);
 }catch(e){appendText('signal-chart','结构化数据读取失败：'+e.message);appendText('market-chart','无法绘图');$('signals').replaceChildren();$('indices').replaceChildren()}}
 else{appendText('signal-chart','历史报告未包含结构化数据。');appendText('market-chart','历史报告未包含结构化数据。')}
 $('detail').scrollIntoView({behavior:'smooth',block:'start'});
}
$('close-detail').addEventListener('click',()=>$('detail').hidden=true);
for(const id of ['agent','date','query'])$(id).addEventListener('input',render);
fetch('catalog.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(x=>{if(![1,2].includes(x.schema_version)||!Array.isArray(x.reports))throw Error('catalog 版本不支持');catalog=x.reports;stats();render();const requested=new URLSearchParams(window.location.search).get('report');if(requested){const item=catalog.find(v=>v.run_key===requested);if(item)openReport(item)}}).catch(e=>{$('count').textContent='目录读取失败';appendText('items','无法读取 catalog.json：'+e.message);$('last-updated').textContent='目录不可用'});
