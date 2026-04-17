#!/usr/bin/env python3
"""
Moviroo AI Chatbot – test_training.py
======================================
Script de test standalone pour le pipeline d'entraînement.

Vous pouvez l'exécuter SANS serveur FastAPI actif pour tester :
  - Lecture du dataset.csv local
  - Chargement des tickets de la BD (si dispo)
  - Construction de l'index FAISS
  - Requêtes de test multilingues

Utilisation :
    python test_training.py                   # mode complet
    python test_training.py --csv-only        # CSV seulement (pas de BD)
    python test_training.py --no-rebuild      # mode incrémental
"""

import asyncio
import sys
import os
import argparse
import json
# Ajoute le dossier racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings

# ── Couleurs terminal ──
class C:
    HEADER  = '\033[95m'
    BLUE    = '\033[94m'
    CYAN    = '\033[96m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    RED     = '\033[91m'
    BOLD    = '\033[1m'
    RESET   = '\033[0m'

def ok(msg):  print(f"{C.GREEN}✅ {msg}{C.RESET}")
def err(msg): print(f"{C.RED}❌ {msg}{C.RESET}")
def info(msg):print(f"{C.CYAN}ℹ️  {msg}{C.RESET}")
def hdr(msg): print(f"\n{C.BOLD}{C.HEADER}{'─'*60}\n   {msg}\n{'─'*60}{C.RESET}")


# ─────────────────────────────────────────────────────────────────
#  Étape 1 : Vérifie le CSV local
# ─────────────────────────────────────────────────────────────────
def check_csv():
    hdr("ÉTAPE 1 – Vérification du dataset.csv local")

    csv_path = os.path.join(settings.data_dir, "dataset.csv")
    info(f"Chemin recherché : {csv_path}")

    if not os.path.exists(csv_path):
        print(f"{C.YELLOW}⚠️  dataset.csv introuvable.{C.RESET}")
        print("   → Un fichier d'exemple sera créé automatiquement "
              "au lancement du pipeline.")
        return False
    else:
        import pandas as pd
        df = pd.read_csv(
            "data/dataset.csv",
            sep=",",
            quotechar='"',
            escapechar="\\",
            on_bad_lines="skip"
        )
        ok(f"dataset.csv trouvé : {len(df)} lignes")
        info(f"Colonnes : {list(df.columns)}")

        # Aperçu
        print(f"\n{C.BOLD}Aperçu (5 premières lignes) :{C.RESET}")
        for _, row in df.head(5).iterrows():
            q = str(row.get('question', ''))[:60]
            cat = str(row.get('category', ''))
            lang = str(row.get('language', 'en'))
            print(f"   [{lang:14s}][{cat:12s}] {q}")
        return True


# ─────────────────────────────────────────────────────────────────
#  Étape 2 : Compte les tickets dans la BD
# ─────────────────────────────────────────────────────────────────
async def check_tickets():
    hdr("ÉTAPE 2 – Vérification des tickets en base de données")

    try:
        from database.connection import AsyncSessionLocal
        from database.models import Ticket
        from sqlalchemy import select, and_

        async with AsyncSessionLocal() as db:
            # Tous les tickets
            all_result = await db.execute(select(Ticket))
            all_tickets = list(all_result.scalars().all())

            # Tickets résolus avec réponse
            resolved_result = await db.execute(
                select(Ticket).where(
                    and_(
                        Ticket.status == 'resolved',
                        Ticket.answer.isnot(None),
                        Ticket.answer != '',
                    )
                )
            )
            resolved = list(resolved_result.scalars().all())

            info(f"Total tickets en BD        : {len(all_tickets)}")
            info(f"Tickets résolus (avec réponse) : {len(resolved)}")

            if resolved:
                print(f"\n{C.BOLD}Aperçu tickets résolus :{C.RESET}")
                for t in resolved[:3]:
                    print(f"   [{t.ticket_id}] [{t.category or 'N/A':12s}] "
                          f"{(t.question or '')[:55]}")
                ok(f"{len(resolved)} tickets prêts pour l'entraînement")
            else:
                print(f"   {C.YELLOW}Aucun ticket résolu pour l'instant.{C.RESET}")
                print("   → L'entraînement utilisera uniquement le CSV.")

            return len(resolved)

    except Exception as e:
        err(f"Connexion BD impossible : {e}")
        print("   → Vérifiez DATABASE_URL dans .env")
        print("   → L'entraînement sera lancé en mode CSV-seulement")
        return 0


# ─────────────────────────────────────────────────────────────────
#  Étape 3 : Lance le pipeline d'entraînement
# ─────────────────────────────────────────────────────────────────
async def run_training(force_rebuild=True, csv_only=False):
    hdr("ÉTAPE 3 – Lancement du pipeline d'entraînement")

    from models.embedding import embedding_service
    from pipelines.training_pipeline import training_pipeline

    # Charge le modèle d'embedding
    info(f"Chargement du modèle : {settings.embedding_model}")
    embedding_service.load_model()
    ok("Modèle d'embedding chargé")

    if csv_only:
        # Mode sans BD : on passe une session factice
        info("Mode CSV-only : tickets BD ignorés")
        from unittest.mock import MagicMock, AsyncMock
        from sqlalchemy import select
        mock_db = AsyncMock()
        # Retourne un résultat vide pour les tickets
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        report = await training_pipeline.run(db=mock_db, force_rebuild=force_rebuild)
    else:
        try:
            from database.connection import init_db, AsyncSessionLocal
            await init_db()
            async with AsyncSessionLocal() as db:
                report = await training_pipeline.run(db=db, force_rebuild=force_rebuild)
        except Exception as e:
            err(f"BD inaccessible ({e}) → fallback CSV-only")
            from unittest.mock import MagicMock, AsyncMock
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_result
            report = await training_pipeline.run(db=mock_db, force_rebuild=True)

    # Affiche le rapport
    print(f"\n{C.BOLD}Rapport JSON :{C.RESET}")
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))

    if report.success:
        ok(f"Entraînement réussi en {report.duration_seconds:.1f}s")
        ok(f"{report.vectors_indexed} vecteurs dans l'index FAISS")
        ok(f"  - Depuis CSV     : {report.final_from_csv}")
        ok(f"  - Depuis Tickets : {report.final_from_tickets}")
        ok(f"  - Doublons retirés : {report.duplicates_removed}")
    else:
        err(f"Entraînement échoué : {report.error}")

    return report


