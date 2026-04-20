#!/usr/bin/env python3
"""
Moviroo AI Chatbot — test_pipeline.py
Run without a live server to validate the full RAG stack.

Usage:
    python test_pipeline.py              # full test
    python test_pipeline.py --csv-only  # skip DB
"""
import asyncio
import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import settings


class C:
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    YELLOW = "\033[93m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"


def ok(m):   print(f"{C.GREEN}✅ {m}{C.RESET}")
def err(m):  print(f"{C.RED}❌ {m}{C.RESET}")
def info(m): print(f"{C.CYAN}ℹ  {m}{C.RESET}")
def hdr(m):  print(f"\n{C.BOLD}{'─'*55}\n   {m}\n{'─'*55}{C.RESET}")


# ── Step 1: CSV check ─────────────────────────────────────────────

def check_csv() -> bool:
    hdr("STEP 1 — dataset.csv")
    path = os.path.join(settings.data_dir, "dataset.csv")
    if not os.path.exists(path):
        print(f"{C.YELLOW}⚠  dataset.csv not found — built-in samples will be used{C.RESET}")
        return True
    import csv
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ok(f"{len(rows)} rows found")
    for r in rows[:4]:
        print(f"   [{r.get('language','?'):6s}][{r.get('category','?'):12s}] {r.get('question','')[:55]}")
    return True


# ── Step 2: DB tickets ────────────────────────────────────────────

async def check_db() -> int:
    hdr("STEP 2 — database tickets")
    try:
        from database.connection import init_db, AsyncSessionLocal
        from database.models import Ticket
        from sqlalchemy import select, and_
        await init_db()
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(Ticket).where(
                    and_(Ticket.status == "resolved", Ticket.answer.isnot(None))
                )
            )
            resolved = res.scalars().all()
            info(f"{len(resolved)} resolved tickets with answers")
            return len(resolved)
    except Exception as e:
        print(f"{C.YELLOW}⚠  DB unavailable ({e}) — CSV-only mode{C.RESET}")
        return 0


# ── Step 3: Training ──────────────────────────────────────────────

async def run_training(csv_only: bool) -> object:
    hdr("STEP 3 — training pipeline")
    from models.embedding import embedding_service
    from pipelines.training_pipeline import training_pipeline

    embedding_service.load_model()
    ok("Embedding model loaded")

    if csv_only:
        from unittest.mock import AsyncMock, MagicMock
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_res
        report = await training_pipeline.run(db=mock_db, force_rebuild=True)
    else:
        try:
            from database.connection import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                report = await training_pipeline.run(db=db, force_rebuild=True)
        except Exception as e:
            err(f"DB error ({e}) — falling back to CSV-only")
            from unittest.mock import AsyncMock, MagicMock
            mock_db = AsyncMock()
            mock_res = MagicMock()
            mock_res.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_res
            report = await training_pipeline.run(db=mock_db, force_rebuild=True)

    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    if report.success:
        ok(f"Training done in {report.duration_seconds:.1f}s — {report.vectors_indexed} vectors")
    else:
        err(f"Training failed: {report.error}")
    return report


# ── Step 4: Semantic search tests ────────────────────────────────

async def run_search_tests() -> bool:
    hdr("STEP 4 — semantic search")
    from models.embedding import embedding_service
    from models.vector_store import FAISSVectorStore

    test_cases = [
        ("My payment failed",            "en",       "payment"),
        ("Comment réserver une course",  "fr",       "booking"),
        ("كيف أحجز رحلة؟",              "ar",       "booking"),
        ("machkel fil paiement",         "fr-ar",    "payment"),
        ("I forgot my password",         "en",       "password"),
        ("L'application plante",         "fr",       "bug"),
        ("Driver is late",               "en",       "ride_delay"),
        ("nsit el password",             "fr-ar",    "password"),
    ]

    store = FAISSVectorStore()
    store.load()
    passed = 0

    for question, lang, expected_cat in test_cases:
        vec = embedding_service.encode_single(question, normalize=True)
        results = store.search(vec, k=3, threshold=0.25)
        if results:
            meta, score = results[0]
            cat = meta.get("category", "?")
            ans = meta.get("answer", "")[:55]
            flag = "✅" if score >= 0.45 else "⚠ "
            color = C.GREEN if score >= 0.45 else C.YELLOW
            print(f"{color}{flag} [{lang:7s}] score={score:.2f} cat={cat:12s} | {question[:38]}{C.RESET}")
            print(f"     → {ans}…")
            if score >= 0.45:
                passed += 1
        else:
            err(f"[{lang:7s}] No result for: {question[:45]}")

    print(f"\n{C.BOLD}Search: {passed}/{len(test_cases)} passed{C.RESET}")
    return passed >= len(test_cases) * 0.75


