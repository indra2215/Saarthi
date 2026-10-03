import sys
print(sys.version)
try:
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("all-MiniLM-L6-v2")
    r = m.encode(["test machine learning"])
    print("OK shape:", r.shape)
except Exception as e:
    print("ERROR:", e)
    import traceback; traceback.print_exc()
