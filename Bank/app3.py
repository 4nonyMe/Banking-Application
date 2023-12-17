from flask import Flask, render_template, request, redirect, flash, session, url_for
from flask_session import Session
from classes import Account
from datetime import timedelta
import socket
import re
import csv
from datetime import datetime
import os

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))

app = Flask (__name__)
app.secret_key = "key"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)

@app.route('/save_use_money', methods=['GET', 'POST'])
def save_use_money_page():
    if request.method == "GET":
        print(session)
        return render_template("save_use_money.html", data=session)
    elif request.method == "POST":
        account_number=session["accountNumber"]
        amount = float(request.form.get("amount", 0))  
        move_type=request.form.get("move_type")

        if not amount:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('save_use_money_page'))

        success = save_use_money(account_number, amount, move_type)
        if success:
            flash('Balance updated successfully!', 'success')
        else:
            flash(f'Failed to update balance. Invalid account number.{account_number}', 'danger')

        return redirect(url_for('save_use_money_page'))


def save_use_money(account_number, amount, move_type):
    with open("customers.txt", "r") as file:
        lines = file.readlines()
        found = False
        for index, line in enumerate(lines):
            data = line.strip().split()
            if len(data) >= 7 and data[2] == account_number:
                found = True
                if move_type == "save":
                    if float(data[4]) >= amount:
                        new_saving_balance = float(data[5]) + amount
                        new_current_balance = float(data[4]) - amount
                        data[4] = str(new_current_balance)
                        data[5] = str(new_saving_balance)
                        recipient_account="Savings"
                        sending_account="Current"
                    else: 
                        return False  #pas assez d'argent à épargner
                elif move_type == "import":
                    if float(data[5]) >= amount:
                        new_saving_balance = float(data[5]) - amount
                        new_current_balance = float(data[4]) + amount
                        data[5] = str(new_saving_balance)
                        data[4] = str(new_current_balance)
                        recipient_account="Current"
                        sending_account="Savings"
                    else:
                        return False

                updated_line = ' '.join(data) + '\n'
                lines[index] = updated_line
                
                session["currentbalance"]=data[4]
                session["savingbalance"]=data[5]
                
                save_transaction(account_number, recipient_account, sending_account , amount, datetime.now().replace(microsecond=0))

        if not found:
            return False

        with open("customers.txt", "w") as file:
            file.writelines(lines)

        return True
    return False

@app.route('/dashboard_choice', methods=['GET'])
def dashboard_choice():
    if 'accountNumber' in session:
        return render_template('dashboard_choice.html', data=session)
    else:
        flash('You are not logged in. Please log in first.', 'warning')
        return redirect(url_for('login_page'))

    
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        return render_template("index.html")
    else:
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        accountNumber = request.form["accountNumber"]
        pin = request.form["pin"]
        
        # Vérification si les champs ne sont pas vides et si le pin et le numéro de compte sont des entiers positifs
        if firstname and lastname and accountNumber.isdigit() and pin:
            with open("customers.txt", "r") as file:
                lines = file.readlines()
                for line in lines:
                    if line.split()[0] == firstname and line.split()[1] == lastname and int(line.split()[2]) == int(accountNumber) and line.split()[3] == pin:
                        account = {
                            "firstname": line.split()[0],
                            "lastname": line.split()[1],
                            "accountNumber": line.split()[2],
                            "pin": line.split()[3],
                            "currentbalance": line.split()[4],
                            "savingbalance": line.split()[5], 
                            "email": line.split()[6]
                        }
                        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        login_data = [accountNumber,current_datetime]
                        try:
                            with open('login_details_customer.csv', mode='a', newline='') as file_csv:
                                writer = csv.writer(file_csv)
                                writer.writerow(login_data)
                        except Exception as e:
                            print(f"Erreur lors de l'écriture dans le fichier CSV : {str(e)}")
                        session["firstname"] = account["firstname"]
                        session["lastname"] = account["lastname"]
                        session["accountNumber"] = account["accountNumber"]
                        session["pin"] = account["pin"]
                        session["currentbalance"] = str(round(float(account["currentbalance"]), 2))
                        session["savingbalance"] = str(round(float(account["savingbalance"]), 2))
                        session["email"] = account["email"]

                        print("setting " + str(session["accountNumber"]))
                        return render_template("dashboard_choice.html", data=session)
                flash("Account not found, please try again!", "warning")
                return render_template("index.html") 
        else:
            flash("Please enter valid data!", "warning")
            return render_template("index_employee.html") 