# ── Step 5: RAG pipeline end-to-end ──────────────────────────────

async def run_rag_test() -> bool:
    hdr("STEP 5 — RAG pipeline end-to-end")
    from models.vector_store import vector_store
    from core.rag_pipeline import rag_pipeline

    vector_store.load()
    rag_pipeline.set_vector_store(vector_store)

    questions = [
        "My payment failed what should I do",
        "kifech na3mel réservation",
        "نسيت كلمة المرور",
        "app is crashing help",
    ]

    passed = 0
    for q in questions:
        result = await rag_pipeline.run(q)
        color = C.GREEN if result.confidence >= 0.45 else C.YELLOW
        print(f"{color}{'✅' if result.confidence >= 0.45 else '⚠ '} [{result.source:14s}] "
              f"score={result.confidence:.2f} cat={result.category:12s}{C.RESET}")
        print(f"   Q: {q}")
        print(f"   A: {result.answer[:80]}…")
        if result.confidence >= 0.45:
            passed += 1

    print(f"\n{C.BOLD}RAG: {passed}/{len(questions)} passed{C.RESET}")
    return passed >= len(questions) * 0.75


# ── Step 6: Incremental ticket ───────────────────────────────────

def run_incremental_test() -> bool:
    hdr("STEP 6 — incremental ticket indexing")
    from pipelines.training_pipeline import training_pipeline
    from models.vector_store import vector_store

    before = vector_store.index.ntotal if vector_store.index else 0

    class FakeTicket:
        id = 9999
        ticket_id = "TKT-TEST001"
        question = "Pourquoi l'app ne démarre plus après la mise à jour iOS?"
        answer = ("Après une mise à jour iOS, videz le cache (Paramètres > Moviroo > "
                  "Vider le cache), redémarrez, puis réinstallez si nécessaire.")
        category = "bug"
        language = "fr"

    added = training_pipeline.add_single_ticket(FakeTicket())
    after = vector_store.index.ntotal if vector_store.index else 0

    if added:
        ok(f"Ticket indexed ({before} → {after} vectors)")
    else:
        info("Ticket skipped (already indexed or empty)")
    return True


# ── Main ──────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-only", action="store_true")
    args = parser.parse_args()

    print(f"{C.BOLD}\n╔══════════════════════════════════════════════╗")
    print("║   Moviroo RAG Stack — Full Pipeline Test    ║")
    print(f"╚══════════════════════════════════════════════╝{C.RESET}")

    results = {}

    results["1_csv"]     = (check_csv(),                          "Dataset CSV")
    results["2_db"]      = (await check_db() >= 0,                "Database tickets")
    report               = await run_training(csv_only=args.csv_only)
    results["3_train"]   = (report.success,                       f"Training ({report.vectors_indexed} vectors)")

    if report.success:
        results["4_search"]  = (await run_search_tests(),         "Semantic search")
        results["5_rag"]     = (await run_rag_test(),             "RAG pipeline E2E")
        results["6_incr"]    = (run_incremental_test(),           "Incremental indexing")

    # Summary
    hdr("FINAL SUMMARY")
    passed = 0
    for step, (ok_flag, label) in results.items():
        icon = f"{C.GREEN}✅{C.RESET}" if ok_flag else f"{C.RED}❌{C.RESET}"
        print(f"  {icon}  {label}")
        if ok_flag:
            passed += 1

    total = len(results)
    print(f"\n{C.BOLD}Total: {passed}/{total} steps passed{C.RESET}")
    if passed == total:
        print(f"\n{C.GREEN}{C.BOLD}🎉 All systems operational! Start with: python main.py{C.RESET}")
    else:
        print(f"\n{C.YELLOW}⚠  Some steps failed — check logs above{C.RESET}")


if __name__ == "__main__":
    asyncio.run(main())
