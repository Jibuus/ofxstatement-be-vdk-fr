# This file is part of ofxstatement-be-vdk-fr.
#
# ofxstatement-be-vdk-fr is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ofxstatement-be-vdk-fr is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ofxstatement-be-vdk-fr.  If not, see <https://www.gnu.org/licenses/>.


from ofxstatement.plugin import Plugin
from ofxstatement.parser import CsvStatementParser
from ofxstatement.statement import StatementLine, Statement
from datetime import datetime
import csv

class BeVdkFrPlugin(Plugin):
    """Plugin for VDK Bank CSV files."""
    # Plugin pour les fichiers CSV de la banque VDK.

    def get_parser(self, filename):
        # Return the parser for the VDK CSV file.
        # Retourne le parser pour le fichier CSV de la banque VDK.
        return BeVdkFrParser(filename)

class BeVdkFrParser(CsvStatementParser):
    date_format = "%d/%m/%Y"
    # Date format used in the CSV file (DD/MM/YYYY).
    # Format de date utilisé dans le fichier CSV (JJ/MM/AAAA).

    def __init__(self, filename):
        super().__init__(filename)
        self.statement = Statement()
        # Initialize a new statement object to hold the parsed data.
        # Initialise un nouvel objet de relevé pour stocker les données analysées.

    def split_payee(self, row, ind_payee_account, ind_payee_bic, ind_payee_name,
                    ind_payee_address, ind_payee_postal_code, ind_payee_city, ind_payee_country):
        """Concatenate payee details using the provided indices.
        Concaténer les détails du bénéficiaire en utilisant les indices."""
        return " - ".join([
            row[ind_payee_account].strip(),
            row[ind_payee_bic].strip(),
            row[ind_payee_name].strip(),
            row[ind_payee_address].strip(),
            row[ind_payee_postal_code].strip(),
            row[ind_payee_city].strip(),
            row[ind_payee_country].strip(),
        ]).replace(" -  - ", " - ")

    def parse_movement_type(self, type_movement):
        """Map CSV transaction types to OFX transaction types.
        Associe les types de transactions du CSV aux types de transactions OFX."""
        mapping = {
            "Ordre permanent": "REPEATPMT",  # Standing order / Ordre permanent
            "Bancontact": "POS",  # Payment terminal / Terminal de paiement
            "Facturation des frais administratifs": "FEE",  # Administrative fee / Frais administratifs
            "Maestro": "POS",  # Maestro card transaction / Transaction Maestro
            "online@vdk internet banking": "PAYMENT",  # Online payment / Paiement en ligne
            "Dépôt de la prime de fidélité": "INT",  # Loyalty deposit / Dépôt de prime de fidélité
            "Dépôt des intérêts de base": "INT",  # Basic interest deposit / Dépôt des intérêts de base
            "Paiement instantané": "DEBIT",  # Instant payment / Paiement instantané
            "Recouvrement": "PAYMENT",  # Recovery payment / Recouvrement
            "Transfert": "XFER",  # Transfer / Transfert
        }
        return mapping.get(type_movement, "OTHER")  # Default to "OTHER" if not mapped / Défaut "AUTRE"

    def parse(self):
        # Initialize statement currency to EUR / Initialiser la devise du relevé en EUR.
        self.statement.currency = "EUR"

        with open(self.fin, newline='', encoding='Windows-1252') as csvfile:
            # Open the CSV file using Windows-1252 encoding / Ouvrir le fichier CSV avec l'encodage Windows-1252.
            reader = csv.reader(csvfile, delimiter=';', skipinitialspace=True)

            # Read the first row to extract the account number / Lire la première ligne pour extraire le numéro de compte.
            first_row = next(reader, None)

            if first_row and first_row[0].strip() == "Numéro de compte":
                self.statement.account_id = first_row[1].strip().replace(" ", "")
                # Store the account ID without spaces / Stocker le numéro de compte sans espaces.

            # Find the header row by looking for "Date d'exécution" in the first column / Déterminer la ligne des en-têtes en recherchant "Date d'exécution" dans la première colonne.
            for row in reader:
                if row and row[0].strip() == "Date d’exécution":
                    headers = row
                    break

            # Extract the indices for each field / Extraire les indices pour chaque champ.
            ind_date = headers.index('Date d’exécution')
            ind_id = headers.index('Numéro de référence de VDK')
            ind_memo = headers.index('Communication')
            ind_amount = headers.index('Montant')
            ind_type_movement = headers.index('Type de mouvement')

            # Indices for payee details / Indices pour les détails du bénéficiaire.
            ind_payee_account = headers.index('Numéro de compte de la contrepartie')
            ind_payee_bic = headers.index('BIC/SWIFT de la contrepartie')
            ind_payee_name = headers.index('Nom de la contrepartie')
            ind_payee_address = headers.index('Adresse de la contrepartie')
            ind_payee_postal_code = headers.index('Code postal de la contrepartie')
            ind_payee_city = headers.index('Domicile de la contrepartie')
            ind_payee_country = headers.index('Pays de la contrepartie')

            # Parse each row of the CSV file / Analyser chaque ligne du fichier CSV.
            for row in reader:
                line = StatementLine()  # Create a new statement line / Créer une nouvelle ligne de relevé.

                # Parse the date / Analyser la date.
                line.date = datetime.strptime(row[ind_date], self.date_format) if len(row) > ind_date and row[ind_date].strip() else ""

                # Parse the transaction ID / Analyser l'identifiant de la transaction.
                line.id = row[ind_id].strip() if len(row) > ind_id and row[ind_id].strip() else ""

                # Concatenate payee details / Concaténer les détails du bénéficiaire.
                line.payee = self.split_payee(row, ind_payee_account, ind_payee_bic, ind_payee_name,
                                              ind_payee_address, ind_payee_postal_code, ind_payee_city, ind_payee_country)

                # Parse the memo / Analyser la communication.
                line.memo = row[ind_memo].strip() if len(row) > ind_memo and row[ind_memo].strip() else ""

                # Parse the amount and convert to float / Analyser le montant et convertir en float.
                line.amount = float(row[ind_amount].replace(',', '.')) if len(row) > ind_amount and row[ind_amount].strip() else ""

                # Parse the transaction type / Analyser le type de mouvement.
                line.trntype = self.parse_movement_type(row[ind_type_movement].strip()) if len(row) > ind_type_movement and row[ind_type_movement].strip() else ""

                # Add the statement line to the list / Ajouter la ligne de relevé à la liste.
                self.statement.lines.append(line)

        return self.statement  # Return the parsed statement / Retourner le relevé analysé.