def read_customer_data():
    customer_data = []
    with open("customers.txt", "r") as file:
        lines = file.readlines()
        for line in lines:
            data = line.strip().split()
            if len(data) >= 7:
                firstname, lastname, accountNumber, pin, currentbalance, savingbalance, email = data[:7]
                customer_data.append({
                    "firstname": firstname,
                    "lastname": lastname,
                    "accountNumber": accountNumber,
                    "pin": pin,
                    "currentbalance": float(currentbalance),
                    "savingbalance": float(savingbalance),
                    "email": email
                })
    return customer_data

@app.route('/customer_data')
def show_customer_data():
    customers = read_customer_data()
    return render_template("customer_table_template.html", customers=customers)

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None


def update_balance(account_number, pin, amount, operation, account_type):
    with open("customers.txt", "r") as file:
        lines = file.readlines()
        found = False
        for index, line in enumerate(lines):
            data = line.strip().split()
            if len(data) >= 7 and data[2] == account_number and data[3] == pin:
                found = True
                if operation == "add":
                    if account_type == "current":
                        new_balance = float(data[4]) + amount
                        if new_balance < 0:
                            return False  # Retourne False si le solde devient négatif
                        data[4] = str(new_balance)
                    elif account_type == "saving":
                        new_balance = float(data[5]) + amount
                        if new_balance < 0:
                            return False  # Retourne False si le solde devient négatif
                        data[5] = str(new_balance)
                elif operation == "subtract":
                    if account_type == "current":
                        new_balance = float(data[4]) - amount
                        if new_balance < 0:
                            return False  # Retourne False si le solde devient négatif
                        data[4] = str(new_balance)
                    elif account_type == "saving":
                        new_balance = float(data[5]) - amount
                        if new_balance < 0:
                            return False  # Retourne False si le solde devient négatif
                        data[5] = str(new_balance)

                updated_line = ' '.join(data) + '\n'
                lines[index] = updated_line

        if not found:
            return False

        with open("customers.txt", "w") as file:
            file.writelines(lines)

        return True
    return False

@app.route('/update_balance', methods=['GET', 'POST'])
def update_balance_page():
    if request.method == "GET":
        return render_template("update_balance_form.html")
    elif request.method == "POST":
        account_number = request.form.get("account_number")
        pin = request.form.get("pin")
        amount = float(request.form.get("amount", 0))  # Gérer le cas où le montant n'est pas fourni
        operation = request.form.get("operation")
        account_type = request.form.get("account_type")

        if account_type == 'current' :
            recipient_account = 'Current'
            sending_account = 'Bank'
        else :
            recipient_account= 'Savings'
            sending_account = 'Bank'

        
            

        if not account_number or not pin or not operation or not account_type:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('update_balance_page'))

        success = update_balance(account_number, pin, amount, operation, account_type)

        if operation != 'add' :
            amount=(-1)*amount

        save_transaction(account_number,   recipient_account, sending_account , amount, datetime.now().replace(microsecond=0))


        if success:
            flash('Balance updated successfully!', 'success')
        else:
            flash('Failed to update balance. Invalid account number or pin or negative balance.', 'danger')

        return redirect(url_for('update_balance_page')) 

@app.route('/employee_view', methods=['GET'])
def employee_view():
    if 'pin' in session:
        return render_template('employee_view.html', data=session)
    else:
        flash('You are not logged in. Please log in first.', 'warning')
        return redirect(url_for('login_employee'))

@app.route('/login_employee', methods=['GET', 'POST'])
def login_employee():
    if request.method == "GET":
        return render_template("index_employee.html")
    else:
        entered_pin = request.form["pin"]
        if entered_pin == 'A1234':
            session.clear()
            session['logged_in'] = True
            flash('Successfully logged in!', 'success')
            log_login_employee_details()
            session.clear()
            session["pin"]=entered_pin
            return render_template("employee_view.html", data=session)


        else:
            flash('Incorrect PIN. Access denied.', 'danger')
            return render_template("index_employee.html")

