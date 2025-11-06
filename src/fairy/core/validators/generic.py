# fairy/core/validators/generic.py

import pandas as pd
from ..validation_api import Meta, register

class GenericCSVValidator:
    name = "generic"
    version = "0.1.0"

    def validate(self, path: str) -> Meta:
        df = pd.read_csv(path)

        # No domain rules; just summarize the shape and the first ~50 columns
        fields = list(df.columns)[:50]

        return Meta(
            n_rows=int(df.shape[0]),
            n_cols=int(df.shape[1]),
            fields_validated=fields,
            warnings=[],
        )

register("generic", GenericCSVValidator())
