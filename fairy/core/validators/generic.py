# fairy/core/validators/generic.py
import pandas as pd
from ..services.validator import Meta, WarningItem, register

class GenericCSVValidator:
    name = "generic"
    version = "0.1.0"
    def validate(self, path: str) -> Meta:
        df = pd.read_csv(path)
        # no domain rules; just counts + discovered fields
        fields = list(df.columns)[:50]  # cap
        return Meta(n_rows=int(df.shape[0]), n_cols=int(df.shape[1]),
                    fields_validated=fields, warnings=[])

register("generic", GenericCSVValidator())