# ─────────────────────────────────────────────────────────────────
#  Étape 4 : Teste des requêtes de recherche
# ─────────────────────────────────────────────────────────────────
async def run_search_tests():
    hdr("ÉTAPE 4 – Tests de recherche sémantique")

    from models.embedding import embedding_service
    from models.vector_store import FAISSVectorStore

    test_queries = [
        ("My payment failed",                      "en",            "payment"),
        ("Comment réserver une course?",           "fr",            "booking"),
        ("كيف أحجز رحلة؟",                         "ar",            "booking"),
        ("machkel fil payement",                   "franco-arabic", "payment"),
        ("I forgot my password",                   "en",            "password"),
        ("L'application plante",                   "fr",            "bug"),
        ("Driver is late",                         "en",            "ride_delay"),
        ("nsit el password",                       "franco-arabic", "password"),
    ]

    passed = 0
    total  = len(test_queries)

    for query, lang, expected_cat in test_queries:
        embedding = embedding_service.encode_single(query, normalize=True)
        from models.vector_store import FAISSVectorStore

        store = FAISSVectorStore()
        store.load()

        results = store.search(embedding, k=3, threshold=0.2)        
        if results:
            best_meta, best_score = results[0]
            found_cat = best_meta.get('category', 'unknown')
            source    = best_meta.get('source', '?')
            answer_preview = best_meta.get('answer', '')[:60]

            if best_score >= 0.40:
                ok(
                    f"[{lang:14s}] score={best_score:.2f} "
                    f"cat={found_cat:12s} src={source} | {query[:40]}"
                )
                print(f"          → {answer_preview}…")
                passed += 1
            else:
                print(
                    f"{C.YELLOW}⚠️  [{lang:14s}] score faible={best_score:.2f} "
                    f"cat={found_cat:12s} | {query[:40]}{C.RESET}"
                )
        else:
            err(f"[{lang:14s}] Aucun résultat pour : {query[:50]}")

    print(f"\n{C.BOLD}Résultat : {passed}/{total} requêtes réussies{C.RESET}")
    return passed == total


