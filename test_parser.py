from agent import find_benchmark, load_benchmark_db

b = load_benchmark_db()
print(f"Loaded {len(b)} tests\n")

tests = [
    "Total R.B.C. Count",
    "Red cell Distribution Width (R.D.W.-CV)",
    "Total W.B.C. Count",
    "M.C.V.",
    "M.C.H.",
    "M.C.H.C.",
    "Platelet Count",
    "Hemoglobin",
    "P.C.V.",
    "Neutrophils",
    "Lymphocytes",
    "Monocytes",
    "Eosinophils",
    "Basophils",
    "ESR",
    "RDW-CV",
]

for t in tests:
    match = find_benchmark(t, b)
    if match:
        print(f"  {t:45s} -> {match['test_name']:30s} [{match['category']}]")
    else:
        print(f"  {t:45s} -> *** NOT FOUND ***")
