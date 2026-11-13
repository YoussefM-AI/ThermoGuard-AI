import sys
import platform
import sqlite3

def run_checks():
    print('=' * 60)
    print('  CabinetSense AI - Phase 1 Environment Verification')
    print('=' * 60)
    print(f'Python Version : {platform.python_version()} on {platform.system()} ({platform.machine()})')
    
    # 1. Test Imports
    modules = [
        ('flask', 'Flask'),
        ('flask_cors', 'Flask-CORS'),
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
        ('sklearn', 'Scikit-learn'),
        ('joblib', 'Joblib'),
        ('requests', 'Requests'),
        ('sqlite3', 'SQLite3 driver')
    ]
    
    import importlib.metadata
    for mod_name, label in modules:
        try:
            mod = __import__(mod_name)
            try:
                ver = importlib.metadata.version(mod_name.replace('_', '-'))
            except Exception:
                ver = getattr(mod, '__version__', 'builtin')
            print(f'  [PASS] {label:<16} (version: {ver})')
        except ImportError as e:
            print(f'  [FAIL] {label:<16} Import failed: {e}')
            return False
            
    # 2. Test Isolation Forest instantiation
    try:
        from sklearn.ensemble import IsolationForest
        clf = IsolationForest(n_estimators=10, random_state=42)
        X = [[25.0, 45.0], [25.2, 45.1], [24.9, 44.8], [75.0, 95.0]]
        clf.fit(X)
        preds = clf.predict(X)
        print(f'  [PASS] IsolationForest test fit/predict successful: {preds}')
    except Exception as e:
        print(f'  [FAIL] IsolationForest check failed: {e}')
        return False

    # 3. Test SQLite engine
    try:
        conn = sqlite3.connect(':memory:')
        cur = conn.cursor()
        cur.execute('CREATE TABLE t (id INTEGER PRIMARY KEY, v REAL)')
        cur.execute('INSERT INTO t (v) VALUES (25.4)')
        conn.commit()
        val = cur.execute('SELECT v FROM t WHERE id=1').fetchone()[0]
        conn.close()
        print(f'  [PASS] SQLite in-memory engine verified: test value={val}')
    except Exception as e:
        print(f'  [FAIL] SQLite check failed: {e}')
        return False

    print('=' * 60)
    print('PHASE 1 ENVIRONMENT STATUS: ALL SYSTEMS OPERATIONAL')
    print('=' * 60)
    return True

if __name__ == '__main__':
    if not run_checks():
        sys.exit(1)
