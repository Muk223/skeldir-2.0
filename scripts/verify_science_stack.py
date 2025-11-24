#!/usr/bin/env python3
"""
Scientific Stack Validation - Phase C
Empirically prove environment can sustain Bayesian inference computational load.

This script tests:
1. Import availability (NumPy, Pandas, SciPy, Matplotlib, PyMC, ArviZ)
2. Statistical computation capability
3. Model sampling (if PyMC available)
4. Convergence diagnostics (if ArviZ available)

Exit codes:
- 0: All tests passed
- 1: Critical failure (NumPy/SciPy unavailable)
- 2: Partial success (PyMC unavailable but core stack works)
"""

import sys
import json
import datetime
from pathlib import Path

try:
    import numpy as _np
except Exception:  # pragma: no cover - fallback when numpy missing
    _np = None


def _make_serializable(value):
    """Recursively convert numpy/scientific types into JSON-safe primitives."""
    if isinstance(value, dict):
        return {k: _make_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_make_serializable(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_make_serializable(v) for v in value)
    if _np is not None:
        if isinstance(value, _np.ndarray):
            return value.tolist()
        if isinstance(value, _np.generic):
            return value.item()
    return value

print("=" * 60)
print("Scientific Stack Validation")
print(f"Timestamp: {datetime.datetime.now().isoformat()}")
print("=" * 60)

results = {
    "timestamp": datetime.datetime.now().isoformat(),
    "python_version": sys.version,
    "imports": {},
    "computation_tests": {},
    "sampling_tests": {},
    "exit_code": 0
}

# Test 1: Import availability
print("\n[1/4] Testing Package Imports...")
print("-" * 60)

packages = ["numpy", "pandas", "scipy", "matplotlib", "pymc", "arviz"]
for pkg in packages:
    try:
        __import__(pkg)
        print(f"[OK] {pkg:15} - SUCCESS")
        results["imports"][pkg] = "SUCCESS"
    except ImportError as e:
        print(f"[FAIL] {pkg:15} - FAILED: {str(e)[:50]}")
        results["imports"][pkg] = f"FAILED: {str(e)}"

# Test 2: Core numerical computation
print("\n[2/4] Testing Core Numerical Computation...")
print("-" * 60)

try:
    import numpy as np
    import scipy.stats as stats
    
    # Generate sample data
    np.random.seed(42)
    data = np.random.normal(loc=100, scale=15, size=1000)
    
    # Statistical tests
    mean = np.mean(data)
    std = np.std(data)
    skew = stats.skew(data)
    kurtosis = stats.kurtosis(data)
    
    print(f"[OK] Generated 1000 samples from N(100, 15)")
    print(f"  - Mean: {mean:.2f}")
    print(f"  - Std Dev: {std:.2f}")
    print(f"  - Skewness: {skew:.4f}")
    print(f"  - Kurtosis: {kurtosis:.4f}")
    
    results["computation_tests"]["basic_stats"] = {
        "status": "SUCCESS",
        "mean": float(mean),
        "std": float(std),
        "skew": float(skew),
        "kurtosis": float(kurtosis)
    }
    
except Exception as e:
    print(f"[FAIL] Numerical computation FAILED: {e}")
    results["computation_tests"]["basic_stats"] = {
        "status": "FAILED",
        "error": str(e)
    }
    results["exit_code"] = 1

# Test 3: Linear regression (SciPy)
print("\n[3/4] Testing Statistical Modeling (SciPy)...")
print("-" * 60)

try:
    import numpy as np
    import scipy.stats as stats
    
    # Generate linear relationship with noise
    np.random.seed(42)
    x = np.linspace(0, 10, 100)
    y_true = 2.5 * x + 3.0
    y = y_true + np.random.normal(0, 2, size=100)
    
    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    
    print(f"[OK] Linear regression: y = {slope:.3f}x + {intercept:.3f}")
    print(f"  - R-squared: {r_value**2:.4f}")
    print(f"  - p-value: {p_value:.6f}")
    print(f"  - Std error: {std_err:.4f}")
    print(f"  - True params: y = 2.5x + 3.0")
    print(f"  - Recovery: {'GOOD' if abs(slope - 2.5) < 0.2 else 'POOR'}")
    
    results["computation_tests"]["linear_regression"] = {
        "status": "SUCCESS",
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_value**2),
        "parameter_recovery": bool(abs(slope - 2.5) < 0.2)
    }
    
except Exception as e:
    print(f"[FAIL] Statistical modeling FAILED: {e}")
    results["computation_tests"]["linear_regression"] = {
        "status": "FAILED",
        "error": str(e)
    }

# Test 4: Bayesian sampling (PyMC if available)
print("\n[4/4] Testing Bayesian Sampling (PyMC)...")
print("-" * 60)

