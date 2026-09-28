from pathlib import Path
from functools import lru_cache
import os,re,json
from docsearch import sync,search
ROOT=Path(__file__).parent
STOP={'the','is','a','an','to','in','of','how','what','when','why','do','does','are','for','long','and','can','i'}
def retrieve(question,root=None,database=None):
 root=Path(root or ROOT/'examples/docs');database=Path(database or ROOT/'var/rag.sqlite');sync(root,database)
 words=[w for w in re.findall(r'[^\W_]+',question.lower()) if w not in STOP]
 found={}
 for word in words[:20]:
  for row in search(database,word,10):
   key=(row['path'],row['start_line']);item=found.setdefault(key,{**row,'matches':0});item['matches']+=1
 results=sorted(found.values(),key=lambda x:(-x['matches'],x['rank'],x['path']))[:3]
 for row in results:
  lines=(root/row['path']).read_text().splitlines();row['body']='\n'.join(lines[row['start_line']-1:row['end_line']]);row.pop('source_uri',None)
 return results
@lru_cache(maxsize=1)
def llm():
 import torch
 from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
 source=os.environ.get('RAG_MODEL',str(ROOT/'var/model'));torch.set_num_threads(4)
 if not Path(source).exists():raise ValueError('Local language model is not downloaded. Run python download_model.py; extractive mode remains available.')
 return AutoTokenizer.from_pretrained(source),AutoModelForSeq2SeqLM.from_pretrained(source).eval()
def answer(question,mode='extractive',sources=None):
 if not isinstance(question,str) or not 3<=len(question)<=1000:raise ValueError('Question must contain 3–1,000 characters')
 if mode not in ['extractive','local-llm']:raise ValueError('Choose a supported engine')
 sources=retrieve(question) if sources is None else sources
 if not sources:return 'No matching evidence was found. Try a runbook topic such as backups or incident response.',[]
 if mode=='extractive':
  q=set(re.findall(r'\w+',question.lower()))-STOP;sentences=[]
  for s in sources:
   for sentence in re.split(r'(?<=[.!?])\s+',s['body']):
    score=len(q&set(re.findall(r'\w+',sentence.lower())))
    if score:sentences.append((score,sentence,s['path'],s['start_line'],s['end_line']))
  sentences.sort(key=lambda x:-x[0]);result='\n\n'.join(f'{s[1]} [{s[2]}:{s[3]}–{s[4]}]' for s in sentences[:3])
 else:
  import torch
  tokenizer,model=llm();context='\n'.join(s['body'] for s in sources)
  prompt='Answer the question using only the context. If the context does not answer it, say unknown.\nContext: '+context+'\nQuestion: '+question+'\nAnswer:'
  x=tokenizer(prompt,return_tensors='pt',truncation=True,max_length=512)
  with torch.no_grad():result=tokenizer.decode(model.generate(**x,max_new_tokens=90,do_sample=False)[0],skip_special_tokens=True)
 return result,sources

def analyze(p):
 q=p.get('question','How long is the backup retention period?');mode=p.get('mode','extractive');result,sources=answer(q,mode)
 return dict(metrics={'Retrieved passages':len(sources),'Engine':mode},answer=result,rows=[{k:s[k] for k in ['path','heading','start_line','end_line','matches']} for s in sources],notice='Generated answers require review against the retrieved passages below. Retrieval citations identify context, not a guarantee that every generated claim is supported.' if mode=='local-llm' else 'Deterministic extractive answer: source sentences, not language-model output.',details={'question':q,'sources':sources,'model':'google/flan-t5-small' if mode=='local-llm' else None})
