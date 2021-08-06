from flask import current_app as app

from pcapi.scripts.educational.import_educational_institution_and_deposit_from_csv import (
    import_educational_institution_and_deposit_from_csv,
)


@app.manager.option(
    "-p",
    "--csv_path",
    dest="csv_path",
    required=True,
    help="Path of the CSV file containing needed informations",
    type=int,
)
def import_educational_institution_and_deposit(csv_path: str) -> None:
    import_educational_institution_and_deposit_from_csv(csv_path)
