# schemas/sample_table.py
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema

# Adjust column names/types to your CSV headers
schema = DataFrameSchema({
    "sample_id": Column(pa.String, nullable=False),
    "collection_date": Column(pa.DateTime, nullable=True, coerce=True),
    "tissue": Column(pa.String, nullable=True),
    "read_length": Column(pa.Int, pa.Check.ge(1), nullable=True),
})
