# Data, code and model sources

The topic comes from the source mapping in the portfolio index. Original authored synthetic fixtures and procedural images are distributed under the repository MIT license. Synthetic records do not describe actual customers, employees, players or transactions.

Implementation references:
- Flask: https://flask.palletsprojects.com/en/stable/ — request handling and security considerations.
- Python SQLite: https://docs.python.org/3/library/sqlite3.html — transactions, parameter binding and authorizers.
- scikit-learn: https://scikit-learn.org/stable/common_pitfalls.html — leakage prevention and fitted preprocessing.

Only applicable libraries are used; their upstream licenses remain in installed distributions. Project code does not claim authorship of dependencies.

Model: [google/flan-t5-small](https://huggingface.co/google/flan-t5-small), revision `0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab`, Apache-2.0. Model weights are downloaded separately. Transformers and PyTorch execute actual local inference. No remote inference API is called.
