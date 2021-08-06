import csv


def import_educational_institution_and_deposit_from_csv(csv_file_path:str)-> None:
    with open(csv_file_path, newline='') as csv_file:
        csv_reader = csv.dictReader(csv_file)

    for row in csv_reader:
        institution_id = row[0]
        deposit_amount = row[1]
        import_educational_institution_and_deposit(institution_id, deposit_amount)

def import_educational_institution_and_deposit(institution_id:str, )