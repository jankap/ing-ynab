"""ing_ynab is a simple tool to add data from German banks to YNAB via FinTS.
"""
from datetime import datetime
from time import sleep
from decimal import Decimal
from hashlib import sha256
import logging
import os
import sys
from getpass import getpass
from dotenv import load_dotenv
from fints.client import FinTS3PinTanClient
import requests

YNAB_BASE_URL = "https://api.youneedabudget.com/v1"


def hash_transaction(transaction):
    """Generate a hash for the transaction to make them identifiable.
    """
    data = transaction.data
    payload = "%s:%s:%s:%s" % (
        data["date"],
        data["applicant_name"],
        data["purpose"],
        data["amount"],
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def transform_transactions(transactions, account_id=None):
    """Transform the FinTS transactions into something the YNAB API understands.
    """
    transformed = []
    for transaction in transactions:
        data = transaction.data
        amount_decimal = data["amount"].amount * Decimal("1000.0")
        transformed.append(
            {
                "account_id": account_id,
                "date": data["date"].isoformat(),
                "amount": int(amount_decimal),
                "payee_name": data["applicant_name"],
                "cleared": "cleared",
                "memo": data["purpose"],
            },
        )
    return transformed


def import_transactions(transactions, access_token=None, budget_id=None):
    """Import the transaction into YNAB, returns an array with transaction ids.

    :param transactions: An array of transactions.
    """
    headers = {"Authorization": "Bearer " + access_token}
    payload = {
        "transactions": transactions,
    }
    path = "/budgets/" + budget_id + "/transactions"
    response = requests.post(YNAB_BASE_URL + path, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["data"]["transaction_ids"]


def ing_to_ynab(fints_client, fints_account, debug=False):
    """This code is called in a predefined interval to add new ing transactions into ynab.
    """
    # Try to read from state
    start_date = None
    last_hash = None
    try:
        with open("state", "r") as state_file:
            contents = state_file.read().splitlines()
            start_date = datetime.fromisoformat(contents[0])
            last_hash = contents[1]
    except:  # pylint: disable=bare-except
        start_date_env = os.environ.get("START_DATE")
        if start_date_env is not None:
            start_date = datetime.fromisoformat(start_date_env)
        else:
            start_date = datetime.now()

    transactions = fints_client.get_transactions(fints_account, start_date=start_date)

    # Figure out where to start by finding the last transaction.
    array_start = 0
    for i, transaction in enumerate(transactions):
        if hash_transaction(transaction) == last_hash:
            array_start = i + 1
    transactions = transactions[array_start:]

    if len(transactions) == 0:
        print("No new transactions found")
        return

    # Transform FinTS transactions to YNAB transactions.
    ynab_transactions = transform_transactions(
        transactions, account_id=os.environ["YNAB_ACCOUNT_ID"]
    )

    # Print or import the transformed transactions.
    if debug:
        for transaction in ynab_transactions:
            print(transaction)
    else:
        imported = import_transactions(
            ynab_transactions,
            access_token=os.environ.get(
                "YNAB_ACCESS_TOKEN", getpass("YNAB Access Token: ")
            ),
            budget_id=os.environ["YNAB_BUDGET_ID"],
        )
        print("Imported %d new transaction(s)" % len(imported))

    with open("state", "w") as state_file:
        state_file.write(
            "%s\n%s"
            % (datetime.now().strftime("%Y-%m-%d"), hash_transaction(transactions[0]))
        )


def main():
    """This is the main function
    """
    load_dotenv()

    debug = os.environ.get("DEBUG") == "1"
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # Initialize FinTS.
    fints_client = FinTS3PinTanClient(
        "50010517",  # BLZ
        os.environ["FINTS_LOGIN"],
        os.environ.get("FINTS_PIN", getpass("FinTS Pin: ")),
        "https://fints.ing-diba.de/fints/",  # Endpoint
        product_id=os.environ.get("FINTS_PRODUCT_ID", None),
    )
    if fints_client.init_tan_response:
        print("TAN required:", fints_client.init_tan_response.challenge)
        tan = input("Please enter TAN:")
        fints_client.send_tan(fints_client.init_tan_response, tan)

    # Get sepa accounts.
    accounts = fints_client.get_sepa_accounts()

    # Find selected one.
    selected_account = None
    for account in accounts:
        if account.iban == os.environ["FINTS_IBAN"]:
            selected_account = account
            break
    if selected_account is None:
        print("Could not find account, is the IBAN correct?")
        print("Available accounts: %s" % accounts)
        sys.exit(1)

    interval = int(os.environ.get("SLEEP_INTERVAL", "300"))

    while True:
        ing_to_ynab(fints_client, selected_account, debug=debug)

        print("Sleeping for %d seconds" % interval)
        sleep(interval)


if __name__ == "__main__":
    main()
