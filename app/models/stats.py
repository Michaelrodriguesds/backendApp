from typing import List
from pydantic import BaseModel


# Mapeados exatamente com stats_model.dart do Flutter
class MonthlyStat(BaseModel):
    month: str      # "Jan", "Fev", "Mar", ...
    year: int
    total: float


class CategoryStat(BaseModel):
    category: str
    total: float
    percentage: float


class TopExpense(BaseModel):
    title: str
    amount: float
    source: str     # "note" ou "project"


class StatsSummary(BaseModel):
    total_invested: float
    total_notes_value: float
    grand_total: float
    monthly: List[MonthlyStat]
    by_category: List[CategoryStat]
    top_expenses: List[TopExpense]