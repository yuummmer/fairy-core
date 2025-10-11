# fairy/core/validators/rna.py
import pandas as pd
from ..services.validator import Meta, WarningItem, register

class RNAValidator:
    name = "rna"
    version = "0.1.0"
    REQUIRED = ["sample_id"]
    OPTIONAL = ["collection_date", "tissue", "read_length"]

    def validate(self, path: str) -> Meta:
        df = pd.read_csv(path)
        warns: List[WarningItem] = []

        # required column checks
        for col in self.REQUIRED:
            if col not in df.columns:
                warns.append(WarningItem(col, "required", "missing column", -1))

        # not-null sample_id
        if "sample_id" in df.columns:
            bad = df["sample_id"].isna()
            for i in df.index[bad]:
                warns.append(WarningItem("sample_id","not_null","null value",int(i)))

        # read_length ≥1
        if "read_length" in df.columns:
            rl = pd.to_numeric(df["read_length"], errors="coerce").fillna(-1)
            for i in df.index[rl < 1]:
                warns.append(WarningItem("read_length",">=1","non-positive or invalid",int(i)))

        fields = [c for c in df.columns if c in set(self.REQUIRED + self.OPTIONAL)]
        return Meta(n_rows=int(df.shape[0]), n_cols=int(df.shape[1]),
                    fields_validated=sorted(fields), warnings=warns[:200])

# register at import time
register("rna", RNAValidator())
