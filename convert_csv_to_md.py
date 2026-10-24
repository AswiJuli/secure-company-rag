import csv
from pathlib import Path


csv_path = Path("data/hr/hr_data.csv")
md_path = Path("data/hr/hr_data.md")

with csv_path.open(
    mode="r",
    encoding="utf-8-sig",
    newline=""
) as csv_file:

    reader = csv.DictReader(csv_file)
    markdown_parts = []

    for row_number, row in enumerate(reader, start=1):
        markdown_parts.append(f"## Employee Record {row_number}")

        for column, value in row.items():
            markdown_parts.append(f"- **{column}:** {value}")

        markdown_parts.append("")


md_path.write_text(
    "\n".join(markdown_parts),
    encoding="utf-8"
)

print(f"Created: {md_path}")