def log_login_employee_details():
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    login_data = [current_datetime]

    # Vérifier si le fichier CSV existe, sinon le créer avec l'en-tête
    try:
        with open('login_details_employee.csv', 'r') as file:
            reader = csv.reader(file)
            # Vérifier si le fichier a des données (au moins une ligne)
            header = next(reader, None)
            if header is None:
                # Si le fichier est vide, écrire l'en-tête
                with open('login_details_employee.csv', 'a', newline='') as file:
                    writer = csv.writer(file)
                    # Ajouter des colonnes supplémentaires au besoin
                    writer.writerow(['Date and Time'])
    except FileNotFoundError:
        # Si le fichier n'existe pas, le créer avec l'en-tête
        with open('login_details_employee.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            # Ajouter des colonnes supplémentaires au besoin
            writer.writerow(['Date and Time'])

    # Écrire les données dans le fichier CSV
    with open('login_details_employee.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(login_data)

@app.route('/create_customer/', methods=['GET', 'POST'])
def create_customer():
    if request.method == "GET":
        return render_template("create_customer.html")
    else:
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        email = request.form["email"]

        # Vérifier la longueur de firstname et lastname
        if not (2 <= len(firstname) <= 20) or not (2 <= len(lastname) <= 20):
            flash("First and last names should be between 2 and 20 characters.", "warning")
            return render_template("create_customer.html")

        # Vérifier le format de l'adresse e-mail
        if not is_valid_email(email):
            flash("Please enter a valid email address.", "warning")
            return render_template("create_customer.html")

        # Vérifier si l'email existe déjà dans le fichier customers.txt
        if check_existing_email(email):
            flash("Email already exists. Customer creation failed.", "error")
            return render_template("create_customer.html")

        # Vérifier si les champs ne sont pas vides
        if firstname and lastname and email:
            # Créer un nouveau compte avec les informations fournies
            Account(firstname, lastname, email)

            # Rediriger vers une page de confirmation ou afficher un message
            flash(f"Customer {firstname} {lastname} created successfully!", "success")
            return render_template("create_customer.html")
        else:
            flash("Please enter valid information for all fields!", "warning")
            return render_template("create_customer.html")
        
@app.route('/create_customer_form', methods=['GET'])
def create_customer_form():
    return render_template("create_customer.html")

def check_existing_email(email):
    with open('customers.txt', 'r') as file:
        for line in file:
            elements = line.strip().split()
            if elements :
                if elements[6] == email:
                    return True
    return False

@app.route('/delete_client', methods=['GET', 'POST'])
def delete_client():
    if request.method == 'GET':
        return render_template("delete.html")
    else:
        account_number = request.form['account_number']
        pin = request.form['pin']

        with open("customers.txt", "r") as file:
            lines = file.readlines()
            clients = [line.split() for line in lines]

        new_clients = []
        client_deleted = False

        for client in clients:
            if (
                len(client) >= 7 and
                client[3] == pin and
                client[2] == account_number and
                float(client[4]) == 0.0 and
                float(client[5]) == 0.0
            ):
                client_deleted = True
            else:
                new_clients.append(client)


        if client_deleted == True:
            with open("customers.txt", "w") as file:
                for c in new_clients:
                    file.write(' '.join(c) + '\n')
            flash("Client deleted successfully!")
            try:
                with open('login_details_customer.csv', 'r') as csv_file:
                    csv_reader = csv.reader(csv_file)
                    rows = list(csv_reader)
    
                with open('login_details_customer.csv', 'w', newline='') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    for row in rows:
                        if row[0] != account_number:
                            csv_writer.writerow(row)
            except Exception as e:
                flash(f"Error: {str(e)}")
            return render_template("delete.html")
        else :
            flash("Client not found, credentials don't match, or account isn't empty.")
            return render_template("delete.html")

    
    return render_template("delete.html", data=session)



def save_transaction(account_number, recipient_account, sending_account, amount, date):
    transaction = f"{account_number} {recipient_account} {sending_account} {amount} {date}"
    save_to_txt(transaction)
    
def save_to_txt(transaction):
    with open('transactions.txt', mode='a') as file:
        file.write(transaction+"\n")

def get_transactions_for_account(account_number):
    transactions = []
    with open("transactions.txt", 'r', encoding="utf-8-sig") as file:
        print("try0")
        lines=file.readlines()
        for line in lines:
            data=line.strip().split()
            print("try")
        
            if int(data[0]) == int(account_number):
                transactions.append({
                    "account_number": data[0],
                    "account_origin": data[2],
                    "account_beneficiary": data[1],
                    "amount": data[3],
                    "date": data[4]+' '+data[5]
                })
                print("done")
            else :
                print(account_number, data[0])
    return transactions

def sort_transactions_by_date(transactions):
    sorted_transactions = sorted(transactions, key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S'), reverse=True)
    return sorted_transactions

@app.route("/account_transactions/<account_number>", methods=["GET", "POST"])
def account_transactions(account_number):
    transactions = get_transactions_for_account(account_number)
    sorted_transactions = sort_transactions_by_date(transactions)
    return render_template("account_transactions.html", transactions=sorted_transactions)



@app.route('/')
def user_choice():
    if not os.path.isfile("customers.txt"):
        with open("customers.txt", "w") as file:
            file.write("")
    if not os.path.isfile("transactions.txt"):
        with open("transactions.txt", "w") as file:
            file.write("")
    return render_template('user_choice.html')       


if __name__ == "__main__":
    app.run(debug=True)

