### Indexing Component

1. **Setup Virtual Environment:**
   - Create and activate a Python 3.11 virtual environment.  
     [Python venv documentation](https://docs.python.org/3/library/venv.html)

2. **Install Python Dependencies:**
   ```bash
   pip install -r process_data/requirements.txt
   ```

3. **Rust Module Compilation:**
   - The indexer uses a Rust helper module for performance.
   - Install `maturin`:
     ```bash
     pip install maturin
     ```
   - Build the Rust module:
     ```bash
     cd process_data/src/rust_python_module
     maturin build --release
     ```

4. **Run the Indexer:**
   ```bash
   cd process_data/
   python main.py
   ```