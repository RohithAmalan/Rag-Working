import os
import re
import numpy as np
from pathlib import Path

# --------- Optional Imports ---------
try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# --------- LangChain Imports ---------
from langchain.embeddings.base import Embeddings
from langchain_community.vectorstores import FAISS


def _load_env_file(env_path: Path):
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def _init_groq_client():
    if Groq is None:
        return None, "Groq SDK not installed. Install with: pip install groq"

    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_api_key:
        return None, "GROQ_API_KEY missing. Add it to your shell or .env file."

    return Groq(api_key=groq_api_key), None

# --------- Your Embedding ---------
def _simple_local_embedding(text: str, dim: int = 256) -> np.ndarray:
    vector = np.zeros(dim, dtype="float32")
    tokens = re.findall(r"\w+", text.lower())
    for token in tokens:
        vector[hash(token) % dim] += 1.0
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector

# --------- Wrap into LangChain ---------
class LocalEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [_simple_local_embedding(t).tolist() for t in texts]

    def embed_query(self, text):
        return _simple_local_embedding(text).tolist()

# --------- Improved Chunking ---------
def _smart_chunk_text(text: str):
    chunks = []

    # split based on bullet points (🔹)
    parts = re.split(r"🔹", text)

    for part in parts:
        cleaned = part.strip()
        if cleaned:
            chunks.append(cleaned)

    return chunks

# --------- Load PDFs (FIXED + DEBUG) ---------
def _load_pdf_documents(pdf_dir: Path):
    if PdfReader is None:
        print("❌ pypdf not installed")
        return []

    if not pdf_dir.exists():
        print("❌ PDF folder not found:", pdf_dir)
        return []

    docs = []

    for pdf_file in pdf_dir.glob("*.pdf"):
        print(f"\n📄 Reading: {pdf_file.name}")

        reader = PdfReader(str(pdf_file))
        full_text = ""

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()

            if page_text:
                print(f"Page {i}: {len(page_text)} chars")
                full_text += page_text + "\n"
            else:
                print(f"Page {i}: ❌ No text extracted")

        print("Total extracted length:", len(full_text))

        if len(full_text.strip()) == 0:
            print("⚠️ PDF has no extractable text")
            continue

        chunks = _smart_chunk_text(full_text)
        print("Chunks created:", len(chunks))

        docs.extend(chunks)

    return docs

# --------- Setup Groq ---------
workspace_root = Path(__file__).resolve().parent.parent
_load_env_file(workspace_root / ".env")
groq_client, groq_error = _init_groq_client()

# --------- Step 1: Load Data ---------
pdf_dir = Path(__file__).parent / "pdfs"
print("📂 Looking for PDFs in:", pdf_dir)

documents = _load_pdf_documents(pdf_dir)

# ❌ Remove silent fallback (IMPORTANT for debugging)
if not documents:
    raise ValueError("❌ No documents loaded from PDF. Check extraction.")

print("\n✅ Documents loaded:", len(documents))

# --------- Step 2: LangChain Vector DB ---------
embedding_model = LocalEmbeddings()
db = FAISS.from_texts(documents, embedding_model)

# --------- Step 3: Retriever ---------
retriever = db.as_retriever(search_kwargs={"k": 3})

# --------- Step 4: Query ---------
query = "What is Model training?"

docs = retriever.invoke(query)

print("\n🔍 Retrieved Chunks:")
for i, doc in enumerate(docs, 1):
    print(f"{i}. {doc.page_content[:200]}...\n")

# --------- Step 5: Build Context ---------
context = "\n\n".join([doc.page_content for doc in docs])

print("\n📄 Context Sent to LLM:\n", context[:500], "...")

# --------- Step 6: LLM Answer ---------
if groq_client:
    try:
        response = groq_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict assistant. Answer ONLY using the provided context. If the answer is not in the context, say 'I don't know based on the given data.' Do not use outside knowledge."
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {query}"
                },
            ],
        )

        print("\n🤖 Final Answer:")
        print(response.choices[0].message.content)
    except Exception as exc:
        print(f"\n❌ Groq request failed: {exc}")
        print("Showing retrieved context so you can still verify retrieval output.")
        print(context)

else:
    print(f"\n⚠️ Groq not configured: {groq_error}")
    print("Create /Users/rohith/RAG/.env with GROQ_API_KEY=your_key (or export it in terminal).")
    print("Showing context only:")
    print(context)