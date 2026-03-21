import re
from collections import defaultdict
from datetime import datetime
from typing import List, Dict

from fastapi import APIRouter, Depends
from app.database import get_projects_collection, get_notes_collection
from app.models.stats import StatsSummary, MonthlyStat, CategoryStat, TopExpense
from app.models.user import UserDB
from app.utils.security import get_current_user

router = APIRouter(prefix="/stats", tags=["Statistics"])

# Regex para valores monetários nas anotações: R$ 43,50 ou R$43.50
_MONEY_RE = re.compile(r"R\$\s*([\d\.]+(?:,\d{2})?)")

_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Lubrificantes": ["óleo", "oleo", "lubrificante"],
    "Manutenção":    ["manutenção", "manutencao", "alternador", "revisão", "revisao", "bomba"],
    "Peças":         ["peça", "peca", "bateria", "vela", "filtro", "kit"],
    "Combustível":   ["combustivel", "combustível", "gasolina", "etanol"],
}

_PT_MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
              "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _parse_brl(raw: str) -> float:
    try:
        return float(raw.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def _detect_category(text: str) -> str:
    lower = text.lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(k in lower for k in keywords):
            return cat
    return "Outros"


# ── GET /stats/summary ────────────────────────────────────────────────── NOVO
# Chamado por StatsService.buscar() no Flutter (EstatisticasScreen)
# Agrega dados de projetos e anotações para montar o dashboard de estatísticas
@router.get("/summary", response_model=StatsSummary)
async def get_summary(current_user: UserDB = Depends(get_current_user)):
    projects_col = await get_projects_collection()
    notes_col    = await get_notes_collection()

    # ── Projetos ──────────────────────────────────────────────────────────────
    total_invested = 0.0
    project_items  = []

    async for p in projects_col.find({"user_id": current_user.id}):
        applied = p.get("applied_value", 0.0)
        total_invested += applied
        if applied > 0:
            project_items.append({
                "title":    p.get("title", ""),
                "amount":   applied,
                "category": p.get("category", "Outros"),
                "date":     p.get("start_date"),
                "source":   "project",
            })

    # ── Anotações — extrai valores monetários via regex ───────────────────────
    note_items        = []
    total_notes_value = 0.0

    async for n in notes_col.find({"user_id": current_user.id}):
        text    = (n.get("content") or "") + " " + (n.get("title") or "")
        matches = _MONEY_RE.findall(text)
        if not matches:
            continue
        amounts = [_parse_brl(m) for m in matches]
        total   = max(amounts)
        if total <= 0:
            continue
        total_notes_value += total
        note_items.append({
            "title":    n.get("title", "Sem título"),
            "amount":   total,
            "category": _detect_category(text),
            "date":     n.get("date") or n.get("created_at"),
            "source":   "note",
        })

    all_items = project_items + note_items

    # ── Agrupamento mensal ────────────────────────────────────────────────────
    monthly_buckets: Dict[tuple, float] = defaultdict(float)
    for item in all_items:
        raw = item.get("date")
        if not raw:
            continue
        try:
            dt = raw if isinstance(raw, datetime) else \
                 datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            monthly_buckets[(dt.year, dt.month)] += item["amount"]
        except Exception:
            continue

    monthly = [
        MonthlyStat(month=_PT_MONTHS[m - 1], year=y, total=round(total, 2))
        for (y, m), total in sorted(monthly_buckets.items())
    ]

    # ── Agrupamento por categoria ─────────────────────────────────────────────
    cat_buckets: Dict[str, float] = defaultdict(float)
    for item in all_items:
        cat_buckets[item["category"]] += item["amount"]

    grand = sum(cat_buckets.values()) or 1
    by_category = sorted(
        [
            CategoryStat(
                category=cat,
                total=round(total, 2),
                percentage=round((total / grand) * 100, 1),
            )
            for cat, total in cat_buckets.items()
        ],
        key=lambda x: x.total,
        reverse=True,
    )

    # ── Top 5 maiores gastos ──────────────────────────────────────────────────
    top = sorted(all_items, key=lambda x: x["amount"], reverse=True)[:5]
    top_expenses = [
        TopExpense(title=t["title"], amount=t["amount"], source=t["source"])
        for t in top
    ]

    return StatsSummary(
        total_invested=    round(total_invested, 2),
        total_notes_value= round(total_notes_value, 2),
        grand_total=       round(total_invested + total_notes_value, 2),
        monthly=           monthly,
        by_category=       by_category,
        top_expenses=      top_expenses,
    )