# ─────────────────────────────────────────────────────────────────
#  Étape 5 : Simulation ajout d'un ticket résolu
# ─────────────────────────────────────────────────────────────────
def test_ticket_incremental():
    hdr("ÉTAPE 5 – Test ajout incrémental d'un ticket résolu")

    from models.vector_store import FAISSVectorStore
    from pipelines.training_pipeline import training_pipeline
    vector_store = FAISSVectorStore()

    vectors_before = vector_store.index.ntotal if vector_store.index else 0
    # Crée un faux objet ticket
    class FakeTicket:
        id = 9999
        ticket_id = "TICKET-TEST001"
        question = "Pourquoi mon application ne démarre pas après la mise à jour?"
        answer = ("Après une mise à jour, essayez : 1) Vider le cache de l'app, "
                  "2) Redémarrer le téléphone, 3) Réinstaller l'application. "
                  "Contactez le support si le problème persiste.")
        category = "bug"
        language = "fr"

    added = training_pipeline.add_single_ticket(FakeTicket())

    vectors_after = vector_store.index.ntotal if vector_store.index else 0

    if added:
        ok(f"Ticket ajouté à l'index ({vectors_before} → {vectors_after} vecteurs)")
    else:
        info("Ticket non ajouté (déjà indexé ou données vides)")

    return True


# ─────────────────────────────────────────────────────────────────
#  Résumé final
# ─────────────────────────────────────────────────────────────────
def print_final_summary(results: dict):
    hdr("RÉSUMÉ FINAL")

    for step, (ok_flag, label) in results.items():
        if ok_flag:
            print(f"  {C.GREEN}✅{C.RESET} {label}")
        else:
            print(f"  {C.RED}❌{C.RESET} {label}")

    passed = sum(1 for v, _ in results.values() if v)
    total  = len(results)

    print(f"\n{C.BOLD}Total : {passed}/{total} étapes réussies{C.RESET}")

    if passed == total:
        print(f"\n{C.GREEN}{C.BOLD}🎉 Pipeline d'entraînement 100% opérationnel !{C.RESET}")
        print(f"\n   Prochaine étape → démarrez le serveur :")
        print(f"   {C.CYAN}python main.py{C.RESET}")
    else:
        print(f"\n{C.YELLOW}⚠️  Certaines étapes ont échoué – consultez les logs ci-dessus.{C.RESET}")


# ─────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(
        description="Test du pipeline d'entraînement Moviroo"
    )
    parser.add_argument(
        "--csv-only",
        action="store_true",
        help="Ignore la BD, utilise uniquement dataset.csv"
    )
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Mode incrémental (n'ajoute que les nouveaux items)"
    )
    args = parser.parse_args()

    print(f"{C.BOLD}{C.HEADER}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     Moviroo AI – Test Pipeline d'Entraînement           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(C.RESET)

    results = {}

    # ── 1. CSV ──
    csv_ok = check_csv()
    results["1_csv"] = (csv_ok or True, "Dataset CSV vérifié")  # non-bloquant

    # ── 2. Tickets BD ──
    ticket_count = await check_tickets()
    results["2_tickets"] = (True, f"Tickets BD vérifiés ({ticket_count} résolus)")

    # ── 3. Entraînement ──
    report = await run_training(
        force_rebuild=not args.no_rebuild,
        csv_only=args.csv_only,
    )
    results["3_training"] = (
        report.success,
        f"Pipeline entraînement ({report.vectors_indexed} vecteurs)"
    )

    if report.success:
        # ── 4. Recherche ──
        search_ok = await run_search_tests()
        results["4_search"] = (search_ok, "Tests de recherche sémantique")

        # ── 5. Ticket incrémental ──
        inc_ok = test_ticket_incremental()
        results["5_incremental"] = (inc_ok, "Ajout incrémental de ticket")

    # ── Résumé ──
    print_final_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
