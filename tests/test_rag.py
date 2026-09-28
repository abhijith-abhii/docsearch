import pytest
from core import answer,retrieve

def test_citations_and_retrieval():
 result,sources=answer('How long is the backup retention period?')
 assert '14 days' in result and any(s['path']=='backups.md' for s in sources)
 for s in sources:assert s['start_line']<=s['end_line']
def test_no_evidence_abstains():
 result,sources=answer('zxqv unicorns');assert sources==[] and 'No matching evidence' in result
@pytest.mark.parametrize('question',['','a','x'*1001])
def test_invalid_question(question):
 with pytest.raises(ValueError):answer(question)
def test_mode_not_silently_replaced():
 with pytest.raises(ValueError):answer('backup retention','fake-model')
