"""Ligne de commande : python -m app.cli {seed|ingest|ask|eval|stats|export}."""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from pathlib import Path

from .bootstrap import AppState, build_state, startup
from .config import get_settings
from .directory import load_seed_file
from .schemas import AskRequest, Hit, SearchMode


def _state(ready: bool = True) -> AppState:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper(), format="%(levelname)s %(name)s: %(message)s")
    state = build_state(settings)
    if ready:
        startup(state)
    return state


def cmd_seed(args: argparse.Namespace) -> int:
    state = _state(ready=False)
    path = Path(args.file) if args.file else state.settings.seed_file
    seed = load_seed_file(path)
    state.repo.upsert_domains(seed.domains)
    result = state.repo.import_many(seed.organizations, replace=args.replace)
    report = state.indexer.rebuild()
    print(f"{path} : {result.created} créées, {result.updated} mises à jour, {result.deleted} supprimées "
          f"-> {state.repo.count(active_only=False)} organisations, index {report.passages} passages")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    state = _state(ready=False)
    report = state.indexer.rebuild()
    print(f"{report.documents} fiches + {report.organizations} organisations -> {report.passages} passages "
          f"en {report.seconds}s")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    state = _state()
    resp = state.assistant.ask(AskRequest(question=args.question, mode=SearchMode(args.mode) if args.mode else None,
                                          debug=True))
    if args.json:
        print(json.dumps(resp.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0
    print(f"Question : {resp.question}   [mode={resp.mode.value}, intent={resp.intent.value}, "
          f"catégorie={resp.category or '—'}, {resp.latency_ms} ms]")
    print("-" * 72)
    print(resp.answer)
    if resp.suggestions:
        print("\nRelances : " + " | ".join(resp.suggestions))
    if resp.hits:
        print("\nPassages candidats :")
        for h in resp.hits[:8]:
            print(f"  {h.rank}. [{h.score:.3f}] {h.source.kind:<12} {h.source.title} › {h.source.section or '—'}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    state = _state()
    docs = state.engine.list_documents()
    print(f"Modèle  : {state.settings.embedding_model} (dim={state.engine.embedder.dimension})")
    print(f"Index   : {len(docs)} entrées, {state.engine.count_passages()} passages, "
          f"seuil min_score={state.settings.min_score}")
    print(f"Annuaire: {state.repo.count()} organisations actives, {len(state.repo.list_domains())} domaines, "
          f"base {state.settings.db_file}")
    for d in docs:
        print(f"  - {d['kind']:<12} {d['doc_id']:<36} {d['passages']:>3} passages   {d['title']}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    state = _state(ready=False)
    items = [o.model_dump(mode="json") for o in state.repo.list(active=None, limit=100_000)[1]]
    text = json.dumps({"organizations": items}, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"{len(items)} organisations exportées vers {args.out}")
    else:
        print(text)
    return 0


# ------------------------------------------------------------------ eval
def _load_questions(path: Path) -> list[dict]:
    """Une question JSON par ligne ; `expected` = doc_id ou titre attendu (ou liste), null = hors périmètre."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            row = json.loads(line)
            exp = row.get("expected")
            row["expected"] = [exp] if isinstance(exp, str) else list(exp or [])
            rows.append(row)
    return rows


def _top_semantic(hits: list[Hit]) -> float | None:
    """Score sémantique du 1er passage (sert à calibrer CHATBOT_MIN_SCORE) ; None si non calculé."""
    return hits[0].semantic_score if hits else None


def cmd_eval(args: argparse.Namespace) -> int:
    """Rejoue les 3 approches du benchmark sur un jeu de questions annotées, en mesurant la RÉPONSE PRODUITE
    (acteurs proposés puis extrait documentaire), comme la verrait l'usager.

    hit@1 : le 1er élément proposé est attendu ; trouvé : un élément attendu figure dans la réponse ;
    MRR : rang du 1er élément attendu ; faux rejets : question du périmètre restée sans réponse ;
    rejet hors-sujet : questions hors périmètre (expected=null) correctement refusées ;
    score ok / HS : score sémantique moyen du 1er passage (périmètre / hors-sujet).
    """
    state = _state()
    config = state.config_store.get()
    questions = _load_questions(Path(args.file))
    in_scope = [q for q in questions if q.get("expected")]
    off_topic = [q for q in questions if not q.get("expected")]
    modes = [SearchMode(m) for m in args.modes.split(",")]

    print(f"{len(in_scope)} questions dans le périmètre, {len(off_topic)} hors périmètre — "
          f"seuil min_score={state.settings.min_score}, max {config.max_organizations} acteurs + 1 extrait\n")
    header = (f"{'mode':<10}{'hit@1':>8}{'trouvé':>8}{'MRR':>8}{'faux rejets':>13}"
              f"{'rejet hors-sujet':>18}{'score ok':>10}{'score HS':>10}")
    print(header)
    print("-" * len(header))
    failures: dict[str, list[str]] = {}
    off_topic_detail: dict[str, list[str]] = {}
    for mode in modes:
        hit1 = found = false_reject = rejected = 0
        rr_sum = 0.0
        ok_scores: list[float] = []
        hs_scores: list[float] = []
        failures[mode.value] = []
        for q in in_scope:
            resp, hits = state.assistant.answer(q["question"], mode, config)
            proposed = [o.name for o in resp.organizations] + [d.source for d in resp.documents]
            expected = set(q["expected"])
            ranks = [i for i, name in enumerate(proposed) if name in expected]
            if ranks and ranks[0] == 0:
                hit1 += 1
            else:
                failures[mode.value].append(
                    f"{q['question']!r} -> {proposed or ['∅']} (attendu {' | '.join(q['expected'])})")
            if ranks:
                found += 1
                rr_sum += 1.0 / (ranks[0] + 1)
            if not resp.answered:
                false_reject += 1
            s = _top_semantic(hits)
            if s is not None:
                ok_scores.append(s)
        for q in off_topic:
            resp, hits = state.assistant.answer(q["question"], mode, config)
            if not resp.answered:
                rejected += 1
            s = _top_semantic(hits)
            if s is not None:
                hs_scores.append(s)
            if args.verbose:
                proposed = [o.name for o in resp.organizations] + [d.source for d in resp.documents]
                off_topic_detail.setdefault(mode.value, []).append(
                    f"[{s if s is not None else 0:.3f}] {'rejeté ' if not resp.answered else 'RÉPONDU'} "
                    f"{q['question']!r}{'' if not resp.answered else ' -> ' + str(proposed)}")
        n, m = max(len(in_scope), 1), max(len(off_topic), 1)
        print(f"{mode.value:<10}{hit1 / n:>8.0%}{found / n:>8.0%}{rr_sum / n:>8.3f}"
              f"{false_reject / n:>13.0%}{rejected / m:>18.0%}"
              f"{(statistics.mean(ok_scores) if ok_scores else 0):>10.3f}"
              f"{(statistics.mean(hs_scores) if hs_scores else 0):>10.3f}")
        if args.verbose and ok_scores and hs_scores:
            print(f"{'':<10}  scores sémantiques 1er passage — périmètre : min {min(ok_scores):.3f} / "
                  f"hors-sujet : max {max(hs_scores):.3f}")
    if args.verbose:
        for mode, items in failures.items():
            if items:
                print(f"\nÉchecs hit@1 en mode {mode} :")
                for it in items:
                    print("  -", it)
        for mode, items in off_topic_detail.items():
            print(f"\nHors périmètre en mode {mode} (score sémantique du 1er passage) :")
            for it in items:
                print("  -", it)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Chatbot territorial — outils")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("seed", help="Importe un annuaire JSON (upsert par nom) puis reconstruit l'index")
    p.add_argument("--file", help="Fichier JSON (défaut : CHATBOT_SEED_FILE)")
    p.add_argument("--replace", action="store_true", help="Supprimer les organisations absentes du fichier")
    p.set_defaults(func=cmd_seed)

    p = sub.add_parser("ingest", help="Reconstruit l'index depuis le corpus et l'annuaire")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("ask", help="Pose une question")
    p.add_argument("question")
    p.add_argument("--mode", choices=[m.value for m in SearchMode], default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("eval", help="Compare mots-clés / sémantique / hybride sur un jeu de questions")
    p.add_argument("--file", default="eval/questions.jsonl")
    p.add_argument("--modes", default="keyword,semantic,hybrid")
    p.add_argument("-v", "--verbose", action="store_true", help="Liste les questions ratées")
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("stats", help="État de l'index et de l'annuaire")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("export", help="Exporte l'annuaire en JSON (réimportable avec seed --file)")
    p.add_argument("--out", help="Fichier de sortie (défaut : sortie standard)")
    p.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
