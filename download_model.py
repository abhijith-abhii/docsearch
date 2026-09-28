from pathlib import Path
import os
os.environ.setdefault('HF_HOME', str(Path(__file__).resolve().parent/'var/hf-cache'))
from pathlib import Path
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
root=Path(__file__).parent/'var/model';name='google/flan-t5-small';rev='0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab'
AutoTokenizer.from_pretrained(name,revision=rev).save_pretrained(root)
AutoModelForSeq2SeqLM.from_pretrained(name,revision=rev).save_pretrained(root,safe_serialization=True)
print(root)
