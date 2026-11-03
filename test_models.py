from app.db.base import Base

print("Registered Tables:")

for table_name, table in Base.metadata.tables.items():
    print(f"\nTable: {table_name}")

    for column in table.columns:
        print(
            f"  {column.name}: "
            f"{column.type}, "
            f"nullable={column.nullable}"
        )

print("\nForeign Keys:")

for table in Base.metadata.tables.values():
    for column in table.columns:
        for fk in column.foreign_keys:
            print(f"{table.name}.{column.name} -> {fk.target_fullname}")