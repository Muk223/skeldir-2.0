"""
B0.5.3.3 Gate B: Import-Chain Forensic Instrumentation

Temporary module to wrap psycopg2.connect and log the exact stack trace
and DSN fingerprint when the first connection attempt is made.

This will identify which import line triggers the premature psycopg2
connection with the wrong password.
"""
import sys
import os
import hashlib
import traceback


# Install import hook to monkey-patch psycopg2 when it's first imported
class Psycopg2ImportHook:
    def find_module(self, fullname, path=None):
        if fullname == 'psycopg2':
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]

        # Import psycopg2 normally
        import importlib
        module = importlib.import_module(fullname)

        # Install monitor immediately after import
        original_connect = module.connect
        first_call_logged = [False]  # Mutable container for closure

        def instrumented_connect(*args, **kwargs):
            if not first_call_logged[0]:
                first_call_logged[0] = True

                # Extract DSN from args or kwargs
                dsn = None
                if args:
                    dsn = args[0] if isinstance(args[0], str) else None
                if not dsn and 'dsn' in kwargs:
                    dsn = kwargs['dsn']

                # Log stack trace
                print("\n" + "="*80, flush=True)
                print("[GATE B FORENSICS] First psycopg2.connect() call detected!", flush=True)
                print("="*80, flush=True)

                if dsn:
                    # Extract password and create fingerprint
                    if '://' in dsn and '@' in dsn:
                        try:
                            creds_part = dsn.split('://')[1].split('@')[0]
                            if ':' in creds_part:
                                user, password = creds_part.split(':', 1)
                                pass_hash = hashlib.sha256(password.encode()).hexdigest()[:8]
                                # Redact password in DSN for logging
                                redacted_dsn = dsn.replace(f':{password}@', ':***@')
                                print(f"DSN: {redacted_dsn}", flush=True)
                                print(f"User: {user}", flush=True)
                                print(f"Password SHA256 prefix: {pass_hash}", flush=True)
                        except Exception as e:
                            print(f"Could not parse DSN: {e}", flush=True)
                            print(f"DSN (raw): {dsn[:50]}...", flush=True)
                else:
                    print("DSN: <not provided as string>", flush=True)
                    print(f"args: {args}", flush=True)
                    print(f"kwargs keys: {list(kwargs.keys())}", flush=True)

                print("\nStack trace at first psycopg2.connect() call:", flush=True)
                print("-" * 80, flush=True)
                for line in traceback.format_stack()[:-1]:  # Exclude this frame
                    print(line.rstrip(), flush=True)
                print("=" * 80, flush=True)
                print("", flush=True)

            # Call original connect
            return original_connect(*args, **kwargs)

        module.connect = instrumented_connect
        print("[GATE B] psycopg2.connect monitor installed via import hook", flush=True)

        return module


# Install hook if in CI mode
if os.getenv("CI") == "true":
    sys.meta_path.insert(0, Psycopg2ImportHook())
    print("[GATE B] Import hook installed to monitor psycopg2.connect", flush=True)