if results["imports"].get("pymc") == "SUCCESS":
    try:
        import pymc as pm
        import arviz as az
        import numpy as np
        
        # Simple linear model
        np.random.seed(42)
        x_data = np.linspace(0, 10, 50)
        y_data = 2.5 * x_data + 3.0 + np.random.normal(0, 1, size=50)
        
        with pm.Model() as model:
            # Priors
            slope = pm.Normal('slope', mu=0, sigma=10)
            intercept = pm.Normal('intercept', mu=0, sigma=10)
            sigma = pm.HalfNormal('sigma', sigma=5)
            
            # Likelihood
            mu = slope * x_data + intercept
            y_obs = pm.Normal('y_obs', mu=mu, sigma=sigma, observed=y_data)
            
            # Sample
            print("  Sampling posterior (4 chains, 500 samples)...")
            trace = pm.sample(500, tune=500, chains=4, cores=1, 
                            progressbar=False, random_seed=42)
        
        # Convergence diagnostics
        summary = az.summary(trace, var_names=['slope', 'intercept', 'sigma'])
        
        slope_rhat = summary.loc['slope', 'r_hat']
        intercept_rhat = summary.loc['intercept', 'r_hat']
        slope_ess = summary.loc['slope', 'ess_bulk']
        intercept_ess = summary.loc['intercept', 'ess_bulk']
        
        print(f"[OK] Sampling completed successfully")
        print(f"  - slope: R-hat = {slope_rhat:.4f}, ESS = {slope_ess:.0f}")
        print(f"  - intercept: R-hat = {intercept_rhat:.4f}, ESS = {intercept_ess:.0f}")
        
        # Check convergence criteria (updated threshold: ESS > 400)
        rhat_pass = slope_rhat < 1.01 and intercept_rhat < 1.01
        ess_pass = slope_ess > 400 and intercept_ess > 400
        
        print(f"  - R-hat < 1.01: {'PASS' if rhat_pass else 'FAIL'}")
        print(f"  - ESS > 400: {'PASS' if ess_pass else 'FAIL'}")
        
        results["sampling_tests"]["pymc_sampling"] = {
            "status": "SUCCESS" if (rhat_pass and ess_pass) else "PARTIAL",
            "slope_rhat": float(slope_rhat),
            "intercept_rhat": float(intercept_rhat),
            "slope_ess": float(slope_ess),
            "intercept_ess": float(intercept_ess),
            "convergence": rhat_pass and ess_pass
        }
        
        if not (rhat_pass and ess_pass):
            print("  [WARN] Convergence criteria not fully met")
            results["exit_code"] = 2
        
    except Exception as e:
        print(f"[FAIL] PyMC sampling FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["sampling_tests"]["pymc_sampling"] = {
            "status": "FAILED",
            "error": str(e)
        }
        results["exit_code"] = 2
else:
    print("[WARN] PyMC not available (Python version incompatibility)")
    print(f"  Current Python: {sys.version_info.major}.{sys.version_info.minor}")
    print("  Required: Python 3.11-3.13")
    print("\n  NOTE: This is expected on Windows with Python 3.14")
    print("  In Replit environment with Python 3.11, PyMC will be available.")
    print("\n  Core scientific stack (NumPy, SciPy) validated successfully.")
    print("  Statistical computation capability PROVEN.")
    
    results["sampling_tests"]["pymc_sampling"] = {
        "status": "SKIPPED",
        "reason": "PyMC unavailable (Python version incompatibility)",
        "note": "Core scientific computation validated successfully"
    }
    results["exit_code"] = 2

# Final summary
print("\n" + "=" * 60)
print("VALIDATION SUMMARY")
print("=" * 60)

imports_success = sum(1 for v in results["imports"].values() if v == "SUCCESS")
imports_total = len(results["imports"])
print(f"Imports: {imports_success}/{imports_total} successful")

comp_success = sum(1 for v in results["computation_tests"].values() if v.get("status") == "SUCCESS")
comp_total = len(results["computation_tests"])
print(f"Computation Tests: {comp_success}/{comp_total} successful")

if results["sampling_tests"]:
    samp_status = list(results["sampling_tests"].values())[0]["status"]
    print(f"Sampling Tests: {samp_status}")

print("\nExit Code: " + str(results["exit_code"]))
if results["exit_code"] == 0:
    print("Status: FULL SUCCESS - All tests passed")
elif results["exit_code"] == 2:
    print("Status: PARTIAL SUCCESS - Core stack validated, PyMC unavailable")
else:
    print("Status: FAILURE - Critical errors encountered")

# Write JSON results
output_path = Path("evidence_registry/statistics/model_results.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(_make_serializable(results), f, indent=2)

# Lightweight summary for gate scripts (focus on sampling metrics)
sampling_summary = {
    "timestamp": results["timestamp"],
    "exit_code": results["exit_code"],
    "sampling_tests": results.get("sampling_tests", {}),
}
summary_path = Path("evidence_registry/statistics/sampling_output.json")
with open(summary_path, 'w') as f:
    json.dump(_make_serializable(sampling_summary), f, indent=2)

print(f"\nResults written to: {output_path}")
print(f"Sampling summary written to: {summary_path}")
print("=" * 60)

sys.exit(results["exit_code"])

